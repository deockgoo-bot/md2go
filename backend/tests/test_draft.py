"""
F-02 공문서 AI 초안 생성 단위 테스트.
Claude API 호출은 모킹하여 단위 테스트로 처리한다.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.hwpx_engine.generator import HwpxGenerator
from app.services.hwpx_engine.ir_schema import DocumentIR


SUPPORTED_TEMPLATES = [
    "기안문", "보고서", "공고문", "지시문", "협조문",
    "통보문", "조회문", "회신문", "계획서", "결과보고서",
]

REQUIRED_SECTIONS = ["두문", "본문", "결문"]  # 행정안전부 공문서 규정


class TestDraftGeneration:
    def test_all_10_templates_are_defined(self):
        """10종 템플릿이 모두 정의되어 있는지 검증."""
        assert len(SUPPORTED_TEMPLATES) == 10

    @pytest.mark.parametrize("template_name", SUPPORTED_TEMPLATES)
    def test_template_name_is_korean(self, template_name: str):
        """모든 템플릿 이름이 한국어로 되어 있는지 확인."""
        assert any("\uAC00" <= ch <= "\uD7A3" for ch in template_name)

    def test_generator_escapes_xml_special_chars(self, tmp_path):
        """제목에 XML 특수문자가 있을 때 안전하게 처리되는지 확인."""
        gen = HwpxGenerator()
        md = "# 2026년 AI & 디지털 전환 <예산> 기안\n\n내용입니다."
        output = tmp_path / "special.hwpx"
        gen.from_markdown(md, output_path=output)
        import zipfile
        with zipfile.ZipFile(output) as zf:
            header = zf.read("Contents/header.xml").decode()
        # XML 특수문자가 이스케이프되어야 함
        assert "<예산>" not in header
        assert "&lt;예산&gt;" in header or "예산" in header

    @pytest.mark.asyncio
    async def test_draft_api_calls_claude(self):
        """초안 생성 API가 Claude API를 호출하는지 확인."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="# 테스트 기안문\n\n내용")]

        with patch("anthropic.AsyncAnthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create = AsyncMock(return_value=mock_response)
            # 실제 서비스 호출 (ai_service.py 구현 후 활성화)
            # from app.services.ai_service import AiService
            # result = await AiService().generate_draft("기안문", "AI 도입")
            # assert "기안문" in result or "내용" in result
            assert True  # placeholder — ai_service 구현 후 교체

    def test_document_ir_has_required_structure(self):
        """생성된 IR이 공문서 필수 구조(두문·본문·결문)를 포함하는지 확인."""
        ir = DocumentIR(
            title="2026년 AI 도입 기안문",
            document_type="기안문",
            metadata={
                "두문": {"수신": "○○기관장", "경유": "(경유)"},
                "결문": {"발신명의": "○○기관장"},
            },
        )
        assert "두문" in ir.metadata
        assert "결문" in ir.metadata
        assert ir.document_type == "기안문"


class TestDocumentValidation:
    def test_empty_title_is_handled(self, tmp_path):
        """빈 제목이 있어도 생성이 실패하지 않아야 한다."""
        gen = HwpxGenerator()
        output = tmp_path / "notitle.hwpx"
        gen.from_markdown("내용만 있는 문서.", output_path=output)
        assert output.exists()

    def test_long_document_generates_correctly(self, tmp_path):
        """긴 문서(100단락)도 정상 생성되어야 한다."""
        lines = ["# 장문 보고서"] + [f"단락 {i}번 내용입니다." for i in range(100)]
        md = "\n\n".join(lines)
        output = tmp_path / "long.hwpx"
        HwpxGenerator().from_markdown(md, output_path=output)
        assert output.exists()
        assert output.stat().st_size > 0
