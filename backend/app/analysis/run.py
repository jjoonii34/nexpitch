"""통계 기준선을 한 번 돌려 결과 표를 찍는다: python -m app.analysis.run [평가 시즌, 기본 2024]

학습: 평가 시즌을 뺀 나머지 시즌. 평가: 그 시즌 전체. 특성은 평가 시즌 경기도 '그 전까지'의 기록으로 만들므로 누출이 없다.
"""

import sys

import pandas as pd
from sqlalchemy.orm import Session

from app.analysis.dataset import FEATURE_COLUMNS, build_features, load_matches
from app.analysis.evaluate import summarize, time_split
from app.analysis.models import MODEL_FEATURES, fit


def run(matches, test_seasons: list[int]) -> pd.DataFrame:
    """경기 목록 → 특성 → 세 모델 학습·평가 → 결과 표."""
    table = build_features(matches)
    train, test = time_split(table, test_seasons)
    rows = []
    for name in MODEL_FEATURES:
        model = fit(name, train)
        rows.append(summarize(name, model.predict_proba(test), test["outcome"]))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    from app.db import get_engine

    test_seasons = [int(sys.argv[1])] if len(sys.argv) > 1 else [2024]
    with Session(get_engine()) as session:
        matches = load_matches(session)
    table = build_features(matches)
    print(f"경기 {len(matches)}건 | 평가 시즌 {test_seasons} | 특성 채워진 비율:")
    for col in FEATURE_COLUMNS:
        print(f"  {col:<22} {table[col].notna().mean():>5.0%}")
    print(run(matches, test_seasons).to_string(index=False))
