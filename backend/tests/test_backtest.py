"""가설 역검증 테스트. 규칙성을 심은 가짜 경기 표로 '근거 있음/없음/표본 부족' 판정을 검사한다."""

import json

import numpy as np
import pandas as pd

from app.analysis.backtest import bootstrap_diff_ci, check_hypothesis, condition_mask, describe
from app.analysis.backtest_run import pending_predictions, run
from app.analysis.llm_analyst import AnalystOutputV2, Hypothesis, ask_v2, hypothesis_text
from app.analysis.llm_run import run_llm
from app.analysis.dataset import build_features
from app.analysis.evaluate import time_split
from app.models.analysis import HypothesisCheck
from tests.test_analysis import biased_season


def table_with_rule(n: int = 400, seed: int = 1) -> pd.DataFrame:
    """rest_diff >= 2 인 경기는 홈 승률 70%, 아니면 35%인 가짜 표. lineup_changes_diff는 거의 비어 있다."""
    rng = np.random.default_rng(seed)
    rest = rng.integers(-4, 5, n).astype(float)
    p_home = np.where(rest >= 2, 0.7, 0.35)
    outcome = np.where(rng.random(n) < p_home, "H", "A")
    return pd.DataFrame({"rest_diff": rest, "elo_diff": rng.normal(0, 50, n), "lineup_changes_diff": [np.nan] * (n - 5) + [1.0] * 5, "outcome": outcome})


def test_condition_mask_and_ci():
    t = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    assert list(condition_mask(t, "x", ">=", 2)) == [False, True, True]
    assert list(condition_mask(t, "x", "<=", 2)) == [True, True, False]
    low, high = bootstrap_diff_ci(np.ones(50), np.zeros(50))
    assert low == high == 1.0


def test_supported_not_supported_insufficient():
    table = table_with_rule()
    supported = check_hypothesis(table, "rest_diff", ">=", 2, "home_win_rate_higher")
    assert supported.verdict == "supported" and supported.diff > 0.2 and supported.ci_low > 0
    wrong_direction = check_hypothesis(table, "rest_diff", ">=", 2, "home_win_rate_lower")
    assert wrong_direction.verdict == "not_supported"
    noise = check_hypothesis(table, "elo_diff", ">=", 0, "home_win_rate_higher")
    assert noise.verdict in {"not_supported", "supported"} and noise.n_condition > 20
    thin = check_hypothesis(table, "lineup_changes_diff", ">=", 1, "home_win_rate_higher")
    assert thin.verdict == "insufficient" and "표본 부족" in describe(thin)
    assert "근거 있음" in describe(supported)


class FakeClientV2:
    interactions = None

    def __init__(self):
        self.interactions = self

    def create(self, **kwargs):
        class R:
            output_text = json.dumps({"p_home": 0.5, "p_draw": 0.25, "p_away": 0.25, "rationale": "r", "hypothesis": {"feature": "rest_diff", "op": ">=", "value": 2, "claim": "home_win_rate_higher", "reason": "휴식이 길면 유리"}})
        return R()


def test_ask_v2_returns_structured_hypothesis():
    r = ask_v2(FakeClientV2(), pd.Series({"elo_diff": 1.0}), "A", "B")
    assert r.structured == Hypothesis(feature="rest_diff", op=">=", value=2, claim="home_win_rate_higher", reason="휴식이 길면 유리")
    assert "홈 승률이 높다" in r.hypothesis and hypothesis_text(r.structured) == r.hypothesis
    AnalystOutputV2.model_json_schema()  # 스키마가 만들어진다 (API에 넘길 수 있다)


def test_backtest_run_checks_pending_v2_predictions_once(session):
    matches = biased_season(2022, n=60) + biased_season(2023, n=60, offset=1000)
    table = build_features(matches)
    history, test = time_split(table, [2023])
    names = {1: "T1", 2: "T2", 3: "T3", 4: "T4"}
    home_ids = {m.id: m.home_id for m in matches}
    away_ids = {m.id: m.away_id for m in matches}
    run_llm(session, FakeClientV2(), test.head(3), names, home_ids, away_ids, "llm", False, 10, pause=0, version="v2")

    assert len(pending_predictions(session)) == 3
    counts = run(session, history)
    assert sum(counts.values()) == 3 and set(counts) <= {"supported", "not_supported", "insufficient"}
    assert session.query(HypothesisCheck).count() == 3
    assert run(session, history) == {}  # 두 번째 실행은 할 일이 없다
