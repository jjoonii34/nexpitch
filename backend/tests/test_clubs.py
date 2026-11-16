"""구단 목록 맞추기 테스트. 메모리 안의 SQLite를 쓴다."""

from sqlalchemy import select

from app.clubs import read_clubs, sync_clubs
from app.models.news import Club


def test_clubs_csv_has_20_unique_clubs():
    rows = read_clubs()
    assert len(rows) == 20
    assert len({name for name, _ in rows}) == 20
    assert len({tag for _, tag in rows}) == 20
    assert all(tag.startswith("football/") for _, tag in rows)


def test_sync_adds_clubs_and_second_run_changes_nothing(session):
    rows = [("Liverpool", "football/liverpool"), ("Arsenal", "football/arsenal")]
    first = sync_clubs(session, rows)
    second = sync_clubs(session, rows)

    assert (first.added, first.updated, first.relegated) == (2, 0, 0)
    assert (second.added, second.updated, second.relegated) == (0, 0, 0)
    assert len(session.scalars(select(Club)).all()) == 2


def test_club_missing_from_list_is_marked_not_deleted(session):
    sync_clubs(session, [("Liverpool", "football/liverpool"), ("Hull City", "football/hullcity")])
    result = sync_clubs(session, [("Liverpool", "football/liverpool")])

    hull = session.scalars(select(Club).where(Club.name == "Hull City")).one()
    assert result.relegated == 1
    assert hull.in_premier_league is False  # 지우지 않고 표시만 바꾼다


def test_returning_club_and_changed_tag_are_updated(session):
    sync_clubs(session, [("Hull City", "football/hullcity")])
    sync_clubs(session, [])  # 강등
    result = sync_clubs(session, [("Hull City", "football/hull")])  # 다시 승격 + 태그 변경

    hull = session.scalars(select(Club)).one()
    assert result.updated == 1
    assert (hull.guardian_tag, hull.in_premier_league) == ("football/hull", True)
