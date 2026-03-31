# HWP Converter AI — Day 3 남은 작업
> 2026-03-31

---

## Phase 1: 브랜드 리네이밍 ✅
| # | 항목 | 상태 |
|---|------|------|
| 1-1 | 프로젝트명 변경 (HWP Bridge AI → HWP Converter AI) | ✅ |
| 1-2 | 폴더/패키지/import 리네이밍 | ✅ |
| 1-3 | README.md 업데이트 | ✅ |
| 1-4 | 랜딩 페이지 텍스트 변경 | ✅ |
| 1-5 | docker-compose 컨테이너명 변경 | ✅ |

## Phase 2: Bedrock 전환 ✅
| # | 항목 | 상태 |
|---|------|------|
| 2-1 | anthropic[bedrock] + boto3 추가 | ✅ |
| 2-2 | ai_service.py Bedrock 클라이언트 | ✅ |
| 2-3 | .env에 AWS 키 + 리전 설정 | ✅ |
| 2-4 | Bedrock Claude 모델 활성화 | ✅ |
| 2-5 | 초안/교정 Bedrock 테스트 | ✅ |
| 2-6 | RAG 임베딩 Titan Embed 전환 | ✅ |
| 2-7 | AWS Budget Alert ($50) | ✅ |

## Phase 2.5: 추가 완료 항목 ✅
| # | 항목 | 상태 |
|---|------|------|
| - | Rate limit 분리 (변환 5회, AI 3회) | ✅ |
| - | 검색/교정 Pro 잠금 (Coming Soon) | ✅ |
| - | langchain import 수정 | ✅ |
| - | pgvector CAST 쿼리 수정 | ✅ |
| - | RAG AI 기반 청킹 (Claude) | ✅ |
| - | 로딩 스피너 개선 | ✅ |

## Phase 3: PyPI 패키지 (`pip install hwp-converter-ai`)
| # | 항목 | 상태 |
|---|------|------|
| 3-1 | `packages/hwp-converter-ai/` 코드 분리 | ⬜ |
| 3-2 | `pyproject.toml` 작성 | ⬜ |
| 3-3 | 공개 API 정리 (HwpWriter, HwpParser, HwpxGenerator) | ⬜ |
| 3-4 | README + 3줄 코드 예제 | ⬜ |
| 3-5 | PyPI 업로드 테스트 | ⬜ |

## Phase 4: AWS 배포
| # | 항목 | 상태 |
|---|------|------|
| 4-1 | 도메인 구매 | ⬜ |
| 4-2 | EC2 인스턴스 생성 | ⬜ |
| 4-3 | Docker 배포 | ⬜ |
| 4-4 | SSL + HTTPS | ⬜ |
| 4-5 | 도메인 연결 | ⬜ |
| 4-6 | 라이브 테스트 | ⬜ |

## Phase 5: GitHub 공개
| # | 항목 | 상태 |
|---|------|------|
| 5-1 | .gitignore 정리 | ⬜ |
| 5-2 | GitHub 레포 생성 | ⬜ |
| 5-3 | 첫 커밋 + 푸시 | ⬜ |
| 5-4 | public 전환 | ⬜ |

## Phase 6: 문의 기능
| # | 항목 | 상태 |
|---|------|------|
| 6-1 | 문의 폼/페이지 | ⬜ |

---

## 사전 준비 (사용자)
- [x] AWS Access Key ID + Secret Access Key
- [x] AWS Bedrock Claude 활성화
- [x] AWS Budget Alert 설정
- [ ] 도메인 결정
- [ ] PyPI 계정 (https://pypi.org/account/register/)
- [ ] GitHub 레포 생성
