# ADR 0011 — DB 구조 변경은 Alembic 마이그레이션으로

- 날짜: 2026-11-18
- 상태: 승인

## 배경
지금까지 테이블은 `Base.metadata.create_all`로 만들었다. 이 함수는 **없는 테이블만** 만들고, 이미 있는 테이블에 열을 더하거나 바꾸지 못한다. 4단계에서 `predictions.hypothesis_json` 열이 필요해지자 Neon에 손으로 `ALTER TABLE`을 실행했는데, 이 변경은 어디에도 기록이 없어 새 DB를 만들면 빠지고, 테스트 DB·Neon이 서로 다른 모양이 될 수 있다. 앞으로 5·6단계에서 테이블이 계속 바뀐다.

## 선택지
1. **Alembic (채택)** — SQLAlchemy 저자가 만든 공식 마이그레이션 도구. 변경마다 `upgrade`/`downgrade`가 든 파이썬 파일이 생기고, DB 안의 `alembic_version` 표가 "어디까지 적용됐나"를 기억한다. 모델과 DB를 비교해 초안을 써 주는 autogenerate가 있다.
2. 손으로 쓴 SQL 파일 + 적용 기록 표 — 도구가 없어 단순하지만, 순서·적용 여부 관리와 모델과의 비교를 직접 짜야 한다.
3. 계속 `create_all` + 손 ALTER — 기록이 남지 않는다 (지금의 문제 그대로).

## 결정
Alembic. 설정은 `backend/alembic.ini`(ASCII만 — 윈도우에서 시스템 인코딩으로 읽어 한글이 깨짐), `backend/migrations/env.py`(접속은 `app.db.get_engine()` → 주소를 설정 파일에 적지 않음, 테스트는 연결을 직접 넘김, SQLite는 batch 모드).
- 기준선 `0001`: 지금 테이블 14개 전체. Neon에는 이미 같은 테이블이 있어 실행하지 않고 `alembic stamp 0001`만 했고, `alembic check`로 모델과 Neon이 같음을 확인했다.
- GitHub Actions 배치 두 개는 시작할 때 `python -m alembic upgrade head`를 돈다 (최신이면 아무것도 안 함).
- 테스트 `tests/test_migrations.py`: 빈 SQLite에 `upgrade head` → 모델과 테이블이 같은지, `check`로 "모델을 바꾸고 마이그레이션을 안 만든" 상태를 잡는지, `downgrade base`로 다 지워지는지.
- `create_tables`(create_all)는 테스트 fixture용으로만 남긴다.

## 결과
- 구조를 바꾸는 순서: 모델 수정 → `python -m alembic revision --autogenerate -m "설명"` → 생성된 파일 확인·수정 → 테스트 → `python -m alembic upgrade head`(Neon) 또는 배치에 맡김.
- **틀릴 수 있는 것**: autogenerate는 열 이름 변경을 "지우고 새로 만들기"로 읽는 등 완벽하지 않다 → 생성 파일을 반드시 읽는다(기준선에서도 `Text()` import 누락을 손봤다). 테스트는 SQLite라 PostgreSQL 전용 차이(JSONB 등)는 Neon에서 `alembic check`로만 확인된다.
