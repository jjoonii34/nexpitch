"""24시간 보관 정리 테스트. 메모리 안의 SQLite를 쓴다."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cleanup import delete_all_translations, delete_stale
from app.models.news import Article, ArticleTranslation, Club, article_clubs
from app.storage import save_articles
from tests.conftest import NOW, make_article, make_club, make_raw


def seed(session: Session, url: str, seen_hours_ago: float, club: Club) -> Article:
    """club에 연결되고 번역 1건이 붙은 기사를 seen_hours_ago 시간 전에 확인한 것으로 만든다."""
    a = make_article(session, url, collected_at=NOW - timedelta(hours=seen_hours_ago))
    a.clubs.append(club)
    a.translations.append(ArticleTranslation(prompt_version="v1", model="m", title_ko="제목", summary_ko="요약"))
    session.commit()
    return a


def counts(session: Session) -> tuple[int, int, int]:
    return tuple(session.scalar(select(func.count()).select_from(t)) for t in (Article, article_clubs, ArticleTranslation))


def test_stale_article_is_deleted_with_links_and_translations(session):
    club = make_club(session, "Liverpool")
    seed(session, "https://old", 25, club)
    seed(session, "https://fresh", 23, club)

    report = delete_stale(session, now=NOW)

    assert (report.articles, report.links, report.translations) == (1, 1, 1)
    assert counts(session) == (1, 1, 1)
    assert session.scalars(select(Article.url)).all() == ["https://fresh"]


def test_reseen_article_gets_retention_extended(session):
    club = make_club(session, "Liverpool")
    old = seed(session, "https://old", 30, club)

    save_articles(session, [make_raw("https://old")], club)  # 가디언이 아직 내보내는 기사 → 다시 봤다
    session.refresh(old)
    real_now = datetime.now(timezone.utc)  # 갱신은 실제 시각으로 되므로 실제 시각 기준으로 본다
    assert old.collected_at.replace(tzinfo=timezone.utc) > real_now - timedelta(minutes=1)
    assert delete_stale(session, now=real_now).articles == 0


def test_delete_all_translations(session):
    club = make_club(session, "Liverpool")
    seed(session, "https://a", 1, club)
    assert delete_all_translations(session) == 1
    assert counts(session) == (1, 1, 0)
