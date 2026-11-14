"""배치(구단별 수집 → 저장) 테스트. 가짜 수집기와 메모리 안의 SQLite를 써서 네트워크가 필요 없다."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.clubs import sync_clubs
from app.collect import collect_all
from app.collectors.base import RawArticle
from app.collectors.guardian import GuardianCollector
from app.db import create_tables
from app.models.news import Article, Club


@pytest.fixture
def session():
    """구단 3곳이 등록된 빈 DB. 헐 시티는 강등된 상태로 둔다."""
    engine = create_engine("sqlite://")
    create_tables(engine)
    with Session(engine) as s:
        sync_clubs(s, [("Arsenal", "football/arsenal"), ("Liverpool", "football/liverpool"), ("Hull City", "football/hullcity")])
        sync_clubs(s, [("Arsenal", "football/arsenal"), ("Liverpool", "football/liverpool")])
        yield s


class FakeCollector:
    """정해 둔 주소의 기사만 돌려주는 가짜 수집기. broken이면 실패한다."""

    source = "fake"

    def __init__(self, urls: list[str], broken: bool = False) -> None:
        self.urls = urls
        self.broken = broken

    def collect(self) -> list[RawArticle]:
        if self.broken:
            raise RuntimeError("가디언 API 응답 오류 (500)")
        when = datetime(2026, 11, 14, 9, 30, tzinfo=timezone.utc)
        return [RawArticle(title="t", body_or_summary="s", url=u, author=None, published_at=when, source="fake") for u in self.urls]


def test_collects_only_premier_league_clubs_and_shares_common_article(session):
    by_club = {"Arsenal": ["https://match", "https://ars"], "Liverpool": ["https://match", "https://liv"]}
    reports = collect_all(session, lambda club: FakeCollector(by_club[club.name]))

    assert [r.club for r in reports] == ["Arsenal", "Liverpool"]  # 강등된 헐 시티는 건너뛴다
    assert [(r.fetched, r.new_articles) for r in reports] == [(2, 2), (2, 1)]  # 경기 기사는 한 번만 저장
    assert session.scalar(select(func.count()).select_from(Article)) == 3


def test_one_failing_club_does_not_stop_the_rest(session):
    reports = collect_all(session, lambda club: FakeCollector(["https://liv"], broken=club.name == "Arsenal"))

    assert reports[0].error == "가디언 API 응답 오류 (500)"
    assert (reports[1].error, reports[1].new_articles) == (None, 1)
    liverpool = session.scalars(select(Club).where(Club.name == "Liverpool")).one()
    assert len(liverpool.articles) == 1


def test_raw_file_path_differs_per_club():
    day = date(2026, 11, 14)
    liverpool = GuardianCollector(tag="football/liverpool").raw_path(day)
    arsenal = GuardianCollector(tag="football/arsenal").raw_path(day)

    assert liverpool != arsenal
    assert liverpool.parts[-2:] == ("2026-11-14", "football-liverpool.json")
