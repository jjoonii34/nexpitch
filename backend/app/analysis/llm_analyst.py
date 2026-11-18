"""LLM 분석가 (ADR 0009): 통계 모델과 **같은 숫자**를 Gemini에 주고 승·무·패 확률 + 한국어 근거 + 선발 가설을 JSON으로 받는다.

- 입력은 특성 표의 숫자뿐이다 (기사 텍스트 없음 — 약관, 그리고 공정한 비교).
- masked=True면 팀 이름을 '팀 A / 팀 B'로 가린다 → LLM이 지난 시즌 결과를 '기억'해 맞히는지, '데이터로 추론'하는지 분리하는 실험.
- 네트워크는 ask() 한 곳. 입력 만들기·확률 다듬기는 순수 함수라 가짜 클라이언트로 테스트한다.
"""

import math
from dataclasses import dataclass

import pandas as pd
from pydantic import BaseModel, Field

MODEL = "gemini-3.5-flash-lite"
PROMPT_VERSION = "v1"
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
    interaction = client.interactions.create(
        model=MODEL,
        system_instruction=SYSTEM_INSTRUCTION,
        input=build_input(row, home_name, away_name, masked),
        response_format={"type": "text", "mime_type": "application/json", "schema": AnalystOutput.model_json_schema()},
    )
    out = AnalystOutput.model_validate_json(interaction.output_text)
    p_home, p_draw, p_away = normalize(out.p_home, out.p_draw, out.p_away)
    return AnalystResult(p_home, p_draw, p_away, out.rationale.strip(), out.hypothesis.strip())
