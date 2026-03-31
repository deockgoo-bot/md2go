# /run-tests

프로젝트 테스트를 실행하고 결과를 분석합니다.

## 사용법
```
/run-tests [범위]
```

## 예시
- `/run-tests` — 전체 테스트 실행
- `/run-tests engine` — HWPX 변환 엔진 테스트만
- `/run-tests backend` — FastAPI 백엔드 테스트
- `/run-tests frontend` — Next.js 프론트엔드 테스트
- `/run-tests coverage` — 커버리지 리포트 포함 전체 실행

## 동작
1. 해당 범위의 테스트 실행
2. 실패 테스트 원인 분석
3. 커버리지 현황 보고 (목표: 백엔드 80%+, 엔진 90%+)
4. 변환 오류율 집계 (목표: 5% 이하)

## 연관 에이전트
test-runner 에이전트를 사용합니다.
