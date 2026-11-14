"""구단 목록을 data/clubs.csv에서 읽어 clubs 테이블에 맞춘다. 승격·강등 때는 csv만 고치고 다시 실행한다."""

import csv
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.news import Club

CLUBS_CSV = Path(__file__).resolve().parents[2] / "data" / "clubs.csv"  # nexpitch/data/clubs.csv


@dataclass
class SyncResult:
    """맞춘 결과. 실행할 때 무엇이 바뀌었는지 눈으로 확인하기 위해 센다."""

    added: int = 0  # 새로 등록한 구단
    updated: int = 0  # 태그가 바뀌었거나 다시 승격한 구단
    relegated: int = 0  # csv에서 빠져 '프리미어리그 아님'으로 바꾼 구단


def read_clubs(path: Path = CLUBS_CSV) -> list[tuple[str, str]]:
    """csv를 읽어 (구단 이름, 가디언 태그) 목록으로 돌려준다."""
    with path.open(encoding="utf-8", newline="") as f:
        return [(row["name"].strip(), row["guardian_tag"].strip()) for row in csv.DictReader(f)]


def sync_clubs(session: Session, rows: list[tuple[str, str]]) -> SyncResult:
    """clubs 테이블을 목록과 같게 맞춘다.

    목록에서 빠진 구단은 지우지 않고 in_premier_league만 False로 바꾼다
    — 지우면 그 구단에 연결된 과거 기사가 갈 곳을 잃기 때문.
    """
    result = SyncResult()
    existing = {club.name: club for club in session.scalars(select(Club))}

    for name, tag in rows:
        club = existing.get(name)
        if club is None:
            session.add(Club(name=name, guardian_tag=tag))
            result.added += 1
        elif club.guardian_tag != tag or not club.in_premier_league:
            club.guardian_tag = tag
            club.in_premier_league = True
            result.updated += 1

    names = {name for name, _ in rows}
    for name, club in existing.items():
        if name not in names and club.in_premier_league:
            club.in_premier_league = False
            result.relegated += 1

    session.commit()
    return result


if __name__ == "__main__":
    # 직접 실행하면 csv 내용을 DB에 반영한다: python -m app.clubs
    from app.db import get_engine

    with Session(get_engine()) as session:
        print(sync_clubs(session, read_clubs()))
        active = session.scalars(select(Club).where(Club.in_premier_league).order_by(Club.name)).all()
        print(f"프리미어리그 구단 {len(active)}개:", ", ".join(c.name for c in active))
