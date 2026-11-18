"""Gemini 클라이언트를 만드는 한 곳. 호출하는 쪽이 한도 초과(429)를 바로 알 수 있게 SDK의 자동 재시도를 끈다.

google-genai는 기본으로 429·5xx를 최대 5번(대기 최대 60초씩) 조용히 다시 시도한다. 하루 한도를 넘으면 호출 하나가
몇 분씩 '응답 없음'으로 보였고(2026-11-18: llm_run 정지, readme-translate 10분 초과 취소), 우리 코드의 "429면 멈춘다"가 동작하지 못했다.
"""

from google import genai
from google.genai import types

from app.settings import load_env


def gemini_client(timeout_seconds: int = 60) -> genai.Client:
    """GEMINI_API_KEY(backend/.env 또는 Secrets)로 접속한다. 재시도 없음 → 오류가 1~2초 안에 그대로 올라온다."""
    load_env()
    return genai.Client(http_options=types.HttpOptions(timeout=timeout_seconds * 1000, retry_options=types.HttpRetryOptions(attempts=1)))
