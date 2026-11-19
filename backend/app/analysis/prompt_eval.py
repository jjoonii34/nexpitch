"""프롬프트 평가 하네스 (4.5단계 ①): LLM 분석가의 프롬프트 버전을 같은 잣대로 자동 채점해 한 표에 놓는다.

python -m app.analysis.prompt_eval [평가 시즌=2024]

버전(v1, v2, …)마다 네 가지를 잰다. 새 프롬프트가 '나아졌다'고 말하려면 이 표의 숫자가 바뀌어야 한다.
1. 예측 품질 — Brier, 같은 경기에서 Elo와의 차이와 95% 구간
2. 가설 검증 가능성 — 틀+숫자 가설(검증 가능)의 비율
3. 가설의 질 — 서로 다른 가설 수, 쓰인 특성 종류, Elo 단독이 아닌 가설 비율(비자명성), 판정이 난 가설 중 근거 있음 비율
4. 근거 충실도 — 근거 문장에 나온 숫자가 실제로 준 입력에 있는 숫자인가 (없는 숫자를 지어내는 '환각' 검출)

채점 함수는 전부 순수 함수다 (DB·네트워크 없음) → 가짜 데이터로 테스트한다. DB 읽기는 evaluate_versions 한 곳.
"""

import math
import re
import sys
from collections import Counter

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.dataset import FORM_WINDOW, OUTCOMES, build_features, load_matches
from app.analysis.evaluate import brier, paired_brier_diff, time_split
from app.analysis.predictions import load_probs
from app.models.analysis import HypothesisCheck, Prediction

TRIVIAL_FEATURES = {"elo_diff"}  # 이것만 쓴 가설은 '당연한 말'로 센다 (ADR 0010: v2 가설 97건이 전부 여기에 해당)
INPUT_DIGITS = {"elo_diff": 0, "form_diff": 0, "goal_diff_form": 0, "rest_diff": 1, "xg_diff_form": 2, "lineup_changes_diff": 0}  # llm_analyst.build_input이 보여주는 자릿수
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


# ── 가설 ──


def hypothesis_key(h: dict) -> tuple:
    """같은 가설인지 가리는 열쇠. 이유 문장(reason)은 달라도 조건이 같으면 같은 가설이다."""
    return (h["feature"], h["op"], float(h["value"]), h["claim"])


def hypothesis_metrics(hypotheses: list[dict | None], verdicts: dict[tuple, str]) -> dict:
    """가설 목록(예측당 하나, 자유 문장뿐이면 None)과 가설별 판정으로 질 지표를 만든다.

    근거율은 '서로 다른 가설' 단위로 센다 — 같은 가설이 여러 경기에서 반복되면 건수가 부풀기 때문이다.
    """
    structured = [h for h in hypotheses if h]
    distinct = {hypothesis_key(h) for h in structured}
    decided = [verdicts[k] for k in distinct if verdicts.get(k) in ("supported", "not_supported")]
    return {
        "testable_rate": len(structured) / len(hypotheses) if hypotheses else math.nan,
        "distinct": len(distinct),
        "features_used": len({h["feature"] for h in structured}),
        "nontrivial_rate": sum(h["feature"] not in TRIVIAL_FEATURES for h in structured) / len(structured) if structured else math.nan,
        "supported_rate": decided.count("supported") / len(decided) if decided else math.nan,
        "insufficient": sum(verdicts.get(k) == "insufficient" for k in distinct),
    }


# ── 근거 충실도 ──


def allowed_numbers(row: pd.Series, probs: tuple[float, float, float]) -> set[float]:
    """근거 문장에 나와도 되는 숫자: 모델에 보여준 입력값(보여준 자릿수로, 부호 없이), '최근 5경기'의 5, 모델 자신의 확률."""
    allowed = {float(FORM_WINDOW)}
    for column, digits in INPUT_DIGITS.items():
        value = row.get(column)
        if value is not None and not pd.isna(value):
            allowed.add(abs(round(float(value), digits)))
    for p in probs:
        allowed.update({round(p * 100), round(p * 100, 1), round(p, 2)})
    return allowed


def grounded_numbers(text: str, allowed: set[float]) -> tuple[int, int]:
    """(입력에 근거가 있는 숫자 수, 문장에 나온 숫자 수). 부호는 보지 않는다 ('-6'과 '6점 뒤진다'를 같게 본다)."""
    numbers = [float(n) for n in NUMBER_RE.findall(text or "")]
    return sum(any(math.isclose(n, a, abs_tol=1e-9) for a in allowed) for n in numbers), len(numbers)


def faithfulness_metrics(pairs: list[tuple[int, int]]) -> dict:
    """예측별 (근거 있는 숫자, 전체 숫자) 목록 → 숫자 단위 충실도와 '지어낸 숫자가 하나라도 있는 근거'의 비율."""
    total = sum(t for _, t in pairs)
    return {
        "numbers_per_rationale": total / len(pairs) if pairs else math.nan,
        "grounded_rate": sum(g for g, _ in pairs) / total if total else math.nan,
        "rationales_with_ungrounded": sum(g < t for g, t in pairs) / len(pairs) if pairs else math.nan,
    }


# ── 한 버전 채점 ──


