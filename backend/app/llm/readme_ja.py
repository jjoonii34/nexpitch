"""README.md(한국어)를 Gemini로 일본어 번역해 README.ja.md를 갱신한다 (ADR 0012).

python -m app.llm.readme_ja           # 원본이 바뀌었으면 번역 (GitHub Actions가 README.md push 때 실행)
python -m app.llm.readme_ja --stamp   # 사람이 직접 번역했을 때: 번역은 그대로 두고 '원본 지문'만 갱신

- 원본 지문(sha256)을 README.ja.md 맨 끝 HTML 주석에 적는다. 지문이 같으면 아무것도 안 한다
  → 직접 고친 번역을 기계 번역으로 덮지 않고, 같은 원본을 두 번 번역하지 않는다.
- 결과 표 숫자와 링크가 번역 중에 바뀌면 저장하지 않고 실패한다 ("측정하지 않은 숫자는 쓰지 않는다").
- 네트워크는 translate() 한 곳. 나머지는 순수 함수라 가짜 클라이언트로 테스트한다.
"""

import hashlib
import re
import sys
from pathlib import Path

from app.settings import REPO_ROOT

MODEL = "gemini-3.5-flash-lite"
ATTEMPTS = 2  # 검사 실패 시 재시도 포함 최대 호출 수 (2026-11-18 첫 실험에서 1회차가 숫자 2개를 바꿨고 2회차는 통과)
SOURCE = REPO_ROOT / "README.md"
TARGET = REPO_ROOT / "README.ja.md"

KO_SWITCH = "**한국어** · [日本語](README.ja.md)"
JA_SWITCH = "[한국어](README.md) · **日本語**"
JA_NOTICE = (
    "> 本 README は韓国語版 [README.md](README.md) を Gemini で自動翻訳したものです（数値・リンクは原文と一致することを自動検査しています）。"
    "設計記録（ADR）・開発ノート・コードコメントは韓国語です。"
)
NOTICE_START = "> 本 README は"  # 안내문(예전 손 번역의 것 포함)을 알아보는 앞부분
STAMP_PREFIX ="<!-- readme-ja source-sha256: "
STAMP_RE = re.compile(r"<!-- readme-ja source-sha256: ([0-9a-f]{64}) -->")

SYSTEM_INSTRUCTION = (
    "You translate a Korean GitHub README (Markdown) into natural, professional Japanese for engineers and recruiters at Japanese companies. "
    "Rules: (1) Keep the Markdown structure exactly: headings, tables (same rows and columns), lists, code blocks, badges, HTML. "
    "(2) Never change numbers, dates, percentages, code, file paths, URLs or link targets; translate only link text and prose. "
    "Inside code blocks translate only comments after '#'. "
    "(3) Use です/ます for prose; keep tables concise. Use the previous Japanese translation, if given, for consistent terminology. "
    "(4) Do not add or remove content. Output only the translated Markdown document, with no preface and no code fence around it."
)


def normalize(text: str) -> str:
    """줄바꿈을 LF로 맞춘다. 윈도우(CRLF)와 Actions(LF)에서 같은 지문이 나오게 하기 위해."""
    return text.replace("\r\n", "\n")


def source_hash(source: str) -> str:
    return hashlib.sha256(normalize(source).encode("utf-8")).hexdigest()


def read_stamp(target: str) -> str | None:
    """README.ja.md에 적힌 원본 지문. 없으면 None."""
    match = STAMP_RE.search(target)
    return match.group(1) if match else None


def with_stamp(target: str, digest: str) -> str:
    """지문 주석을 맨 끝에 하나만 두게 바꾼다 (GitHub 화면에는 보이지 않는다)."""
    body = STAMP_RE.sub("", normalize(target)).rstrip("\n")
    return f"{body}\n\n{STAMP_PREFIX}{digest} -->\n"


def needs_update(source: str, target: str | None) -> bool:
    return target is None or read_stamp(target) != source_hash(source)


def prepare_source(source: str) -> str:
    """번역할 글: 언어 전환 줄은 빼고 보낸다 (일본어판 줄은 코드가 직접 넣는다)."""
    return "\n".join(line for line in normalize(source).split("\n") if line.strip() != KO_SWITCH)


def finalize(translated: str) -> str:
    """번역 결과를 다듬는다: 모델이 감쌌을 수 있는 ``` 울타리를 벗기고, 첫 제목 아래에 언어 전환 줄과 안내문을 넣는다."""
    text = normalize(translated).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0].strip()
    # 모델이 이전 번역을 보고 전환 줄·안내문을 따라 쓸 수 있어 지운 뒤 한 번만 넣는다 (2026-11-18 실험에서 두 번 나옴)
    lines = [line for line in text.split("\n") if line.strip() not in (JA_SWITCH, KO_SWITCH) and not line.startswith(NOTICE_START)]
    title_end = 1 if lines and lines[0].startswith("# ") else 0
    body = "\n".join(lines[title_end:]).lstrip("\n")
    return "\n".join(lines[:title_end] + ["", JA_SWITCH, "", JA_NOTICE, "", body]).rstrip("\n") + "\n"


