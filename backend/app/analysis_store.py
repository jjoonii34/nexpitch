"""API-Football에서 받은 것을 분석 테이블에 넣는다. 같은 경기를 다시 받으면 덮어쓴다 (id가 API id라 같은 행을 찾는다)."""

import json
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.collectors.api_football import (
    SOURCE,
    FixtureRow,
    LineupRow,
    PlayerStatsRow,
    TeamStatsRow,
    to_float,
    to_int,
)
from app.models.analysis import Fixture, Lineup, LineupPlayer, Player, PlayerMatchStats, RawResponse, Team, TeamMatchStats
from app.models.news import Club, utc_now

# API-Football 팀 이름 → data/clubs.csv 이름. 같으면 적지 않는다.
TEAM_NAME_ALIASES = {
    "Newcastle": "Newcastle United",
    "Leeds": "Leeds United",
    "Ipswich": "Ipswich Town",
    "Coventry": "Coventry City",
    "Nottingham Forest": "Nottingham Forest",
    "Manchester United": "Manchester United",
    "Manchester City": "Manchester City",
    "Tottenham": "Tottenham",
    "Brighton": "Brighton",
    "Hull": "Hull City",
    "Wolves": "Wolverhampton Wanderers",
    "West Ham": "West Ham United",
    "Sheffield Utd": "Sheffield United",
    "Luton": "Luton Town",
    "Leicester": "Leicester City",
}


def save_raw(session: Session, endpoint: str, params: dict, payload: dict) -> None:
    """원본 응답을 그대로 남긴다 (4-1 규칙: 재실행 시 재호출 대신 파싱만 다시)."""
    session.add(RawResponse(source=SOURCE, endpoint=endpoint, params=json.dumps(params, sort_keys=True), payload=payload))


def ensure_team(session: Session, team_id: int, name: str, known: dict[int, Team] | None = None) -> Team:
    """팀이 없으면 만들고, 이름이 우리 구단 목록과 맞으면 club_id를 잇는다. known은 미리 읽어 둔 {id: Team} (왕복 절약)."""
    team = known.get(team_id) if known is not None else session.get(Team, team_id)
    if team is None:
        club_name = TEAM_NAME_ALIASES.get(name, name)
        club = session.scalars(select(Club).where(Club.name == club_name)).first()
        team = Team(id=team_id, name=name, club_id=club.id if club else None)
        session.add(team)
        if known is not None:
            known[team_id] = team
    return team


def ensure_player(session: Session, player_id: int, name: str, known: dict[int, Player] | None = None) -> Player:
    """선수가 없으면 만든다. known은 미리 읽어 둔 {id: Player} (왕복 절약)."""
    player = known.get(player_id) if known is not None else session.get(Player, player_id)
    if player is None:
        player = Player(id=player_id, name=name)
        session.add(player)
        if known is not None:
            known[player_id] = player
    return player


def preload(session: Session, model, ids: set[int]) -> dict:
    """id 목록에 해당하는 행을 한 번의 질의로 읽어 {id: 행}으로 돌려준다."""
    if not ids:
        return {}
    return {row.id: row for row in session.scalars(select(model).where(model.id.in_(ids)))}


def save_fixtures(session: Session, rows: list[FixtureRow]) -> int:
    """경기 목록을 넣거나 갱신한다(결과·상태가 바뀔 수 있다). 새로 들어온 경기 수를 돌려준다."""
    new = 0
    teams = preload(session, Team, {r.home_team_id for r in rows} | {r.away_team_id for r in rows})
    fixtures = preload(session, Fixture, {r.id for r in rows})
    with session.no_autoflush:  # 행마다 flush하지 않고 마지막에 한 번
        for r in rows:
            ensure_team(session, r.home_team_id, r.home_team_name, teams)
            ensure_team(session, r.away_team_id, r.away_team_name, teams)
            fixture = fixtures.get(r.id)
            if fixture is None:
                fixture = Fixture(id=r.id, season=r.season, home_team_id=r.home_team_id, away_team_id=r.away_team_id, kickoff=r.kickoff, status=r.status)
                session.add(fixture)
                fixtures[r.id] = fixture
                new += 1
            fixture.kickoff, fixture.status = r.kickoff, r.status
            fixture.home_goals, fixture.away_goals, fixture.referee = r.home_goals, r.away_goals, r.referee
    session.commit()
    return new


