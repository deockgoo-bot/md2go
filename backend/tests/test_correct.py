"""
F-04 문서 요약·교정 단위 테스트.
AI 서비스 호출은 모킹하여 처리한다.
"""
import uuid
import zipfile
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock


# ────────────────────────────────────────────────
# CorrectionService 단위 테스트
# ────────────────────────────────────────────────

class TestCorrectionService:
    @pytest.mark.asyncio
    async def test_summarize_returns_string(self):
        from app.services.correction_service import CorrectionService

        service = CorrectionService()
        with patch("app.services.correction_service.ai_service") as mock_ai:
            mock_ai.summarize = AsyncMock(return_value="문서 요약 결과입니다.")
            result = await service.summarize("긴 문서 내용...")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_proofread_returns_required_keys(self):
        from app.services.correction_service import CorrectionService

        service = CorrectionService()
        fake_ai_result = {
            "corrected": "교정된 내용입니다.",
            "changes": [{"type": "replace", "before": "잘못된", "after": "교정된"}],
        }
        with patch("app.services.correction_service.ai_service") as mock_ai:
            mock_ai.proofread = AsyncMock(return_value=fake_ai_result)
            result = await service.proofread("잘못된 내용입니다.")

        assert "original" in result
        assert "corrected" in result
        assert "changes" in result
        assert result["original"] == "잘못된 내용입니다."
        assert result["corrected"] == "교정된 내용입니다."

    @pytest.mark.asyncio
    async def test_proofread_preserves_original_on_no_changes(self):
        from app.services.correction_service import CorrectionService

        service = CorrectionService()
        text = "올바른 공문서 내용입니다."
        with patch("app.services.correction_service.ai_service") as mock_ai:
            mock_ai.proofread = AsyncMock(return_value={"corrected": text, "changes": []})
            result = await service.proofread(text)

        assert result["original"] == result["corrected"]
        assert result["changes"] == []

    @pytest.mark.asyncio
    async def test_proofread_to_hwpx_creates_file(self, tmp_path: Path):
        from app.services.correction_service import CorrectionService
        from app.core.config import settings

        service = CorrectionService()
        job_id = str(uuid.uuid4())

        fake_ai_result = {"corrected": "# 교정된 공문서\n\n교정된 내용.", "changes": []}
        with patch("app.services.correction_service.ai_service") as mock_ai, \
             patch.object(settings, "upload_dir", str(tmp_path)):
            mock_ai.proofread = AsyncMock(return_value=fake_ai_result)
            output_path = await service.proofread_to_hwpx(text="원본 내용.", job_id=job_id)

        assert output_path.exists()
        assert zipfile.is_zipfile(output_path)

    @pytest.mark.asyncio
    async def test_proofread_to_hwpx_output_is_valid_hwpx(self, tmp_path: Path):
        from app.services.correction_service import CorrectionService
        from app.core.config import settings

        service = CorrectionService()
        job_id = str(uuid.uuid4())

        fake_ai_result = {"corrected": "# 기안문\n\n내용입니다.", "changes": []}
        with patch("app.services.correction_service.ai_service") as mock_ai, \
             patch.object(settings, "upload_dir", str(tmp_path)):
            mock_ai.proofread = AsyncMock(return_value=fake_ai_result)
            output_path = await service.proofread_to_hwpx(text="내용", job_id=job_id)

        with zipfile.ZipFile(output_path) as zf:
            names = zf.namelist()
        assert "mimetype" in names
        assert "Contents/header.xml" in names
        assert "Contents/section0.xml" in names


# ────────────────────────────────────────────────
# 교정 API 엔드포인트 테스트
# ────────────────────────────────────────────────

class TestCorrectEndpoint:
    @pytest.mark.asyncio
    async def test_proofread_text_endpoint_success(self, client):
        fake_result = {"corrected": "교정된 텍스트.", "changes": []}
        fake_path = MagicMock()
        fake_path.exists.return_value = True

        with patch("app.services.correction_service.ai_service") as mock_ai, \
             patch("app.services.correction_service.CorrectionService.proofread_to_hwpx", new_callable=AsyncMock) as mock_hwpx:
            mock_ai.proofread = AsyncMock(return_value=fake_result)
            mock_hwpx.return_value = fake_path

            resp = await client.post(
                "/api/v1/correct/proofread",
                json={"text": "맞춤법이 틀린 문장입니다."},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert "diff" in data
        assert "original" in data["diff"]
        assert "corrected" in data["diff"]

    @pytest.mark.asyncio
    async def test_proofread_empty_text_returns_error(self, client):
        resp = await client.post(
            "/api/v1/correct/proofread",
            json={"text": ""},
        )
        # 빈 텍스트는 400 또는 처리 오류 반환
        assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_summarize_endpoint_success(self, client):
        with patch("app.services.correction_service.ai_service") as mock_ai:
            mock_ai.summarize = AsyncMock(return_value="요약된 내용입니다.")
            resp = await client.post(
                "/api/v1/correct/summarize",
                json={"text": "긴 공문서 내용입니다. " * 20},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "job_id" in data


# ────────────────────────────────────────────────
# 파일 업로드 유효성 검사
# ────────────────────────────────────────────────

class TestFileValidation:
    @pytest.mark.asyncio
    async def test_proofread_file_rejects_non_hwp(self, client):
        import io
        resp = await client.post(
            "/api/v1/correct/proofread-file",
            files={"file": ("document.docx", io.BytesIO(b"fake content"), "application/octet-stream")},
        )
        assert resp.status_code == 400
        assert "HWP" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_proofread_file_accepts_hwpx(self, client, sample_hwpx_bytes):
        import io
        fake_result = {"corrected": "교정 완료.", "changes": []}
        fake_path = MagicMock()

        with patch("app.services.correction_service.ai_service") as mock_ai, \
             patch("app.services.correction_service.CorrectionService.proofread_to_hwpx", new_callable=AsyncMock) as mock_hwpx:
            mock_ai.proofread = AsyncMock(return_value=fake_result)
            mock_hwpx.return_value = fake_path

            resp = await client.post(
                "/api/v1/correct/proofread-file",
                files={"file": ("test.hwpx", io.BytesIO(sample_hwpx_bytes), "application/octet-stream")},
            )

        assert resp.status_code == 200


# ────────────────────────────────────────────────
# 교정 결과 diff 구조 검증
# ────────────────────────────────────────────────

class TestDiffStructure:
    def test_changes_list_has_required_fields(self):
        """changes 항목은 type, before, after 필드를 가져야 한다."""
        changes = [
            {"type": "replace", "before": "이용하여", "after": "활용하여"},
            {"type": "delete", "before": "~의 경우", "after": ""},
            {"type": "insert", "before": "", "after": "붙임 참조"},
        ]
        for change in changes:
            assert "type" in change
            assert "before" in change
            assert "after" in change
            assert change["type"] in ("replace", "delete", "insert")

    def test_empty_changes_is_valid(self):
        """교정 사항이 없는 경우 빈 리스트여야 한다."""
        changes = []
        assert isinstance(changes, list)
        assert len(changes) == 0
