"""수집한 기사를 DB에 저장한다. 같은 기사(url)는 한 번만 저장한다."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import RawArticle
from app.models.news import Article, Club, utc_now


@dataclass
class SaveResult:
    """저장 결과. 배치 로그에 '새 기사 몇 건'을 남기기 위해 센다."""

    new_articles: int = 0  # 처음 저장한 기사 수
    new_links: int = 0  # 새로 생긴 기사 ↔ 구단 연결 수


def save_articles(session: Session, raws: list[RawArticle], club: Club) -> SaveResult:
    """한 구단의 태그로 수집한 기사들을 저장하고 그 구단과 연결한다.

    이미 있는 기사(url 일치)는 다시 저장하지 않고 연결만 추가하며, '마지막 확인 시각'을 갱신한다
    — 리버풀 태그로 저장된 기사가 아스널 태그로 또 들어오면 기사는 1건, 연결은 2건이 된다.
    """
    result = SaveResult()
    urls = [raw.url for raw in raws]
    known = {a.url: a for a in session.scalars(select(Article).where(Article.url.in_(urls)))}

    for raw in raws:
        article = known.get(raw.url)
        if article is not None:
            article.collected_at = utc_now()  # 아직 가디언이 내보내는 기사 → 보관 기한 연장 (ADR 0006)
        if article is None:
            article = Article(
                url=raw.url,
                title=raw.title,
                body_or_summary=raw.body_or_summary,
                author=raw.author,
                published_at=raw.published_at,
                source=raw.source,
            )
            session.add(article)
            known[raw.url] = article  # 같은 묶음 안에 url이 두 번 나와도 한 번만 저장되게
            result.new_articles += 1
        if club not in article.clubs:
            article.clubs.append(club)
            result.new_links += 1

    session.commit()
    return result
