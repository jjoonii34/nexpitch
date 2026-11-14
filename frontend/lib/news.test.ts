// 실행: npm test  (뉴스 탭의 순수 함수만 검사한다. DB에는 접속하지 않는다)
import assert from "node:assert/strict";
import { test } from "node:test";
import { clubsLabel, likePattern, mapNewsRow, newsHref, parseClubId, parseQuery } from "./newsMap.ts";

test("mapNewsRow: DB 행을 뉴스 카드 모양으로 바꾼다", () => {
  const item = mapNewsRow({
    id: "7", // DB 드라이버가 숫자를 문자열로 줄 수 있다
    title: "Liverpool agree fee",
    body_or_summary: "Deal worth £40m",
    url: "https://www.theguardian.com/x",
    author: null,
    source: "guardian",
    published_at: "2026-11-14T09:30:00Z",
    clubs: ["Liverpool"],
  });
  assert.equal(item.id, 7);
  assert.equal(item.summary, "Deal worth £40m");
  assert.equal(item.author, null);
  assert.deepEqual(item.clubs, ["Liverpool"]);
  assert.deepEqual(mapNewsRow({ id: 1, url: "u", clubs: null }).clubs, []); // 연결된 구단이 없어도 깨지지 않는다
});

test("parseClubId: 숫자가 아닌 주소 값은 전체 구단으로 본다", () => {
  assert.equal(parseClubId("14"), 14);
  assert.equal(parseClubId("0"), null);
  assert.equal(parseClubId("abc"), null);
  assert.equal(parseClubId("1; DROP TABLE clubs"), null);
  assert.equal(parseClubId(undefined), null);
  assert.equal(parseClubId(["1", "2"]), null); // ?club=1&club=2
});

test("parseQuery: 공백을 떼고 50자로 자른다", () => {
  assert.equal(parseQuery("  Salah "), "Salah");
  assert.equal(parseQuery("   "), null);
  assert.equal(parseQuery(undefined), null);
  assert.equal(parseQuery("a".repeat(80))?.length, 50);
});

test("likePattern: 사용자가 넣은 %와 _는 글자 그대로 찾는다", () => {
  assert.equal(likePattern("Salah"), "%Salah%");
  assert.equal(likePattern("100%"), "%100\\%%");
  assert.equal(likePattern("a_b"), "%a\\_b%");
});

test("clubsLabel: 구단이 많으면 이름 대신 수를 보여준다", () => {
  assert.equal(clubsLabel([]), "");
  assert.equal(clubsLabel(["Arsenal", "Liverpool"]), "Arsenal · Liverpool");
  assert.equal(clubsLabel(["A", "B", "C", "D"]), "4개 구단");
});

test("newsHref: 구단과 검색어를 주소로 만든다", () => {
  assert.equal(newsHref(null, null), "/news");
  assert.equal(newsHref(14, null), "/news?club=14");
  assert.equal(newsHref(14, "van dijk"), "/news?club=14&q=van+dijk");
});
