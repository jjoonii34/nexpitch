"""경기 목록 → 학습용 표. 각 경기의 특성은 **그 경기 전까지의 정보만**으로 만든다 (정보 누출 금지).

입력은 DB 행이 아니라 평범한 dict 목록이라 DB 없이 테스트한다. 로딩은 load_matches()가 맡는다.
"""

from dataclasses import dataclass
from datetime import datetime

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.elo import EloTable
from app.collectors.api_football import to_int
from app.models.analysis import Fixture, Lineup, TeamMatchStats

FORM_WINDOW = 5  # 최근 몇 경기로 '흐름'을 재는가
OUTCOMES = ["H", "D", "A"]  # 홈 승 / 무 / 원정 승 — 모델이 맞히는 세 가지

FEATURE_COLUMNS = [
    "elo_diff",  # (a) 모델은 이것만 쓴다
    "form_diff",  # 최근 5경기 승점 차 (홈 − 원정)
    "goal_diff_form",  # 최근 5경기 득실 차의 차
    "rest_diff",  # 휴식일 차 (홈 − 원정)
    "xg_diff_form",  # 최근 5경기 xG 차의 차 (팀 스탯이 있을 때만, 없으면 NaN)
    "lineup_changes_diff",  # 직전 경기 대비 선발 변경 수의 차 (라인업이 있을 때만, 없으면 NaN)
]

# 전술 특성 (4.5단계 ②). 전부 '최근 5경기 평균의 홈 − 원정 차'이고, 팀 스탯·라인업을 받은 경기에서만 채워진다.
# 결과(승패)가 아니라 **어떻게 경기했는가**를 담는다: 공을 쥐는 팀인가, 좋은 위치에서 쏘는가, 기회를 만들고 막는가.
TACTICAL_COLUMNS = [
    "possession_diff",  # 평균 점유율(%) 차 — 점유형 vs 역습형
    "pass_volume_diff",  # 경기당 패스 수 차 — 짧게 이어가는 팀인가
    "pass_accuracy_diff",  # 패스 성공률(0~1) 차
    "box_shot_share_diff",  # 슈팅 중 박스 안 비율(0~1) 차 — 슈팅의 질 (멀리서 쏘는가, 파고드는가)
    "xg_for_diff",  # 경기당 만든 xG 차 — 공격이 만든 기회
    "xg_against_diff",  # 경기당 내준 xG 차 — 수비가 내준 기회 (낮을수록 좋다)
    "formation_change_diff",  # 직전 경기와 포메이션이 바뀌었는가(1/0)의 차
]


@dataclass(frozen=True)
class TeamStyle:
    """한 팀이 한 경기에서 '어떻게 했는가'의 재료. 빠진 값은 None."""

    possession: float | None = None  # %
    passes: float | None = None
    passes_accurate: float | None = None
    shots: float | None = None
    shots_in_box: float | None = None


@dataclass
class MatchRecord:
    """특성을 만들 때 필요한 경기 하나의 재료."""

    id: int
    season: int
    kickoff: datetime
    home_id: int
    away_id: int
    home_goals: int
    away_goals: int
    home_xg: float | None = None
    away_xg: float | None = None
    home_starters: frozenset[int] | None = None  # 선발 11명 선수 id
    away_starters: frozenset[int] | None = None
    home_style: TeamStyle | None = None  # 그 경기에서의 팀 스탯 (받은 경기만)
    away_style: TeamStyle | None = None
    home_formation: str | None = None  # 예: 4-2-3-1
    away_formation: str | None = None


def outcome(home_goals: int, away_goals: int) -> str:
    return "H" if home_goals > away_goals else "A" if home_goals < away_goals else "D"


def load_matches(session: Session) -> list[MatchRecord]:
    """DB에서 끝난 경기를 시간순으로 읽는다. xG·선발은 받은 경기만 채워진다."""
    fixtures = session.scalars(select(Fixture).where(Fixture.status == "FT", Fixture.home_goals.is_not(None)).order_by(Fixture.kickoff)).all()
    xg: dict[tuple[int, int], float | None] = {}
    style: dict[tuple[int, int], TeamStyle] = {}
    for s in session.scalars(select(TeamMatchStats)):
        xg[(s.fixture_id, s.team_id)] = s.xg
        style[(s.fixture_id, s.team_id)] = TeamStyle(s.possession, s.passes_total, s.passes_accurate, s.shots_total, to_int((s.stats_json or {}).get("Shots insidebox")))
    starters: dict[tuple[int, int], frozenset[int]] = {}
    formation: dict[tuple[int, int], str | None] = {}
    for lineup in session.scalars(select(Lineup)):
        starters[(lineup.fixture_id, lineup.team_id)] = frozenset(p.player_id for p in lineup.players if p.is_starter)
        formation[(lineup.fixture_id, lineup.team_id)] = lineup.formation
    return [
        MatchRecord(
            id=f.id, season=f.season, kickoff=f.kickoff, home_id=f.home_team_id, away_id=f.away_team_id,
            home_goals=f.home_goals, away_goals=f.away_goals,
            home_xg=xg.get((f.id, f.home_team_id)), away_xg=xg.get((f.id, f.away_team_id)),
            home_starters=starters.get((f.id, f.home_team_id)), away_starters=starters.get((f.id, f.away_team_id)),
            home_style=style.get((f.id, f.home_team_id)), away_style=style.get((f.id, f.away_team_id)),
            home_formation=formation.get((f.id, f.home_team_id)), away_formation=formation.get((f.id, f.away_team_id)),
        )
        for f in fixtures
    ]


