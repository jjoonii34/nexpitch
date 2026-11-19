"""선수별 경기 기록 → 임베딩 모델의 입력 (ADR 0014). 정제 규칙을 한곳에 모은다.

만드는 것: 경기마다 양 팀 선발 11명 각각의 '경기 전 프로필 벡터'. 프로필은 **그 경기 전까지의 기록만**으로 만든다 (정보 누출 금지).

정제 규칙 (API-Football 원본의 버릇에 맞춘 것 — 2026-11-19 DB에서 확인):
- minutes가 비었거나 0인 줄은 '출전하지 않음'이다 → 프로필에 넣지 않는다.
- 출전했는데 goals·shots 등이 비어 있으면 '0개'라는 뜻이다 (API는 0을 None으로 보낸다. goals는 6%만 채워져 있다) → 0으로 바꾼다.
- rating(평점)은 비면 정말 없는 것이다 → 0으로 바꾸지 않고, 평점이 있는 출전 시간만으로 평균을 낸다.
- 횟수 스탯은 출전 시간이 다른 선수를 비교할 수 있게 90분당 값으로 바꾼다.

입력은 DB 행이 아니라 평범한 dataclass 목록이라 DB 없이 테스트한다. 로딩은 load_player_lines()가 맡는다.
"""

import math
from dataclasses import dataclass, field

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.dataset import OUTCOMES, MatchRecord, outcome
from app.models.analysis import PlayerMatchStats

COUNT_STATS = ["goals", "assists", "shots", "passes", "key_passes", "tackles", "duels_won", "dribbles"]  # 90분당 값으로 바꾸는 스탯
POSITIONS = ["G", "D", "M", "F"]  # API 표기: 골키퍼·수비·미드필더·공격
FEATURE_NAMES = [f"{s}_per90" for s in COUNT_STATS] + ["rating", "log_minutes"] + [f"pos_{p}" for p in POSITIONS] + ["has_history"]
N_CONTINUOUS = len(COUNT_STATS) + 2  # 앞의 이만큼만 표준화한다 (포지션·기록 유무는 0/1 그대로)
SQUAD = 11
DEFAULT_RATING = 6.5  # 평점이 한 번도 없던 선수에게 주는 값 (평점 척도의 대략 가운데 — 확인 필요: 데이터의 평균으로 바꿀 것)


@dataclass
class PlayerLine:
    """한 선수가 한 경기에서 남긴 기록 (원본 그대로, 빈 값은 None)."""

    fixture_id: int
    team_id: int
    player_id: int
    minutes: int | None = None
    position: str | None = None
    rating: float | None = None
    goals: int | None = None
    assists: int | None = None
    shots: int | None = None
    passes: int | None = None
    key_passes: int | None = None
    tackles: int | None = None
    duels_won: int | None = None
    dribbles: int | None = None


def load_player_lines(session: Session) -> list[PlayerLine]:
    """DB의 선수별 경기 기록을 읽는다."""
    return [
        PlayerLine(
            fixture_id=p.fixture_id, team_id=p.team_id, player_id=p.player_id, minutes=p.minutes, position=p.position, rating=p.rating,
            goals=p.goals, assists=p.assists, shots=p.shots_total, passes=p.passes_total, key_passes=p.key_passes,
            tackles=p.tackles, duels_won=p.duels_won, dribbles=p.dribbles_success,
        )
        for p in session.scalars(select(PlayerMatchStats))
    ]


def played(line: PlayerLine) -> bool:
    """실제로 뛴 기록인가."""
    return bool(line.minutes and line.minutes > 0)


