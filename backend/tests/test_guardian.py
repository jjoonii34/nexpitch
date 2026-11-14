"""가디언 응답 → RawArticle 변환 테스트. 실제 API를 부르지 않는다."""

from app.collectors.guardian import parse, strip_html

SAMPLE = {
    "response": {
        "results": [
            {
                "webTitle": "Liverpool agree fee for midfielder",
                "webUrl": "https://www.theguardian.com/football/example",
                "webPublicationDate": "2026-11-14T09:30:00Z",
                "fields": {"trailText": "<p>Deal worth &pound;40m</p>", "byline": "Andy Hunter"},
            },
            {"webTitle": "링크가 없는 깨진 기사"},
        ]
    }
}


def test_parse_maps_fields():
    article = parse(SAMPLE)[0]
    assert article.title == "Liverpool agree fee for midfielder"
    assert article.author == "Andy Hunter"
    assert article.source == "guardian"
    assert article.published_at.year == 2026


def test_parse_skips_broken_items():
    assert len(parse(SAMPLE)) == 1


def test_strip_html_removes_tags_and_entities():
    assert strip_html("<p>Deal worth &pound;40m</p>") == "Deal worth £40m"


def test_parse_handles_empty_response():
    assert parse({}) == []
