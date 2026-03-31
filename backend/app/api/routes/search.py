import uuid
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_api_key, check_rate_limit
from app.core.config import settings
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.models.document import Document
from app.schemas.document import SearchRequest, SearchResponse, SearchResult
from app.services.hwpx_engine.parser import HwpxParser
from app.services.hwpx_engine.hwp_parser import parse_hwp
from app.services.rag_service import rag_service

router = APIRouter()


def _is_hw_file(filename: str) -> bool:
    return filename.endswith(".hwpx") or filename.endswith(".hwp")


@router.post("/upload", summary="HWP·HWPX 파일 업로드 및 RAG 인덱싱")
async def upload_and_index(
    request: Request,
    file: UploadFile = File(..., description="인덱싱할 HWP 또는 HWPX 파일"),
    api_key: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """HWP·HWPX 파일을 업로드하여 텍스트를 추출하고 벡터 DB에 인덱싱합니다."""
    await check_rate_limit(request, "ai")
    if not file.filename or not _is_hw_file(file.filename):
        raise HTTPException(status_code=400, detail="HWP 또는 HWPX 파일만 업로드 가능합니다.")

    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(status_code=413, detail=f"파일 크기가 {settings.max_file_size_mb}MB를 초과합니다.")

    is_hwpx = file.filename.endswith(".hwpx")
    suffix = ".hwpx" if is_hwpx else ".hwp"
    file_type = "hwpx" if is_hwpx else "hwp"

    doc = Document(
        id=uuid.uuid4(),
        user_id=api_key.user_id,
        filename=file.filename,
        file_type=file_type,
        status="processing",
    )
    db.add(doc)
    await db.flush()

    tmp_path = Path(tempfile.mktemp(suffix=suffix))
    try:
        tmp_path.write_bytes(content)
        ir = HwpxParser().parse(tmp_path) if is_hwpx else parse_hwp(tmp_path)
        markdown = ir.to_markdown()

        chunk_count = await rag_service.index_document(
            db=db,
            document_id=doc.id,
            text=ir.to_plain_text(),
            filename=file.filename,
            markdown=markdown,
        )

        doc.status = "done"
        doc.doc_metadata = {"chunk_count": chunk_count}
    except Exception as e:
        doc.status = "error"
        doc.error_message = str(e)
        raise HTTPException(status_code=422, detail=f"인덱싱 실패: {str(e)}")
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return {
        "document_id": str(doc.id),
        "filename": file.filename,
        "status": "done",
        "chunk_count": doc.doc_metadata.get("chunk_count", 0),
    }


@router.post("/query", response_model=SearchResponse, summary="자연어 RAG 검색")
async def search_documents(
    request: Request,
    body: SearchRequest,
    _: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """자연어로 인덱싱된 문서를 검색합니다. (3초 이내)"""
    await check_rate_limit(request, "ai")
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="검색 쿼리가 비어 있습니다.")

    try:
        hits = await rag_service.search(
            db=db,
            query=body.query,
            top_k=body.top_k,
            document_ids=body.document_ids,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"검색 실패: {str(e)}")

    elapsed_ms = hits[0]["elapsed_ms"] if hits else 0.0
    results = [
        SearchResult(
            document_id=h["document_id"],
            filename=h["filename"],
            chunk_index=h["chunk_index"],
            page_number=h["page_number"],
            content=h["content"],
            score=h["score"],
        )
        for h in hits
    ]
    return SearchResponse(query=body.query, results=results, elapsed_ms=elapsed_ms)
