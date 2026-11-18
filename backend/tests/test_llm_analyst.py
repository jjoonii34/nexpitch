"""LLM 분석가 테스트. Gemini를 부르지 않고 가짜 클라이언트로 입력 만들기·확률 다듬기·저장·재실행·채점을 검사한다."""

import json

import pandas as pd
import pytest

from app.analysis.dataset import OUTCOMES, build_features
from app.analysis.evaluate import time_split
from app.analysis.llm_analyst import PROMPT_VERSION, AnalystResult, ask, build_input, normalize
from app.analysis.llm_run import masked_subset, run_llm, score_table
from app.analysis.predictions import done_fixture_ids, load_probs, save_llm, save_probs
from tests.test_analysis import biased_season


def test_build_input_uses_only_numbers_and_marks_missing():
    row = pd.Series({"elo_diff": 75.4, "form_diff": 4.0, "goal_diff_form": float("nan"), "rest_diff": -2.0, "xg_diff_form": None, "lineup_changes_diff": 1.0})
    text = build_input(row, "Liverpool", "Arsenal")
    assert "Liverpool (home) vs Arsenal (away)" in text and "75" in text and "not available" in text
    masked = build_input(row, "Liverpool", "Arsenal", masked=True)
    assert "Liverpool" not in masked and "Team A (home) vs Team B (away)" in masked


def test_normalize_sums_to_one_and_floors_zero():
    h, d, a = normalize(0.7, 0.2, 0.1)
    assert (round(h, 6), round(d, 6), round(a, 6)) == (0.7, 0.2, 0.1)
    h, d, a = normalize(1.0, 0.0, 0.0)
    assert d > 0 and a > 0 and abs(h + d + a - 1) < 1e-9


class FakeInteraction:
    def __init__(self, text): self.output_text = text


class FakeClient:
    """정해 둔 JSON을 돌려주는 가짜 Gemini. 몇 번 불렸는지, 어떤 입력이었는지 남긴다."""

    def __init__(self, fail_ids: set[int] | None = None):
        self.inputs: list[str] = []
        self.interactions = self

    def create(self, **kwargs):
        self.inputs.append(kwargs["input"])
        if "elo_diff" in kwargs["input"] and "fail" in kwargs["input"]:
            raise RuntimeError("boom")
        return FakeInteraction(json.dumps({"p_home": 0.5, "p_draw": 0.3, "p_away": 0.2, "rationale": "Elo 차이가 큼", "hypothesis": "선발 변경 3명 이상이면 승률 하락"}))


def test_ask_parses_and_normalizes():
    row = pd.Series({"elo_diff": 10.0})
    result = ask(FakeClient(), row, "A", "B")
    assert isinstance(result, AnalystResult) and abs(result.p_home + result.p_draw + result.p_away - 1) < 1e-9
    assert result.rationale == "Elo 차이가 큼"


def test_run_llm_saves_and_resumes(session):
    matches = biased_season(2022, n=24) + biased_season(2023, n=12, offset=100)
    table = build_features(matches)
    _, test = time_split(table, [2023])
    names = {1: "T1", 2: "T2", 3: "T3", 4: "T4"}
    home_ids = {m.id: m.home_id for m in matches}
    away_ids = {m.id: m.away_id for m in matches}

    client = FakeClient()
    calls, errors = run_llm(session, client, test, names, home_ids, away_ids, "llm", False, max_calls=5, pause=0)
    assert (calls, errors) == (5, []) and len(done_fixture_ids(session, "llm", PROMPT_VERSION)) == 5
    calls2, _ = run_llm(session, client, test, names, home_ids, away_ids, "llm", False, max_calls=100, pause=0)
    assert calls2 == 7  # 나머지만 이어서
    assert "T1 (home)" in client.inputs[0]

    probs = load_probs(session, "llm", PROMPT_VERSION)
    assert probs.shape == (12, 3) and probs.sum(axis=1).round(6).eq(1).all()


def test_masked_subset_is_spread_over_season():
    test = pd.DataFrame({"fixture_id": range(100)})
    sub = masked_subset(test, 10)
    assert list(sub["fixture_id"]) == [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
    assert len(masked_subset(test, 500)) == 100
    assert len(masked_subset(test, 0)) == 0  # 가린 변형을 끄는 경우


def test_score_table_includes_llm_combined_and_masked_rows(session):
    matches = biased_season(2022, n=24) + biased_season(2023, n=12, offset=100)
    table = build_features(matches)
    train, test = time_split(table, [2023])
    names = {1: "T1", 2: "T2", 3: "T3", 4: "T4"}
    home_ids = {m.id: m.home_id for m in matches}
    away_ids = {m.id: m.away_id for m in matches}
    run_llm(session, FakeClient(), test, names, home_ids, away_ids, "llm", False, 100, pause=0)
    run_llm(session, FakeClient(), masked_subset(test, 4), names, home_ids, away_ids, "llm_masked", True, 100, pause=0)

    result = score_table(session, train, test, "train2022-2022")
    models = list(result["model"])
    assert {"constant", "elo", "features", "llm", "combined(llm+elo)"} <= set(models)
    assert any(m.startswith("llm_masked (4경기)") for m in models)
    assert result["brier"].between(0, 2).all()
    assert load_probs(session, "combined", f"{PROMPT_VERSION}+elo").shape == (12, 3)
    assert load_probs(session, "elo", "train2022-2022").shape == (12, 3)  # 통계 모델 예측도 저장된다


def test_save_probs_replaces_same_model_version(session):
    matches = biased_season(2022, n=6)
    table = build_features(matches)
    probs = pd.DataFrame([[0.5, 0.3, 0.2]] * 6, columns=OUTCOMES, index=table["fixture_id"].to_numpy())
    assert save_probs(session, "elo", "v", probs, table["fixture_id"]) == 6
    assert save_probs(session, "elo", "v", probs, table["fixture_id"]) == 6
    assert load_probs(session, "elo", "v").shape == (6, 3)
    with pytest.raises(KeyError):
        _ = load_probs(session, "none", "v").loc[1]
