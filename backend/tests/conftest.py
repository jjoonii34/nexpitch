"""모든 테스트가 같이 쓰는 재료. 메모리 안의 SQLite로 빈 DB를 만들고, 구단·기사를 짧게 만드는 도우미를 둔다."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.collectors.base import RawArticle
from app.db import create_tables
from app.models.news import Article, Club

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)  # 테스트용 고정 시각


@pytest.fixture
def session():
    """테스트마다 빈 DB를 새로 만든다 (테스트끼리 서로 영향을 주지 않게). 실제 DB(Neon)에는 접속하지 않는다."""
    engine = create_engine("sqlite://")
    create_tables(engine)
    with Session(engine) as s:
        yield s


def make_club(session: Session, name: str, tag: str | None = None) -> Club:
    """구단 하나를 저장하고 돌려준다. 태그를 안 주면 이름으로 만든다."""
    club = Club(name=name, guardian_tag=tag or f"football/{name.lower().replace(' ', '')}")
    session.add(club)
    session.commit()
    return club


def make_raw(url: str, title: str = "제목", author: str | None = "Andy Hunter") -> RawArticle:
    """수집기가 돌려주는 모양의 기사 하나."""
    return RawArticle(title=title, body_or_summary="요약", url=url, author=author, published_at=NOW, source="guardian")


def make_article(session: Session, url: str, title: str = "제목", published_at: datetime = NOW, **fields) -> Article:
    """DB에 기사 하나를 저장하고 돌려준다. collected_at 같은 추가 값은 fields로 넘긴다."""
    article = Article(url=url, title=title, body_or_summary="요약", author=None, published_at=published_at, source="guardian", **fields)
    session.add(article)
    session.commit()
    return article
