"""경기 분석용 테이블 (ADR 0007). API-Football에서 받은 경기·라인업·스탯을 정규화해 쌓는다.

id는 API-Football의 id를 그대로 쓴다 (다시 받을 때 같은 행을 찾기 위해). 원본 응답은 raw_responses에 JSON으로 남긴다.
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.news import Base, Club, utc_now

# SQLite(테스트)에서는 JSON, PostgreSQL(Neon)에서는 JSONB로 저장된다.
JsonColumn = JSON().with_variant(JSONB(), "postgresql")


class RawResponse(Base):
    """API 원본 응답 한 건. Actions 컴퓨터는 매번 새것이라 파일 대신 DB에 둔다 → 호출을 다시 하지 않고 파싱만 다시 할 수 있다."""

    __tablename__ = "raw_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(30))  # 예: api-football
    endpoint: Mapped[str] = mapped_column(String(60))  # 예: fixtures/lineups
    params: Mapped[str] = mapped_column(String(200))  # 예: fixture=1208021
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    payload: Mapped[dict] = mapped_column(JsonColumn)


class Team(Base):
    """API-Football의 팀. 우리 clubs와는 club_id로 잇는다 (과거 시즌의 강등 팀은 club_id가 비어 있을 수 있다)."""

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)  # API-Football team id
    name: Mapped[str] = mapped_column(String(100))
    club_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id"))

    club: Mapped[Club | None] = relationship()


class Player(Base):
    """선수. 이름만 둔다 (이미지는 약관상 쓰지 않는다)."""

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)  # API-Football player id
    name: Mapped[str] = mapped_column(String(100))


class Fixture(Base):
    """경기 한 건과 결과. *_at 열은 그 데이터를 언제 받았는지(비어 있으면 아직 안 받음) → 배치가 '아직 없는 것'을 고르는 기준."""

    __tablename__ = "fixtures"

    id: Mapped[int] = mapped_column(primary_key=True)  # API-Football fixture id
    season: Mapped[int] = mapped_column(Integer)  # 예: 2024 (= 2024-25 시즌)
    kickoff: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(10))  # API의 짧은 상태 (FT, NS, PST …)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    home_goals: Mapped[int | None] = mapped_column(Integer)
    away_goals: Mapped[int | None] = mapped_column(Integer)
    referee: Mapped[str | None] = mapped_column(String(100))
    lineups_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    team_stats_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    player_stats_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    home_team: Mapped[Team] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped[Team] = relationship(foreign_keys=[away_team_id])


class Lineup(Base):
    """한 경기에서 한 팀의 라인업 (포메이션·감독). 선수 명단은 lineup_players."""

    __tablename__ = "lineups"
    __table_args__ = (UniqueConstraint("fixture_id", "team_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    formation: Mapped[str | None] = mapped_column(String(20))  # 예: 4-2-3-1
    coach: Mapped[str | None] = mapped_column(String(100))

    players: Mapped[list["LineupPlayer"]] = relationship(back_populates="lineup", cascade="all, delete-orphan")


class LineupPlayer(Base):
    """라인업의 선수 한 명. 선발이면 is_starter=True, 벤치면 False."""

    __tablename__ = "lineup_players"

    id: Mapped[int] = mapped_column(primary_key=True)
    lineup_id: Mapped[int] = mapped_column(ForeignKey("lineups.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    number: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[str | None] = mapped_column(String(5))  # G/D/M/F
    grid: Mapped[str | None] = mapped_column(String(10))  # 예: "1:1" (선발만)
    is_starter: Mapped[bool] = mapped_column(Boolean)

    lineup: Mapped[Lineup] = relationship(back_populates="players")


class TeamMatchStats(Base):
    """한 경기에서 한 팀의 스탯. 자주 쓰는 값은 열로, 나머지 전부는 stats_json에."""

    __tablename__ = "team_match_stats"
    __table_args__ = (UniqueConstraint("fixture_id", "team_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    shots_total: Mapped[int | None] = mapped_column(Integer)
    shots_on: Mapped[int | None] = mapped_column(Integer)
    possession: Mapped[int | None] = mapped_column(Integer)  # %
    passes_total: Mapped[int | None] = mapped_column(Integer)
    passes_accurate: Mapped[int | None] = mapped_column(Integer)
    corners: Mapped[int | None] = mapped_column(Integer)
    fouls: Mapped[int | None] = mapped_column(Integer)
    yellow_cards: Mapped[int | None] = mapped_column(Integer)
    red_cards: Mapped[int | None] = mapped_column(Integer)
    xg: Mapped[float | None] = mapped_column(Float)  # expected_goals
    stats_json: Mapped[dict] = mapped_column(JsonColumn)  # API의 (type → value) 전부


class PlayerMatchStats(Base):
    """한 경기에서 선수 한 명의 스탯. 자주 쓰는 값은 열로, 나머지 전부는 stats_json에."""

    __tablename__ = "player_match_stats"
    __table_args__ = (UniqueConstraint("fixture_id", "player_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    minutes: Mapped[int | None] = mapped_column(Integer)
    is_starter: Mapped[bool | None] = mapped_column(Boolean)
    position: Mapped[str | None] = mapped_column(String(5))
    rating: Mapped[float | None] = mapped_column(Float)
    goals: Mapped[int | None] = mapped_column(Integer)
    assists: Mapped[int | None] = mapped_column(Integer)
    shots_total: Mapped[int | None] = mapped_column(Integer)
    passes_total: Mapped[int | None] = mapped_column(Integer)
    key_passes: Mapped[int | None] = mapped_column(Integer)
    tackles: Mapped[int | None] = mapped_column(Integer)
    duels_won: Mapped[int | None] = mapped_column(Integer)
    dribbles_success: Mapped[int | None] = mapped_column(Integer)
    yellow_cards: Mapped[int | None] = mapped_column(Integer)
    red_cards: Mapped[int | None] = mapped_column(Integer)
    stats_json: Mapped[dict] = mapped_column(JsonColumn)
