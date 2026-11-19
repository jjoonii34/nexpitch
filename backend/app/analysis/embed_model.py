"""선수·팀 임베딩 모델 (ADR 0014). 직접 모은 선수별 경기 기록으로 학습하는 작은 신경망 (PyTorch, CPU).

python -m app.analysis.embed_model [시즌=2024]     # 설치: pip install -r requirements-ml.txt

구조 — '스탯 기반 선수 표현':
  선수의 경기 전 프로필(15개 숫자) ──[선수 인코더: 작은 신경망]──► 선수 벡터(16차원)
  선발 11명의 선수 벡터 평균 ──► 팀 벡터
  [홈 팀 벡터, 원정 팀 벡터, 둘의 차] ──[예측 층]──► 홈 승 / 무 / 원정 승 확률

선수 번호가 아니라 **기록**을 입력으로 받는다 → 처음 보는 선수(신인, 이적생, 다른 리그 선수)도 기록만 있으면 벡터가 나온다.
같은 인코더가 모든 선수에 쓰이므로 학습할 숫자가 적다(2,707개) — 경기 수가 적은 우리 데이터에 맞춘 선택이다.

예측 확률은 통계 모델·LLM과 같은 모양(H, D, A 표)으로 돌려줘 evaluate의 같은 지표로 채점한다.
"""

import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd
import torch
from torch import nn

from app.analysis.dataset import OUTCOMES
from app.analysis.player_data import FEATURE_NAMES, N_CONTINUOUS, LineupData

VECTOR_DIM = 16  # 선수·팀 벡터의 크기
HIDDEN = 32
MIN_MATCHES = 150  # 선발 명단이 있는 경기가 이보다 적으면 실제 데이터 평가를 보류한다 (ADR 0014)


