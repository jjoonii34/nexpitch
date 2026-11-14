"""번역 묶음 처리 테스트. 가짜 번역 함수와 메모리 안의 SQLite를 써서 Gemini를 부르지 않는다."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db import create_tables
from app.llm.translate import (
    BATCH_SIZE,
    PROMPT_VERSION,
    TranslatedItem,
    TranslationOutput,
    build_input,
    chunk,
    pending_articles,
    pick_valid,
    translate_pending,
)
from app.models.news import Article, ArticleTranslation


@pytest.fixture
def session():
    """기사 n건이 들어 있는 빈 DB를 만드는 도우미를 돌려준다."""
    engine = create_engine("sqlite://")
    create_tables(engine)
    with Session(engine) as s:
        yield s


def add_articles(session: Session, n: int) -> list[Article]:
    """제목이 'Title k'인 기사 n건. 최신이 k가 큰 쪽."""
    articles = [
        Article(
            url=f"https://a/{k}",
            title=f"Title {k}",
            body_or_summary=f"Summary {k}",
            author=None,
            published_at=datetime(2026, 11, 1, k % 24, tzinfo=timezone.utc),
            source="guardian",
        )
        for k in range(1, n + 1)
    ]
    session.add_all(articles)
    session.commit()
    return articles


def fake_translate(batch: list[Article]) -> TranslationOutput:
    """보낸 기사를 그대로 '번역'한 척 돌려주는 가짜."""
    return TranslationOutput(items=[TranslatedItem(id=a.id, title_ko=f"제목 {a.id}", summary_ko=f"요약 {a.id}") for a in batch])


def test_chunk_splits_into_batches():
    assert chunk(list(range(23)), 10) == [list(range(10)), list(range(10, 20)), [20, 21, 22]]
    assert chunk([], 10) == []


def test_build_input_contains_ids_and_text(session):
    (a,) = add_articles(session, 1)
    text = build_input([a])
    assert f'"id": {a.id}' in text and "Title 1" in text and "Summary 1" in text


def test_pick_valid_drops_unknown_duplicate_and_empty():
    out = TranslationOutput(
        items=[
            TranslatedItem(id=1, title_ko="하나", summary_ko="요약"),
            TranslatedItem(id=1, title_ko="중복", summary_ko="요약"),
            TranslatedItem(id=9, title_ko="엉뚱한 id", summary_ko="요약"),
            TranslatedItem(id=2, title_ko="   ", summary_ko="제목 비어 있음"),
        ]
    )
    picked = pick_valid(out, {1, 2, 3})
    assert list(picked) == [1]
    assert picked[1].title_ko == "하나"


def test_translate_pending_saves_in_batches_newest_first(session):
    add_articles(session, 23)
    report = translate_pending(session, fake_translate, pause_seconds=0)

    assert (report.calls, report.saved, report.skipped, report.errors) == (3, 23, 0, [])
    assert session.scalar(select(func.count()).select_from(ArticleTranslation)) == 23
    assert pending_articles(session) == []
    row = session.scalars(select(ArticleTranslation).where(ArticleTranslation.article_id == 5)).one()
    assert (row.title_ko, row.prompt_version) == ("제목 5", PROMPT_VERSION)


def test_second_run_translates_nothing(session):
    add_articles(session, 3)
    translate_pending(session, fake_translate, pause_seconds=0)
    report = translate_pending(session, fake_translate, pause_seconds=0)
    assert (report.calls, report.saved) == (0, 0)


def test_failed_batch_is_left_for_next_run(session):
    add_articles(session, BATCH_SIZE * 2)
    calls = []

    def flaky(batch):
        calls.append(len(batch))
        if len(calls) == 1:
            raise RuntimeError("network down")
        return fake_translate(batch)

    report = translate_pending(session, flaky, pause_seconds=0)
    assert (report.calls, report.saved) == (2, BATCH_SIZE)
    assert len(report.errors) == 1
    assert len(pending_articles(session)) == BATCH_SIZE  # 실패한 묶음은 남아 있다


def test_missing_item_in_response_is_skipped_not_saved(session):
    a, b = add_articles(session, 2)
    only_a = lambda batch: TranslationOutput(items=[TranslatedItem(id=a.id, title_ko="제목", summary_ko="요약")])  # noqa: E731
    report = translate_pending(session, only_a, pause_seconds=0)
    assert (report.saved, report.skipped) == (1, 1)
    assert [x.id for x in pending_articles(session)] == [b.id]


def test_max_calls_limits_one_run(session):
    add_articles(session, BATCH_SIZE * 3)
    report = translate_pending(session, fake_translate, max_calls=1, pause_seconds=0)
    assert (report.calls, report.saved) == (1, BATCH_SIZE)


def test_rate_limit_error_stops_the_run(session):
    add_articles(session, BATCH_SIZE * 3)

    def limited(batch):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    report = translate_pending(session, limited, pause_seconds=0)
    assert report.calls == 1
    assert any("429" in e for e in report.errors)
