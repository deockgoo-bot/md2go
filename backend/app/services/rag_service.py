"""RAG 서비스 — HWPX 텍스트 청크 → pgvector 인덱싱 → 유사도 검색."""
from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document, DocumentChunk

logger = logging.getLogger(__name__)

class RagService:
    """Claude AI 청킹 + pgvector 임베딩 검색."""

    async def _chunk_with_ai(self, markdown: str) -> list[str]:
        """Claude로 마크다운을 검색에 최적화된 청크로 분할."""
        from app.services.ai_service import ai_service

        prompt = f"""다음 공문서 마크다운을 RAG 검색용 청크로 분할하세요.

규칙:
1. 제목/조항 단위로 분할 (제1조, 제2조 등)
2. 각 청크에 소속 섹션 제목을 [제목] 접두사로 포함
3. 표는 별도 청크로 분리하고 [표: 제목] 접두사 포함
4. 청크당 200~800자 유지
5. 문맥이 끊기지 않도록 관련 내용은 같은 청크에

반드시 JSON 배열로만 응답하세요:
["청크1 텍스트", "청크2 텍스트", ...]

마크다운:
{markdown[:8000]}"""

        import json
        raw = await ai_service.generate(
            prompt,
            system_prompt="당신은 RAG 검색 최적화 전문가입니다. JSON 배열로만 응답하세요.",
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            chunks = json.loads(raw)
            if isinstance(chunks, list):
                return [str(c) for c in chunks if str(c).strip()]
        except json.JSONDecodeError:
            pass

        # AI 청킹 실패 시 단순 분할 fallback
        logger.warning("AI 청킹 실패, 단순 분할 사용")
        return self._simple_chunk(markdown)

    @staticmethod
    def _simple_chunk(text: str, size: int = 500, overlap: int = 50) -> list[str]:
        """fallback: 고정 크기 분할."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + size
            chunks.append(text[start:end])
            start = end - overlap
        return [c.strip() for c in chunks if c.strip()]

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        """텍스트 목록을 임베딩 벡터로 변환."""
        if settings.use_ollama:
            return await self._embed_ollama(texts)
        if settings.aws_access_key_id:
            return await self._embed_bedrock(texts)
        return await self._embed_openai(texts)

    async def _embed_bedrock(self, texts: list[str]) -> list[list[float]]:
        """AWS Bedrock Titan Embeddings."""
        import boto3, json

        client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        results = []
        for t in texts:
            resp = client.invoke_model(
                modelId="amazon.titan-embed-text-v2:0",
                body=json.dumps({"inputText": t}),
            )
            body = json.loads(resp["body"].read())
            results.append(body["embedding"])
        return results

    async def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        from openai import AsyncOpenAI  # type: ignore

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.embeddings.create(model=settings.embedding_model, input=texts)
        return [item.embedding for item in resp.data]

    async def _embed_ollama(self, texts: list[str]) -> list[list[float]]:
        import ollama as _ollama  # type: ignore

        client = _ollama.AsyncClient(host=settings.ollama_base_url)
        results = []
        for t in texts:
            resp = await client.embeddings(model=settings.embedding_model, prompt=t)
            results.append(resp["embedding"])
        return results

    async def index_document(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        text: str,
        filename: str,
        markdown: str = "",
    ) -> int:
        """문서를 AI로 청킹하고 임베딩을 DB에 저장한다.

        Args:
            text: plain text (fallback용)
            markdown: 마크다운 (AI 청킹에 사용)
        Returns:
            저장된 청크 수
        """
        source = markdown if markdown else text
        chunks: list[str] = await self._chunk_with_ai(source)

        if not chunks:
            logger.warning("document %s: 청크 없음 (빈 텍스트)", document_id)
            return 0

        embeddings = await self._embed(chunks)

        db_chunks = [
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=document_id,
                chunk_index=i,
                content=chunk,
                embedding=emb,
            )
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
        ]
        db.add_all(db_chunks)
        await db.flush()
        return len(db_chunks)

    async def search(
        self,
        db: AsyncSession,
        query: str,
        top_k: int = 5,
        document_ids: list[uuid.UUID] | None = None,
    ) -> list[dict]:
        """자연어 질의로 유사 청크를 검색한다.

        Returns:
            [{"document_id", "filename", "chunk_index", "page_number", "content", "score"}, ...]
        """
        t0 = time.monotonic()
        query_vec = (await self._embed([query]))[0]

        # pgvector cosine 유사도 검색
        vec_str = "[" + ",".join(str(v) for v in query_vec) + "]"
        filter_clause = ""
        params: dict = {"vec": vec_str, "top_k": top_k}

        if document_ids:
            # UUID 목록 필터 (파라미터 바인딩)
            validated = [str(uuid.UUID(str(d))) for d in document_ids]  # UUID 검증
            placeholders = ", ".join(f":did{i}" for i in range(len(validated)))
            filter_clause = f"AND dc.document_id IN ({placeholders})"
            for i, d in enumerate(validated):
                params[f"did{i}"] = d

        sql = text(f"""
            SELECT
                dc.id,
                dc.document_id,
                d.filename,
                dc.chunk_index,
                dc.page_number,
                dc.content,
                1 - (dc.embedding <=> CAST(:vec AS vector)) AS score
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.embedding IS NOT NULL
            {filter_clause}
            ORDER BY dc.embedding <=> CAST(:vec AS vector)
            LIMIT :top_k
        """)

        result = await db.execute(sql, params)
        rows = result.mappings().all()

        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info("RAG 검색 완료: query=%r, hits=%d, %.1fms", query, len(rows), elapsed_ms)

        return [
            {
                "document_id": row["document_id"],
                "filename": row["filename"],
                "chunk_index": row["chunk_index"],
                "page_number": row["page_number"],
                "content": row["content"],
                "score": float(row["score"]),
                "elapsed_ms": elapsed_ms,
            }
            for row in rows
        ]


# 싱글턴
rag_service = RagService()
