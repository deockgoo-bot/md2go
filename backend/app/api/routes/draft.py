import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse

from app.api.deps import verify_api_key, check_rate_limit
from app.core.config import settings
from app.schemas.document import DraftRequest, DraftResponse
from app.services.ai_service import ai_service
from app.services.hwpx_engine.generator import HwpxGenerator
from app.services.hwpx_engine.hwp_writer import HwpBinaryWriter

router = APIRouter()


@router.post("/generate", response_model=DraftResponse, summary="공문서 AI 초안 생성")
async def generate_draft(
    request: Request,
    body: DraftRequest,
    _: object = Depends(verify_api_key),
):
    """행정안전부 공문서 규정에 맞는 초안을 AI로 생성합니다. (60초 이내)

    body 필드:
    - format: "hwpx" (기본) | "hwp" | "hwp-legacy"
    """
    await check_rate_limit(request, "ai")
    job_id = str(uuid.uuid4())
    output_format = (body.format or "hwpx").lower()
    if output_format not in ("hwp", "hwpx"):
        output_format = "hwpx"

    try:
        markdown = await ai_service.generate_draft(
            template=body.template,
            title=body.title,
            body_hint=body.body_hint,
            department=body.department,
            reference_number=body.reference_number,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 초안 생성 실패: {str(e)}")

    # HWP/HWPX 변환 및 저장
    try:
        output_dir = Path(settings.upload_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if output_format == "hwp":
            ext = "hwp"
            output_path = output_dir / f"{job_id}.hwp"
            HwpBinaryWriter().from_markdown(markdown, output_path=output_path)
        else:
            ext = "hwpx"
            output_path = output_dir / f"{job_id}.hwpx"
            HwpxGenerator().from_markdown(markdown, template=body.template, output_path=output_path)

        download_url = f"{settings.app_base_url}/api/v1/draft/download/{job_id}?fmt={ext}"
    except Exception:
        # 변환 실패 시에도 Markdown은 반환
        download_url = None
        ext = output_format

    return DraftResponse(
        job_id=job_id,
        status="completed",
        markdown=markdown,
        download_url=download_url,
    )


@router.get("/download/{job_id}", summary="생성된 초안 다운로드")
async def download_draft(
    job_id: str,
    fmt: str = Query(default="hwpx"),
    _: object = Depends(verify_api_key),
):
    ext = "hwp" if fmt == "hwp" else "hwpx"
    file_path = Path(settings.upload_dir) / f"{job_id}.{ext}"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없거나 만료되었습니다.")

    return FileResponse(
        path=file_path,
        filename=f"draft-{job_id}.{ext}",
        media_type="application/octet-stream",
    )
