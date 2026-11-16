"""Elo 팀 레이팅. 경기마다 결과로 두 팀 점수를 조금씩 옮긴다. 홈 이점은 홈 팀 점수에 더해서 계산한다.

가장 단순한 기준선이라 'LLM 없이 이만큼'의 바닥을 보여주는 용도다. K·홈 이점 값은 축구에서 흔히 쓰는 범위에서 골랐다 (확인 필요: 데이터로 조정).
"""

from dataclasses import dataclass, field

START_RATING = 1500.0
K = 20.0  # 한 경기가 점수를 얼마나 움직이는지
HOME_ADVANTAGE = 60.0  # 홈 팀에 더해 주는 점수


def expected_score(home_rating: float, away_rating: float, home_advantage: float = HOME_ADVANTAGE) -> float:
    """홈 팀이 '승=1, 무=0.5, 패=0' 기준으로 기대하는 점수 (0~1)."""
    diff = home_rating + home_advantage - away_rating
    return 1.0 / (1.0 + 10 ** (-diff / 400.0))


def actual_score(home_goals: int, away_goals: int) -> float:
    """홈 팀 입장의 실제 점수: 승 1, 무 0.5, 패 0."""
    return 1.0 if home_goals > away_goals else 0.5 if home_goals == away_goals else 0.0


@dataclass
class EloTable:
    """팀별 현재 레이팅. 경기를 시간순으로 넣어야 한다 (미래 경기를 먼저 넣으면 정보가 샌다)."""

    ratings: dict[int, float] = field(default_factory=dict)
    k: float = K
    home_advantage: float = HOME_ADVANTAGE

    def get(self, team_id: int) -> float:
        return self.ratings.get(team_id, START_RATING)

    def pre_match_diff(self, home_id: int, away_id: int) -> float:
        """경기 전 (홈 레이팅 + 홈 이점 − 원정 레이팅). 모델의 특성으로 쓴다."""
        return self.get(home_id) + self.home_advantage - self.get(away_id)

    def update(self, home_id: int, away_id: int, home_goals: int, away_goals: int) -> None:
        """경기 결과를 반영한다. 기대보다 잘하면 오르고 못하면 내린다."""
        expected = expected_score(self.get(home_id), self.get(away_id), self.home_advantage)
        delta = self.k * (actual_score(home_goals, away_goals) - expected)
        self.ratings[home_id] = self.get(home_id) + delta
        self.ratings[away_id] = self.get(away_id) - delta
