"""프롬프트 평가 하네스 테스트. 직접 만든 가설·근거 문장으로 지표가 뜻대로 계산되는지 본다 (DB·네트워크 없음)."""

import math

import pandas as pd

from app.analysis.prompt_eval import allowed_numbers, faithfulness_metrics, format_table, grounded_numbers, hypothesis_metrics, score_version


def hyp(feature: str, value: float, op: str = ">=", claim: str = "home_win_rate_higher") -> dict:
    return {"feature": feature, "op": op, "value": value, "claim": claim, "reason": "이유는 달라도 된다"}


def test_hypothesis_metrics_count_distinct_and_nontrivial():
    hyps = [hyp("elo_diff", 200), hyp("elo_diff", 200), hyp("rest_diff", 2), None]
    verdicts = {("elo_diff", ">=", 200.0, "home_win_rate_higher"): "supported", ("rest_diff", ">=", 2.0, "home_win_rate_higher"): "insufficient"}
    m = hypothesis_metrics(hyps, verdicts)
    assert m["testable_rate"] == 0.75  # 4건 중 3건이 틀+숫자
    assert m["distinct"] == 2 and m["features_used"] == 2  # 같은 가설 두 번은 한 번으로
    assert m["nontrivial_rate"] == 1 / 3  # Elo 단독이 아닌 것은 3건 중 1건
    assert m["supported_rate"] == 1.0 and m["insufficient"] == 1  # 표본 부족은 근거율 분모에서 뺀다


def test_hypothesis_metrics_free_text_only_is_untestable():
    m = hypothesis_metrics([None, None], {})
    assert m["testable_rate"] == 0 and m["distinct"] == 0 and math.isnan(m["nontrivial_rate"])


def test_grounded_numbers_flags_invented_numbers():
    row = pd.Series({"elo_diff": 255.6, "form_diff": -6.0, "goal_diff_form": 3.0, "rest_diff": 1.0, "xg_diff_form": float("nan"), "lineup_changes_diff": None})
    allowed = allowed_numbers(row, (0.62, 0.22, 0.16))
    assert {256.0, 6.0, 3.0, 1.0, 5.0, 62} <= allowed  # 보여준 자릿수로 반올림, 부호 없이, '최근 5경기'의 5, 자기 확률
    assert grounded_numbers("엘로 256 우위, 최근 5경기 승점 차 -6, 홈 승 62%", allowed) == (4, 4)
    assert grounded_numbers("점유율 60퍼센트를 유지한다", allowed) == (0, 1)  # 입력에 없는 숫자
    assert grounded_numbers("숫자 없는 문장", allowed) == (0, 0)


def test_faithfulness_metrics():
    m = faithfulness_metrics([(2, 2), (1, 2), (0, 0)])
    assert m["grounded_rate"] == 0.75 and m["rationales_with_ungrounded"] == 1 / 3 and m["numbers_per_rationale"] == 4 / 3


def test_score_version_builds_one_row_and_table():
    features = pd.DataFrame({"elo_diff": [100.0, -50.0], "form_diff": [3.0, -2.0]}, index=[1, 2])
    outcomes = pd.Series(["H", "A"], index=[1, 2])
    elo = pd.DataFrame({"H": [0.5, 0.5], "D": [0.25, 0.25], "A": [0.25, 0.25]}, index=[1, 2])
    predictions = [
        {"fixture_id": 1, "p_home": 0.8, "p_draw": 0.1, "p_away": 0.1, "rationale": "엘로 100 우위", "hypothesis_json": hyp("elo_diff", 50)},
        {"fixture_id": 2, "p_home": 0.1, "p_draw": 0.1, "p_away": 0.8, "rationale": "승점 차 2, 점유율 70", "hypothesis_json": hyp("form_diff", 0, "<=", "home_win_rate_lower")},
        {"fixture_id": 99, "p_home": 0.3, "p_draw": 0.3, "p_away": 0.4, "rationale": "평가 시즌 밖 경기", "hypothesis_json": None},
    ]
    row = score_version("llm vX", predictions, features, outcomes, elo, {("form_diff", "<=", 0.0, "home_win_rate_lower"): "supported"})
    assert row["n"] == 2  # 평가 시즌 밖 경기는 뺀다
    assert row["vs_elo"] < 0  # 두 경기 다 Elo(반반)보다 잘 맞혔다
    assert row["nontrivial_rate"] == 0.5 and row["supported_rate"] == 1.0
    assert row["grounded_rate"] == 2 / 3 and row["rationales_with_ungrounded"] == 0.5  # '70'만 지어낸 숫자
    table = format_table([row, {"version": "빈 버전", "n": 0}])
    assert len(table) == 1 and table.iloc[0]["비자명 가설"] == "50%"
