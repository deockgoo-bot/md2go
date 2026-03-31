"""
HWPX → JSON IR 파서.
HWPX는 ZIP 아카이브이며 내부 XML을 파싱한다.
"""
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from .ir_schema import (
    DocumentIR, BlockNode, InlineNode, BlockType, InlineType,
    TextStyle, ParagraphStyle,
)

# 한컴 HWPX XML 네임스페이스
_NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2012/HWPUnit",
    "hs": "http://www.hancom.co.kr/hwpml/2012/Section",
    "hc": "http://www.hancom.co.kr/hwpml/2012/CharShape",
    "hp2": "urn:hancom:hwpml:2011",
}


class ConversionError(Exception):
    """HWPX 변환 실패 시 발생하는 예외."""


def _strip_ns(tag: str) -> str:
    """XML 태그에서 네임스페이스 제거."""
    return tag.split("}")[-1] if "}" in tag else tag


class HwpxParser:
    """HWPX 파일을 DocumentIR로 파싱한다."""

    def __init__(self):
        self._char_shapes: list[dict] = []
        self._para_shapes: list[dict] = []

    def parse(self, hwpx_path: str | Path) -> DocumentIR:
        hwpx_path = Path(hwpx_path)
        if not hwpx_path.exists():
            raise ConversionError(f"파일이 존재하지 않습니다: {hwpx_path}")

        try:
            with zipfile.ZipFile(hwpx_path, "r") as zf:
                file_list = zf.namelist()
                header_xml = self._read_xml(zf, "Contents/header.xml", file_list)
                section_xml = self._read_xml(zf, "Contents/section0.xml", file_list)

                # BinData 이미지 추출
                images = self._extract_images(zf, file_list)

            ir = DocumentIR()
            if header_xml is not None:
                self._parse_header(header_xml, ir)
            if section_xml is not None:
                self._parse_section(section_xml, ir)

            # 이미지를 IR에 추가
            if images:
                ir.metadata['images'] = images
                for name in images:
                    stem = name.rsplit('/', 1)[-1]
                    ir.blocks.append(BlockNode(
                        type=BlockType.IMAGE,
                        metadata={'src': stem, 'alt': stem.rsplit('.', 1)[0]},
                    ))

            return ir

        except zipfile.BadZipFile:
            raise ConversionError("유효하지 않은 HWPX 파일입니다 (ZIP 구조 오류).")
        except ET.ParseError as e:
            raise ConversionError(f"XML 파싱 오류: {e}")

    @staticmethod
    def _extract_images(zf: zipfile.ZipFile, file_list: list[str]) -> dict[str, bytes]:
        """HWPX ZIP 내 BinData 폴더에서 이미지 파일 추출."""
        _IMG_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff', '.webp'}
        images: dict[str, bytes] = {}
        for name in file_list:
            lower = name.lower()
            if ('bindata' in lower or 'bin_data' in lower or 'image' in lower):
                ext = '.' + lower.rsplit('.', 1)[-1] if '.' in lower else ''
                if ext in _IMG_EXTS:
                    try:
                        images[name.rsplit('/', 1)[-1]] = zf.read(name)
                    except Exception:
                        pass
        return images

    def _read_xml(self, zf: zipfile.ZipFile, path: str, file_list: list[str]) -> ET.Element | None:
        # 경로 변형 시도 (대소문자, 다른 경로)
        candidates = [path, path.lower(), path.replace("Contents/", "contents/")]
        for p in candidates:
            if p in file_list:
                with zf.open(p) as f:
                    return ET.parse(f).getroot()
        return None

    def _parse_header(self, root: ET.Element, ir: DocumentIR) -> None:
        for elem in root.iter():
            tag = _strip_ns(elem.tag).lower()
            if tag == "title":
                ir.title = (elem.text or "").strip()
            elif tag == "author":
                ir.author = (elem.text or "").strip()
            elif tag == "charshape":
                self._parse_char_shape_def(elem)

    def _parse_char_shape_def(self, elem: ET.Element) -> None:
        """header.xml의 charShape 정의를 파싱."""
        attrs = elem.attrib
        bold = attrs.get('bold', '0') in ('1', 'true')
        italic = attrs.get('italic', '0') in ('1', 'true')
        size_pt = 10.0
        try:
            size_pt = int(attrs.get('height', '1000')) / 100.0
        except ValueError:
            pass

        # FONT 자식 요소에서도 bold/italic/size 확인 (generator 호환)
        for child in elem:
            child_tag = _strip_ns(child.tag).lower()
            if child_tag == "font":
                ca = child.attrib
                if ca.get('bold') in ('1', 'true'):
                    bold = True
                if ca.get('italic') in ('1', 'true'):
                    italic = True
                if 'size' in ca:
                    try:
                        size_pt = int(ca['size']) / 100.0
                    except ValueError:
                        pass

        self._char_shapes.append({
            'bold': bold, 'italic': italic, 'size_pt': size_pt,
        })

    def _parse_section(self, root: ET.Element, ir: DocumentIR) -> None:
        """section XML에서 직계 자식 <p>, <table> 순회."""
        for child in root:
            tag = _strip_ns(child.tag).lower()
            if tag == "p":
                block = self._parse_paragraph(child)
                if block:
                    ir.blocks.append(block)
            elif tag in ("tbl", "table"):
                block = self._parse_table(child)
                if block:
                    ir.blocks.append(block)

    def _parse_paragraph(self, elem: ET.Element) -> BlockNode | None:
        """단락 요소를 파싱. 제목/본문 감지, 인라인 서식 추출."""
        inline_nodes: list[InlineNode] = []
        is_bold = False
        is_italic = False
        font_size = 10.0
        para_style_id = None

        # 단락 속성에서 스타일 참조 확인
        for attr_name in ('paraPrIDRef', 'styleIDRef', 'style-id'):
            val = elem.attrib.get(attr_name)
            if val is not None:
                try:
                    para_style_id = int(val)
                except ValueError:
                    pass
                break

        # 하위 요소 순회
        for child in elem:
            child_tag = _strip_ns(child.tag).lower()

            if child_tag == "run":
                # <run>/<RUN>: 인라인 텍스트 단위 (charShape 참조 포함)
                run_bold, run_italic, run_size = self._parse_run_style(child)
                if run_bold:
                    is_bold = True
                if run_italic:
                    is_italic = True
                if run_size > font_size:
                    font_size = run_size

                for sub in child:
                    sub_tag = _strip_ns(sub.tag).lower()
                    if sub_tag in ("t", "char") and sub.text:
                        inline_type = InlineType.TEXT
                        if run_bold:
                            inline_type = InlineType.BOLD
                        elif run_italic:
                            inline_type = InlineType.ITALIC
                        inline_nodes.append(InlineNode(
                            type=inline_type,
                            text=sub.text,
                            style=TextStyle(bold=run_bold, italic=run_italic, font_size=run_size),
                        ))

            elif child_tag in ("t", "char") and child.text:
                # 직접 <t>/<CHAR> (run 없이)
                inline_nodes.append(InlineNode(type=InlineType.TEXT, text=child.text))

            elif child_tag in ("lineseg", "charpr"):
                pass  # 레이아웃/서식 정보 — 현재 무시

        if not inline_nodes:
            return None

        # 블록 타입 결정
        block_type = BlockType.PARAGRAPH
        heading_level = None

        # 방법 1: 폰트 크기 + 볼드 기반 판단
        if font_size >= 16.0 and is_bold:
            block_type = BlockType.HEADING
            heading_level = 1
        elif font_size >= 13.0 and is_bold:
            block_type = BlockType.HEADING
            heading_level = 2
        elif font_size >= 11.0 and is_bold:
            block_type = BlockType.HEADING
            heading_level = 3

        # 방법 2: 스타일 ID 기반 (1~6 = 제목)
        if para_style_id is not None and 1 <= para_style_id <= 6:
            block_type = BlockType.HEADING
            heading_level = para_style_id

        # 제목이면 인라인 타입을 TEXT로 통일 (Markdown에서 # 이 서식 역할)
        if block_type == BlockType.HEADING:
            for node in inline_nodes:
                node.type = InlineType.TEXT

        return BlockNode(
            type=block_type,
            level=heading_level,
            children=inline_nodes,  # type: ignore[arg-type]
        )

    def _parse_run_style(self, run_elem: ET.Element) -> tuple[bool, bool, float]:
        """<run> 요소에서 charShape 참조를 읽어 볼드/이탤릭/크기 반환."""
        bold = False
        italic = False
        size = 10.0

        # charPrIDRef 또는 charShapeId 속성으로 charShape 참조
        cs_ref = run_elem.attrib.get('charPrIDRef') or run_elem.attrib.get('charShapeId')
        if cs_ref is not None:
            try:
                idx = int(cs_ref)
                if idx < len(self._char_shapes):
                    cs = self._char_shapes[idx]
                    bold = cs.get('bold', False)
                    italic = cs.get('italic', False)
                    size = cs.get('size_pt', 10.0)
                    return bold, italic, size
            except ValueError:
                pass

        # 직접 속성 확인
        for child in run_elem:
            tag = _strip_ns(child.tag).lower()
            if tag == "charpr":
                bold = child.attrib.get('bold', '0') == '1'
                italic = child.attrib.get('italic', '0') == '1'
                h = child.attrib.get('height')
                if h:
                    try:
                        size = int(h) / 100.0
                    except ValueError:
                        pass
                break

        return bold, italic, size

    def _parse_table(self, elem: ET.Element) -> BlockNode:
        """테이블 요소를 파싱."""
        table_node = BlockNode(type=BlockType.TABLE)
        for child in elem:
            child_tag = _strip_ns(child.tag).lower()
            if child_tag == "tr":
                row_node = BlockNode(type=BlockType.PARAGRAPH)
                for td in child:
                    td_tag = _strip_ns(td.tag).lower()
                    if td_tag in ("tc", "td"):
                        cell_node = BlockNode(type=BlockType.PARAGRAPH)
                        for sub in td.iter():
                            sub_tag = _strip_ns(sub.tag).lower()
                            if sub_tag in ("t", "char") and sub.text:
                                cell_node.children.append(
                                    InlineNode(type=InlineType.TEXT, text=sub.text)
                                )
                        row_node.children.append(cell_node)  # type: ignore[arg-type]
                table_node.children.append(row_node)  # type: ignore[arg-type]
        return table_node
