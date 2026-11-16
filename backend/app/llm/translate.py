"""기사 제목·요약을 Gemini로 한국어 번역해 article_translations에 저장한다 (ADR 0005).

호출 1회에 기사 여러 건을 묶어 보낸다 — 무료 한도(분당 15회·하루 500회)를 아끼기 위해.
네트워크가 필요한 부분(translate_batch)과 순수 함수(chunk, build_input, pick_valid)를 나눠 테스트한다.
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.news import Article, ArticleTranslation

MODEL = "gemini-3.5-flash-lite"
PROMPT_VERSION = "v1"  # 프롬프트나 모델을 바꾸면 올린다. 결과 행에 함께 저장된다.
BATCH_SIZE = 10  # 한 번에 보내는 기사 수. 너무 크면 한 묶음 실패의 피해가 크고, 너무 작으면 호출 수가 는다.
SECONDS_BETWEEN_CALLS = 5  # 분당 15회 한도 → 4초 간격이면 충분, 여유를 둔다

SYSTEM_INSTRUCTION = (
    "You translate English football news headlines and summaries into natural Korean for Korean football fans. "
    "Write club and player names the way Korean sports media commonly write them (e.g. 리버풀, 살라, 반 다이크). "
    "Keep the meaning exact; do not add or drop facts. Translate every item and keep each item's id unchanged. "
    "Return JSON only."
)


class TranslatedItem(BaseModel):
    """모델이 돌려줘야 하는 한 건의 모양."""

    id: int
    title_ko: str
    summary_ko: str


class TranslationOutput(BaseModel):
    """모델 응답 전체의 모양. 이 스키마를 API에 넘겨 JSON을 강제한다."""

    items: list[TranslatedItem]


@dataclass
class TranslateReport:
    """한 번 실행의 결과. 배치 로그용."""

    calls: int = 0  # API 호출 수
    saved: int = 0  # 저장한 번역 수
    skipped: int = 0  # 응답에 빠졌거나 모양이 이상해 건너뛴 기사 수
    errors: list[str] = field(default_factory=list)  # 묶음 단위 오류


def chunk(items: list, size: int) -> list[list]:
    """목록을 size개씩 자른다."""
    return [items[i : i + size] for i in range(0, len(items), size)]


def build_input(articles: list[Article]) -> str:
    """기사 묶음을 모델에 보낼 본문(JSON)으로 만든다. id로 응답과 짝을 맞춘다."""
    payload = [{"id": a.id, "title": a.title, "summary": a.body_or_summary} for a in articles]
    return "Translate each item.\n" + json.dumps(payload, ensure_ascii=False)


def pick_valid(output: TranslationOutput, expected_ids: set[int]) -> dict[int, TranslatedItem]:
    """응답에서 우리가 보낸 id에 해당하고 내용이 비어 있지 않은 것만 고른다. 중복 id는 첫 것만 쓴다."""
    picked: dict[int, TranslatedItem] = {}
    for item in output.items:
        if item.id in expected_ids and item.id not in picked and item.title_ko.strip():
            picked[item.id] = item
    return picked


def translate_batch(client, articles: list[Article]) -> TranslationOutput:
    """기사 묶음을 Gemini에 보내 번역 JSON을 받는다. 네트워크가 필요한 유일한 함수."""
    interaction = client.interactions.create(
        model=MODEL,
        system_instruction=SYSTEM_INSTRUCTION,
        input=build_input(articles),
        response_format={"type": "text", "mime_type": "application/json", "schema": TranslationOutput.model_json_schema()},
    )
    return TranslationOutput.model_validate_json(interaction.output_text)


def pending_articles(session: Session, limit: int | None = None) -> list[Article]:
    """현재 프롬프트 버전의 번역이 아직 없는 기사를 최신순으로 고른다 (새 기사부터 번역되도록)."""
    done = select(ArticleTranslation.article_id).where(ArticleTranslation.prompt_version == PROMPT_VERSION)
    query = select(Article).where(Article.id.not_in(done)).order_by(Article.published_at.desc())
    if limit:
        query = query.limit(limit)
    return list(session.scalars(query))


def translate_pending(
    session: Session,
    translate: Callable[[list[Article]], TranslationOutput],
    max_calls: int | None = None,
    pause_seconds: float = SECONDS_BETWEEN_CALLS,
) -> TranslateReport:
    """번역이 없는 기사를 묶음으로 번역해 저장한다. 한 묶음이 실패해도 다음 묶음으로 넘어간다.

    translate는 묶음 → 응답 함수 (실제로는 translate_batch, 테스트에서는 가짜).
    max_calls로 한 번 실행의 호출 수를 막을 수 있다 (하루 한도 보호).
    """
    report = TranslateReport()
    batches = chunk(pending_articles(session), BATCH_SIZE)
    if max_calls is not None:
        batches = batches[:max_calls]

    for i, batch in enumerate(batches):
        if i > 0:
            time.sleep(pause_seconds)
        report.calls += 1
        try:
            output = translate(batch)
        except Exception as error:  # 호출 실패·JSON 깨짐(ValidationError 포함) → 이 묶음은 다음 실행에서 다시
            report.errors.append(f"{type(error).__name__}: {str(error)[:120]}")
            if "429" in str(error):  # 한도 초과면 더 보내 봐야 소용없다
                report.errors.append("한도 초과(429)로 중단. 나머지는 다음 실행에서.")
                break
            continue

        valid = pick_valid(output, {a.id for a in batch})
        for article in batch:
            item = valid.get(article.id)
            if item is None:
                report.skipped += 1
                continue
            session.add(
                ArticleTranslation(
                    article_id=article.id,
                    prompt_version=PROMPT_VERSION,
                    model=MODEL,
                    title_ko=item.title_ko.strip()[:500],
                    summary_ko=item.summary_ko.strip(),
                )
            )
            report.saved += 1
        session.commit()

    return report


if __name__ == "__main__":
    # 직접 실행: python -m app.llm.translate [최대 호출 수]
    import sys

    from google import genai

    from app.db import get_engine
    from app.settings import load_env

    load_env()  # GEMINI_API_KEY를 genai.Client()가 읽는다
    # 응답이 안 오는 호출이 배치 전체를 멈추지 않도록 60초 제한(밀리초 단위). 실제로 2번째 묶음이 몇 분간 멈춘 적이 있다.
    client = genai.Client(http_options={"timeout": 60_000})
    max_calls = int(sys.argv[1]) if len(sys.argv) > 1 else None

    with Session(get_engine()) as session:
        before = len(pending_articles(session))
        print(f"번역 대기 {before}건 → 묶음 {BATCH_SIZE}건씩, 최대 호출 {max_calls or '제한 없음'}")
        report = translate_pending(session, lambda batch: translate_batch(client, batch), max_calls=max_calls)
        print(f"호출 {report.calls} · 저장 {report.saved} · 건너뜀 {report.skipped} · 오류 {len(report.errors)}")
        for e in report.errors:
            print("  -", e)
        print(f"남은 대기 {len(pending_articles(session))}건")
