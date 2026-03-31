"""교정 서비스 — 요약 + 맞춤법·행정 문체 교정, HWPX 다운로드."""
from __future__ import annotations

import uuid
from pathlib import Path

from app.core.config import settings
from app.services.ai_service import ai_service
from app.services.hwpx_engine.generator import HwpxGenerator


class CorrectionService:
    async def summarize(self, text: str) -> str:
        return await ai_service.summarize(text)

    async def proofread(self, text: str) -> dict:
        """교정 수행. 원문·교정문·변경 목록 반환."""
        result = await ai_service.proofread(text)
        return {
            "original": text,
            "corrected": result.get("corrected", text),
            "changes": result.get("changes", []),
        }

    async def proofread_to_hwpx(self, text: str, job_id: str) -> Path:
        """교정 후 결과를 HWPX로 저장하고 경로 반환."""
        result = await self.proofread(text)
        corrected_md = result["corrected"]

        output_dir = Path(settings.upload_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{job_id}.hwpx"

        generator = HwpxGenerator()
        generator.from_markdown(corrected_md, template="default", output_path=output_path)
        return output_path


# 싱글턴
correction_service = CorrectionService()
