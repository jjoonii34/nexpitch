"""LLM 가설 역검증 (ADR 0010): '<특성> op <값>이면 홈 승률이 높다/낮다'를 과거 경기에서 센다.

가설 생성은 LLM, 검증은 통계 — 역할을 나눈다. 결과는 효과 크기(승률 차) + 부트스트랩 95% 구간 + 표본 수로 보여주고,
표본이 적으면 'insufficient', 구간이 0을 포함하면 'not_supported'로 솔직하게 표시한다.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

MIN_CONDITION_MATCHES = 20  # 이보다 적으면 판단 보류
BOOTSTRAP_SAMPLES = 1000


@dataclass
class CheckResult:
    feature: str
    op: str
    value: float
    claim: str
    n_condition: int
    n_other: int
    rate_condition: float | None
    rate_other: float | None
    diff: float | None
    ci_low: float | None
    ci_high: float | None
    verdict: str  # supported / not_supported / insufficient


def condition_mask(table: pd.DataFrame, feature: str, op: str, value: float) -> pd.Series:
    """조건이 성립한 경기(True). 특성이 비어 있는 경기(NaN)는 어느 쪽에도 넣지 않는다 → 호출한 쪽이 NaN을 먼저 뺀다."""
    col = table[feature]
    return col >= value if op == ">=" else col <= value


def bootstrap_diff_ci(a: np.ndarray, b: np.ndarray, samples: int = BOOTSTRAP_SAMPLES, seed: int = 0) -> tuple[float, float]:
    """두 집단 평균 차(a − b)의 95% 부트스트랩 구간. 같은 씨앗을 써서 결과가 재현된다."""
    rng = np.random.default_rng(seed)
    diffs = rng.choice(a, (samples, len(a))).mean(axis=1) - rng.choice(b, (samples, len(b))).mean(axis=1)
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def check_hypothesis(table: pd.DataFrame, feature: str, op: str, value: float, claim: str) -> CheckResult:
    """과거 경기 표(특성 + outcome)에서 가설을 검사한다."""
    known = table.dropna(subset=[feature])
    home_win = (known["outcome"] == "H").astype(float).to_numpy()
    mask = condition_mask(known, feature, op, value).to_numpy()
    a, b = home_win[mask], home_win[~mask]
    n_a, n_b = int(mask.sum()), int((~mask).sum())

    if n_a < MIN_CONDITION_MATCHES or n_b < MIN_CONDITION_MATCHES:
        return CheckResult(feature, op, value, claim, n_a, n_b, float(a.mean()) if n_a else None, float(b.mean()) if n_b else None, None, None, None, "insufficient")

    diff = float(a.mean() - b.mean())
    low, high = bootstrap_diff_ci(a, b)
    expected_positive = claim == "home_win_rate_higher"
    supported = (low > 0) if expected_positive else (high < 0)
    return CheckResult(feature, op, value, claim, n_a, n_b, float(a.mean()), float(b.mean()), diff, low, high, "supported" if supported else "not_supported")


def describe(r: CheckResult) -> str:
    """결과를 한국어 한 줄로 (화면·로그용)."""
    label = {"supported": "근거 있음", "not_supported": "근거 없음", "insufficient": "표본 부족"}[r.verdict]
    if r.diff is None:
        return f"[{label}] 조건 성립 {r.n_condition}경기 / 나머지 {r.n_other}경기 — 20경기 미만이라 판단 보류"
    return (
        f"[{label}] 조건 성립 {r.n_condition}경기 홈 승률 {r.rate_condition:.0%} vs 나머지 {r.n_other}경기 {r.rate_other:.0%} "
        f"(차 {r.diff:+.0%}, 95% 구간 {r.ci_low:+.0%}~{r.ci_high:+.0%})"
    )
