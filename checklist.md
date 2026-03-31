# HWP Converter AI Platform — 진행 체크리스트
> 마지막 업데이트: 2026-03-31 (Day 3 진행 중)

---

## 1. 프로젝트 기반 설정

| 항목 | 파일 | 상태 |
|------|------|------|
| PRD 문서 | `hwp-bridge-prd.md` | ✅ |
| CLAUDE.md | `CLAUDE.md` | ✅ |
| 환경변수 | `.env` / `.env.example` | ✅ |
| Turborepo 설정 | `turbo.json` | ✅ |
| 루트 package.json | `package.json` | ✅ |
| .gitignore | `.gitignore` | ✅ |
| docker-compose.yml | `docker-compose.yml` | ✅ |
| README.md | `README.md` | ✅ |
| 디렉토리 구조 | `apps/ backend/ packages/ docs/` | ✅ |

---

## 2. 백엔드 (FastAPI)

| 항목 | 상태 |
|------|------|
| `backend/app/main.py` | ✅ |
| `backend/app/core/config.py` | ✅ |
| `backend/app/core/security.py` | ✅ |
| `backend/app/api/deps.py` | ✅ |
| `backend/app/db/session.py` + Alembic | ✅ |
| `backend/Dockerfile` | ✅ |

### API 라우트
| 엔드포인트 | 상태 |
|-----------|------|
| `POST /api/v1/convert/hwp-to-md` | ✅ |
| `POST /api/v1/convert/md-to-hwp` | ✅ |
| `GET /api/v1/convert/download/{job_id}` | ✅ |
| `POST /api/v1/draft/generate` | ✅ |
| `POST /api/v1/search/upload` | ✅ |
| `POST /api/v1/search/query` | ✅ |
| `POST /api/v1/correct/summarize` | ✅ |
| `POST /api/v1/correct/proofread` | ✅ |

### HWP 엔진
| 항목 | 상태 |
|------|------|
| `ir_schema.py` — 볼드/이탤릭/표/리스트/구분선 | ✅ |
| `parser.py` (HWPX→MD) — 제목/서식 감지 | ✅ |
| `hwp_parser.py` (HWP→MD) — 직접 레코드 파싱 | ✅ |
| `hwp_parser.py` — 표 파싱 → Markdown 테이블 | ✅ |
| `hwp_parser.py` — 리스트 감지 (숫자/글머리/원번호) | ✅ |
| `hwp_parser.py` — 다중 섹션 | ✅ |
| `hwp_parser.py` — 서로게이트/컨트롤 문자 필터링 | ✅ |
| `hwp_writer.py` (MD→HWP) — 텍스트+제목 | ✅ |
| `hwp_writer.py` — 표(Table) 생성 | ✅ |
| `hwp_writer.py` — 빈 셀 처리 | ✅ |
| `hwp_writer.py` — 표로 끝나는 문서 | ✅ |
| `hwp_writer.py` — 긴 문서 (regular sector) | ✅ |
| `hwp_writer.py` — TAB 문자 전처리 | ✅ |
| `hwp_template.hwp` — OLE 템플릿 | ✅ |
| `generator.py` (MD→HWPX) — 표/인라인 파싱 | ✅ |
| `ai_service.py` (Claude/Ollama) | ✅ |
| `rag_service.py` (LangChain+pgvector) | ✅ |
| `correction_service.py` | ✅ |

---

## 3. 프론트엔드 (Next.js + shadcn/ui)

| 항목 | 상태 |
|------|------|
| 랜딩 페이지 (`/`) — Hero/Features/CTA | ✅ |
| 레이아웃 분리 — 랜딩(사이드바 없음) / 앱(사이드바) | ✅ |
| 변환 페이지 (`/convert`) | ✅ |
| AI 초안 페이지 (`/draft`) | ✅ |
| RAG 검색 페이지 (`/search`) | ✅ |
| 요약·교정 페이지 (`/correct`) | ✅ |
| 파일 업로더 컴포넌트 | ✅ |
| Diff 비교 컴포넌트 | ✅ |

---

## 4. 문서

| 문서 | 상태 |
|------|------|
| `README.md` | ✅ |
| `CLAUDE.md` (페이지 구조 추가) | ✅ |
| `docs/hwp-format-implementation.md` (비공개) | ✅ |
| `docs/hwp-5.0-spec-revision1.3.pdf` (비공개) | ✅ |
| `.gitignore`에 비공개 문서 등록 | ✅ |

---

## 5. 테스트

| 항목 | 상태 |
|------|------|
| `test_convert.py` | ✅ |
| `test_draft.py` | ✅ |
| `test_search.py` | ❌ |
| `test_correct.py` | ❌ |
| 프론트엔드 테스트 | ❌ |

---

## 6. 앞으로 해야 할 것

