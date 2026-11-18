"""4단계 실행: 저장된 v2 LLM 가설을 과거(학습) 시즌 경기로 역검증해 hypothesis_checks에 넣는다.

python -m app.analysis.backtest_run [평가 시즌=2024]
- 검증 데이터는 평가 시즌을 뺀 나머지 시즌(= 통계 모델의 학습 시즌). 가설이 나온 경기 자체는 검증에 들어가지 않는다.
- 이미 검증한 예측은 건너뛴다.
"""

import sys
from collections import Counter

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.backtest import CheckResult, check_hypothesis, describe
from app.analysis.dataset import build_features, load_matches
from app.analysis.evaluate import time_split
from app.analysis.llm_analyst import PROMPT_VERSION_V2
from app.models.analysis import HypothesisCheck, Prediction


def pending_predictions(session: Session, version: str = PROMPT_VERSION_V2) -> list[Prediction]:
    """구조화 가설이 있고 아직 검증 행이 없는 LLM 예측."""
    checked = select(HypothesisCheck.prediction_id)
    return list(session.scalars(select(Prediction).where(Prediction.version == version, Prediction.hypothesis_json.is_not(None), Prediction.id.not_in(checked))))


def save_check(session: Session, prediction: Prediction, r: CheckResult) -> HypothesisCheck:
    row = HypothesisCheck(
        prediction_id=prediction.id, feature=r.feature, op=r.op, value=r.value, claim=r.claim,
        n_condition=r.n_condition, n_other=r.n_other, rate_condition=r.rate_condition, rate_other=r.rate_other,
        diff=r.diff, ci_low=r.ci_low, ci_high=r.ci_high, verdict=r.verdict,
    )
    session.add(row)
    return row


def run(session: Session, history: pd.DataFrame, version: str = PROMPT_VERSION_V2) -> Counter:
    """대기 중인 가설을 전부 검증하고 판정별 개수를 돌려준다."""
    counts: Counter = Counter()
    for prediction in pending_predictions(session, version):
        h = prediction.hypothesis_json
        result = check_hypothesis(history, h["feature"], h["op"], float(h["value"]), h["claim"])
        save_check(session, prediction, result)
        counts[result.verdict] += 1
    session.commit()
    return counts


if __name__ == "__main__":
    from app.db import get_engine

    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    with Session(get_engine()) as session:
        table = build_features(load_matches(session))
        history, _ = time_split(table, [season])
        counts = run(session, history)
        print(f"검증 {sum(counts.values())}건 → {dict(counts)} (과거 데이터 {len(history)}경기)")
        for check in session.scalars(select(HypothesisCheck).order_by(HypothesisCheck.id.desc()).limit(5)):
            r = CheckResult(check.feature, check.op, check.value, check.claim, check.n_condition, check.n_other, check.rate_condition, check.rate_other, check.diff, check.ci_low, check.ci_high, check.verdict)
            print(f"  {check.feature} {check.op} {check.value:g} → {describe(r)}")
