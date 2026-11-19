"""가설 역검증 테스트. 규칙성을 심은 가짜 경기 표로 '근거 있음/없음/표본 부족' 판정을 검사한다."""

import json

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from app.analysis.backtest import bootstrap_diff_ci, check_hypothesis, condition_mask, describe
from app.analysis.backtest_run import pending_predictions, run
from app.analysis.llm_analyst import HYPOTHESIS_FEATURES_V3, SYSTEM_INSTRUCTION_V3, TACTICAL_INPUT_LINES, AnalystOutputV2, AnalystOutputV3, Hypothesis, ask_v2, ask_v3, build_input_v3, hypothesis_text
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
    assert all(p.input_text.startswith("Match: ") for p in pending_predictions(session))  # 보낸 입력을 함께 저장한다
    counts = run(session, history)
    assert sum(counts.values()) == 3 and set(counts) <= {"supported", "not_supported", "insufficient"}
    assert session.query(HypothesisCheck).count() == 3
    assert run(session, history) == {}  # 두 번째 실행은 할 일이 없다
class FakeClientV3:
    """정해 둔 v3 답을 돌려주고, 받은 입력을 기억한다."""

    def __init__(self, feature: str = "possession_diff"):
        self.interactions, self.feature, self.seen = self, feature, {}

    def create(self, **kwargs):
        self.seen = kwargs
        feature = self.feature

        class R:
            output_text = json.dumps({"p_home": 0.5, "p_draw": 0.3, "p_away": 0.2, "rationale": "점유율 차 12.5가 크다", "hypothesis": {"feature": feature, "op": ">=", "value": 10, "claim": "home_win_rate_higher", "reason": "공을 오래 쥔다"}})

        return R()


def test_v3_input_adds_tactical_numbers_and_marks_missing():
    row = pd.Series({"elo_diff": 80.0, "possession_diff": 12.46, "xg_for_diff": 0.512, "pass_accuracy_diff": None})
    text = build_input_v3(row, "Arsenal", "Everton")
    assert "possession % difference (home - away): 12.5" in text and "xG created per match difference (home - away): 0.51" in text
    assert "pass accuracy difference, 0-1 scale (home - away): not available" in text  # 없는 값은 지어내지 못하게 표시
    assert text.splitlines()[0] == "Match: Arsenal (home) vs Everton (away)" and text.splitlines()[-1] == "Return the JSON object."


def test_v3_schema_forbids_elo_only_hypothesis():
    assert "elo_diff" not in HYPOTHESIS_FEATURES_V3 and "Elo difference is not allowed" in SYSTEM_INSTRUCTION_V3
    allowed = AnalystOutputV3.model_json_schema()["$defs"]["HypothesisV3"]["properties"]["feature"]["enum"]
    assert set(allowed) == set(HYPOTHESIS_FEATURES_V3)  # 프롬프트 문장과 스키마가 같은 목록을 쓴다
    with pytest.raises(ValidationError):
        ask_v3(FakeClientV3(feature="elo_diff"), pd.Series({"elo_diff": 1.0}), "A", "B")  # 스키마 밖의 답은 저장되지 않는다


def test_ask_v3_returns_hypothesis_and_keeps_input():
    client = FakeClientV3()
    r = ask_v3(client, pd.Series({"elo_diff": 80.0, "possession_diff": 12.5}), "A", "B")
    assert r.structured.feature == "possession_diff" and "possession_diff >= 10 이면 홈 승률이 높다" in r.hypothesis
    assert r.input_text == client.seen["input"] and client.seen["system_instruction"] == SYSTEM_INSTRUCTION_V3


def test_v3_hypothesis_features_exist_in_feature_table():
    table = build_features(biased_season(2022, n=12))
    assert set(HYPOTHESIS_FEATURES_V3) <= set(table.columns)  # 가설의 특성은 과거 경기 표에서 셀 수 있어야 한다
    assert {column for column, _, _ in TACTICAL_INPUT_LINES} <= set(table.columns)