@dataclass
class PlayerProfile:
    """한 선수의 지금까지 누적 기록. update로 한 경기씩 더하고, vector로 모델 입력을 낸다."""

    minutes: float = 0.0
    counts: dict[str, float] = field(default_factory=lambda: dict.fromkeys(COUNT_STATS, 0.0))
    rating_sum: float = 0.0  # 평점 × 출전 시간의 합
    rating_minutes: float = 0.0  # 평점이 있던 경기의 출전 시간
    position: str | None = None

    def update(self, line: PlayerLine) -> None:
        if not played(line):
            return
        self.minutes += line.minutes
        for stat in COUNT_STATS:
            self.counts[stat] += getattr(line, stat) or 0  # 출전했는데 빈 값 = 0개
        if line.rating is not None:
            self.rating_sum += line.rating * line.minutes
            self.rating_minutes += line.minutes
        self.position = line.position or self.position

    def vector(self, position: str | None = None) -> np.ndarray:
        """모델에 넣는 벡터. 기록이 없는 선수(신인·첫 경기)는 스탯이 0이고 has_history=0이다 — 모델이 '모름'을 구분할 수 있게."""
        has_history = self.minutes > 0
        per90 = [self.counts[s] * 90 / self.minutes if has_history else 0.0 for s in COUNT_STATS]
        rating = self.rating_sum / self.rating_minutes if self.rating_minutes else DEFAULT_RATING
        pos = position or self.position
        return np.array([*per90, rating, math.log1p(self.minutes), *[float(pos == p) for p in POSITIONS], float(has_history)], dtype=np.float32)


@dataclass
class LineupData:
    """모델이 먹는 묶음. home·away는 (경기 수, 11, 특성 수), mask는 선수 자리가 채워졌는지(0/1), y는 OUTCOMES의 번호."""

    fixture_ids: np.ndarray
    kickoffs: np.ndarray
    seasons: np.ndarray
    home: np.ndarray
    away: np.ndarray
    home_mask: np.ndarray
    away_mask: np.ndarray
    y: np.ndarray

    def __len__(self) -> int:
        return len(self.fixture_ids)

    def subset(self, index: np.ndarray) -> "LineupData":
        return LineupData(*(getattr(self, f)[index] for f in ("fixture_ids", "kickoffs", "seasons", "home", "away", "home_mask", "away_mask", "y")))


def build_lineup_data(matches: list[MatchRecord], lines: list[PlayerLine]) -> LineupData:
    """시간순으로 돌며 경기마다 양 팀 선발 11명의 '경기 전 프로필'을 쌓고, 그 다음에 그 경기 기록을 프로필에 반영한다.

    선발 명단이 양쪽 다 있는 경기만 표본이 된다. 선발 명단과 포지션은 경기 전에 공개되므로 써도 누출이 아니다.
    """
    by_fixture: dict[int, list[PlayerLine]] = {}
    for line in lines:
        by_fixture.setdefault(line.fixture_id, []).append(line)
    profiles: dict[int, PlayerProfile] = {}
    rows: list[tuple] = []
    for m in sorted(matches, key=lambda x: x.kickoff):
        match_lines = by_fixture.get(m.id, [])
        announced = {line.player_id: line.position for line in match_lines}  # 오늘 명단의 포지션
        if m.home_starters and m.away_starters:
            sides = []
            for starters in (m.home_starters, m.away_starters):
                vectors = np.zeros((SQUAD, len(FEATURE_NAMES)), dtype=np.float32)
                mask = np.zeros(SQUAD, dtype=np.float32)
                for slot, player_id in enumerate(sorted(starters)[:SQUAD]):
                    vectors[slot] = profiles.get(player_id, PlayerProfile()).vector(announced.get(player_id))
                    mask[slot] = 1.0
                sides.append((vectors, mask))
            rows.append((m.id, m.kickoff, m.season, sides[0][0], sides[1][0], sides[0][1], sides[1][1], OUTCOMES.index(outcome(m.home_goals, m.away_goals))))
        for line in match_lines:  # 반영은 표본을 만든 뒤 — 이 순서가 누출을 막는다
            profiles.setdefault(line.player_id, PlayerProfile()).update(line)
    columns = list(zip(*rows)) if rows else [[]] * 8
    shape = (0, SQUAD, len(FEATURE_NAMES))
    return LineupData(
        fixture_ids=np.array(columns[0], dtype=np.int64), kickoffs=np.array(columns[1], dtype=object), seasons=np.array(columns[2], dtype=np.int64),
        home=np.stack(columns[3]) if rows else np.zeros(shape, np.float32), away=np.stack(columns[4]) if rows else np.zeros(shape, np.float32),
        home_mask=np.stack(columns[5]) if rows else np.zeros(shape[:2], np.float32), away_mask=np.stack(columns[6]) if rows else np.zeros(shape[:2], np.float32),
        y=np.array(columns[7], dtype=np.int64),
    )
