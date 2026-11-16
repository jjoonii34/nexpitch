"""기사 저장 테스트. 메모리 안의 SQLite를 써서 실제 DB(Neon)에 접속하지 않는다."""

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db import create_tables, to_sqlalchemy_url
from app.models.news import Article, article_clubs
from app.storage import save_articles
from tests.conftest import make_club as club
from tests.conftest import make_raw as raw


def count(session: Session, table) -> int:
    return session.scalar(select(func.count()).select_from(table))


def test_create_tables_makes_all_tables():
    assert create_tables(create_engine("sqlite://")) == ["article_clubs", "article_translations", "articles", "clubs"]


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
