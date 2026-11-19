"""전술 특성 점검 (4.5단계 ②): 전술 스탯이 '팀의 성격'을 담는가, 그리고 예측에 보태는 것이 있는가.

python -m app.analysis.tactical_run [시즌=2024]

1. 팀 스타일 표 — 팀별 평균 점유율·패스·박스 안 슈팅 비율·만든/내준 xG
2. 반분 안정성 — 한 팀의 경기를 번갈아 둘로 나눠 각 절반의 평균이 얼마나 닮았는지(상관계수).
   높으면 그 스탯은 경기마다 바뀌는 우연이 아니라 팀이 일관되게 가진 성격(전술)이다. 낮으면 잡음이라 특성으로 쓸 가치가 적다.
3. 시즌 안 시간순 평가 — 스탯이 있는 경기만 모아 앞쪽으로 학습, 뒤쪽으로 평가 (Elo와 같은 경기로 비교).
   학습 시즌(2022·2023)에 전술 데이터가 찰 때까지의 잠정 평가다.

계산은 순수 함수, DB 읽기는 __main__에서만.
"""

import sys

import numpy as np
import pandas as pd

from app.analysis.dataset import TACTICAL_COLUMNS, MatchRecord, build_features
from app.analysis.evaluate import brier, paired_brier_diff
from app.analysis.models import fit

STYLE_COLUMNS = ["possession", "passes", "pass_accuracy", "box_shot_share", "xg_for", "xg_against", "goal_diff"]
MIN_MATCHES_PER_TEAM = 6  # 반분 안정성: 절반마다 3경기는 있어야 평균이 의미 있다
MIN_EVAL_MATCHES = 60  # 이보다 적으면 모델 비교를 하지 않는다 (구간이 너무 넓어 아무 말도 못 한다)


def team_match_rows(matches: list[MatchRecord]) -> pd.DataFrame:
    """경기 목록 → (팀, 경기)당 한 줄의 스타일 표. 팀 스탯이 있는 경기만 들어간다."""
    rows = []
    for m in sorted(matches, key=lambda x: x.kickoff):
        for team_id, style, xg_for, xg_against, gf, ga in ((m.home_id, m.home_style, m.home_xg, m.away_xg, m.home_goals, m.away_goals), (m.away_id, m.away_style, m.away_xg, m.home_xg, m.away_goals, m.home_goals)):
            if style is None:
                continue
            rows.append(
                {
                    "team_id": team_id,
                    "kickoff": m.kickoff,
                    "possession": style.possession,
                    "passes": style.passes,
                    "pass_accuracy": style.passes_accurate / style.passes if style.passes and style.passes_accurate is not None else None,
                    "box_shot_share": style.shots_in_box / style.shots if style.shots and style.shots_in_box is not None else None,
                    "xg_for": xg_for,
                    "xg_against": xg_against,
                    "goal_diff": gf - ga,  # 비교용: 결과(운이 많이 섞임)는 스타일보다 덜 안정적일 것으로 예상
                }
            )
    return pd.DataFrame(rows, columns=["team_id", "kickoff", *STYLE_COLUMNS])


def style_table(rows: pd.DataFrame) -> pd.DataFrame:
    """팀별 평균 스타일과 경기 수."""
    table = rows.groupby("team_id")[STYLE_COLUMNS].mean()
    table.insert(0, "matches", rows.groupby("team_id").size())
    return table


def split_half_stability(rows: pd.DataFrame, min_matches: int = MIN_MATCHES_PER_TEAM) -> pd.DataFrame:
    """스탯별 반분 상관: 팀마다 경기를 시간순으로 번갈아(홀·짝) 나눠 각 절반의 평균을 내고, 팀들에 걸쳐 두 절반의 상관계수를 구한다.

    번갈아 나누는 이유: 앞·뒤 절반으로 나누면 시즌 중 변화(감독 교체, 부상)가 섞인다. 홀·짝은 같은 시기를 고르게 담는다.
    """
    ordered = rows.sort_values("kickoff")
    ordered = ordered.assign(half=ordered.groupby("team_id").cumcount() % 2)
    counts = ordered.groupby("team_id").size()
    kept = ordered[ordered["team_id"].isin(counts[counts >= min_matches].index)]
    means = kept.groupby(["team_id", "half"])[STYLE_COLUMNS].mean().unstack("half")
    out = [{"stat": c, "teams": int(means[c].dropna().shape[0]), "split_half_r": means[c].dropna().corr().iloc[0, 1] if means[c].dropna().shape[0] >= 3 else np.nan} for c in STYLE_COLUMNS]
    return pd.DataFrame(out)


def within_season_eval(table: pd.DataFrame, train_share: float = 0.5, min_eval: int = MIN_EVAL_MATCHES) -> pd.DataFrame | None:
    """전술 특성이 전부 채워진 경기만 시간순으로 놓고 앞쪽으로 학습, 뒤쪽으로 평가한다. 경기가 모자라면 None."""
    usable = table.dropna(subset=[c for c in TACTICAL_COLUMNS if c != "formation_change_diff"]).sort_values("kickoff")
    cut = int(len(usable) * train_share)
    train, test = usable.iloc[:cut], usable.iloc[cut:]
    if len(test) < min_eval:
        return None
    outcomes = pd.Series(test["outcome"].to_numpy(), index=test.index)
    probs = {name: fit(name, train).predict_proba(test) for name in ("constant", "elo", "elo+tactical", "tactical")}
    rows = []
    for name, p in probs.items():
        diff, low, high = paired_brier_diff(p, probs["elo"], outcomes)
        rows.append({"model": name, "train": len(train), "test": len(test), "brier": round(brier(p, outcomes), 4), "vs_elo": round(diff, 4), "low": round(low, 4), "high": round(high, 4)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.analysis.dataset import load_matches
    from app.db import get_engine
    from app.models.analysis import Team

    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    pd.set_option("display.width", 220)
    with Session(get_engine()) as session:
        matches = load_matches(session)
        names = {t.id: t.name for t in session.scalars(select(Team))}
    season_matches = [m for m in matches if m.season == season]
    rows = team_match_rows(season_matches)
    print(f"{season} 시즌: 팀 스탯이 있는 경기 {len(rows) // 2} / {len(season_matches)}")

    styles = style_table(rows).rename(index=names).sort_values("possession", ascending=False)
    print("\n팀 스타일 (점유율 순):")
    print(styles.round(2).to_string())

    print("\n반분 안정성 (1에 가까울수록 '팀의 성격', 0에 가까울수록 우연):")
    print(split_half_stability(rows).round(2).to_string(index=False))

    table = build_features(matches)
    table = table[table["season"] == season]
    filled = table[TACTICAL_COLUMNS].notna().mean().round(2).to_dict()
    print("\n전술 특성이 채워진 비율:", filled)
    result = within_season_eval(table)
    if result is None:
        usable = len(table.dropna(subset=[c for c in TACTICAL_COLUMNS if c != "formation_change_diff"]))
        print(f"\n모델 비교는 보류: 전술 특성이 채워진 경기 {usable}개 → 평가용 절반이 {MIN_EVAL_MATCHES}경기 미만 (수집이 더 필요)")
    else:
        print("\n시즌 안 시간순 평가 (잠정):")
        print(result.to_string(index=False))
