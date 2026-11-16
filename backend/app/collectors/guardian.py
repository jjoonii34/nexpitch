"""가디언 Open Platform 수집기. 구단 태그(예: football/liverpool)의 최신 기사를 받아 RawArticle로 바꾼다."""

import html
import json
import re
from datetime import date
from pathlib import Path

import httpx
from pydantic import ValidationError

from app.collectors.base import RawArticle
from app.settings import RAW_DIR, require_env

API_URL = "https://content.guardianapis.com/search"
GUARDIAN_RAW_DIR = RAW_DIR / "guardian"  # nexpitch/data/raw/guardian


def strip_html(text: str) -> str:
    """요약문에 섞인 HTML 태그와 &amp; 같은 기호를 걷어낸다 (화면에 태그가 그대로 보이지 않게)."""
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def parse(raw: dict) -> list[RawArticle]:
    """가디언 응답(dict)을 RawArticle 목록으로 바꾼다. 네트워크가 필요 없어 테스트하기 쉽다."""
    articles: list[RawArticle] = []
    for item in raw.get("response", {}).get("results", []):
        fields = item.get("fields", {})
        try:
            articles.append(
                RawArticle(
                    title=item["webTitle"],
                    body_or_summary=strip_html(fields.get("trailText", "")),
                    url=item["webUrl"],
                    author=fields.get("byline") or None,
                    published_at=item["webPublicationDate"],
                    source="guardian",
                )
            )
        except (KeyError, ValidationError):
            continue  # 필수 값이 빠진 기사는 건너뛴다 (나중에 '파싱 실패율'로 셀 자리)
    return articles


class GuardianCollector:
    """가디언에서 특정 태그의 최신 기사를 수집한다."""

    source = "guardian"

    def __init__(self, tag: str = "football/liverpool", page_size: int = 30) -> None:
        self.tag = tag
        self.page_size = page_size

    def raw_path(self, day: date | None = None) -> Path:
        """원본 응답을 저장할 파일 위치. 구단(태그)마다 파일이 달라야 서로 덮어쓰지 않는다."""
        day = day or date.today()
        return GUARDIAN_RAW_DIR / day.isoformat() / f"{self.tag.replace('/', '-')}.json"

    def fetch_raw(self, day: date | None = None, force: bool = False) -> dict:
        """원본 응답을 가져온다. 그날 그 태그의 파일이 이미 있으면 API를 다시 부르지 않고 파일을 읽는다."""
        path = self.raw_path(day)
        if path.exists() and not force:
            return json.loads(path.read_text(encoding="utf-8"))

        key = require_env("GUARDIAN_API_KEY")
        response = httpx.get(
            API_URL,
            params={
                "tag": self.tag,
                "order-by": "newest",
                "page-size": self.page_size,
                "show-fields": "trailText,byline",
                "api-key": key,
            },
            timeout=10,
        )
        if response.status_code != 200:
            # 주소에 키가 들어 있으므로 httpx의 기본 오류(주소 포함) 대신 상태 코드만 알린다.
            raise RuntimeError(f"가디언 API 응답 오류 ({response.status_code})")
        raw = response.json()

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        return raw

    def collect(self) -> list[RawArticle]:
        """원본을 가져와(또는 저장된 파일을 읽어) RawArticle 목록으로 돌려준다."""
        return parse(self.fetch_raw())


if __name__ == "__main__":
    # 직접 실행하면 수집 결과를 눈으로 확인할 수 있다: python -m app.collectors.guardian
    for article in GuardianCollector().collect():
        print(article.published_at.date(), "|", article.author, "|", article.title)
