import uuid
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.deps import verify_api_key, check_rate_limit
from app.core.config import settings
from app.services.hwpx_engine.parser import HwpxParser
from app.services.hwpx_engine.generator import HwpxGenerator
from app.services.hwpx_engine.hwp_parser import parse_hwp
from app.services.hwpx_engine.hwp_writer import HwpBinaryWriter

router = APIRouter()


class ConvertResponse(BaseModel):
    job_id: str
    status: str
    markdown: str | None = None
    download_url: str | None = None


@router.post("/hwp-to-md", response_model=ConvertResponse, summary="HWP·HWPX → Markdown 변환")
async def convert_hwp_to_markdown(
    request: Request,
    file: UploadFile = File(..., description="변환할 HWP 또는 HWPX 파일 (최대 50MB)"),
    _: object = Depends(verify_api_key),
):
    """HWP·HWPX 파일을 Markdown으로 변환합니다. 처리 후 업로드 파일은 즉시 삭제됩니다."""
    await check_rate_limit(request)
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
        return ConvertResponse(job_id=job_id, status="completed", markdown=ir.to_markdown())
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"변환 실패: {str(e)}")
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


# 이전 경로 호환 유지
@router.post("/hwpx-to-md", response_model=ConvertResponse, include_in_schema=False)
async def convert_hwpx_to_markdown_compat(
    request: Request,
    file: UploadFile = File(...),
    _: object = Depends(verify_api_key),
):
    return await convert_hwp_to_markdown(request=request, file=file, _=_)


@router.post("/md-to-hwp", summary="Markdown → HWP·HWPX 변환")
async def convert_markdown_to_hwp(
    request: Request,
    body: dict,
    _: object = Depends(verify_api_key),
):
    """Markdown을 HWP 또는 HWPX 파일로 변환합니다.

    body 필드:
    - markdown: 변환할 Markdown 텍스트
    - format: "hwpx" (기본) 또는 "hwp"
    - template: 공문서 템플릿 (기본: "default")
    """
    await check_rate_limit(request)
    markdown_text: str = body.get("markdown", "")
    output_format: str = body.get("format", "hwpx").lower()
    template: str = body.get("template", "default")

    if not markdown_text:
        raise HTTPException(status_code=400, detail="markdown 필드가 필요합니다.")
    if output_format not in ("hwp", "hwpx"):
        output_format = "hwpx"

    job_id = str(uuid.uuid4())
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    try:
        if output_format == "hwp":
            ext = "hwp"
            output_path = upload_dir / f"{job_id}.hwp"
            HwpBinaryWriter().from_markdown(markdown_text, output_path=output_path)
        else:
            ext = "hwpx"
            output_path = upload_dir / f"{job_id}.hwpx"
            HwpxGenerator().from_markdown(markdown_text, template=template, output_path=output_path)

        download_url = f"{settings.app_base_url}/api/v1/convert/download/{job_id}?fmt={ext}"
        return {"job_id": job_id, "status": "completed", "download_url": download_url, "format": ext}
    except Exception as e:
        for p in upload_dir.glob(f"{job_id}*"):
            p.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"변환 실패: {str(e)}")


# 이전 경로 호환 유지
@router.post("/md-to-hwpx", include_in_schema=False)
async def convert_md_to_hwpx_compat(request: Request, body: dict, _: object = Depends(verify_api_key)):
    return await convert_markdown_to_hwp(request=request, body=body, _=_)


@router.get("/download/{job_id}", summary="변환된 파일 다운로드")
async def download_converted_file(
    job_id: str,
    background_tasks: BackgroundTasks,
    fmt: str = Query(default="hwpx"),
    _: object = Depends(verify_api_key),
):
    # Path traversal 방지: UUID 형식 검증
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 job_id 형식입니다.")
    ext = "hwp" if fmt == "hwp" else "hwpx"
    file_path = Path(settings.upload_dir) / f"{job_id}.{ext}"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없거나 만료되었습니다.")

    background_tasks.add_task(lambda: file_path.unlink(missing_ok=True))
    return FileResponse(
        path=file_path,
        filename=f"converted.{ext}",
        media_type="application/octet-stream",
    )
