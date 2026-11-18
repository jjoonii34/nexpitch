"""예측 확률을 실제 결과와 대조하는 지표. 셋 다 낮을수록 좋다. 같은 지표로 통계 모델·LLM·결합을 비교한다 (4-4)."""

import numpy as np
import pandas as pd

from app.analysis.dataset import OUTCOMES


def brier(probs: pd.DataFrame, outcomes: pd.Series) -> float:
    """다항 Brier score: 경기마다 (확률 − 실제)^2 를 세 결과에 대해 더한 뒤 평균. 0이 완벽, 상수 모델은 약 0.6대."""
    actual = np.array([[1.0 if o == c else 0.0 for c in OUTCOMES] for o in outcomes])
    return float(((probs[OUTCOMES].to_numpy() - actual) ** 2).sum(axis=1).mean())


def log_loss(probs: pd.DataFrame, outcomes: pd.Series, eps: float = 1e-12) -> float:
    """로그 손실: 실제 결과에 준 확률의 −log 평균. 자신 있게 틀리면 크게 벌한다."""
    p = np.array([probs.loc[i, o] for i, o in zip(probs.index, outcomes)])
    return float(-np.log(np.clip(p, eps, 1)).mean())


def accuracy(probs: pd.DataFrame, outcomes: pd.Series) -> float:
    """가장 높은 확률의 결과가 맞은 비율. 참고용 (확률의 질은 Brier·로그 손실이 더 잘 보여준다)."""
    predicted = probs[OUTCOMES].idxmax(axis=1)
    return float((predicted.to_numpy() == outcomes.to_numpy()).mean())


def time_split(table: pd.DataFrame, test_seasons: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """시즌으로 학습/평가를 나눈다. 평가 시즌은 학습에 전혀 쓰지 않는다 (미래를 과거로 예측하는 실제 상황과 같게)."""
    is_test = table["season"].isin(test_seasons)
    return table[~is_test], table[is_test]


def brier_each(probs: pd.DataFrame, outcomes: pd.Series) -> np.ndarray:
    """경기별 Brier (평균 내기 전). 두 모델을 같은 경기끼리 짝지어 비교할 때 쓴다."""
    actual = np.array([[1.0 if o == c else 0.0 for c in OUTCOMES] for o in outcomes])
    return ((probs[OUTCOMES].to_numpy() - actual) ** 2).sum(axis=1)


def paired_brier_diff(a: pd.DataFrame, b: pd.DataFrame, outcomes: pd.Series, samples: int = 1000, seed: int = 0) -> tuple[float, float, float]:
    """같은 경기에서 Brier(a) − Brier(b)의 평균과 95% 부트스트랩 구간. 음수면 a가 낫고, 구간이 0을 포함하면 차이가 우연일 수 있다.

    경기를 통째로 다시 뽑는다(짝 유지) → 경기 난이도 차이가 상쇄돼 독립 비교보다 구간이 좁다.
    """
    d = brier_each(a.loc[outcomes.index], outcomes) - brier_each(b.loc[outcomes.index], outcomes)
    rng = np.random.default_rng(seed)
    means = rng.choice(d, (samples, len(d))).mean(axis=1)
    return float(d.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def summarize(name: str, probs: pd.DataFrame, outcomes: pd.Series) -> dict:
    return {"model": name, "n": int(len(outcomes)), "brier": round(brier(probs, outcomes), 4), "log_loss": round(log_loss(probs, outcomes), 4), "accuracy": round(accuracy(probs, outcomes), 3)}
