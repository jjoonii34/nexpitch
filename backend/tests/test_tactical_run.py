"""전술 점검 테스트. 스타일이 뚜렷한 가짜 팀으로 스타일 표·반분 안정성·시즌 안 평가를 확인한다."""

import numpy as np
import pandas as pd

from app.analysis.dataset import TACTICAL_COLUMNS, MatchRecord, TeamStyle, build_features
from app.analysis.tactical_run import split_half_stability, style_table, team_match_rows, within_season_eval
from tests.test_analysis import biased_season

# 팀마다 고정된 점유율 성향 (1번이 가장 점유형)
POSSESSION = {1: 65, 2: 55, 3: 45, 4: 35}


def styled_season(n: int = 96, seed: int = 0) -> list[MatchRecord]:
    """팀의 점유 성향은 일정하고(작은 흔들림만), 박스 안 슈팅 비율은 팀과 무관한 완전한 우연인 시즌."""
    rng = np.random.default_rng(seed)
    out = []
    for m in biased_season(2024, n=n):
        styles = {}
        for team in (m.home_id, m.away_id):
            possession = POSSESSION[team] + rng.normal(0, 2)
            shots = 10
            styles[team] = TeamStyle(possession=possession, passes=possession * 10, passes_accurate=possession * 8, shots=shots, shots_in_box=int(rng.integers(0, shots + 1)))
        out.append(MatchRecord(**{**m.__dict__, "home_style": styles[m.home_id], "away_style": styles[m.away_id], "home_xg": float(m.home_goals), "away_xg": float(m.away_goals)}))
    return out


def test_style_table_and_rows():
    rows = team_match_rows(styled_season(24) + biased_season(2023, n=6, offset=500))  # 스탯 없는 경기는 빠진다
    assert len(rows) == 48
    table = style_table(rows)
    assert table["matches"].sum() == 48
    assert table["possession"].idxmax() == 1 and table["possession"].idxmin() == 4


def test_split_half_stability_separates_trait_from_noise():
    stability = split_half_stability(team_match_rows(styled_season())).set_index("stat")["split_half_r"]
    assert stability["possession"] > 0.9  # 팀이 일관되게 가진 성격
    assert stability["box_shot_share"] < stability["possession"]  # 우연으로 만든 스탯은 덜 안정적이다


def test_within_season_eval_needs_enough_matches():
    table = build_features(styled_season(240))
    assert within_season_eval(table.head(40)) is None  # 경기가 적으면 비교를 보류한다
    result = within_season_eval(table)
    assert list(result["model"]) == ["constant", "elo", "elo+tactical", "tactical"]
    assert result.set_index("model").loc["elo", "vs_elo"] == 0  # 자기 자신과의 차이는 0
    assert (result["test"] >= 60).all() and table[TACTICAL_COLUMNS[0]].notna().sum() > 0
