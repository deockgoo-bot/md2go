# CLAUDE.md — HWP Converter AI Platform

## 프로젝트 개요

공공기관의 HWPX 문서를 AI로 생성·검색·변환·교정하는 문서 자동화 플랫폼.
HWPX ↔ Markdown 변환 엔진은 오픈소스(MIT)로 공개하고, AI 기능(초안생성·RAG·교정)은 SaaS/온프레미스 유료 제공.

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| HWPX 파싱/생성 | Python + HWPX XML 직접 처리 (자체 엔진) |
| 중간 표현(IR) | 자체 JSON IR Schema |
| AI | Claude API (`claude-sonnet-4-6`) / Ollama (오프라인 fallback) |
| RAG | LangChain + pgvector |
| 백엔드 | FastAPI (Python) |
| 프론트 | Next.js + shadcn/ui |
| 배포 | Docker + Kubernetes |
| 오픈소스 | GitHub (변환 엔진 코어, MIT 라이선스) |

---

## 아키텍처 원칙

- **HWPX 파싱**: HWPX는 ZIP 기반 XML 포맷. 직접 XML 파싱으로 처리하며 한컴 SDK에 의존하지 않는다.
- **JSON IR**: HWPX ↔ Markdown 변환 시 중간 표현(IR)으로 자체 JSON 스키마를 사용한다. 변환 양방향 모두 IR을 경유한다.
- **AI 연동**: 기본은 Claude API(`claude-sonnet-4-6`). 망분리 환경에서는 Ollama로 fallback.
- **RAG**: HWPX 문서 → 텍스트 추출 → 청크 분할 → pgvector 임베딩 인덱싱. LangChain 파이프라인 사용.
- **API**: FastAPI로 REST 엔드포인트 제공. OpenAPI(Swagger) 자동 생성 필수.
- **보안**: 파일 처리 후 서버 내 즉시 삭제. API 키 인증 필수. 온프레미스 Docker 배포 지원.

---

## 핵심 기능 모듈

### F-01. HWPX ↔ Markdown 변환 엔진 (오픈소스 코어)
- 변환 오류율 5% 이하 (공문서 샘플 100종 기준) — P0 품질 기준
- 보존 대상: 단락, 제목(H1~H6), 표, 리스트, 이미지, 공문서 스타일(글꼴·여백·줄간격)
- HWPX 변환 API 응답: 10초 이내 (10MB 기준)

### F-02. 공문서 AI 초안 생성
- 기안문·보고서·공고문 등 10종 템플릿 내장
- 행정안전부 공문서 규정(두문·본문·결문) 준수
- 초안 생성: 60초 이내

### F-03. RAG 검색
- HWPX 배치 업로드 → 벡터 DB 인덱싱 (문서 1건당 5초 이내)
- 자연어 질의 검색 응답: 3초 이내
- 검색 결과에 문서명·페이지 출처 포함

### F-04. 문서 요약·교정
- 맞춤법 + 행정 문체 교정
- 교정 전·후 비교 UI
- 결과물 HWPX 다운로드

### F-05. REST API
- 변환·생성·검색·요약 엔드포인트
- API 키 인증
- 비동기 처리 + 웹훅 콜백
- OpenAPI(Swagger) 자동 생성

---

## 개발 가이드라인

### 일반
- Python 코드는 타입 힌트를 사용한다.
- FastAPI 엔드포인트는 OpenAPI 스키마가 자동 생성되도록 Pydantic 모델을 정의한다.
- 파일 업로드 처리 후 반드시 서버에서 즉시 삭제한다 (보안 요건).
- 동시 요청 100건 이상 처리를 고려해 비동기(async/await) 패턴을 사용한다.

### HWPX 처리
- HWPX는 `.hwpx` 확장자의 ZIP 아카이브. `zipfile` 모듈로 열고 내부 XML을 파싱한다.
- 한컴 HWPX XML 네임스페이스: `http://www.hancom.co.kr/hwpml/2012/Section` 등 버전별 차이 주의.
- 변환 중간 표현은 항상 JSON IR을 경유한다 — HWPX→IR→MD, MD→IR→HWPX.

### AI / Claude API
- 모델: `claude-sonnet-4-6` (기본), Ollama (오프라인 환경 fallback).
- 프롬프트에 행정안전부 공문서 규정 컨텍스트를 포함한다.
- Claude API 사용 시 `/claude-api` 스킬 참고.

### 프론트엔드
- Next.js App Router + shadcn/ui 사용.
- 파일 업로드/다운로드 UI 필수.
- 교정 비교 UI는 diff 형태로 제공.

### 페이지 구조
- `/` — 랜딩 페이지 (서비스 소개, Hero, 기능 설명, CTA)
- `/app` — 대시보드 (로그인 후 메인)
- `/app/convert` — HWP 변환
- `/app/draft` — AI 초안 생성
- `/app/search` — RAG 검색
- `/app/correct` — 요약·교정
- 랜딩 페이지는 비로그인 상태에서 접근 가능. 나머지는 인증 필요.

---

## MVP 마일스톤

| 단계 | 목표 | 완료 기준 |
|------|------|-----------|
| M1 | HWPX 변환 엔진 | 샘플 100종 오류율 5% 이하 |
| M2 | AI 초안 생성 + 요약·교정 | 기안문 10종 생성 성공 |
| M3 | RAG 인덱싱 + 검색 | 자연어 검색 응답 3초 이내 |
| M4 | PoC 배포 | 1개 기관 실사용 피드백 수집 |

현재 목표: **2026년 내 PoC 기관 3곳 확보**, 6개월 내 GitHub Star 500+.

---

## 비기능 요구사항 요약

- 보안: 망분리 환경 온프레미스 배포 지원, 파일 처리 후 즉시 삭제
- 성능: 변환 API 10초 이내, RAG 검색 3초 이내, 초안 생성 60초 이내
- 가용성: SaaS 99.5% uptime
- 확장성: 동시 요청 100건 이상
- 호환성: 한컴오피스 2018 이상 HWPX 포맷
- AI 오프라인: Ollama fallback 필수

---

## 오픈소스 정책

- **공개 범위**: HWPX ↔ Markdown 변환 엔진 코어만 MIT 라이선스로 공개
- **비공개**: AI 기능(초안생성·RAG·교정) — SaaS/온프레미스 유료 전용
- 오픈소스 코드에 유료 기능 로직이 혼입되지 않도록 모듈 경계를 명확히 유지한다