def score_version(label: str, predictions: list[dict], features: pd.DataFrame, outcomes: pd.Series, elo: pd.DataFrame, verdicts: dict[tuple, str]) -> dict:
    """한 (모델, 버전)의 예측 목록을 채점해 표의 한 줄로 만든다.

    predictions: {fixture_id, p_home, p_draw, p_away, rationale, hypothesis_json} 목록.
    features: fixture_id를 인덱스로 한 특성 표. outcomes·elo도 fixture_id 인덱스.
    """
    rows = [p for p in predictions if p["fixture_id"] in outcomes.index]
    ids = [p["fixture_id"] for p in rows]
    result: dict = {"version": label, "n": len(rows)}
    if not rows:
        return result
    probs = pd.DataFrame({"H": [p["p_home"] for p in rows], "D": [p["p_draw"] for p in rows], "A": [p["p_away"] for p in rows]}, index=ids)[OUTCOMES]
    sub = outcomes.loc[ids]
    diff, low, high = paired_brier_diff(probs, elo, sub)
    result.update({"brier": brier(probs, sub), "vs_elo": diff, "vs_elo_low": low, "vs_elo_high": high})
    result.update(hypothesis_metrics([p.get("hypothesis_json") for p in rows], verdicts))
    pairs = [grounded_numbers(p.get("rationale") or "", allowed_numbers(features.loc[p["fixture_id"]], (p["p_home"], p["p_draw"], p["p_away"]))) for p in rows]
    result.update(faithfulness_metrics(pairs))
    return result


def format_table(rows: list[dict]) -> pd.DataFrame:
    """사람이 읽는 표로 (README·로그용). 잴 수 없는 칸은 '—'."""

    def pct(x) -> str:
        return "—" if x is None or pd.isna(x) else f"{x:.0%}"

    return pd.DataFrame(
        [
            {
                "버전": r["version"],
                "경기": r["n"],
                "Brier": f"{r['brier']:.4f}",
                "Elo 대비 (95% 구간)": f"{r['vs_elo']:+.4f} ({r['vs_elo_low']:+.4f}~{r['vs_elo_high']:+.4f})",
                "검증 가능 가설": pct(r["testable_rate"]),
                "서로 다른 가설": r["distinct"] or "—",
                "쓰인 특성": r["features_used"] or "—",
                "비자명 가설": pct(r["nontrivial_rate"]),
                "근거 있음(판정 난 것 중)": pct(r["supported_rate"]),
                "근거 속 숫자/건": f"{r['numbers_per_rationale']:.1f}",
                "입력에 있는 숫자": pct(r["grounded_rate"]),
                "지어낸 숫자가 있는 근거": pct(r["rationales_with_ungrounded"]),
            }
            for r in rows
            if r["n"]
        ]
    )


# ── DB 읽기 ──


def evaluate_versions(session: Session, season: int) -> list[dict]:
    """DB의 LLM 예측을 (모델, 버전)별로 읽어 채점한다. Elo는 같은 평가 시즌에 저장된 예측을 쓴다."""
    table = build_features(load_matches(session))
    train, test = time_split(table, [season])
    seasons = sorted(set(train["season"]))
    features = test.set_index(test["fixture_id"].astype(int))
    outcomes = pd.Series(test["outcome"].to_numpy(), index=features.index)
    elo = load_probs(session, "elo", f"train{seasons[0]}-{seasons[-1]}")

    verdicts = {(c.feature, c.op, float(c.value), c.claim): c.verdict for c in session.scalars(select(HypothesisCheck))}
    groups: dict[tuple[str, str], list[dict]] = {}
    for p in session.scalars(select(Prediction).where(Prediction.model.in_(["llm", "llm_masked"]))):
        groups.setdefault((p.model, p.version), []).append(
            {"fixture_id": p.fixture_id, "p_home": p.p_home, "p_draw": p.p_draw, "p_away": p.p_away, "rationale": p.rationale, "hypothesis_json": p.hypothesis_json}
        )
    return [score_version(f"{model} {version}", rows, features, outcomes, elo, verdicts) for (model, version), rows in sorted(groups.items())]


def ungrounded_examples(session: Session, season: int, limit: int = 5) -> list[str]:
    """지어낸 숫자가 있는 근거의 예 (사람이 눈으로 확인하기 위해). 검사가 틀리게 잡는 경우를 찾는 데도 쓴다."""
    table = build_features(load_matches(session))
    _, test = time_split(table, [season])
    features = test.set_index(test["fixture_id"].astype(int))
    examples = []
    for p in session.scalars(select(Prediction).where(Prediction.model == "llm").order_by(Prediction.version.desc(), Prediction.fixture_id)):
        if p.fixture_id not in features.index:
            continue
        allowed = allowed_numbers(features.loc[p.fixture_id], (p.p_home, p.p_draw, p.p_away))
        bad = [n for n in NUMBER_RE.findall(p.rationale or "") if not any(math.isclose(float(n), a, abs_tol=1e-9) for a in allowed)]
        if bad:
            examples.append(f"[{p.version}] 입력에 없는 숫자 {bad} ← {p.rationale}")
        if len(examples) >= limit:
            break
    return examples


if __name__ == "__main__":
    from app.db import get_engine

    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    pd.set_option("display.width", 250)
    with Session(get_engine()) as session:
        rows = evaluate_versions(session, season)
        print(format_table(rows).T.to_string(header=False))
        used = Counter()
        for p in session.scalars(select(Prediction).where(Prediction.hypothesis_json.is_not(None))):
            used[(p.version, p.hypothesis_json["feature"])] += 1
        print("\n가설에 쓰인 특성:", dict(used))
        print("\n지어낸 숫자로 잡힌 근거 예:")
        for line in ungrounded_examples(session, season):
            print("  -", line)
