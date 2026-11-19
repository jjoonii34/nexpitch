"""LLM 분석가 (ADR 0009): 통계 모델과 **같은 숫자**를 Gemini에 주고 승·무·패 확률 + 한국어 근거 + 선발 가설을 JSON으로 받는다.

- 입력은 특성 표의 숫자뿐이다 (기사 텍스트 없음 — 약관, 그리고 공정한 비교).
- masked=True면 팀 이름을 '팀 A / 팀 B'로 가린다 → LLM이 지난 시즌 결과를 '기억'해 맞히는지, '데이터로 추론'하는지 분리하는 실험.
- 네트워크는 ask() 한 곳. 입력 만들기·확률 다듬기는 순수 함수라 가짜 클라이언트로 테스트한다.
"""

import math
from dataclasses import dataclass
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

MODEL = "gemini-3.5-flash-lite"
PROMPT_VERSION = "v1"  # 자유 문장 가설 (3단계 채점에 쓴 버전)
PROMPT_VERSION_V2 = "v2"  # 가설을 틀+숫자로 제한 (4단계 역검증용, ADR 0010)
SECONDS_BETWEEN_CALLS = 4.5  # 분당 15회 한도

SYSTEM_INSTRUCTION = (
    "You are a football data analyst. You receive pre-match numbers for one Premier League match and must output a JSON object. "
    "Rules: (1) p_home, p_draw, p_away are probabilities that sum to 1. (2) Base your estimate ONLY on the numbers given; "
    "do not use memory of real results. If a number is missing, say so in the rationale instead of guessing. "
    "(3) rationale: 2-3 sentences in Korean explaining which numbers drove the estimate. "
    "(4) hypothesis: one testable sentence in Korean about lineup or tactics (e.g. '선발 변경이 3명 이상이면 이 팀의 승률이 낮아진다'), "
    "phrased so it could be checked against past data. Output JSON only."
)


class AnalystOutput(BaseModel):
    """모델이 돌려줘야 하는 모양. 스키마를 API에 넘겨 JSON을 강제한다."""

    p_home: float = Field(ge=0, le=1)
    p_draw: float = Field(ge=0, le=1)
    p_away: float = Field(ge=0, le=1)
    rationale: str
    hypothesis: str


@dataclass
class AnalystResult:
    p_home: float
    p_draw: float
    p_away: float
    rationale: str
    hypothesis: str
    input_text: str | None = None  # 모델에 보낸 입력 그대로 (예측과 함께 저장해 나중에 근거를 대조한다)


