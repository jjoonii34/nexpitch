"""분석 데이터 배치 (ADR 0007): 하루 호출 예산 안에서 '아직 없는 것'부터 받아 저장한다. 매일 1회 실행.

순서: (1) 시즌별 경기 목록이 없으면 받기 (시즌당 1회) (2) 오늘·어제 날짜의 경기 목록 (현재 시즌용, 2회)
(3) 끝난 경기 중 라인업·팀 스탯·선수 스탯이 빠진 것을 최신 시즌부터 채우기 (경기당 최대 3회).
"""

import time
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.analysis_store import save_fixtures, save_lineups, save_player_stats, save_raw, save_team_stats
from app.collectors.api_football import (
    PREMIER_LEAGUE_ID,
    ApiFootballClient,
    ApiFootballError,
    parse_fixtures,
    parse_lineups,
    parse_player_stats,
    parse_team_stats,
)
from app.models.analysis import Fixture, RawResponse

PAST_SEASONS = [2024, 2023, 2022]  # 무료 플랜이 시즌 지정 조회를 허용하는 시즌. 최신부터.
FINISHED = "FT"
SECONDS_BETWEEN_CALLS = 7  # 분당 10회 한도 → 6초면 되지만 여유를 둔다


@dataclass
class CollectReport:
    """한 번 실행의 결과. 배치 로그용."""

    calls: int = 0
    new_fixtures: int = 0
    lineups: int = 0  # 라인업을 채운 경기 수
    team_stats: int = 0
    player_stats: int = 0
    errors: list[str] = field(default_factory=list)
    remaining_today: int | None = None


class Budget:
    """하루 호출 예산. 호출마다 하나씩 줄고, 바닥나면 더 부르지 않는다."""

    def __init__(self, calls: int, pause: float = SECONDS_BETWEEN_CALLS) -> None:
        self.left = calls
        self.pause = pause
        self.used = 0

    def take(self) -> bool:
        if self.left <= 0:
            return False
        if self.used > 0 and self.pause:
            time.sleep(self.pause)
        self.left -= 1
        self.used += 1
        return True


def seasons_without_fixtures(session: Session) -> list[int]:
    """경기 목록을 아직 한 번도 받지 않은 과거 시즌. '받았는지'는 원본 응답(raw_responses)이 있는지로 본다 (빈 응답이어도 다시 묻지 않게)."""
    fetched = set()
    for season in PAST_SEASONS:
        marker = f'"season": {season}'
        exists = session.scalars(select(RawResponse.id).where(RawResponse.endpoint == "fixtures", RawResponse.params.like(f"%{marker}%")).limit(1)).first()
        if exists is not None:
            fetched.add(season)
    return [s for s in PAST_SEASONS if s not in fetched]


def fixtures_missing_data(session: Session, limit: int) -> list[Fixture]:
    """끝난 경기 중 라인업·팀 스탯·선수 스탯 하나라도 없는 것. 최신 시즌·최신 경기부터."""
    query = (
        select(Fixture)
        .where(Fixture.status == FINISHED, or_(Fixture.lineups_at.is_(None), Fixture.team_stats_at.is_(None), Fixture.player_stats_at.is_(None)))
        .order_by(Fixture.season.desc(), Fixture.kickoff.desc())
        .limit(limit)
    )
    return list(session.scalars(query))


def collect(session: Session, client: ApiFootballClient, budget: Budget, today: date | None = None) -> CollectReport:
    """예산 안에서 수집 → 저장. 한 호출이 실패해도 다음으로 넘어가되, 한도 초과(오류 문구에 'request' 또는 'limit')면 멈춘다."""
    report = CollectReport()
    today = today or date.today()

    def call(endpoint: str, **params) -> dict | None:
        if not budget.take():
            return None
        report.calls += 1
        try:
            data = client.get(endpoint, **params)
        except ApiFootballError as error:
            report.errors.append(f"{endpoint} {params}: {error}")
            if "limit" in str(error).lower() or "request" in str(error).lower():
                budget.left = 0  # 한도 초과 → 오늘은 그만
            return None
        save_raw(session, endpoint, params, data)
        report.remaining_today = client.remaining_today
        return data

    # (1) 과거 시즌 경기 목록
    for season in seasons_without_fixtures(session):
        data = call("fixtures", league=PREMIER_LEAGUE_ID, season=season)
        if data:
            report.new_fixtures += save_fixtures(session, parse_fixtures(data))

    # (2) 현재 시즌: 어제·오늘 경기 (무료 플랜은 3일 창 안의 날짜만 조회 가능)
    for day in (today - timedelta(days=1), today):
        data = call("fixtures", date=day.isoformat())
        if data:
            report.new_fixtures += save_fixtures(session, parse_fixtures(data))

    # (3) 빠진 데이터 채우기
    for fixture in fixtures_missing_data(session, limit=budget.left):
        if budget.left <= 0:
            break
        if fixture.lineups_at is None and (data := call("fixtures/lineups", fixture=fixture.id)):
            save_lineups(session, fixture, parse_lineups(data))
            report.lineups += 1
        if fixture.team_stats_at is None and (data := call("fixtures/statistics", fixture=fixture.id)):
            save_team_stats(session, fixture, parse_team_stats(data))
            report.team_stats += 1
        if fixture.player_stats_at is None and (data := call("fixtures/players", fixture=fixture.id)):
            save_player_stats(session, fixture, parse_player_stats(data))
            report.player_stats += 1

    session.commit()
    return report


def progress(session: Session) -> str:
    """시즌별로 '끝난 경기 중 셋 다 채운 경기 / 전체'를 한 줄로."""
    rows = session.execute(select(Fixture.season, Fixture.lineups_at.is_not(None) & Fixture.team_stats_at.is_not(None) & Fixture.player_stats_at.is_not(None)).where(Fixture.status == FINISHED)).all()
    done: dict[int, int] = {}
    total: dict[int, int] = {}
    for season, complete in rows:
        total[season] = total.get(season, 0) + 1
        done[season] = done.get(season, 0) + (1 if complete else 0)
    return " | ".join(f"{s}: {done[s]}/{total[s]}" for s in sorted(total, reverse=True)) or "경기 없음"


if __name__ == "__main__":
    # 직접 실행: python -m app.analysis_collect [호출 예산]   (기본 90)
    import sys

    from app.db import get_engine
    from app.settings import require_env

    calls = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    client = ApiFootballClient(require_env("API_FOOTBALL_KEY"))
    with Session(get_engine()) as session:
        r = collect(session, client, Budget(calls))
        print(f"호출 {r.calls} · 새 경기 {r.new_fixtures} · 라인업 {r.lineups} · 팀 스탯 {r.team_stats} · 선수 스탯 {r.player_stats} · 오류 {len(r.errors)} · 오늘 남은 호출 {r.remaining_today}")
        for e in r.errors[:5]:
            print("  -", e)
        print("진행:", progress(session))
