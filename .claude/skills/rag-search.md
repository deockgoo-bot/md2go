# /rag-search

내부 HWPX 문서를 자연어로 검색합니다.

## 사용법
```
/rag-search [자연어 질의]
```

## 예시
- `/rag-search "작년 스마트시티 사업 예산 근거"` — 관련 문서 검색
- `/rag-search "AI 바우처 신청 자격 요건"` — 특정 내용 검색
- `/rag-search index path/to/documents/` — 문서 배치 인덱싱

## 동작
1. 질의 → 임베딩 변환
2. pgvector cosine similarity 검색
3. Top-5 결과 반환 (문서명, 페이지, 관련 텍스트)
4. 출처 기반 Claude API 답변 생성

## 인덱싱
- `/rag-search index [경로]` 명령으로 새 문서 인덱싱
- 문서 1건당 5초 이내 처리

## 연관 에이전트
rag-indexer 에이전트를 사용합니다.
