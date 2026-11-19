"""예측 저장·읽기 (predictions 테이블). 통계 모델과 LLM이 같은 모양으로 쌓인다."""

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.analysis.dataset import OUTCOMES
from app.models.analysis import Prediction


def save_probs(session: Session, model: str, version: str, probs: pd.DataFrame, fixture_ids: pd.Series) -> int:
    """확률 표(H, D, A 열)를 한 모델의 예측으로 저장한다. 같은 (모델, 버전)의 기존 행은 교체."""
    ids = [int(i) for i in fixture_ids]
    session.execute(delete(Prediction).where(Prediction.model == model, Prediction.version == version, Prediction.fixture_id.in_(ids)))
    for fixture_id, (_, p) in zip(ids, probs[OUTCOMES].iterrows()):
        session.add(Prediction(fixture_id=fixture_id, model=model, version=version, p_home=float(p["H"]), p_draw=float(p["D"]), p_away=float(p["A"])))
    session.commit()
    return len(ids)


def save_llm(session: Session, model: str, version: str, fixture_id: int, result) -> None:
    """LLM 예측 한 건 (확률 + 근거 + 가설)."""
    session.execute(delete(Prediction).where(Prediction.model == model, Prediction.version == version, Prediction.fixture_id == fixture_id))
    session.add(
        Prediction(
            fixture_id=fixture_id, model=model, version=version, p_home=result.p_home, p_draw=result.p_draw, p_away=result.p_away,
            rationale=result.rationale, hypothesis=result.hypothesis,
            hypothesis_json=getattr(result, "structured", None).model_dump() if getattr(result, "structured", None) else None,
            input_text=getattr(result, "input_text", None),
        )
    )
    session.commit()


def load_probs(session: Session, model: str, version: str) -> pd.DataFrame:
    """한 모델의 예측을 fixture_id를 인덱스로 한 (H, D, A) 표로 읽는다."""
    rows = session.scalars(select(Prediction).where(Prediction.model == model, Prediction.version == version)).all()
    if not rows:
        return pd.DataFrame(columns=OUTCOMES)
    return pd.DataFrame({"H": [r.p_home for r in rows], "D": [r.p_draw for r in rows], "A": [r.p_away for r in rows]}, index=[r.fixture_id for r in rows])


def done_fixture_ids(session: Session, model: str, version: str) -> set[int]:
    """이미 예측이 있는 경기 id (재실행 때 건너뛰기 위해)."""
    return set(session.scalars(select(Prediction.fixture_id).where(Prediction.model == model, Prediction.version == version)))