class _TeamHistory:
    """한 팀의 지난 경기 기록 (특성 계산용)."""

    def __init__(self) -> None:
        self.points: list[int] = []
        self.goal_diff: list[int] = []
        self.xg_diff: list[float] = []
        self.last_kickoff: datetime | None = None
        self.last_starters: frozenset[int] | None = None
        self.styles: list[TeamStyle] = []
        self.xg_for: list[float] = []
        self.xg_against: list[float] = []
        self.last_formation: str | None = None

    def form(self, window: int = FORM_WINDOW) -> float | None:
        return sum(self.points[-window:]) if self.points else None

    def goal_form(self, window: int = FORM_WINDOW) -> float | None:
        return sum(self.goal_diff[-window:]) if self.goal_diff else None

    def xg_form(self, window: int = FORM_WINDOW) -> float | None:
        return sum(self.xg_diff[-window:]) if self.xg_diff else None

    def rest_days(self, kickoff: datetime) -> float | None:
        return (kickoff - self.last_kickoff).total_seconds() / 86400 if self.last_kickoff else None

    def lineup_changes(self, starters: frozenset[int] | None) -> float | None:
        if starters is None or self.last_starters is None:
            return None
        return float(len(starters - self.last_starters))


    def style_mean(self, field: str, window: int = FORM_WINDOW) -> float | None:
        """최근 경기들의 한 스탯 평균. 값이 있는 경기만 센다."""
        values = [getattr(s, field) for s in self.styles[-window:] if getattr(s, field) is not None]
        return sum(values) / len(values) if values else None

    def style_ratio(self, part: str, whole: str, window: int = FORM_WINDOW) -> float | None:
        """최근 경기들을 합쳐서 낸 비율 (예: 성공 패스 합 / 패스 합). 경기별 비율의 평균보다 슈팅이 적은 경기에 덜 흔들린다."""
        pairs = [(getattr(s, part), getattr(s, whole)) for s in self.styles[-window:] if getattr(s, part) is not None and getattr(s, whole)]
        return sum(a for a, _ in pairs) / sum(b for _, b in pairs) if pairs else None

    @staticmethod
    def recent_mean(values: list[float], window: int = FORM_WINDOW) -> float | None:
        return sum(values[-window:]) / len(values[-window:]) if values else None

    def formation_changed(self, formation: str | None) -> float | None:
        if formation is None or self.last_formation is None:
            return None
        return float(formation != self.last_formation)


def _diff(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a - b


def build_features(matches: list[MatchRecord]) -> pd.DataFrame:
    """시간순으로 돌며 경기마다 '그 전까지의 기록'으로 특성을 만들고, 그 다음에 결과를 기록에 반영한다.

    시즌 첫 경기처럼 기록이 없으면 특성은 NaN이다 (모델 쪽에서 채운다).
    """
    elo = EloTable()
    history: dict[int, _TeamHistory] = {}
    rows = []
    for m in sorted(matches, key=lambda x: x.kickoff):
        home, away = history.setdefault(m.home_id, _TeamHistory()), history.setdefault(m.away_id, _TeamHistory())
        rows.append(
            {
                "fixture_id": m.id,
                "season": m.season,
                "kickoff": m.kickoff,
                "outcome": outcome(m.home_goals, m.away_goals),
                "elo_diff": elo.pre_match_diff(m.home_id, m.away_id),
                "form_diff": _diff(home.form(), away.form()),
                "goal_diff_form": _diff(home.goal_form(), away.goal_form()),
                "rest_diff": _diff(home.rest_days(m.kickoff), away.rest_days(m.kickoff)),
                "xg_diff_form": _diff(home.xg_form(), away.xg_form()),
                "lineup_changes_diff": _diff(home.lineup_changes(m.home_starters), away.lineup_changes(m.away_starters)),
                "possession_diff": _diff(home.style_mean("possession"), away.style_mean("possession")),
                "pass_volume_diff": _diff(home.style_mean("passes"), away.style_mean("passes")),
                "pass_accuracy_diff": _diff(home.style_ratio("passes_accurate", "passes"), away.style_ratio("passes_accurate", "passes")),
                "box_shot_share_diff": _diff(home.style_ratio("shots_in_box", "shots"), away.style_ratio("shots_in_box", "shots")),
                "xg_for_diff": _diff(home.recent_mean(home.xg_for), away.recent_mean(away.xg_for)),
                "xg_against_diff": _diff(home.recent_mean(home.xg_against), away.recent_mean(away.xg_against)),
                # 오늘의 포메이션은 선발 명단과 함께 경기 전에 공개된다 → 누출이 아니다 (lineup_changes_diff와 같은 근거)
                "formation_change_diff": _diff(home.formation_changed(m.home_formation), away.formation_changed(m.away_formation)),
            }
        )
        # 결과 반영은 특성을 만든 **뒤** — 이 순서가 정보 누출을 막는다
        elo.update(m.home_id, m.away_id, m.home_goals, m.away_goals)
        sides = (
            (home, m.home_goals, m.away_goals, m.home_xg, m.away_xg, m.home_starters, m.home_style, m.home_formation),
            (away, m.away_goals, m.home_goals, m.away_xg, m.home_xg, m.away_starters, m.away_style, m.away_formation),
        )
        for team, gf, ga, xf, xa, starters, style, formation in sides:
            team.points.append(3 if gf > ga else 1 if gf == ga else 0)
            team.goal_diff.append(gf - ga)
            if xf is not None and xa is not None:
                team.xg_diff.append(xf - xa)
                team.xg_for.append(xf)
                team.xg_against.append(xa)
            if style is not None:
                team.styles.append(style)
            if formation is not None:
                team.last_formation = formation
            team.last_kickoff = m.kickoff
            if starters is not None:
                team.last_starters = starters
    return pd.DataFrame(rows)
