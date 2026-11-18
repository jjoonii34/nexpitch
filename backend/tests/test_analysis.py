"""통계 기준선 테스트. DB 없이 직접 만든 경기 목록으로 Elo·특성(정보 누출 금지)·모델·지표를 검사한다."""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from app.analysis.dataset import OUTCOMES, MatchRecord, build_features, outcome
from app.analysis.elo import EloTable, expected_score
from app.analysis.evaluate import accuracy, brier, brier_each, log_loss, paired_brier_diff, time_split
from app.analysis.models import fit
from app.analysis.run import run

T0 = datetime(2022, 8, 6, 15, 0, tzinfo=timezone.utc)


def match(i: int, home: int, away: int, hg: int, ag: int, season: int = 2022, days: int | None = None, **extra) -> MatchRecord:
    """i번째 경기 (기본으로 7일 간격)."""
    return MatchRecord(id=i, season=season, kickoff=T0 + timedelta(days=days if days is not None else 7 * i), home_id=home, away_id=away, home_goals=hg, away_goals=ag, **extra)


def test_elo_moves_rating_toward_winner_and_home_advantage_counts():
    elo = EloTable()
    assert expected_score(1500, 1500, home_advantage=0) == 0.5
    assert expected_score(1500, 1500) > 0.5  # 홈 이점
    elo.update(1, 2, 3, 0)
    assert elo.get(1) > 1500 > elo.get(2)
    assert abs((elo.get(1) - 1500) + (elo.get(2) - 1500)) < 1e-9  # 점수 총합은 보존


def test_features_use_only_past_matches():
    matches = [match(1, 10, 20, 2, 0), match(2, 20, 10, 0, 0), match(3, 10, 20, 1, 3)]
    table = build_features(matches)
    first, second, third = table.iloc[0], table.iloc[1], table.iloc[2]
    assert pd.isna(first["form_diff"]) and first["elo_diff"] == 60.0  # 첫 경기: 기록 없음, 홈 이점만
    assert second["elo_diff"] < 60.0  # 10번 팀이 이겨서 20번(홈)이 낮아짐
    assert second["form_diff"] == 0 - 3  # 홈 20번 0점, 원정 10번 3점
    assert third["form_diff"] == (3 + 1) - (0 + 1)
    assert third["rest_diff"] == 0  # 둘 다 7일 휴식
    assert list(table["outcome"]) == ["H", "D", "A"]


def test_lineup_changes_and_xg_features_appear_only_when_data_exists():
    xi_a, xi_b = frozenset(range(1, 12)), frozenset(range(3, 14))  # 2명 교체
    matches = [
        match(1, 10, 20, 1, 0, home_starters=xi_a, home_xg=1.5, away_xg=0.5),
        match(2, 10, 20, 0, 0, home_starters=xi_b, home_xg=1.0, away_xg=1.0),
        match(3, 20, 10, 0, 0),
    ]
    table = build_features(matches)
    assert pd.isna(table.iloc[0]["lineup_changes_diff"])
    assert pd.isna(table.iloc[1]["lineup_changes_diff"])  # 원정 20번의 선발 정보가 없다 → 차이를 못 구함
    assert table.iloc[1]["xg_diff_form"] == pytest.approx(1.0 - (-1.0))
    assert pd.isna(table.iloc[2]["lineup_changes_diff"])


def biased_season(season: int, n: int = 60, offset: int = 0) -> list[MatchRecord]:
    """팀 1이 강하고 팀 4가 약한 가짜 시즌: 모델이 배울 규칙성이 있다."""
    strength = {1: 3, 2: 2, 3: 1, 4: 0}
    out = []
    pairs = [(h, a) for h in strength for a in strength if h != a]
    for i in range(n):
        h, a = pairs[i % len(pairs)]
        hg, ag = strength[h] + (1 if i % 3 == 0 else 0), strength[a]
        out.append(match(offset + i, h, a, hg, ag, season=season, days=i * 3))
    return out


def test_models_beat_constant_baseline_on_learnable_data():
    matches = biased_season(2022) + biased_season(2023, offset=1000)
    results = run(matches, test_seasons=[2023]).set_index("model")
    assert results.loc["elo", "brier"] < results.loc["constant", "brier"]
    assert results.loc["features", "brier"] < results.loc["constant", "brier"]
    assert set(results.index) == {"constant", "elo", "features"}


def test_metrics_perfect_and_constant():
    outcomes = pd.Series(["H", "D", "A"])
    perfect = pd.DataFrame([[1, 0, 0], [0, 1, 0], [0, 0, 1]], columns=OUTCOMES)
    assert brier(perfect, outcomes) == 0 and log_loss(perfect, outcomes) < 1e-9 and accuracy(perfect, outcomes) == 1
    uniform = pd.DataFrame([[1 / 3] * 3] * 3, columns=OUTCOMES)
    assert brier(uniform, outcomes) == pytest.approx(2 / 3)


def test_time_split_and_constant_model_probs():
    matches = biased_season(2022, n=12) + biased_season(2023, n=6, offset=100)
    table = build_features(matches)
    train, test = time_split(table, [2023])
    assert set(train["season"]) == {2022} and set(test["season"]) == {2023}
    probs = fit("constant", train).predict_proba(test)
    assert probs.shape == (6, 3) and probs.sum(axis=1).round(6).eq(1).all()
    assert outcome(2, 1) == "H" and outcome(0, 0) == "D"


def test_paired_brier_diff_prefers_better_model():
    outcomes = pd.Series(["H", "A", "D", "H"] * 10, index=range(40))
    perfect = pd.DataFrame([{c: 1.0 if c == o else 0.0 for c in OUTCOMES} for o in outcomes], index=outcomes.index)
    flat = pd.DataFrame([{c: 1 / 3 for c in OUTCOMES}] * 40, index=outcomes.index)
    assert brier_each(perfect, outcomes).sum() == 0
    diff, low, high = paired_brier_diff(perfect, flat, outcomes)
    assert diff < 0 and high < 0  # 완벽한 모델이 확실히 낫다
    assert paired_brier_diff(flat, flat, outcomes) == (0.0, 0.0, 0.0)
