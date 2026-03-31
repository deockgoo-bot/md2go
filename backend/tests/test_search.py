"""
F-03 RAG 검색 단위 테스트.
DB/임베딩 외부 의존성은 모킹하여 처리한다.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ────────────────────────────────────────────────
# 청크 분할 테스트
# ────────────────────────────────────────────────

class TestChunking:
    def _get_splitter(self):
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        return RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", ". ", " ", ""],
        )

    def test_short_text_produces_single_chunk(self):
        splitter = self._get_splitter()
        text = "짧은 문서 내용입니다."
        chunks = splitter.split_text(text)
        assert len(chunks) == 1
        assert "짧은 문서 내용입니다" in chunks[0]

    def test_long_text_is_split_into_multiple_chunks(self):
        splitter = self._get_splitter()
        # 500자 초과 텍스트
        text = "단락 내용입니다. " * 80
        chunks = splitter.split_text(text)
        assert len(chunks) > 1

    def test_empty_text_produces_no_chunks(self):
        splitter = self._get_splitter()
        chunks = splitter.split_text("")
        assert chunks == []

    def test_chunk_size_does_not_exceed_limit(self):
        splitter = self._get_splitter()
        text = "가나다라마바사아자차카타파하" * 100
        chunks = splitter.split_text(text)
        for chunk in chunks:
            # overlap 허용 (chunk_size + chunk_overlap)
            assert len(chunk) <= 600

    def test_paragraph_boundaries_are_preferred(self):
        splitter = self._get_splitter()
        text = "첫 번째 단락입니다.\n\n두 번째 단락입니다.\n\n세 번째 단락입니다."
        chunks = splitter.split_text(text)
        # 단락 경계에서 분리되어야 함
        assert any("첫 번째 단락" in c for c in chunks)
        assert any("두 번째 단락" in c for c in chunks)


# ────────────────────────────────────────────────
# RagService 단위 테스트 (DB·임베딩 모킹)
# ────────────────────────────────────────────────

class TestRagService:
    @pytest.mark.asyncio
    async def test_index_document_returns_chunk_count(self):
        from app.services.rag_service import RagService

        service = RagService()
        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()

        fake_embedding = [0.1] * 1024

        with patch.object(service, "_embed", return_value=[fake_embedding, fake_embedding]) as mock_embed:
            count = await service.index_document(
                db=mock_db,
                document_id=uuid.uuid4(),
                text="첫 번째 청크 내용.\n\n두 번째 청크 내용.",
                filename="test.hwpx",
            )
        assert count >= 1
        mock_db.add_all.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_empty_text_returns_zero(self):
        from app.services.rag_service import RagService

        service = RagService()
        mock_db = AsyncMock()

        count = await service.index_document(
            db=mock_db,
            document_id=uuid.uuid4(),
            text="",
            filename="empty.hwpx",
        )
        assert count == 0
        mock_db.add_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_returns_list(self):
        from app.services.rag_service import RagService

        service = RagService()
        mock_db = AsyncMock()

        # DB 결과 모킹
        fake_row = {
            "document_id": uuid.uuid4(),
            "filename": "doc.hwpx",
            "chunk_index": 0,
            "page_number": None,
            "content": "검색 결과 내용",
            "score": 0.87,
        }
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [fake_row]
        mock_db.execute = AsyncMock(return_value=mock_result)

        fake_embedding = [0.1] * 1024
        with patch.object(service, "_embed", return_value=[fake_embedding]):
            results = await service.search(db=mock_db, query="예산 편성 절차", top_k=5)

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["content"] == "검색 결과 내용"
        assert "elapsed_ms" in results[0]

    @pytest.mark.asyncio
    async def test_search_empty_result(self):
        from app.services.rag_service import RagService

        service = RagService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        fake_embedding = [0.1] * 1024
        with patch.object(service, "_embed", return_value=[fake_embedding]):
            results = await service.search(db=mock_db, query="없는 내용 검색", top_k=5)

        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_document_id_filter(self):
        """document_ids 필터가 SQL에 반영되는지 확인."""
        from app.services.rag_service import RagService

        service = RagService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        fake_embedding = [0.1] * 1024
        doc_id = uuid.uuid4()
        with patch.object(service, "_embed", return_value=[fake_embedding]):
            results = await service.search(
                db=mock_db,
                query="특정 문서 검색",
                top_k=3,
                document_ids=[doc_id],
            )

        # execute가 호출되어야 함
        mock_db.execute.assert_called_once()
        # SQL에 필터가 포함되었는지 확인
        call_args = mock_db.execute.call_args[0][0]
        assert str(doc_id) in str(call_args)


# ────────────────────────────────────────────────
# 업로드 유효성 검사 테스트
# ────────────────────────────────────────────────

class TestUploadValidation:
    def test_hwpx_filename_is_valid(self):
        from app.api.routes.search import _is_hw_file
        assert _is_hw_file("document.hwpx") is True

    def test_hwp_filename_is_valid(self):
        from app.api.routes.search import _is_hw_file
        assert _is_hw_file("document.hwp") is True

    def test_docx_filename_is_invalid(self):
        from app.api.routes.search import _is_hw_file
        assert _is_hw_file("document.docx") is False

    def test_pdf_filename_is_invalid(self):
        from app.api.routes.search import _is_hw_file
        assert _is_hw_file("document.pdf") is False

    def test_empty_filename_is_invalid(self):
        from app.api.routes.search import _is_hw_file
        assert _is_hw_file("") is False
