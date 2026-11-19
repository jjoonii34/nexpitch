"""승·무·패 확률 모델 세 가지 (ADR 0008). 모두 같은 입력(특성 표)을 받아 같은 모양(확률 표)을 돌려준다.

- constant: 학습 데이터의 승·무·패 비율을 그대로 — 비교선 ("아무것도 모를 때")
- elo: Elo 차이 하나만 쓰는 로지스틱 회귀 — 가장 단순한 통계 모델
- features: Elo 차이 + 흐름·휴식일·xG·선발 변경 — 라인업·스탯 데이터가 예측에 보태는 것이 있는지 보는 모델
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from app.analysis.dataset import FEATURE_COLUMNS, OUTCOMES, TACTICAL_COLUMNS

MODEL_FEATURES = {
    "constant": [],
    "elo": ["elo_diff"],
    "features": FEATURE_COLUMNS,
}

# 실험용 모델 (4.5단계 ②). 기본 채점(run·llm_run)에는 넣지 않는다 — 학습 시즌에 전술 데이터가 아직 없어 같은 표에 놓으면 오해를 부른다.
# 평가는 analysis/tactical_run.py가 스탯이 있는 경기만으로 따로 한다.
EXPERIMENTAL_FEATURES = {
    "tactical": FEATURE_COLUMNS + TACTICAL_COLUMNS,  # 팀 스타일·xG 공수·포메이션 변경을 더한 모델
    "elo+tactical": ["elo_diff"] + TACTICAL_COLUMNS,  # Elo에 전술 특성만 더한 모델 (전술 특성의 순수한 기여를 보기 위해)
}


@dataclass
class FittedModel:
    name: str
    columns: list[str]
    pipeline: Pipeline | None  # constant 모델은 None
    class_probs: np.ndarray  # constant 모델이 쓰는 비율 (H, D, A 순)

    def predict_proba(self, X: pd.DataFrame) -> pd.DataFrame:
        """경기별 (H, D, A) 확률. 행 순서는 입력과 같다."""
        if self.pipeline is None:
            probs = np.tile(self.class_probs, (len(X), 1))
        else:
            raw = self.pipeline.predict_proba(X[self.columns])
            order = [list(self.pipeline.classes_).index(o) for o in OUTCOMES]  # sklearn은 클래스를 알파벳순으로 둔다
            probs = raw[:, order]
        return pd.DataFrame(probs, columns=OUTCOMES, index=X.index)


def fit(name: str, train: pd.DataFrame) -> FittedModel:
    """이름에 맞는 모델을 학습한다. NaN 특성은 학습 데이터 평균으로 채운다 (시즌 초 경기 등)."""
    columns = {**MODEL_FEATURES, **EXPERIMENTAL_FEATURES}[name]
    class_probs = np.array([(train["outcome"] == o).mean() for o in OUTCOMES])
    if not columns:
        return FittedModel(name, [], None, class_probs)
    pipeline = make_pipeline(SimpleImputer(strategy="mean"), StandardScaler(), LogisticRegression(max_iter=1000))
    pipeline.fit(train[columns], train["outcome"])
    return FittedModel(name, columns, pipeline, class_probs)
