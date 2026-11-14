"""뉴스 저장용 테이블 3개: 구단, 기사, 그리고 둘을 잇는 연결표."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """모든 테이블 클래스의 부모. 여기에 등록된 테이블을 한 번에 만들 수 있다."""


def utc_now() -> datetime:
    """지금 시각(UTC). 저장 시각의 기본값으로 쓴다."""
    return datetime.now(timezone.utc)


# 기사 ↔ 구단 연결표. 한 기사가 여러 구단에 걸릴 수 있어(예: 리버풀 대 아스널 경기 기사) 따로 둔다.
article_clubs = Table(
    "article_clubs",
    Base.metadata,
    Column("article_id", ForeignKey("articles.id"), primary_key=True),
    Column("club_id", ForeignKey("clubs.id"), primary_key=True),
)


class Club(Base):
    """구단 한 곳. 승격·강등으로 목록이 바뀌므로 코드에 적어 두지 않고 테이블로 둔다."""

    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    guardian_tag: Mapped[str] = mapped_column(String(100), unique=True)  # 예: football/liverpool
    in_premier_league: Mapped[bool] = mapped_column(default=True)  # 강등되면 False (지우지 않는다)

    articles: Mapped[list["Article"]] = relationship(secondary=article_clubs, back_populates="clubs")


class Article(Base):
    """수집한 기사 한 건. RawArticle과 같은 내용이며, 원문 전체가 아니라 제목·요약·링크만 담는다."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(500), unique=True)  # 같은 기사를 두 번 저장하지 않는 기준
    title: Mapped[str] = mapped_column(String(500))
    body_or_summary: Mapped[str] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(200))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(50))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    clubs: Mapped[list[Club]] = relationship(secondary=article_clubs, back_populates="articles")
