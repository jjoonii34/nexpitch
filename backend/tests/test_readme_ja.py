"""README 일본어 자동 번역 테스트 (ADR 0012). 가짜 Gemini로 지문·검사·덮어쓰기 방지를 확인한다."""

import pytest

from app.llm.readme_ja import JA_SWITCH, KO_SWITCH, check, finalize, needs_update, read_stamp, source_hash, stamp, update, with_stamp

SOURCE = f"# ⚽ nexpitch\r\n\r\n{KO_SWITCH}\r\n\r\n| 모델 | Brier |\r\n|---|---|\r\n| Elo | 0.6021 |\r\n\r\n정확도 53.2% · [ADR](docs/adr/0008.md)\r\n"
GOOD = "# ⚽ nexpitch\n\n| モデル | Brier |\n|---|---|\n| Elo | 0.6021 |\n\n正解率 53.2% · [ADR](docs/adr/0008.md)\n"


class FakeClient:
    """interactions.create(...)가 정해 둔 번역을 돌려준다. 몇 번 불렸는지 센다."""

    def __init__(self, markdown: str):
        self.markdown, self.calls, self.interactions = markdown, 0, self

    def create(self, **kwargs):
        self.calls += 1
        markdown = self.markdown

        class R:
            output_text = markdown

        return R()


def test_hash_ignores_line_endings_and_stamp_roundtrip():
    assert source_hash("a\r\nb") == source_hash("a\nb")  # 윈도우와 Actions에서 같은 지문
    stamped = with_stamp(with_stamp("본문", "0" * 64), "1" * 64)
    assert read_stamp(stamped) == "1" * 64 and stamped.count("source-sha256") == 1
    assert needs_update(SOURCE, None) and not needs_update(SOURCE, with_stamp("x", source_hash(SOURCE)))


def test_finalize_unwraps_fence_and_adds_switch_under_title():
    out = finalize("```markdown\n# タイトル\n本文\n```")
    lines = out.split("\n")
    assert lines[0] == "# タイトル" and lines[2] == JA_SWITCH and "本文" in out and "```" not in out
    copied = finalize(f"# タイトル\n\n{JA_SWITCH}\n\n> 本 README は古い案内です。\n\n本文")  # 모델이 이전 번역의 줄을 따라 쓴 경우
    assert copied.count(JA_SWITCH) == 1 and "古い案内" not in copied and copied.count("> 本 README は") == 1


def test_check_catches_changed_numbers_and_links():
    assert check(SOURCE, GOOD) == []
    assert any("숫자" in p for p in check(SOURCE, GOOD.replace("0.6021", "0.6012")))
    assert any("링크" in p for p in check(SOURCE, GOOD.replace("docs/adr/0008.md", "docs/adr/0009.md")))
    assert any("제목" in p for p in check(SOURCE + "\n## 끝 절\n", GOOD))  # 번역이 중간에 끊겨 절이 빠진 경우


def test_update_translates_once_then_skips(tmp_path):
    src, dst = tmp_path / "README.md", tmp_path / "README.ja.md"
    src.write_bytes(SOURCE.encode("utf-8"))  # 윈도우의 줄바꿈 변환 없이 그대로
    client = FakeClient(GOOD)
    assert update(client, src, dst) == "updated"
    written = dst.read_text(encoding="utf-8")
    assert JA_SWITCH in written and KO_SWITCH not in written and read_stamp(written) == source_hash(SOURCE)
    assert update(client, src, dst) == "skipped" and client.calls == 1  # 같은 원본은 다시 번역하지 않는다


def test_update_refuses_bad_translation_and_stamp_protects_manual_edit(tmp_path):
    src, dst = tmp_path / "README.md", tmp_path / "README.ja.md"
    src.write_bytes(SOURCE.encode("utf-8"))  # 윈도우의 줄바꿈 변환 없이 그대로
    dst.write_text("직접 고친 번역", encoding="utf-8")
    bad = FakeClient(GOOD.replace("53.2%", "52.3%"))
    with pytest.raises(ValueError, match="번역 검사 실패"):
        update(bad, src, dst)
    assert bad.calls == 2  # 한 번 더 시도하고 포기
    assert dst.read_text(encoding="utf-8") == "직접 고친 번역"  # 실패하면 파일을 건드리지 않는다

    stamp(src, dst)  # 사람이 번역한 뒤 지문만 맞추면
    client = FakeClient(GOOD)
    assert update(client, src, dst) == "skipped" and client.calls == 0  # 기계 번역이 덮지 않는다
    assert dst.read_text(encoding="utf-8").startswith("직접 고친 번역")