class LineupModel(nn.Module):
    """선수 인코더 + 평균으로 팀 벡터 + 예측 층."""

    def __init__(self, n_features: int = len(FEATURE_NAMES), dim: int = VECTOR_DIM, hidden: int = HIDDEN, dropout: float = 0.2):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(n_features, hidden), nn.ReLU(), nn.Dropout(dropout), nn.Linear(hidden, dim))
        self.head = nn.Sequential(nn.Linear(dim * 3, hidden), nn.ReLU(), nn.Dropout(dropout), nn.Linear(hidden, len(OUTCOMES)))

    def team_vector(self, players: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """(경기, 11, 특성) → (경기, dim). 비어 있는 자리(mask=0)는 평균에서 뺀다."""
        vectors = self.encoder(players) * mask.unsqueeze(-1)
        return vectors.sum(dim=1) / mask.sum(dim=1, keepdim=True).clamp(min=1)

    def forward(self, home: torch.Tensor, home_mask: torch.Tensor, away: torch.Tensor, away_mask: torch.Tensor) -> torch.Tensor:
        h, a = self.team_vector(home, home_mask), self.team_vector(away, away_mask)
        return self.head(torch.cat([h, a, h - a], dim=-1))  # 홈·원정을 따로 넣어 홈 이점을 배울 수 있게 한다


@dataclass
class Scaler:
    """연속 특성의 평균·표준편차 (학습 데이터의 실제 선수 자리만으로 계산). 평가 데이터에도 같은 값을 쓴다 — 평가 데이터로 다시 재면 누출이다."""

    mean: np.ndarray
    std: np.ndarray

    @classmethod
    def fit(cls, data: LineupData) -> "Scaler":
        players = np.concatenate([data.home[data.home_mask > 0], data.away[data.away_mask > 0]])[:, :N_CONTINUOUS]
        return cls(players.mean(axis=0), players.std(axis=0) + 1e-6)

    def apply(self, players: np.ndarray) -> np.ndarray:
        out = players.copy()
        out[..., :N_CONTINUOUS] = (out[..., :N_CONTINUOUS] - self.mean) / self.std
        return out


def _tensors(data: LineupData, scaler: Scaler) -> tuple[torch.Tensor, ...]:
    return (torch.from_numpy(scaler.apply(data.home)), torch.from_numpy(data.home_mask), torch.from_numpy(scaler.apply(data.away)), torch.from_numpy(data.away_mask))


@dataclass
class FittedLineupModel:
    model: LineupModel
    scaler: Scaler
    losses: list[float]  # 에폭별 학습 손실 (학습이 됐는지 확인용)

    def predict_proba(self, data: LineupData) -> pd.DataFrame:
        """경기별 (H, D, A) 확률. 인덱스는 fixture_id — 통계 모델·LLM과 같은 모양."""
        self.model.eval()
        with torch.no_grad():
            probs = torch.softmax(self.model(*_tensors(data, self.scaler)), dim=-1).numpy()
        return pd.DataFrame(probs, columns=OUTCOMES, index=data.fixture_ids)

    def player_vectors(self, profiles: np.ndarray) -> np.ndarray:
        """프로필 벡터들(선수 수, 특성) → 선수 임베딩(선수 수, dim). 비슷한 선수 찾기·6단계 추천에 쓴다."""
        self.model.eval()
        with torch.no_grad():
            return self.model.encoder(torch.from_numpy(self.scaler.apply(profiles.astype(np.float32)))).numpy()


def train(data: LineupData, epochs: int = 300, lr: float = 0.01, weight_decay: float = 1e-3, seed: int = 0) -> FittedLineupModel:
    """전체 데이터를 한 묶음으로 Adam 학습. 씨앗을 고정해 같은 데이터면 같은 모델이 나온다.

    weight_decay·dropout은 과적합을 누르는 장치다 (경기 수가 적다). 값은 관행값이며 데이터가 차면 검증 구간으로 고른다.
    """
    torch.manual_seed(seed)
    scaler = Scaler.fit(data)
    model = LineupModel()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    inputs, target = _tensors(data, scaler), torch.from_numpy(data.y)
    losses = []
    model.train()
    for _ in range(epochs):
        optimizer.zero_grad()
        loss = nn.functional.cross_entropy(model(*inputs), target)
        loss.backward()
        optimizer.step()
        losses.append(loss.item())
    return FittedLineupModel(model, scaler, losses)


def time_ordered_split(data: LineupData, train_share: float = 0.5) -> tuple[LineupData, LineupData]:
    """킥오프 순서로 앞쪽은 학습, 뒤쪽은 평가."""
    order = np.argsort(data.kickoffs)
    cut = int(len(order) * train_share)
    return data.subset(order[:cut]), data.subset(order[cut:])


if __name__ == "__main__":
    from sqlalchemy.orm import Session

    from app.analysis.dataset import build_features, load_matches
    from app.analysis.evaluate import brier, paired_brier_diff
    from app.analysis.models import fit
    from app.analysis.player_data import build_lineup_data, load_player_lines
    from app.db import get_engine

    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    with Session(get_engine()) as session:
        matches, lines = load_matches(session), load_player_lines(session)
    data = build_lineup_data(matches, lines)
    data = data.subset(np.where(data.seasons == season)[0])
    known = float(np.concatenate([data.home[..., -1], data.away[..., -1]]).mean()) if len(data) else 0.0
    print(f"{season} 시즌: 선발 명단이 있는 경기 {len(data)} · 선발 자리 중 지난 기록이 있는 비율 {known:.0%} · 학습할 숫자 {sum(p.numel() for p in LineupModel().parameters())}개")
    if len(data) < MIN_MATCHES:
        print(f"평가 보류: {MIN_MATCHES}경기 미만 (수집이 더 필요). 학습 코드가 도는지만 확인한다.")
        fitted = train(data, epochs=50)
        print(f"  학습 손실 {fitted.losses[0]:.3f} → {fitted.losses[-1]:.3f} (이 숫자는 성능이 아니다 — 같은 데이터로 잰 것)")
        sys.exit(0)

    train_data, test_data = time_ordered_split(data)
    fitted = train(train_data)
    probs = fitted.predict_proba(test_data)
    outcomes = pd.Series([OUTCOMES[i] for i in test_data.y], index=test_data.fixture_ids)
    table = build_features(matches).set_index("fixture_id")
    elo = fit("elo", table.loc[train_data.fixture_ids]).predict_proba(table.loc[test_data.fixture_ids])
    diff, low, high = paired_brier_diff(probs, elo, outcomes)
    print(f"시즌 안 시간순 평가 (잠정): 학습 {len(train_data)} · 평가 {len(test_data)}")
    print(f"  임베딩 모델 Brier {brier(probs, outcomes):.4f} | Elo {brier(elo, outcomes):.4f} | 차 {diff:+.4f} (95% 구간 {low:+.4f}~{high:+.4f})")
