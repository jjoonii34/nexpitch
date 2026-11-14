"""모든 수집기가 지키는 공통 규칙. 소스가 달라도 결과 모양은 같다."""

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel


class RawArticle(BaseModel):
    """수집기가 돌려주는 기사 한 건. 원문 전체가 아니라 제목·요약·링크만 담는다."""

    title: str
    body_or_summary: str
    url: str
    author: str | None  # 바이라인이 없는 기사도 있다
    published_at: datetime
    source: str


class Collector(Protocol):
    """수집기라면 갖춰야 할 모양. 새 소스 = 이 모양을 따르는 클래스 하나 추가."""

    source: str

    def collect(self) -> list[RawArticle]:
        """기사를 가져와 RawArticle 목록으로 돌려준다."""
        ...
