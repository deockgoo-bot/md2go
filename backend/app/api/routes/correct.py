import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_api_key, check_rate_limit
from app.core.config import settings
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.schemas.document import (
    ProofreadDiff,
    ProofreadRequest,
    ProofreadResponse,
    SummarizeRequest,
    SummarizeResponse,
)
from app.services.correction_service import correction_service
from app.services.hwpx_engine.parser import HwpxParser
from app.services.hwpx_engine.hwp_parser import parse_hwp

router = APIRouter()


def _resolve_text(body_text: str | None, body_document_id, db: AsyncSession) -> str | None:
    """요청에서 텍스트 소스를 결정한다 (직접 텍스트 또는 document_id)."""
    return body_text  # document_id 기반 조회는 아래 엔드포인트에서 직접 처리


@router.post("/summarize", response_model=SummarizeResponse, summary="문서 요약")
async def summarize(
    request: Request,
    body: SummarizeRequest,
    _: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """공문서 텍스트를 3~5줄로 요약합니다."""
    await check_rate_limit(request, "ai")
    text = body.text

    if not text and body.document_id:
        from sqlalchemy import select
        from app.models.document import DocumentChunk
        result = await db.execute(
            select(DocumentChunk.content)
            .where(DocumentChunk.document_id == body.document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        rows = result.scalars().all()
        if not rows:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
        text = "\n".join(rows)

    if not text:
        raise HTTPException(status_code=400, detail="text 또는 document_id가 필요합니다.")

    try:
        summary = await correction_service.summarize(text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"요약 실패: {str(e)}")

    return SummarizeResponse(job_id=str(uuid.uuid4()), summary=summary)


@router.post("/proofread", response_model=ProofreadResponse, summary="맞춤법·행정 문체 교정")
async def proofread(
    request: Request,
    body: ProofreadRequest,
    _: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """공문서의 맞춤법과 행정 문체를 교정하고 차이를 반환합니다."""
    await check_rate_limit(request, "ai")
    text = body.text

    if not text and body.document_id:
        from sqlalchemy import select
        from app.models.document import DocumentChunk
        result = await db.execute(
            select(DocumentChunk.content)
            .where(DocumentChunk.document_id == body.document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        rows = result.scalars().all()
        if not rows:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
        text = "\n".join(rows)

    if not text:
        raise HTTPException(status_code=400, detail="text 또는 document_id가 필요합니다.")

    job_id = str(uuid.uuid4())

    try:
        result = await correction_service.proofread(text)
        output_path = await correction_service.proofread_to_hwpx(text=result["corrected"], job_id=job_id)
        download_url = f"{settings.app_base_url}/api/v1/correct/download/{job_id}"
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"교정 실패: {str(e)}")

    return ProofreadResponse(
        job_id=job_id,
        diff=ProofreadDiff(
            original=result["original"],
            corrected=result["corrected"],
            changes=result["changes"],
        ),
        download_url=download_url,
    )


@router.post("/proofread-file", response_model=ProofreadResponse, summary="HWP·HWPX 파일 교정")
async def proofread_file(
    request: Request,
    file: UploadFile = File(..., description="교정할 HWP 또는 HWPX 파일"),
    api_key: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """HWP·HWPX 파일을 업로드하여 교정합니다."""
    await check_rate_limit(request, "ai")
    if not file.filename or not (file.filename.endswith(".hwpx") or file.filename.endswith(".hwp")):
        raise HTTPException(status_code=400, detail="HWP 또는 HWPX 파일만 업로드 가능합니다.")

    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(status_code=413, detail=f"파일 크기가 {settings.max_file_size_mb}MB를 초과합니다.")

    is_hwpx = file.filename.endswith(".hwpx")
    suffix = ".hwpx" if is_hwpx else ".hwp"
    job_id = str(uuid.uuid4())
    tmp_path = Path(tempfile.mktemp(suffix=suffix))

    try:
        tmp_path.write_bytes(content)
        ir = HwpxParser().parse(tmp_path) if is_hwpx else parse_hwp(tmp_path)
        text = ir.to_plain_text()

        result = await correction_service.proofread(text)
        output_path = await correction_service.proofread_to_hwpx(text=result["corrected"], job_id=job_id)
        download_url = f"{settings.app_base_url}/api/v1/correct/download/{job_id}"
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"교정 실패: {str(e)}")
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return ProofreadResponse(
        job_id=job_id,
        diff=ProofreadDiff(
            original=result["original"],
            corrected=result["corrected"],
            changes=result["changes"],
        ),
        download_url=download_url,
    )


@router.get("/download/{job_id}", summary="교정된 HWPX 파일 다운로드")
async def download_corrected(
    job_id: str,
    _: ApiKey = Depends(verify_api_key),
):
    file_path = Path(settings.upload_dir) / f"{job_id}.hwpx"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없거나 만료되었습니다.")

    return FileResponse(
        path=file_path,
        filename=f"corrected-{job_id}.hwpx",
        media_type="application/octet-stream",
    )
