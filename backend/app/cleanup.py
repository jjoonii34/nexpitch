"""가디언 약관(OP Content는 24시간 안에 다시 받거나 지운다)을 지키기 위한 정리 단계 (ADR 0006).

매 배치의 수집 단계가 '아직 가디언이 내보내는 기사'의 collected_at을 갱신하므로,
24시간 넘게 갱신되지 않은 기사 = 더 이상 내보내지 않는 기사 → 연결·번역과 함께 지운다.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.news import Article, ArticleTranslation, article_clubs

RETENTION_HOURS = 24


@dataclass
class CleanupReport:
    """지운 수. 배치 로그용."""

    articles: int = 0
    links: int = 0
    translations: int = 0


def delete_stale(session: Session, now: datetime | None = None, hours: int = RETENTION_HOURS) -> CleanupReport:
    """collected_at이 hours 시간보다 오래된 기사를 연결·번역과 함께 지운다. 외래키 때문에 자식부터 지운다."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    stale = select(Article.id).where(Article.collected_at < cutoff)

    report = CleanupReport()
    report.translations = session.execute(delete(ArticleTranslation).where(ArticleTranslation.article_id.in_(stale))).rowcount
    report.links = session.execute(delete(article_clubs).where(article_clubs.c.article_id.in_(stale))).rowcount
    report.articles = session.execute(delete(Article).where(Article.id.in_(stale))).rowcount
    session.commit()
    return report


def delete_all_translations(session: Session) -> int:
    """번역을 전부 지운다. 가디언 기사를 LLM으로 가공한 결과는 약관상 둘 수 없어서 (ADR 0006, 한 번 실행)."""
    count = session.execute(delete(ArticleTranslation)).rowcount
    session.commit()
    return count


if __name__ == "__main__":
    # 직접 실행: python -m app.cleanup
    from app.db import get_engine

    with Session(get_engine()) as session:
        r = delete_stale(session)
        remaining = session.scalar(select(func.count()).select_from(Article))
        print(f"지움: 기사 {r.articles} · 연결 {r.links} · 번역 {r.translations} | 남은 기사 {remaining}")
