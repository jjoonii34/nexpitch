"""3단계 실행: 평가 시즌 경기마다 LLM 분석가에게 묻고 저장한 뒤, 통계 모델과 같은 표로 채점한다.

python -m app.analysis.llm_run [평가 시즌=2024] [최대 호출 수=400] [가린 변형 경기 수=100] [프롬프트 버전=v1]
python -m app.analysis.llm_run 2024 100 100 v2   # 4단계: 고르게 뽑은 100경기에서 틀+숫자 가설만 모은다

- 이미 예측이 있는 경기는 건너뛴다 → 중간에 멈춰도 다시 실행하면 이어서 한다.
- 가린 변형(llm_masked)은 비용을 아끼려 일부 경기(시즌을 고르게 나눠 뽑음)에만 묻고, 그 경기들에 대해서만 가림/안 가림을 비교한다.
"""

import sys
import time

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.dataset import OUTCOMES, build_features, load_matches
from app.analysis.evaluate import summarize, time_split
from app.analysis.llm_analyst import PROMPT_VERSION, PROMPT_VERSION_V2, SECONDS_BETWEEN_CALLS, ask, ask_v2
from app.analysis.models import MODEL_FEATURES, fit
from app.analysis.predictions import done_fixture_ids, load_probs, save_llm, save_probs
from app.models.analysis import Team


def team_names(session: Session) -> dict[int, str]:
    return {t.id: t.name for t in session.scalars(select(Team))}


def masked_subset(test: pd.DataFrame, n: int) -> pd.DataFrame:
    """시즌 전체에서 고르게 n경기 뽑는다 (시즌 초·중·후반이 섞이게)."""
    if n <= 0:
        return test.iloc[0:0]
    if n >= len(test):
        return test
    step = len(test) / n
    return test.iloc[[int(i * step) for i in range(n)]]


def run_llm(session: Session, client, test: pd.DataFrame, names: dict[int, str], home_ids: dict[int, int], away_ids: dict[int, int], model: str, masked: bool, max_calls: int, pause: float = SECONDS_BETWEEN_CALLS, version: str = PROMPT_VERSION) -> tuple[int, list[str]]:
    """아직 예측이 없는 경기에 대해 LLM을 부른다. (호출 수, 오류 목록). version이 v2면 틀+숫자 가설을 받는다."""
    asker = ask_v2 if version == PROMPT_VERSION_V2 else ask
    done = done_fixture_ids(session, model, version)
    calls, errors = 0, []
    for _, row in test.iterrows():
        fixture_id = int(row["fixture_id"])
        if fixture_id in done or calls >= max_calls:
            continue
        if calls > 0:
            time.sleep(pause)
        calls += 1
        try:
            result = asker(client, row, names.get(home_ids[fixture_id], "?"), names.get(away_ids[fixture_id], "?"), masked=masked)
        except Exception as error:  # 한 경기 실패는 기록만 하고 계속; 한도(429)면 멈춘다
            errors.append(f"{fixture_id}: {str(error)[:100]}")
            if "429" in str(error):
                break
            continue
        save_llm(session, model, version, fixture_id, result)
    return calls, errors


def score_table(session: Session, train: pd.DataFrame, test: pd.DataFrame, train_label: str) -> pd.DataFrame:
    """통계 모델(다시 학습해 저장) + LLM + 결합을 같은 평가 경기로 채점한다. LLM 예측이 없는 경기는 LLM 쪽 표에서만 빠진다."""
    rows = []
    stat_probs = {}
    for name in MODEL_FEATURES:
        probs = fit(name, train).predict_proba(test)
        probs.index = test["fixture_id"].to_numpy()
        save_probs(session, name, train_label, probs, test["fixture_id"])
        stat_probs[name] = probs
        rows.append(summarize(name, probs, pd.Series(test["outcome"].to_numpy(), index=probs.index)))

    outcomes = pd.Series(test["outcome"].to_numpy(), index=test["fixture_id"].to_numpy())
    llm = load_probs(session, "llm", PROMPT_VERSION)
    llm = llm[llm.index.isin(outcomes.index)]
    if len(llm):
        sub = outcomes.loc[llm.index]
        rows.append(summarize("llm", llm, sub))
        combined = (llm[OUTCOMES] + stat_probs["elo"].loc[llm.index, OUTCOMES]) / 2  # 단순 평균 (가중치 학습은 다음 단계)
        save_probs(session, "combined", f"{PROMPT_VERSION}+elo", combined, pd.Series(llm.index))
        rows.append(summarize("combined(llm+elo)", combined, sub))
        rows.append(summarize("elo (같은 경기)", stat_probs["elo"].loc[llm.index], sub))

    masked = load_probs(session, "llm_masked", PROMPT_VERSION)
    masked = masked[masked.index.isin(outcomes.index)]
    if len(masked):
        sub = outcomes.loc[masked.index]
        rows.append(summarize(f"llm_masked ({len(masked)}경기)", masked, sub))
        both = llm.index.intersection(masked.index)
        if len(both):
            rows.append(summarize(f"llm, 같은 {len(both)}경기", llm.loc[both], outcomes.loc[both]))
            rows.append(summarize(f"elo, 같은 {len(both)}경기", stat_probs["elo"].loc[both], outcomes.loc[both]))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    from google import genai

    from app.db import get_engine
    from app.settings import load_env

    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    max_calls = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    masked_n = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    version = sys.argv[4] if len(sys.argv) > 4 else PROMPT_VERSION
    load_env()
    client = genai.Client(http_options={"timeout": 60_000})

    with Session(get_engine()) as session:
        matches = load_matches(session)
        table = build_features(matches)
        train, test = time_split(table, [season])
        names = team_names(session)
        home_ids = {m.id: m.home_id for m in matches}
        away_ids = {m.id: m.away_id for m in matches}

        if version == PROMPT_VERSION_V2:  # 4단계용: 시즌에서 고르게 masked_n경기만 가설을 모은다 (채점은 v1 표 그대로)
            calls, errors = run_llm(session, client, masked_subset(test, masked_n), names, home_ids, away_ids, "llm", False, max_calls, version=version)
            print(f"llm v2: 호출 {calls} · 오류 {len(errors)}")
            for e in errors[:5]:
                print("  -", e)
            sys.exit(0)

        calls, errors = run_llm(session, client, test, names, home_ids, away_ids, "llm", False, max_calls)
        print(f"llm: 호출 {calls} · 오류 {len(errors)}")
        left = max(0, max_calls - calls)
        calls_m, errors_m = run_llm(session, client, masked_subset(test, masked_n), names, home_ids, away_ids, "llm_masked", True, left)
        print(f"llm_masked: 호출 {calls_m} · 오류 {len(errors_m)}")
        for e in (errors + errors_m)[:5]:
            print("  -", e)

        seasons = sorted(set(train["season"]))
        print(score_table(session, train, test, f"train{seasons[0]}-{seasons[-1]}").to_string(index=False))
