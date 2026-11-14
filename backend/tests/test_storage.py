"""기사 저장 테스트. 메모리 안의 SQLite를 써서 실제 DB(Neon)에 접속하지 않는다."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.collectors.base import RawArticle
from app.db import create_tables, to_sqlalchemy_url
from app.models.news import Article, Club, article_clubs
from app.storage import save_articles


@pytest.fixture
def session():
    """테스트마다 빈 DB를 새로 만든다 (테스트끼리 서로 영향을 주지 않게)."""
    engine = create_engine("sqlite://")
    create_tables(engine)
    with Session(engine) as s:
        yield s


def raw(url: str, title: str = "제목") -> RawArticle:
    """테스트용 기사 만들기."""
    return RawArticle(
        title=title,
        body_or_summary="요약",
        url=url,
        author="Andy Hunter",
        published_at=datetime(2026, 11, 14, 9, 30, tzinfo=timezone.utc),
        source="guardian",
    )


def club(session: Session, name: str) -> Club:
    """테스트용 구단 만들기."""
    c = Club(name=name, guardian_tag=f"football/{name.lower()}")
    session.add(c)
    session.commit()
    return c


def count(session: Session, table) -> int:
    return session.scalar(select(func.count()).select_from(table))


def test_create_tables_makes_three_tables():
    assert create_tables(create_engine("sqlite://")) == ["article_clubs", "articles", "clubs"]


def test_save_stores_articles_and_links_club(session):
    liverpool = club(session, "Liverpool")
    result = save_articles(session, [raw("https://a"), raw("https://b")], liverpool)

    assert (result.new_articles, result.new_links) == (2, 2)
    saved = session.scalars(select(Article).order_by(Article.url)).first()
    assert saved.author == "Andy Hunter"
    assert saved.clubs == [liverpool]
    assert saved.collected_at is not None


def test_saving_same_url_twice_keeps_one_article(session):
    liverpool = club(session, "Liverpool")
    save_articles(session, [raw("https://a")], liverpool)
    result = save_articles(session, [raw("https://a"), raw("https://b")], liverpool)

    assert (result.new_articles, result.new_links) == (1, 1)  # b만 새로 저장
    assert count(session, Article) == 2


def test_same_article_from_two_clubs_is_one_article_two_links(session):
    liverpool, arsenal = club(session, "Liverpool"), club(session, "Arsenal")
    save_articles(session, [raw("https://match-report")], liverpool)
    result = save_articles(session, [raw("https://match-report")], arsenal)

    assert (result.new_articles, result.new_links) == (0, 1)
    assert count(session, Article) == 1
    assert count(session, article_clubs) == 2


def test_duplicate_url_inside_one_batch_is_saved_once(session):
    liverpool = club(session, "Liverpool")
    result = save_articles(session, [raw("https://a"), raw("https://a")], liverpool)

    assert (result.new_articles, result.new_links) == (1, 1)


def test_neon_url_is_converted_for_psycopg():
    assert to_sqlalchemy_url("postgresql://u:p@host/db?sslmode=require") == "postgresql+psycopg://u:p@host/db?sslmode=require"
    assert to_sqlalchemy_url("sqlite://") == "sqlite://"
