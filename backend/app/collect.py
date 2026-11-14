"""배치의 본체: 프리미어리그 구단마다 기사를 수집해 DB에 저장한다. 하루 2회 실행할 예정."""

import time
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import Collector
from app.models.news import Club
from app.storage import SaveResult, save_articles


@dataclass
class ClubReport:
    """구단 하나의 수집 결과. 배치가 끝난 뒤 무엇이 들어왔는지 한눈에 보기 위해 남긴다."""

    club: str
    fetched: int = 0  # 받아 온 기사 수
    new_articles: int = 0  # 그중 처음 저장한 기사 수
    error: str | None = None  # 실패했다면 그 이유


def collect_all(
    session: Session,
    collector_for: Callable[[Club], Collector],
    pause_seconds: float = 0,
) -> list[ClubReport]:
    """프리미어리그 구단을 하나씩 돌며 수집 → 저장한다.

    한 구단이 실패해도 멈추지 않고 다음 구단으로 넘어간다 (한 곳의 오류로 19곳을 잃지 않게).
    pause_seconds는 구단 사이에 쉬는 시간 — 외부 API를 연달아 두드리지 않기 위해.
    """
    reports: list[ClubReport] = []
    clubs = session.scalars(select(Club).where(Club.in_premier_league).order_by(Club.name)).all()

    for club in clubs:
        report = ClubReport(club=club.name)
        try:
            raws = collector_for(club).collect()
            saved: SaveResult = save_articles(session, raws, club)
            report.fetched = len(raws)
            report.new_articles = saved.new_articles
        except Exception as error:  # 어떤 오류든 기록만 하고 다음 구단으로
            session.rollback()
            report.error = str(error)
        reports.append(report)
        time.sleep(pause_seconds)

    return reports


if __name__ == "__main__":
    # 직접 실행: python -m app.collect
    from app.collectors.guardian import GuardianCollector
    from app.db import get_engine

    with Session(get_engine()) as session:
        reports = collect_all(session, lambda club: GuardianCollector(tag=club.guardian_tag), pause_seconds=1)

    for r in reports:
        print(f"{r.club:<18} " + (f"실패: {r.error}" if r.error else f"받음 {r.fetched:>2} · 새 기사 {r.new_articles:>2}"))
    print(f"합계: 받음 {sum(r.fetched for r in reports)} · 새 기사 {sum(r.new_articles for r in reports)} · 실패 {sum(1 for r in reports if r.error)}")