### 즉시 (GitHub 공개 전)
| 항목 | 우선순위 | 예상 시간 |
|------|----------|-----------|
| `pip install hwp-engine` 패키지 만들기 | **최우선** | 4시간 |
| ├ `packages/hwpx-engine/` 코드 분리 | | |
| ├ `pyproject.toml` 설정 | | |
| ├ `HwpWriter` / `HwpParser` 공개 API 정리 | | |
| └ 사용 예제 README | | |
| HWP 시각적 볼드/이탤릭 (DocInfo CharShape 추가) | ✅ 완료 | — |
| 이미지 추출 (HWP BinData / HWPX BinData) | ✅ 완료 | — |
| 이미지 삽입 (MD→HWP 바이너리) | 높음 | 4시간 |
| 셀 병합 표 지원 | 중간 | 4시간 |
| 메타데이터 추출 (작성자/날짜) | 중간 | 2시간 |
| 테스트 보강 (search, correct) | 중간 | 3시간 |

### GitHub 공개 후
| 항목 | 우선순위 |
|------|----------|
| AWS 도메인 등록 + 배포 | 높음 |
| 랜딩 페이지 디자인 개선 | 중간 |
| API 문서 (Swagger) 정리 | 중간 |
| 블로그 포스트 ("Python으로 HWP 파일 생성하기") | 높음 |
| 커뮤니티 홍보 (GeekNews, Reddit r/korea, 개발자 카페) | 높음 |

---

## 7. Day 3 작업 계획

### 오전: HWP 엔진 완성
| 순서 | 항목 | 예상 시간 | 설명 |
|------|------|-----------|------|
| 1 | HWP 시각적 볼드/이탤릭 | 3시간 | DocInfo에 볼드 CharShape 추가, PARA_CHAR_SHAPE 다중 엔트리 |
| 2 | 이미지 삽입 (MD→HWP) | 3시간 | BinData 스트림 + 0x0B 인라인 컨트롤 |
| 3 | 이미지 추출 (HWP→MD) | 2시간 | BinData 스트림 파싱 → 파일 저장 |

### 오후: 패키지 + 배포
| 순서 | 항목 | 예상 시간 | 설명 |
|------|------|-----------|------|
| 4 | `pip install hwp-engine` 패키지 | 2시간 | 코드 분리, pyproject.toml, 공개 API |
| 5 | 패키지 README + 사용 예제 | 1시간 | 3줄 코드 예제, 설치 가이드 |
| 6 | AWS 계정 + 도메인 등록 | 1시간 | Route 53 도메인 |
| 7 | EC2 + Docker 배포 | 2시간 | docker compose up |
| 8 | 도메인 연결 + HTTPS | 1시간 | SSL 인증서 |

### 저녁: 마무리
| 순서 | 항목 | 예상 시간 | 설명 |
|------|------|-----------|------|
| 9 | 라이브 테스트 | 30분 | 실제 도메인에서 변환 테스트 |
| 10 | GitHub 레포 공개 | 30분 | public 전환, topics 태그 |
| 11 | 홍보 글 초안 | 1시간 | "Python으로 HWP 파일 생성하기" 블로그 |

### 브랜드 리뉴얼
| 순서 | 항목 | 설명 |
|------|------|------|
| 0-1 | 브랜드명 확정 | HWP Bridge AI → 새 이름 결정 |
| 0-2 | 로고 제작 | 간단한 로고/아이콘 |
| 0-3 | 전체 코드 리네이밍 | 패키지명, 폴더명, import, README, 랜딩 |
| 0-4 | 도메인 확인 | 새 이름.com / .io / .kr 가능 여부 |
| 0-5 | GitHub 레포명 | 새 이름으로 생성 |
| 0-6 | PyPI 패키지명 | `pip install 새이름` 가능 여부 확인 |

### Day 3 목표
```
✅ HWP 볼드/이탤릭 시각적 렌더링 — DocInfo 4 charshape, PARA_CHAR_SHAPE 다중 엔트리, HWPX RUN 분리
✅ HWP 이미지 추출 — BinData 스트림 파싱 (HWP/HWPX 모두)
⬜ HWP 이미지 삽입 (MD→HWP 바이너리)
⬜ pip install hwp-engine 동작
⬜ AWS 라이브 배포 (도메인 + HTTPS)
⬜ GitHub 공개
```

---

### 사용자 확보 후 (3~6개월)
| 항목 | 우선순위 |
|------|----------|
| 로그인/회원가입 | 높음 |
| 사용량 대시보드 | 중간 |
| Pro 플랜 (수동 → Stripe 자동화) | 중간 |
| 온프레미스 Docker 패키지 | 중간 |
| CI/CD (GitHub Actions) | 중간 |
| 모니터링 (Grafana/Sentry) | 낮음 |
| 부하 테스트 (k6) | 낮음 |
