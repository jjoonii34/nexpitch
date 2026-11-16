"""API-Football 응답 변환·저장·배치 테스트. 실제 API를 부르지 않고, 2026-11-16에 받은 응답 모양을 본뜬 예시로 검사한다."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analysis_collect import Budget, CollectReport, collect, fixtures_missing_data
from app.analysis_store import save_fixtures, save_lineups, save_player_stats, save_team_stats
from app.collectors.api_football import ApiFootballError, parse_fixtures, parse_lineups, parse_player_stats, parse_team_stats, to_float, to_int
from app.models.analysis import Fixture, Lineup, LineupPlayer, Player, PlayerMatchStats, RawResponse, Team, TeamMatchStats
from tests.conftest import make_club

FIXTURES = {
    "response": [
        {
            "fixture": {"id": 1208021, "date": "2024-08-16T19:00:00+00:00", "status": {"short": "FT"}, "referee": "R. Jones"},
            "league": {"id": 39, "season": 2024},
            "teams": {"home": {"id": 33, "name": "Manchester United"}, "away": {"id": 36, "name": "Fulham"}},
            "goals": {"home": 1, "away": 0},
        },
        {  # 다른 리그 → 걸러져야 한다
            "fixture": {"id": 999, "date": "2024-08-16T19:00:00+00:00", "status": {"short": "FT"}},
            "league": {"id": 40, "season": 2024},
            "teams": {"home": {"id": 1, "name": "A"}, "away": {"id": 2, "name": "B"}},
            "goals": {"home": 0, "away": 0},
        },
    ]
}
LINEUPS = {
    "response": [
        {
            "team": {"id": 33, "name": "Manchester United"},
            "formation": "4-2-3-1",
            "coach": {"name": "E. ten Hag"},
            "startXI": [{"player": {"id": 526, "name": "A. Onana", "number": 24, "pos": "G", "grid": "1:1"}}],
            "substitutes": [{"player": {"id": 889, "name": "Bench Guy", "number": 9, "pos": "F", "grid": None}}, {"player": {"id": None, "name": "No Id"}}],
        },
        {"team": {"id": 36, "name": "Fulham"}, "formation": "4-2-3-1", "coach": {"name": "Marco Silva"}, "startXI": [], "substitutes": []},
    ]
}
TEAM_STATS = {
    "response": [
        {"team": {"id": 33, "name": "Manchester United"}, "statistics": [{"type": "Total Shots", "value": 14}, {"type": "Ball Possession", "value": "55%"}, {"type": "expected_goals", "value": "2.43"}, {"type": "Red Cards", "value": None}]},
        {"team": {"id": 36, "name": "Fulham"}, "statistics": [{"type": "Total Shots", "value": 10}, {"type": "Ball Possession", "value": "45%"}, {"type": "expected_goals", "value": "0.44"}]},
    ]
}
PLAYER_STATS = {
    "response": [
        {
            "team": {"id": 33, "name": "Manchester United"},
            "players": [
                {"player": {"id": 526, "name": "André Onana"}, "statistics": [{"games": {"minutes": 90, "position": "G", "rating": "7.2", "substitute": False}, "shots": {"total": None}, "goals": {"total": None, "assists": None}, "passes": {"total": 23, "key": None}, "tackles": {"total": None}, "duels": {"won": 1}, "dribbles": {"success": None}, "cards": {"yellow": 0, "red": 0}}]},
                {"player": {"id": 889, "name": "Bench Guy"}, "statistics": [{"games": {"minutes": 12, "position": "F", "rating": "6.5", "substitute": True}, "goals": {"total": 1}}]},
            ],
        }
    ]
}


def test_to_int_and_to_float_handle_api_formats():
    assert (to_int("55%"), to_int(7), to_int(None), to_int("abc")) == (55, 7, None, None)
    assert (to_float("2.43"), to_float(None), to_float("x")) == (2.43, None, None)


def test_parse_fixtures_keeps_only_premier_league():
    rows = parse_fixtures(FIXTURES)
    assert len(rows) == 1
    f = rows[0]
    assert (f.id, f.season, f.status, f.home_team_name, f.home_goals, f.away_goals, f.referee) == (1208021, 2024, "FT", "Manchester United", 1, 0, "R. Jones")
    assert f.kickoff.isoformat() == "2024-08-16T19:00:00+00:00"


def test_parse_lineups_marks_starters_and_skips_missing_ids():
    rows = parse_lineups(LINEUPS)
    assert [r.team_name for r in rows] == ["Manchester United", "Fulham"]
    assert rows[0].formation == "4-2-3-1" and rows[0].coach == "E. ten Hag"
    assert [(p["player_id"], p["is_starter"]) for p in rows[0].players] == [(526, True), (889, False)]


def test_parse_team_and_player_stats():
    team = parse_team_stats(TEAM_STATS)
    assert team[0].stats["Ball Possession"] == "55%"
    players = parse_player_stats(PLAYER_STATS)
    assert [(p.player_id, p.team_id) for p in players] == [(526, 33), (889, 33)]


def test_save_fixtures_links_teams_to_clubs_and_updates_result(session):
    make_club(session, "Manchester United")
    assert save_fixtures(session, parse_fixtures(FIXTURES)) == 1
    utd, fulham = session.get(Team, 33), session.get(Team, 36)
    assert utd.club_id is not None and fulham.club_id is None  # Fulham은 테스트 DB에 구단이 없다
    # 같은 경기를 다시 받으면 새 경기 0, 결과만 갱신
    changed = {**FIXTURES, "response": [dict(FIXTURES["response"][0], goals={"home": 2, "away": 0})]}
    assert save_fixtures(session, parse_fixtures(changed)) == 0
    assert session.get(Fixture, 1208021).home_goals == 2


def test_save_lineups_stats_and_rerun_replaces(session):
    save_fixtures(session, parse_fixtures(FIXTURES))
    fixture = session.get(Fixture, 1208021)

    assert save_lineups(session, fixture, parse_lineups(LINEUPS)) == 2
    assert save_team_stats(session, fixture, parse_team_stats(TEAM_STATS)) == 2
    assert save_player_stats(session, fixture, parse_player_stats(PLAYER_STATS)) == 2
    assert fixture.lineups_at and fixture.team_stats_at and fixture.player_stats_at

    utd_stats = session.scalars(select(TeamMatchStats).where(TeamMatchStats.team_id == 33)).one()
    assert (utd_stats.shots_total, utd_stats.possession, utd_stats.xg, utd_stats.red_cards) == (14, 55, 2.43, None)
    onana = session.scalars(select(PlayerMatchStats).where(PlayerMatchStats.player_id == 526)).one()
    assert (onana.minutes, onana.rating, onana.is_starter, onana.passes_total, onana.goals) == (90, 7.2, True, 23, None)
    assert session.get(Player, 889).name == "Bench Guy"

    # 다시 저장해도 행이 늘지 않는다
    save_lineups(session, fixture, parse_lineups(LINEUPS))
    save_team_stats(session, fixture, parse_team_stats(TEAM_STATS))
    save_player_stats(session, fixture, parse_player_stats(PLAYER_STATS))
    assert session.scalar(select(func.count()).select_from(Lineup)) == 2
    assert session.scalar(select(func.count()).select_from(LineupPlayer)) == 2
    assert session.scalar(select(func.count()).select_from(TeamMatchStats)) == 2
    assert session.scalar(select(func.count()).select_from(PlayerMatchStats)) == 2
    assert fixtures_missing_data(session, 10) == []


class FakeClient:
    """엔드포인트별로 정해 둔 응답을 돌려주는 가짜. 호출 기록을 남긴다."""

    remaining_today = 50

    def __init__(self, fail_on: str | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.fail_on = fail_on

    def get(self, endpoint: str, **params) -> dict:
        self.calls.append((endpoint, params))
        if endpoint == self.fail_on:
            raise ApiFootballError("API-Football 오류: {'requests': 'You have reached the request limit'}")
        if endpoint == "fixtures":
            return FIXTURES if "season" in params and params["season"] == 2024 else {"response": []}
        return {"fixtures/lineups": LINEUPS, "fixtures/statistics": TEAM_STATS, "fixtures/players": PLAYER_STATS}[endpoint]


def test_collect_fetches_seasons_then_fills_missing_data(session):
    client = FakeClient()
    report = collect(session, client, Budget(calls=20, pause=0), today=date(2026, 11, 16))

    endpoints = [e for e, _ in client.calls]
    assert endpoints[:3] == ["fixtures", "fixtures", "fixtures"]  # 과거 시즌 3개
    assert endpoints[3:5] == ["fixtures", "fixtures"]  # 어제·오늘
    assert endpoints[5:] == ["fixtures/lineups", "fixtures/statistics", "fixtures/players"]
    assert (report.calls, report.new_fixtures, report.lineups, report.team_stats, report.player_stats) == (8, 1, 1, 1, 1)
    assert session.scalar(select(func.count()).select_from(RawResponse)) == 8  # 원본은 호출마다 남는다
    assert report.remaining_today == 50


def test_collect_second_run_only_checks_dates(session):
    client = FakeClient()
    collect(session, client, Budget(calls=20, pause=0), today=date(2026, 11, 16))
    client.calls.clear()
    report = collect(session, client, Budget(calls=20, pause=0), today=date(2026, 11, 16))
    assert [e for e, _ in client.calls] == ["fixtures", "fixtures"]  # 시즌 목록·경기 데이터는 이미 있음
    assert report.calls == 2


def test_collect_stops_on_rate_limit_and_respects_budget(session):
    limited = collect(session, FakeClient(fail_on="fixtures"), Budget(calls=20, pause=0), today=date(2026, 11, 16))
    assert limited.calls == 1 and len(limited.errors) == 1  # 첫 호출에서 한도 초과 → 멈춤

    small: CollectReport = collect(session, FakeClient(), Budget(calls=4, pause=0), today=date(2026, 11, 16))
    assert small.calls == 4  # 예산을 넘지 않는다
