# /convert-hwpx

HWPX ↔ Markdown 변환 작업을 수행합니다.

## 사용법
```
/convert-hwpx [파일경로 또는 방향]
```

## 예시
- `/convert-hwpx` — 현재 디렉토리의 HWPX 파일 변환 방법 안내
- `/convert-hwpx to-markdown path/to/file.hwpx` — HWPX → Markdown 변환
- `/convert-hwpx to-hwpx path/to/file.md` — Markdown → HWPX 변환

## 동작
1. 변환 엔진 코드(`packages/hwpx-engine/src/`)를 확인합니다
2. 변환 API 엔드포인트(`POST /api/v1/convert/hwpx-to-md` 또는 `POST /api/v1/convert/md-to-hwpx`)를 통해 변환합니다
3. 변환 결과와 오류율을 보고합니다
4. 실패 시 JSON IR 중간 표현을 출력하여 디버깅을 돕습니다

## 연관 에이전트
hwpx-converter 에이전트를 사용하여 상세 변환 로직을 처리합니다.