def _fmt(value, digits: int = 1) -> str:
    """NaN/None은 '정보 없음'으로. 모델이 없는 값을 지어내지 않게 분명히 표시한다."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "not available"
    return f"{value:.{digits}f}"


def build_input(row: pd.Series, home_name: str, away_name: str, masked: bool = False) -> str:
    """특성 표의 한 행을 모델에 보낼 글로 만든다. 통계 모델이 쓰는 열과 같은 숫자만 넣는다."""
    home, away = ("Team A (home)", "Team B (away)") if masked else (f"{home_name} (home)", f"{away_name} (away)")
    lines = [
        f"Match: {home} vs {away}",
        f"Elo difference (home + home advantage - away): {_fmt(row.get('elo_diff'), 0)}",
        f"Last-5 points difference (home - away): {_fmt(row.get('form_diff'), 0)}",
        f"Last-5 goal difference gap (home - away): {_fmt(row.get('goal_diff_form'), 0)}",
        f"Rest days difference (home - away): {_fmt(row.get('rest_diff'), 1)}",
        f"Last-5 xG difference gap (home - away): {_fmt(row.get('xg_diff_form'), 2)}",
        f"Starting-XI changes vs previous match, difference (home - away): {_fmt(row.get('lineup_changes_diff'), 0)}",
        "Return the JSON object.",
    ]
    return "\n".join(lines)


def normalize(p_home: float, p_draw: float, p_away: float, floor: float = 0.02) -> tuple[float, float, float]:
    """확률 세 개를 합 1로 맞춘다. 0은 floor로 올려 로그 손실이 무한대가 되지 않게 한다 (채점의 공정성: 통계 모델도 0을 내지 않는다)."""
    values = [max(float(p), floor) for p in (p_home, p_draw, p_away)]
    total = sum(values)
    return tuple(v / total for v in values)  # type: ignore[return-value]


def ask(client, row: pd.Series, home_name: str, away_name: str, masked: bool = False) -> AnalystResult:
    """Gemini에 한 경기를 묻는다. 네트워크가 필요한 유일한 함수."""
    text = build_input(row, home_name, away_name, masked)
    interaction = client.interactions.create(
        model=MODEL,
        system_instruction=SYSTEM_INSTRUCTION,
        input=text,
        response_format={"type": "text", "mime_type": "application/json", "schema": AnalystOutput.model_json_schema()},
    )
    out = AnalystOutput.model_validate_json(interaction.output_text)
    p_home, p_draw, p_away = normalize(out.p_home, out.p_draw, out.p_away)
    return AnalystResult(p_home, p_draw, p_away, out.rationale.strip(), out.hypothesis.strip(), input_text=text)


# ── v2: 검증 가능한 가설 (ADR 0010) ──

HYPOTHESIS_FEATURES = {
    # 가설에 쓸 수 있는 특성 — 전부 '홈 − 원정' 차이 열이라 과거 경기에서 바로 셀 수 있다
    "lineup_changes_diff": "starting-XI changes difference (home - away)",
    "rest_diff": "rest days difference (home - away)",
    "elo_diff": "Elo difference (home + home advantage - away)",
    "form_diff": "last-5 points difference (home - away)",
    "xg_diff_form": "last-5 xG difference gap (home - away)",
}
FeatureName = Literal["lineup_changes_diff", "rest_diff", "elo_diff", "form_diff", "xg_diff_form"]


class Hypothesis(BaseModel):
    """검증 가능한 가설 한 개: '<특성>이 <op> <value>이면 홈 승률이 <claim>'."""

    feature: FeatureName
    op: Literal[">=", "<="]
    value: float
    claim: Literal["home_win_rate_higher", "home_win_rate_lower"]
    reason: str  # 한국어 한 문장


class AnalystOutputV2(BaseModel):
    p_home: float = Field(ge=0, le=1)
    p_draw: float = Field(ge=0, le=1)
    p_away: float = Field(ge=0, le=1)
    rationale: str
    hypothesis: Hypothesis


SYSTEM_INSTRUCTION_V2 = (
    SYSTEM_INSTRUCTION.split("(4) hypothesis:")[0]
    + "(4) hypothesis: ONE testable rule built only from these features: "
    + ", ".join(f"{k} = {v}" for k, v in HYPOTHESIS_FEATURES.items())
    + ". Choose a feature, an operator (>= or <=), a numeric threshold, and whether the home win rate should be higher or lower when the condition holds. "
    + "Add a one-sentence Korean reason. Output JSON only."
)


@dataclass
class AnalystResultV2(AnalystResult):
    structured: Hypothesis | None = None


def hypothesis_text(h: Hypothesis) -> str:
    """구조화 가설을 사람이 읽는 한 줄로 (DB의 hypothesis 열과 화면용)."""
    direction = "높다" if h.claim == "home_win_rate_higher" else "낮다"
    return f"{h.feature} {h.op} {h.value:g} 이면 홈 승률이 {direction} — {h.reason}"


def ask_v2(client, row: pd.Series, home_name: str, away_name: str, masked: bool = False) -> AnalystResultV2:
    """v2: 같은 입력, 가설만 틀+숫자로 받는다."""
    text = build_input(row, home_name, away_name, masked)
    interaction = client.interactions.create(
        model=MODEL,
        system_instruction=SYSTEM_INSTRUCTION_V2,
        input=text,
        response_format={"type": "text", "mime_type": "application/json", "schema": AnalystOutputV2.model_json_schema()},
    )
    out = AnalystOutputV2.model_validate_json(interaction.output_text)
    p_home, p_draw, p_away = normalize(out.p_home, out.p_draw, out.p_away)
    return AnalystResultV2(p_home, p_draw, p_away, out.rationale.strip(), hypothesis_text(out.hypothesis), input_text=text, structured=out.hypothesis)
# ── v3: 전술 숫자를 주고, Elo 단독 가설을 막는다 (4.5단계 ③, ADR 0013) ──
# v2 가설 97건이 전부 elo_diff였다(ADR 0010). v3는 (1) 입력에 전술 특성을 더하고 (2) 가설에 쓸 수 있는 특성 목록에서 elo_diff를 뺀다.
# '금지'를 부탁하는 문장이 아니라 출력 스키마로 막는다 — 스키마에 없는 값은 모델이 낼 수 없다.

PROMPT_VERSION_V3 = "v3"

TACTICAL_INPUT_LINES = [
    # (특성 열, 모델에 보여줄 설명, 소수 자릿수)
    ("possession_diff", "Last-5 average possession % difference (home - away)", 1),
    ("pass_volume_diff", "Last-5 passes per match difference (home - away)", 0),
    ("pass_accuracy_diff", "Last-5 pass accuracy difference, 0-1 scale (home - away)", 3),
    ("box_shot_share_diff", "Last-5 share of shots taken inside the box, 0-1 scale, difference (home - away)", 3),
    ("xg_for_diff", "Last-5 xG created per match difference (home - away)", 2),
    ("xg_against_diff", "Last-5 xG conceded per match difference (home - away; lower is better for home)", 2),
    ("formation_change_diff", "Formation changed vs previous match, 1 or 0, difference (home - away)", 0),
]

HYPOTHESIS_FEATURES_V3 = {
    "form_diff": "last-5 points difference",
    "rest_diff": "rest days difference",
    "lineup_changes_diff": "starting-XI changes difference",
    "possession_diff": "last-5 average possession % difference",
    "pass_volume_diff": "last-5 passes per match difference",
    "pass_accuracy_diff": "last-5 pass accuracy difference (0-1)",
    "box_shot_share_diff": "last-5 inside-box shot share difference (0-1)",
    "xg_for_diff": "last-5 xG created per match difference",
    "xg_against_diff": "last-5 xG conceded per match difference",
    "formation_change_diff": "formation changed (1/0) difference",
}
FeatureNameV3 = Literal[
    "form_diff", "rest_diff", "lineup_changes_diff", "possession_diff", "pass_volume_diff",
    "pass_accuracy_diff", "box_shot_share_diff", "xg_for_diff", "xg_against_diff", "formation_change_diff",
]


class HypothesisV3(Hypothesis):
    """v2와 같은 틀이지만 고를 수 있는 특성이 다르다: Elo가 없고 전술 특성이 있다."""

    feature: FeatureNameV3  # type: ignore[assignment]


class AnalystOutputV3(BaseModel):
    p_home: float = Field(ge=0, le=1)
    p_draw: float = Field(ge=0, le=1)
    p_away: float = Field(ge=0, le=1)
    rationale: str
    hypothesis: HypothesisV3


SYSTEM_INSTRUCTION_V3 = (
    SYSTEM_INSTRUCTION.split("(4) hypothesis:")[0]
    + "In the rationale, explain HOW the two teams play using the style numbers (possession, passing, shot quality, xG created and conceded), not only who is stronger. "
    + "(4) hypothesis: ONE testable tactical rule built only from these features: "
    + ", ".join(f"{k} = {v} (home - away)" for k, v in HYPOTHESIS_FEATURES_V3.items())
    + ". Use a feature whose value IS given for this match (never one marked 'not available'), preferably the one that stands out most. "
    + "Elo difference is not allowed as the hypothesis feature: 'the stronger team wins' is not a useful hypothesis. "
    + "Choose an operator (>= or <=), a numeric threshold near this match's value, and whether the home win rate should be higher or lower when the condition holds. "
    + "Add a one-sentence Korean reason. Output JSON only."
)


def build_input_v3(row: pd.Series, home_name: str, away_name: str, masked: bool = False) -> str:
    """v1 입력에 전술 숫자 7줄을 더한다. 스탯이 없는 경기는 'not available'로 보인다."""
    base = build_input(row, home_name, away_name, masked).split("\n")
    tactical = [f"{label}: {_fmt(row.get(column), digits)}" for column, label, digits in TACTICAL_INPUT_LINES]
    return "\n".join(base[:-1] + tactical + base[-1:])


def ask_v3(client, row: pd.Series, home_name: str, away_name: str, masked: bool = False) -> AnalystResultV2:
    """v3: 전술 숫자를 포함한 입력, Elo를 고를 수 없는 가설 틀."""
    text = build_input_v3(row, home_name, away_name, masked)
    interaction = client.interactions.create(
        model=MODEL,
        system_instruction=SYSTEM_INSTRUCTION_V3,
        input=text,
        response_format={"type": "text", "mime_type": "application/json", "schema": AnalystOutputV3.model_json_schema()},
    )
    out = AnalystOutputV3.model_validate_json(interaction.output_text)
    p_home, p_draw, p_away = normalize(out.p_home, out.p_draw, out.p_away)
    return AnalystResultV2(p_home, p_draw, p_away, out.rationale.strip(), hypothesis_text(out.hypothesis), input_text=text, structured=out.hypothesis)