def measured_numbers(text: str) -> list[str]:
    """지켜야 할 숫자: 소수(0.6595, 0.0083 등)와 백분율(40.8%). 결과 표가 여기에 다 걸린다."""
    return sorted(re.findall(r"\d+\.\d+%?|\d+%", text))


def link_targets(text: str) -> set[str]:
    """Markdown 링크의 대상 주소·경로 ( ](대상) 부분)."""
    return set(re.findall(r"\]\(([^)\s]+)\)", text))


def heading_count(text: str) -> int:
    """코드 블록 밖의 제목 줄 수. 번역이 중간에 끊기거나 절이 빠지면 달라진다."""
    count, in_code = 0, False
    for line in text.split("\n"):
        if line.startswith("```"):
            in_code = not in_code
        elif not in_code and re.match(r"#{1,6} ", line):
            count += 1
    return count


def check(source: str, translated: str) -> list[str]:
    """번역이 숫자·링크를 바꾸지 않았는지. 문제 목록을 돌려준다 (빈 목록이면 통과)."""
    problems = []
    src, out = prepare_source(source), normalize(translated)
    missing_numbers = [n for n in measured_numbers(src) if measured_numbers(src).count(n) > measured_numbers(out).count(n)]
    if missing_numbers:
        problems.append(f"숫자가 바뀌거나 빠짐: {sorted(set(missing_numbers))[:10]}")
    missing_links = link_targets(src) - link_targets(out)
    if missing_links:
        problems.append(f"링크가 바뀌거나 빠짐: {sorted(missing_links)[:10]}")
    if src.count("```") != out.count("```"):
        problems.append("코드 블록 개수가 다름")
    if heading_count(src) != heading_count(out):
        problems.append(f"제목(#) 개수가 다름: 원문 {heading_count(src)} / 번역 {heading_count(out)} — 번역이 중간에 끊겼을 수 있다")
    return problems


def translate(client, source: str, previous: str | None) -> str:
    """Gemini에 한 번 묻는다. 네트워크가 필요한 유일한 함수.

    출력은 JSON으로 감싸지 않고 Markdown 그대로 받는다. JSON 문자열 안에서 README의 큰따옴표(`"55%"`)가 문자열을 끝내 버려
    번역이 그 자리에서 잘렸다 (2026-11-19 확인, Actions 실패의 원인).
    """
    parts = ["Korean README to translate:\n\n" + prepare_source(source)]
    if previous:
        parts.append("Previous Japanese translation (for terminology only; translate the README above fully):\n\n" + STAMP_RE.sub("", normalize(previous)))
    interaction = client.interactions.create(
        model=MODEL,
        system_instruction=SYSTEM_INSTRUCTION,
        input="\n\n---\n\n".join(parts),
    )
    return interaction.output_text


def update(client, source_path: Path = SOURCE, target_path: Path = TARGET) -> str:
    """필요하면 번역해 저장한다. 결과: 'skipped' / 'updated'. 검사에 걸리면 저장하지 않고 오류를 낸다."""
    source = source_path.read_text(encoding="utf-8")
    previous = target_path.read_text(encoding="utf-8") if target_path.exists() else None
    if not needs_update(source, previous):
        return "skipped"
    for _ in range(ATTEMPTS):  # 같은 입력에도 답이 조금씩 달라서, 검사에 걸리면 한 번 더 시도한다
        translated = finalize(translate(client, source, previous))
        problems = check(source, translated)
        if not problems:
            target_path.write_bytes(with_stamp(translated, source_hash(source)).encode("utf-8"))
            return "updated"
    raise ValueError("번역 검사 실패 — README.ja.md를 바꾸지 않았습니다: " + " / ".join(problems))


def stamp(source_path: Path = SOURCE, target_path: Path = TARGET) -> None:
    """사람이 번역을 직접 고쳤을 때: 내용은 두고 지문만 지금 원본으로 맞춘다."""
    source = source_path.read_text(encoding="utf-8")
    target_path.write_bytes(with_stamp(target_path.read_text(encoding="utf-8"), source_hash(source)).encode("utf-8"))


if __name__ == "__main__":
    if "--stamp" in sys.argv:
        stamp()
        print("README.ja.md 지문을 현재 README.md에 맞췄습니다 (번역 내용은 그대로).")
    else:
        from app.llm.client import gemini_client

        print("README.ja.md:", update(gemini_client(120)))
