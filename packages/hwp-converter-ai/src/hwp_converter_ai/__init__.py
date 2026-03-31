"""HWP Converter AI — Python으로 HWP/HWPX 파일 생성·파싱·변환.

사용법:
    from hwp_converter_ai import HwpWriter, HwpParser, HwpxGenerator, HwpxParser

    # Markdown → HWP
    HwpWriter().from_markdown("# 제목\\n\\n본문", "output.hwp")

    # Markdown → HWPX
    HwpxGenerator().from_markdown("# 제목\\n\\n본문", output_path="output.hwpx")

    # HWP → Markdown
    ir = HwpParser.parse("input.hwp")
    print(ir.to_markdown())

    # HWPX → Markdown
    ir = HwpxParser().parse("input.hwpx")
    print(ir.to_markdown())
"""

from .hwp_writer import HwpBinaryWriter as HwpWriter
from .hwp_parser import parse_hwp
from .generator import HwpxGenerator
from .parser import HwpxParser
from .ir_schema import DocumentIR, BlockNode, InlineNode, BlockType, InlineType

__version__ = "0.1.0"
__all__ = [
    "HwpWriter",
    "HwpxGenerator",
    "HwpxParser",
    "parse_hwp",
    "DocumentIR",
    "BlockNode",
    "InlineNode",
    "BlockType",
    "InlineType",
]


class HwpParser:
    """HWP 바이너리 파일 파서 (편의 래퍼)."""

    @staticmethod
    def parse(file_path) -> DocumentIR:
        from pathlib import Path
        return parse_hwp(Path(file_path))