def save_lineups(session: Session, fixture: Fixture, rows: list[LineupRow], at: datetime | None = None) -> int:
    """한 경기의 라인업을 저장한다(이미 있으면 지우고 다시). 저장한 선수 수를 돌려준다."""
    saved = 0
    players = preload(session, Player, {p["player_id"] for r in rows for p in r.players})
    for r in rows:
        ensure_team(session, r.team_id, r.team_name)
        old = session.scalars(select(Lineup).where(Lineup.fixture_id == fixture.id, Lineup.team_id == r.team_id)).first()
        if old is not None:
            session.delete(old)
            session.flush()
        lineup = Lineup(fixture_id=fixture.id, team_id=r.team_id, formation=r.formation, coach=r.coach)
        for p in r.players:
            ensure_player(session, p["player_id"], p["name"], players)
            lineup.players.append(LineupPlayer(player_id=p["player_id"], number=p["number"], position=p["position"], grid=p["grid"], is_starter=p["is_starter"]))
            saved += 1
        session.add(lineup)
    fixture.lineups_at = at or utc_now()
    session.commit()
    return saved


def save_team_stats(session: Session, fixture: Fixture, rows: list[TeamStatsRow], at: datetime | None = None) -> int:
    """한 경기의 팀 스탯 두 줄을 저장한다 (이미 있으면 교체)."""
    session.execute(delete(TeamMatchStats).where(TeamMatchStats.fixture_id == fixture.id))
    for r in rows:
        ensure_team(session, r.team_id, r.team_name)
        s = r.stats
        session.add(
            TeamMatchStats(
                fixture_id=fixture.id,
                team_id=r.team_id,
                shots_total=to_int(s.get("Total Shots")),
                shots_on=to_int(s.get("Shots on Goal")),
                possession=to_int(s.get("Ball Possession")),
                passes_total=to_int(s.get("Total passes")),
                passes_accurate=to_int(s.get("Passes accurate")),
                corners=to_int(s.get("Corner Kicks")),
                fouls=to_int(s.get("Fouls")),
                yellow_cards=to_int(s.get("Yellow Cards")),
                red_cards=to_int(s.get("Red Cards")),
                xg=to_float(s.get("expected_goals")),
                stats_json=s,
            )
        )
    fixture.team_stats_at = at or utc_now()
    session.commit()
    return len(rows)


def save_player_stats(session: Session, fixture: Fixture, rows: list[PlayerStatsRow], at: datetime | None = None) -> int:
    """한 경기의 선수 스탯(양 팀)을 저장한다 (이미 있으면 교체)."""
    session.execute(delete(PlayerMatchStats).where(PlayerMatchStats.fixture_id == fixture.id))
    players = preload(session, Player, {r.player_id for r in rows})
    for r in rows:
        ensure_player(session, r.player_id, r.player_name, players)
        s = r.stats
        games, shots, goals, passes = s.get("games") or {}, s.get("shots") or {}, s.get("goals") or {}, s.get("passes") or {}
        tackles, duels, dribbles, cards = s.get("tackles") or {}, s.get("duels") or {}, s.get("dribbles") or {}, s.get("cards") or {}
        session.add(
            PlayerMatchStats(
                fixture_id=fixture.id,
                team_id=r.team_id,
                player_id=r.player_id,
                minutes=to_int(games.get("minutes")),
                is_starter=(not games["substitute"]) if games.get("substitute") is not None else None,
                position=games.get("position"),
                rating=to_float(games.get("rating")),
                goals=to_int(goals.get("total")),
                assists=to_int(goals.get("assists")),
                shots_total=to_int(shots.get("total")),
                passes_total=to_int(passes.get("total")),
                key_passes=to_int(passes.get("key")),
                tackles=to_int(tackles.get("total")),
                duels_won=to_int(duels.get("won")),
                dribbles_success=to_int(dribbles.get("success")),
                yellow_cards=to_int(cards.get("yellow")),
                red_cards=to_int(cards.get("red")),
                stats_json=s,
            )
        )
    fixture.player_stats_at = at or utc_now()
    session.commit()
    return len(rows)
