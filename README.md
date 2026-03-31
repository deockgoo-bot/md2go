# HWP Converter AI

공공기관 HWP 문서를 AI로 생성, 변환, 검색, 교정하는 문서 자동화 플랫폼.

> HWP 5.0 바이너리 + HWPX(OWPML) 포맷을 직접 생성/파싱하는 자체 엔진 탑재.
> 순수 Python으로 구현. 별도 소프트웨어 설치 불필요.

## Python 패키지

[![PyPI](https://img.shields.io/pypi/v/hwp-converter-ai)](https://pypi.org/project/hwp-converter-ai/)

```bash
pip install hwp-converter-ai
```

```python
from hwp_converter_ai import HwpWriter

# 3줄이면 HWP 생성
writer = HwpWriter()
writer.from_markdown("# 업무 보고\n\n내용입니다.", "report.hwp")
```

```python
from hwp_converter_ai import HwpParser

# HWP → Markdown 변환
ir = HwpParser.parse("document.hwp")
print(ir.to_markdown())
```

```python
from hwp_converter_ai import HwpxGenerator, HwpxParser

# Markdown → HWPX
HwpxGenerator().from_markdown("# 제목\n\n**볼드** 텍스트", output_path="report.hwpx")

# HWPX → Markdown
ir = HwpxParser().parse("document.hwpx")
print(ir.to_markdown())
```

## 주요 기능

### F-01. HWP ↔ Markdown 변환 (오픈소스)
- **HWP → Markdown**: OLE 스트림 직접 파싱, 표/제목/볼드/이탤릭 보존
- **Markdown → HWP**: 한컴오피스 97~2024에서 열 수 있는 .hwp 파일 생성
- **Markdown → HWPX**: 한컴오피스 2014+에서 열 수 있는 .hwpx 파일 생성
- 표, 제목(H1~H3), **볼드**, *이탤릭*, 리스트, 구분선, 이미지 추출

### F-02. 공문서 AI 초안 생성
- 기안문, 보고서, 공고문 등 10종 템플릿
- 행정안전부 공문서 규정 준수 (두문·본문·결문)
- AWS Bedrock Claude 기반

### F-03. RAG 검색 (Pro)
- HWP 문서 업로드 → AI 기반 청킹 → Titan 임베딩 → pgvector 인덱싱
- 자연어 질의 검색, 문서명·페이지 출처 포함

### F-04. 문서 요약·교정 (Pro)
- 맞춤법 + 행정 문체 교정
- 교정 전·후 비교 UI
- 결과물 HWP/HWPX 다운로드

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| HWP 엔진 | Python + OLE/HWP 5.0 직접 처리 (자체 엔진) |
| HWPX 엔진 | Python + OWPML XML 템플릿 기반 |
| 중간 표현 | JSON IR Schema |
| AI | AWS Bedrock Claude Sonnet 4.6 |
| 임베딩 | Amazon Titan Embed Text v2 |
| RAG | AI 기반 청킹 + pgvector |
| 백엔드 | FastAPI |
| 프론트엔드 | Next.js + shadcn/ui |
| 배포 | Docker Compose |

## 빠른 시작

### 요구사항
- Docker & Docker Compose
- Node.js 18+
- Python 3.12+

### 실행

```bash
# 환경변수 설정
cp .env.example .env
# AWS 키, API 키 등 입력

# Docker로 백엔드 + DB + Redis 실행
docker compose up -d

# 프론트엔드 실행
cd apps/web
npm install
npm run dev
```

- 백엔드 API: http://localhost:8000
- 프론트엔드: http://localhost:3002
- API 문서 (Swagger): http://localhost:8000/docs

## 엔진 지원 현황

| 기능 | HWP | HWPX |
|------|-----|------|
| 텍스트/문단 | ✅ | ✅ |
| 제목 (H1~H3) | ✅ | ✅ |
| **볼드**/*이탤릭* | ✅ | ✅ |
| 표 (테두리 포함) | ✅ | ✅ |
| 이미지 추출 | ✅ | ✅ |
| 리스트 감지 | ✅ | ✅ |
| 긴 문서 | ✅ | ✅ |

## API 엔드포인트

| 메서드 | 경로 | 설명 | Rate Limit |
|--------|------|------|-----------|
| POST | `/api/v1/convert/hwp-to-md` | HWP·HWPX → Markdown | 5회/일 |
| POST | `/api/v1/convert/md-to-hwp` | Markdown → HWP·HWPX | 5회/일 |
| GET | `/api/v1/convert/download/{job_id}` | 변환 파일 다운로드 | - |
| POST | `/api/v1/draft/generate` | AI 공문서 초안 생성 | 3회/일 |
| POST | `/api/v1/search/upload` | RAG 문서 업로드 | 3회/일 |
| POST | `/api/v1/search/query` | 자연어 검색 | 3회/일 |
| POST | `/api/v1/correct/summarize` | 문서 요약 | 3회/일 |
| POST | `/api/v1/correct/proofread` | 맞춤법·문체 교정 | 3회/일 |

모든 API는 `X-API-Key` 헤더 인증 필요.

## 프로젝트 구조

```
├── apps/web/                   # Next.js 프론트엔드
├── backend/                    # FastAPI 백엔드
│   └── app/services/
│       ├── hwpx_engine/        # HWP/HWPX 엔진 (핵심)
│       │   ├── hwp_writer.py   # MD → HWP 생성
│       │   ├── hwp_parser.py   # HWP → MD 파싱
│       │   ├── generator.py    # MD → HWPX 생성
│       │   ├── parser.py       # HWPX → MD 파싱
│       │   └── ir_schema.py    # JSON IR 스키마
│       ├── ai_service.py       # Bedrock Claude
│       └── rag_service.py      # AI 청킹 + pgvector
├── packages/
│   └── hwp-converter-ai/      # PyPI 패키지 (pip install hwp-converter-ai)
├── docker-compose.yml
└── CLAUDE.md
```

## 오픈소스 정책

- **공개 (MIT)**: HWP ↔ Markdown 변환 엔진 코어 (`pip install hwp-converter-ai`)
- **비공개**: AI 기능 (초안생성·RAG·교정) — SaaS 유료

## 라이선스

변환 엔진 코어: MIT License
AI 기능: Proprietary
