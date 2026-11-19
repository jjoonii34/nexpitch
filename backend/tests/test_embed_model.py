"""임베딩 모델 테스트 (ADR 0014). 실력이 스탯에 드러나는 가짜 리그로 정제 규칙·누출 방지·학습을 확인한다 (DB·네트워크 없음)."""

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from app.analysis.dataset import OUTCOMES, MatchRecord
from app.analysis.evaluate import brier
from app.analysis.player_data import COUNT_STATS, FEATURE_NAMES, PlayerLine, PlayerProfile, build_lineup_data

torch = pytest.importorskip("torch")  # requirements-ml.txt를 설치하지 않은 환경(수집 배치)에서는 이 파일을 건너뛴다
from app.analysis.embed_model import Scaler, time_ordered_split, train  # noqa: E402

T0 = datetime(2024, 8, 1, tzinfo=timezone.utc)
IDX = {name: i for i, name in enumerate(FEATURE_NAMES)}


def test_profile_cleaning_rules():
    p = PlayerProfile()
    assert p.vector("M")[IDX["has_history"]] == 0 and p.vector("M")[IDX["pos_M"]] == 1  # 기록 없는 선수: '모름' 표시 + 오늘 명단의 포지션
    p.update(PlayerLine(1, 1, 7, minutes=None, goals=3))  # 벤치에만 있던 경기는 무시
    assert p.minutes == 0
    p.update(PlayerLine(1, 1, 7, minutes=45, position="F", rating=None, goals=None, shots=2))  # 뛰었는데 빈 값 = 0개, 평점은 없음
    p.update(PlayerLine(2, 1, 7, minutes=90, position="F", rating=8.0, goals=1, shots=1))
    v = p.vector()
    assert v[IDX["goals_per90"]] == pytest.approx(1 * 90 / 135) and v[IDX["shots_per90"]] == pytest.approx(3 * 90 / 135)
    assert v[IDX["rating"]] == pytest.approx(8.0)  # 평점이 있던 90분만으로 평균
    assert v[IDX["pos_F"]] == 1 and v[IDX["has_history"]] == 1 and len(v) == len(FEATURE_NAMES)


def league(n_matches: int = 240, seed: int = 0) -> tuple[list[MatchRecord], list[PlayerLine]]:
    """팀 4개, 팀마다 선수 11명. 팀 실력이 선수 스탯(패스·평점)과 승패에 같이 드러난다."""
    rng = np.random.default_rng(seed)
    skill = {1: 1.5, 2: 0.5, 3: -0.5, 4: -1.5}
    squads = {team: frozenset(range(team * 100, team * 100 + 11)) for team in skill}
    pairs = [(h, a) for h in skill for a in skill if h != a]
    matches, lines = [], []
    for i in range(n_matches):
        home, away = pairs[i % len(pairs)]
        edge = skill[home] - skill[away] + 0.3
        p_home = 1 / (1 + np.exp(-edge))
        r = rng.random()
        hg, ag = (2, 0) if r < p_home * 0.8 else (1, 1) if r < p_home * 0.8 + 0.2 else (0, 2)
        matches.append(MatchRecord(id=i, season=2024, kickoff=T0 + timedelta(days=i), home_id=home, away_id=away, home_goals=hg, away_goals=ag, home_starters=squads[home], away_starters=squads[away]))
        for team in (home, away):
            for player in squads[team]:
                lines.append(PlayerLine(i, team, player, minutes=90, position="M", rating=6.5 + 0.5 * skill[team] + rng.normal(0, 0.3), passes=int(40 + 10 * skill[team] + rng.normal(0, 5)), shots=int(rng.integers(0, 3))))
    return matches, lines


def test_build_lineup_data_uses_only_past_matches():
    matches, lines = league(24)
    data = build_lineup_data(matches, lines)
    assert len(data) == 24 and data.home.shape == (24, 11, len(FEATURE_NAMES)) and data.home_mask.sum() == 24 * 11
    assert data.home[0, :, IDX["has_history"]].sum() == 0  # 첫 경기: 그 경기의 기록을 그 경기 입력에 쓰지 않는다
    assert data.home[-1, :, IDX["has_history"]].sum() == 11
    assert set(data.y) <= {0, 1, 2}

    no_lineup = [MatchRecord(**{**matches[0].__dict__, "home_starters": None})]
    assert len(build_lineup_data(no_lineup, lines)) == 0  # 선발 명단이 없는 경기는 표본이 아니다


def test_training_learns_and_predicts_in_shared_format():
    data = build_lineup_data(*league())
    train_data, test_data = time_ordered_split(data)
    assert max(train_data.kickoffs) < min(test_data.kickoffs)  # 과거로 학습, 미래로 평가
    fitted = train(train_data, epochs=200)
    assert fitted.losses[-1] < fitted.losses[0]

    probs = fitted.predict_proba(test_data)
    assert list(probs.columns) == OUTCOMES and list(probs.index) == list(test_data.fixture_ids) and np.allclose(probs.sum(axis=1), 1, atol=1e-5)
    outcomes = pd.Series([OUTCOMES[i] for i in test_data.y], index=test_data.fixture_ids)
    constant = pd.DataFrame([np.bincount(train_data.y, minlength=3) / len(train_data)] * len(test_data), columns=OUTCOMES, index=test_data.fixture_ids)
    assert brier(probs, outcomes) < brier(constant, outcomes)  # 배울 규칙이 있는 데이터에서는 '비율로 찍기'보다 낫다

    again = train(train_data, epochs=200).predict_proba(test_data)
    assert np.allclose(probs.to_numpy(), again.to_numpy())  # 씨앗 고정 → 재현된다


def test_scaler_uses_training_players_only_and_player_vectors():
    data = build_lineup_data(*league(48))
    scaler = Scaler.fit(data)
    assert scaler.mean.shape == (len(COUNT_STATS) + 2,)
    scaled = scaler.apply(data.home)
    assert np.array_equal(scaled[..., IDX["pos_M"]], data.home[..., IDX["pos_M"]])  # 0/1 특성은 건드리지 않는다
    vectors = train(data, epochs=20).player_vectors(data.home[-1])
    assert vectors.shape == (11, 16)
