"""API-Football 수집기 (ADR 0007). 네트워크는 ApiFootballClient.get 한 곳, 나머지는 응답(dict) → 우리 모양으로 바꾸는 순수 함수다.

무료 플랜: 하루 100회·분당 10회 (응답 헤더 x-ratelimit-requests-remaining 으로 확인). 2022~2024 시즌은 시즌 지정 조회 가능,
현재 시즌은 어제~내일 날짜 조회만 된다 (2026-11-14, 11-16 직접 확인).
"""

from dataclasses import dataclass, field
from datetime import datetime

import httpx

API_URL = "https://v3.football.api-sports.io"
PREMIER_LEAGUE_ID = 39
SOURCE = "api-football"


class ApiFootballError(RuntimeError):
    """API가 200을 돌려주면서 errors 칸에 오류를 담아 보낼 때 (한도 초과, 잘못된 인자 등)."""


class ApiFootballClient:
    """키를 헤더로 보내 호출한다. 돌려주는 값은 응답 JSON(dict) 그대로이고, 원본 저장은 호출한 쪽이 한다."""

    def __init__(self, key: str, timeout: float = 20) -> None:
        self._key = key
        self.timeout = timeout
        self.remaining_today: int | None = None  # 마지막 응답 헤더의 '오늘 남은 호출 수'

    def get(self, endpoint: str, **params) -> dict:
        """예: get("fixtures/lineups", fixture=1208021). 실패하면 ApiFootballError."""
        response = httpx.get(f"{API_URL}/{endpoint}", params=params, headers={"x-apisports-key": self._key}, timeout=self.timeout)
        if response.status_code != 200:
            raise ApiFootballError(f"API-Football 응답 오류 ({response.status_code})")
        remaining = response.headers.get("x-ratelimit-requests-remaining")
        self.remaining_today = int(remaining) if remaining and remaining.isdigit() else None
        data = response.json()
        errors = data.get("errors")
        if errors:  # 비어 있지 않은 dict/list → 실패
            raise ApiFootballError(f"API-Football 오류: {errors}")
        return data


# ── 순수 변환 함수들: 응답 dict → 평평한 dataclass ──


@dataclass
class FixtureRow:
    id: int
    season: int
    kickoff: datetime
    status: str
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str
    home_goals: int | None
    away_goals: int | None
    referee: str | None


@dataclass
class LineupRow:
    team_id: int
    team_name: str
    formation: str | None
    coach: str | None
    players: list[dict] = field(default_factory=list)  # {player_id, name, number, position, grid, is_starter}


@dataclass
class TeamStatsRow:
    team_id: int
    team_name: str
    stats: dict  # API의 type → value (예: "Ball Possession" → "55%")


@dataclass
class PlayerStatsRow:
    team_id: int
    player_id: int
    player_name: str
    stats: dict  # API의 statistics[0] 전체 (games, shots, passes, …)


def parse_kickoff(value: str) -> datetime:
    """'2024-08-16T19:00:00+00:00' → 시간대가 붙은 datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_fixtures(response: dict) -> list[FixtureRow]:
    """fixtures 응답 → 경기 목록. 프리미어리그가 아닌 경기(날짜 조회 때 섞여 옴)는 뺀다."""
    rows: list[FixtureRow] = []
    for item in response.get("response", []):
        if item.get("league", {}).get("id") != PREMIER_LEAGUE_ID:
            continue
        fx, teams, goals = item["fixture"], item["teams"], item.get("goals", {})
        rows.append(
            FixtureRow(
                id=fx["id"],
                season=item["league"]["season"],
                kickoff=parse_kickoff(fx["date"]),
                status=fx.get("status", {}).get("short", ""),
                home_team_id=teams["home"]["id"],
                home_team_name=teams["home"]["name"],
                away_team_id=teams["away"]["id"],
                away_team_name=teams["away"]["name"],
                home_goals=goals.get("home"),
                away_goals=goals.get("away"),
                referee=fx.get("referee"),
            )
        )
    return rows


def parse_lineups(response: dict) -> list[LineupRow]:
    """fixtures/lineups 응답 → 팀별 라인업 (선발 + 벤치)."""
    rows: list[LineupRow] = []
    for item in response.get("response", []):
        row = LineupRow(
            team_id=item["team"]["id"],
            team_name=item["team"]["name"],
            formation=item.get("formation"),
            coach=(item.get("coach") or {}).get("name"),
        )
        for group, is_starter in ((item.get("startXI") or [], True), (item.get("substitutes") or [], False)):
            for entry in group:
                p = entry.get("player") or {}
                if p.get("id") is None:
                    continue  # 가끔 선수 id가 비어 오는 벤치 항목은 건너뛴다
                row.players.append(
                    {"player_id": p["id"], "name": p.get("name") or "", "number": p.get("number"), "position": p.get("pos"), "grid": p.get("grid"), "is_starter": is_starter}
                )
        rows.append(row)
    return rows


def parse_team_stats(response: dict) -> list[TeamStatsRow]:
    """fixtures/statistics 응답 → 팀별 (type → value) 사전."""
    return [
        TeamStatsRow(team_id=item["team"]["id"], team_name=item["team"]["name"], stats={s["type"]: s["value"] for s in item.get("statistics", [])})
        for item in response.get("response", [])
    ]


def parse_player_stats(response: dict) -> list[PlayerStatsRow]:
    """fixtures/players 응답 → 선수별 스탯. 양 팀 선수가 한 목록으로 나온다."""
    rows: list[PlayerStatsRow] = []
    for team_block in response.get("response", []):
        team_id = team_block["team"]["id"]
        for entry in team_block.get("players", []):
            stats_list = entry.get("statistics") or []
            if not stats_list or entry.get("player", {}).get("id") is None:
                continue
            rows.append(PlayerStatsRow(team_id=team_id, player_id=entry["player"]["id"], player_name=entry["player"].get("name") or "", stats=stats_list[0]))
    return rows


# ── 값 다듬기: API는 "55%", "2.43", None 처럼 섞어서 준다 ──


def to_int(value) -> int | None:
    """'55%' → 55, 7 → 7, None/'' → None."""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = value.strip().rstrip("%")
        if not value.lstrip("-").isdigit():
            return None
    return int(value)


def to_float(value) -> float | None:
    """'2.43' → 2.43, None/'' → None. 숫자가 아니면 None."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
