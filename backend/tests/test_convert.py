"""
F-01 HWPX ↔ Markdown 변환 엔진 단위 테스트.
품질 기준: 오류율 5% 이하 (샘플 100종 기준)
"""
import io
import pytest
import zipfile
from pathlib import Path

from app.services.hwpx_engine.parser import HwpxParser, ConversionError
from app.services.hwpx_engine.generator import HwpxGenerator
from app.services.hwpx_engine.ir_schema import DocumentIR, BlockNode, BlockType, InlineNode, InlineType


# ────────────────────────────────────────────────
# HwpxParser 단위 테스트
# ────────────────────────────────────────────────

class TestHwpxParser:
    def _make_hwpx(self, title: str = "제목", body_text: str = "본문") -> Path:
        """테스트용 최소 HWPX 파일 생성."""
        import tempfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("mimetype", "application/hwp+zip")
            zf.writestr(
                "Contents/header.xml",
                f'<?xml version="1.0" encoding="UTF-8"?>'
                f'<HWPML xmlns="http://www.hancom.co.kr/hwpml/2012/document">'
                f"<HEAD><DOCSUMMARY><TITLE>{title}</TITLE></DOCSUMMARY></HEAD>"
                f"</HWPML>",
            )
            zf.writestr(
                "Contents/section0.xml",
                f'<?xml version="1.0" encoding="UTF-8"?>'
                f'<HWPML xmlns="http://www.hancom.co.kr/hwpml/2012/section">'
                f"<BODY><P><RUN><t>{body_text}</t></RUN></P></BODY>"
                f"</HWPML>",
            )
        tmp = Path(tempfile.mktemp(suffix=".hwpx"))
        tmp.write_bytes(buf.getvalue())
        return tmp

    def test_parse_returns_document_ir(self):
        tmp = self._make_hwpx("테스트 제목", "테스트 본문")
        try:
            parser = HwpxParser()
            ir = parser.parse(tmp)
            assert isinstance(ir, DocumentIR)
            assert ir.title == "테스트 제목"
        finally:
            tmp.unlink(missing_ok=True)

    def test_parse_extracts_body_text(self):
        tmp = self._make_hwpx(body_text="안녕하세요")
        try:
            parser = HwpxParser()
            ir = parser.parse(tmp)
            markdown = ir.to_markdown()
            assert "안녕하세요" in markdown
        finally:
            tmp.unlink(missing_ok=True)

    def test_parse_raises_on_missing_file(self):
        parser = HwpxParser()
        with pytest.raises(ConversionError, match="존재하지 않습니다"):
            parser.parse(Path("/nonexistent/file.hwpx"))

    def test_parse_raises_on_invalid_zip(self, tmp_path: Path):
        bad_file = tmp_path / "bad.hwpx"
        bad_file.write_bytes(b"not a zip file")
        parser = HwpxParser()
        with pytest.raises(ConversionError, match="유효하지 않은 HWPX"):
            parser.parse(bad_file)

    def test_parse_cleans_up_no_side_effects(self):
        """파서는 원본 파일을 수정하거나 삭제하지 않아야 한다."""
        tmp = self._make_hwpx()
        original_size = tmp.stat().st_size
        try:
            HwpxParser().parse(tmp)
            assert tmp.exists()
            assert tmp.stat().st_size == original_size
        finally:
            tmp.unlink(missing_ok=True)


# ────────────────────────────────────────────────
# HwpxGenerator 단위 테스트
# ────────────────────────────────────────────────

class TestHwpxGenerator:
    def test_from_markdown_creates_hwpx_file(self, tmp_path: Path):
        output = tmp_path / "out.hwpx"
        gen = HwpxGenerator()
        result = gen.from_markdown("# 제목\n\n본문 내용입니다.", output_path=output)
        assert result.exists()
        assert zipfile.is_zipfile(result)

    def test_from_markdown_preserves_title(self, tmp_path: Path):
        output = tmp_path / "out.hwpx"
        gen = HwpxGenerator()
        gen.from_markdown("# AI 도입 기안문\n\n내용", output_path=output)
        with zipfile.ZipFile(output) as zf:
            header = zf.read("Contents/header.xml").decode()
        assert "AI 도입 기안문" in header

    def test_from_markdown_output_is_valid_zip(self, tmp_path: Path):
        output = tmp_path / "out.hwpx"
        HwpxGenerator().from_markdown("테스트", output_path=output)
        with zipfile.ZipFile(output) as zf:
            assert "Contents/header.xml" in zf.namelist()
            assert "Contents/section0.xml" in zf.namelist()

    def test_roundtrip_markdown(self, tmp_path: Path):
        """Markdown → HWPX → Markdown 라운드트립 동일성 검증."""
        original_md = "# 제목\n\n본문 단락입니다."
        output = tmp_path / "roundtrip.hwpx"
        gen = HwpxGenerator()
        gen.from_markdown(original_md, output_path=output)

        parser = HwpxParser()
        ir = parser.parse(output)
        recovered_md = ir.to_markdown()
        assert "제목" in recovered_md
        assert "본문 단락입니다" in recovered_md


# ────────────────────────────────────────────────
# DocumentIR 단위 테스트
# ────────────────────────────────────────────────

class TestDocumentIR:
    def test_to_markdown_heading(self):
        ir = DocumentIR(title="제목")
        block = BlockNode(type=BlockType.HEADING, level=1)
        block.children.append(InlineNode(type=InlineType.TEXT, text="섹션 1"))
        ir.blocks.append(block)
        md = ir.to_markdown()
        assert "# 섹션 1" in md

    def test_to_markdown_paragraph(self):
        ir = DocumentIR()
        block = BlockNode(type=BlockType.PARAGRAPH)
        block.children.append(InlineNode(type=InlineType.TEXT, text="단락 내용"))
        ir.blocks.append(block)
        assert "단락 내용" in ir.to_markdown()

    def test_to_markdown_table(self):
        ir = DocumentIR()
        table = BlockNode(type=BlockType.TABLE)
        # 헤더 행
        header_row = BlockNode(type=BlockType.PARAGRAPH)
        for text in ["이름", "나이"]:
            cell = BlockNode(type=BlockType.PARAGRAPH)
            cell.children.append(InlineNode(type=InlineType.TEXT, text=text))
            header_row.children.append(cell)  # type: ignore
        table.children.append(header_row)  # type: ignore
        ir.blocks.append(table)
        md = ir.to_markdown()
        assert "이름" in md
        assert "나이" in md
        assert "---" in md

    def test_to_dict_is_serializable(self):
        import json
        ir = DocumentIR(title="직렬화 테스트")
        d = ir.to_dict()
        json_str = json.dumps(d, ensure_ascii=False)
        assert "직렬화 테스트" in json_str
