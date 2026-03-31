"""
JSON IR → HWPX 생성기.
Markdown → IR → HWPX 파이프라인의 마지막 단계.

hwpx_template.hwpx (실제 한컴 호환 HWPX)를 템플릿으로 사용하고
Contents/section0.xml만 교체한다. HWP 바이너리와 동일한 접근.
"""
import zipfile
from pathlib import Path

from .ir_schema import DocumentIR, BlockNode, BlockType, InlineNode, InlineType

_TEMPLATE = Path(__file__).parent / "hwpx_template.hwpx"

# 템플릿 section0.xml에서 추출한 secPr + colPr (페이지 설정)
# 첫 문단의 첫 run에 반드시 포함되어야 한컴오피스가 인식함
_SEC_PR = (
    '<hp:secPr id="" textDirection="HORIZONTAL" spaceColumns="1134" tabStop="8000"'
    ' tabStopVal="4000" tabStopUnit="HWPUNIT" outlineShapeIDRef="1" memoShapeIDRef="0"'
    ' textVerticalWidthHead="0" masterPageCnt="0">'
    '<hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0"/>'
    '<hp:startNum pageStartsOn="BOTH" page="0" pic="0" tbl="0" equation="0"/>'
    '<hp:visibility hideFirstHeader="0" hideFirstFooter="0" hideFirstMasterPage="0"'
    ' border="SHOW_ALL" fill="SHOW_ALL" hideFirstPageNum="0" hideFirstEmptyLine="0"'
    ' showLineNumber="0"/>'
    '<hp:lineNumberShape restartType="0" countBy="0" distance="0" startNumber="0"/>'
    '<hp:pagePr landscape="WIDELY" width="59528" height="84186" gutterType="LEFT_ONLY">'
    '<hp:margin header="4252" footer="4252" gutter="0" left="8504" right="8504"'
    ' top="5668" bottom="4252"/>'
    '</hp:pagePr>'
    '<hp:footNotePr>'
    '<hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0"/>'
    '<hp:noteLine length="-1" type="SOLID" width="0.12 mm" color="#000000"/>'
    '<hp:noteSpacing betweenNotes="283" belowLine="567" aboveLine="850"/>'
    '<hp:numbering type="CONTINUOUS" newNum="1"/>'
    '<hp:placement place="EACH_COLUMN" beneathText="0"/>'
    '</hp:footNotePr>'
    '<hp:endNotePr>'
    '<hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0"/>'
    '<hp:noteLine length="14692344" type="SOLID" width="0.12 mm" color="#000000"/>'
    '<hp:noteSpacing betweenNotes="0" belowLine="567" aboveLine="850"/>'
    '<hp:numbering type="CONTINUOUS" newNum="1"/>'
    '<hp:placement place="END_OF_DOCUMENT" beneathText="0"/>'
    '</hp:endNotePr>'
    '<hp:pageBorderFill type="BOTH" borderFillIDRef="1" textBorder="PAPER"'
    ' headerInside="0" footerInside="0" fillArea="PAPER">'
    '<hp:offset left="1417" right="1417" top="1417" bottom="1417"/>'
    '</hp:pageBorderFill>'
    '<hp:pageBorderFill type="EVEN" borderFillIDRef="1" textBorder="PAPER"'
    ' headerInside="0" footerInside="0" fillArea="PAPER">'
    '<hp:offset left="1417" right="1417" top="1417" bottom="1417"/>'
    '</hp:pageBorderFill>'
    '<hp:pageBorderFill type="ODD" borderFillIDRef="1" textBorder="PAPER"'
    ' headerInside="0" footerInside="0" fillArea="PAPER">'
    '<hp:offset left="1417" right="1417" top="1417" bottom="1417"/>'
    '</hp:pageBorderFill>'
    '</hp:secPr>'
    '<hp:ctrl>'
    '<hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="1" sameSz="1" sameGap="0"/>'
    '</hp:ctrl>'
)

# 템플릿 section0.xml의 네임스페이스 선언 (hs:sec 열기 태그)
_SEC_OPEN = (
    '<hs:sec'
    ' xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app"'
    ' xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'
    ' xmlns:hp10="http://www.hancom.co.kr/hwpml/2016/paragraph"'
    ' xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"'
    ' xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core"'
    ' xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"'
    ' xmlns:hhs="http://www.hancom.co.kr/hwpml/2011/history"'
    ' xmlns:hm="http://www.hancom.co.kr/hwpml/2011/master-page"'
    ' xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf"'
    ' xmlns:dc="http://purl.org/dc/elements/1.1/"'
    ' xmlns:opf="http://www.idpf.org/2007/opf/"'
    ' xmlns:ooxmlchart="http://www.hancom.co.kr/hwpml/2016/ooxmlchart"'
    ' xmlns:hwpunitchar="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar"'
    ' xmlns:epub="http://www.idpf.org/2007/ops"'
    ' xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0">'
)


class HwpxGenerator:
    """DocumentIR 또는 Markdown을 HWPX 파일로 변환한다.

    hwpx_template.hwpx를 기반으로 Contents/section0.xml만 교체.
    """

    _para_id = 1000000000

    def from_markdown(
        self,
        markdown_text: str,
        template: str = "default",
        output_path: str | Path = Path("output.hwpx"),
    ) -> Path:
        ir = self._markdown_to_ir(markdown_text)
        return self.from_ir(ir, output_path=Path(output_path), template=template)

    def from_ir(
        self,
        ir: DocumentIR,
        output_path: str | Path = Path("output.hwpx"),
        template: str = "default",
    ) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._para_id = 1000000000

        section_xml = self._build_section(ir)

        # 템플릿 복사 + section0.xml 교체 + header.xml 패치 (표 테두리 추가)
        with zipfile.ZipFile(_TEMPLATE, "r") as src, \
             zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as dst:
            for item in src.infolist():
                if item.filename == "mimetype":
                    mi = zipfile.ZipInfo("mimetype")
                    mi.compress_type = zipfile.ZIP_STORED
                    dst.writestr(mi, "application/hwp+zip")
                elif item.filename == "Contents/section0.xml":
                    dst.writestr("Contents/section0.xml", section_xml)
                elif item.filename == "Contents/header.xml":
                    dst.writestr("Contents/header.xml",
                                 self._patch_header(src.read(item.filename).decode()))
                else:
                    dst.writestr(item, src.read(item.filename))

        return output_path

    # 표 테두리용 borderFill id (header.xml에 패치 삽입)
    _TABLE_BORDER_FILL_ID = "3"

    @staticmethod
    def _patch_header(header_xml: str) -> str:
        """header.xml에 실선 테두리 borderFill id=3 추가 + charPr 2,3 (볼드/이탤릭) 추가."""
        # borderFill 3 (실선 테두리) 삽입
        solid_bf = (
            '<hh:borderFill id="3" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
            '<hh:slash type="NONE" Crooked="0" isCounter="0"/>'
            '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
            '<hh:leftBorder type="SOLID" width="0.12 mm" color="#000000"/>'
            '<hh:rightBorder type="SOLID" width="0.12 mm" color="#000000"/>'
            '<hh:topBorder type="SOLID" width="0.12 mm" color="#000000"/>'
            '<hh:bottomBorder type="SOLID" width="0.12 mm" color="#000000"/>'
            '<hh:diagonal type="NONE" width="0.12 mm" color="#000000"/>'
            '</hh:borderFill>'
        )
        header_xml = header_xml.replace(
            '</hh:borderFills>',
            solid_bf + '</hh:borderFills>'
        )
        # itemCnt 업데이트: 2 → 3
        header_xml = header_xml.replace(
            '<hh:borderFills itemCnt="2">',
            '<hh:borderFills itemCnt="3">'
        )

        # charPr 2 (볼드), 3 (이탤릭) 추가
        bold_cp = (
            '<hh:charPr id="2" height="1000" textColor="#000000" shadeColor="none"'
            ' useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="1" bold="1">'
            '<hh:fontRef hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '</hh:charPr>'
        )
        italic_cp = (
            '<hh:charPr id="3" height="1000" textColor="#000000" shadeColor="none"'
            ' useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="1" italic="1">'
            '<hh:fontRef hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '</hh:charPr>'
        )
        header_xml = header_xml.replace(
            '</hh:charProperties>',
            bold_cp + italic_cp + '</hh:charProperties>'
        )
        # charProperties itemCnt 업데이트
        import re
        header_xml = re.sub(
            r'<hh:charProperties itemCnt="\d+">',
            lambda m: m.group(0).replace(
                m.group(0).split('"')[1],
                str(int(m.group(0).split('"')[1]) + 2)
            ),
            header_xml,
        )
        return header_xml

    def _next_id(self) -> str:
        self._para_id += 1
        return str(self._para_id)

    # ──────────────────────────────────────────────────────────
    # section0.xml 생성
    # ──────────────────────────────────────────────────────────

    def _build_section(self, ir: DocumentIR) -> str:
        paras = []
        for i, block in enumerate(ir.blocks):
            prefix = _SEC_PR if i == 0 else ""
            paras.append(self._block_to_xml(block, prefix))

        if not paras:
            pid = self._next_id()
            paras.append(
                f'<hp:p id="{pid}" paraPrIDRef="0" styleIDRef="0"'
                f' pageBreak="0" columnBreak="0" merged="0">'
                f'<hp:run charPrIDRef="0">{_SEC_PR}</hp:run>'
                f'<hp:run charPrIDRef="0"><hp:t/></hp:run>'
                f'</hp:p>'
            )

        body = "".join(paras)
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            f'{_SEC_OPEN}{body}</hs:sec>'
        )

    def _block_to_xml(self, block: BlockNode, first_prefix: str = "") -> str:
        pid = self._next_id()
        pr = f'id="{pid}" paraPrIDRef="{{ppr}}" styleIDRef="{{sid}}"' \
             ' pageBreak="0" columnBreak="0" merged="0"'

        if block.type == BlockType.HEADING:
            text = "".join(
                self._esc(c.text)
                for c in block.children if isinstance(c, InlineNode)
            )
            sid = min(block.level or 1, 3)
            p = pr.replace("{ppr}", "1").replace("{sid}", str(sid))
            prefix_run = f'<hp:run charPrIDRef="0">{first_prefix}</hp:run>' if first_prefix else ''
            return (
                f'<hp:p {p}>'
                f'{prefix_run}'
                f'<hp:run charPrIDRef="1"><hp:t>{text}</hp:t></hp:run>'
                f'</hp:p>'
            )

        if block.type == BlockType.DIVIDER:
            p = pr.replace("{ppr}", "0").replace("{sid}", "0")
            prefix_run = f'<hp:run charPrIDRef="0">{first_prefix}</hp:run>' if first_prefix else ''
            return (
                f'<hp:p {p}>{prefix_run}'
                f'<hp:run charPrIDRef="0"><hp:t>──────────────────────</hp:t></hp:run>'
                f'</hp:p>'
            )

        if block.type == BlockType.TABLE:
            return self._table_to_xml(block, first_prefix)

        if block.type == BlockType.IMAGE:
            alt = self._esc(block.metadata.get("alt", ""))
            p = pr.replace("{ppr}", "0").replace("{sid}", "0")
            prefix_run = f'<hp:run charPrIDRef="0">{first_prefix}</hp:run>' if first_prefix else ''
            return (
                f'<hp:p {p}>{prefix_run}'
                f'<hp:run charPrIDRef="0"><hp:t>[{alt}]</hp:t></hp:run>'
                f'</hp:p>'
            )

        # 일반 문단 — 인라인별 run 분리
        p = pr.replace("{ppr}", "0").replace("{sid}", "0")
        runs = ""
        if first_prefix:
            runs += f'<hp:run charPrIDRef="0">{first_prefix}</hp:run>'

        for child in block.children:
            if not isinstance(child, InlineNode) or not child.text:
                continue
            if child.type == InlineType.BOLD:
                cs = 2
            elif child.type == InlineType.ITALIC:
                cs = 3
            else:
                cs = 0
            runs += f'<hp:run charPrIDRef="{cs}"><hp:t>{self._esc(child.text)}</hp:t></hp:run>'

        if not runs:
            runs = '<hp:run charPrIDRef="0"><hp:t/></hp:run>'

        return f'<hp:p {p}>{runs}</hp:p>'

    def _table_to_xml(self, block: BlockNode, first_prefix: str = "") -> str:
        """TABLE BlockNode → HWPX <hp:tbl> XML.

        구조: hp:p > hp:run > hp:tbl > hp:tr > hp:tc > hp:subList > hp:p > hp:run > hp:t
        요소 순서 (hp:tc 내): subList → cellAddr → cellSpan → cellSz → cellMargin
        요소 순서 (hp:tbl 내): sz → pos → outMargin → inMargin → tr...
        """
        rows = [c for c in block.children if isinstance(c, BlockNode)]
        if not rows:
            return ""
        n_rows = len(rows)
        n_cols = max(
            len([c for c in r.children if isinstance(c, BlockNode)]) for r in rows
        )
        if n_cols == 0:
            return ""

        page_w = 42520  # A4 텍스트 영역 (HWPUNIT)
        col_w = page_w // n_cols
        row_h = 2400

        # 셀 생성
        trs = ""
        for ri, row in enumerate(rows):
            cells = [c for c in row.children if isinstance(c, BlockNode)]
            tcs = ""
            for ci in range(n_cols):
                cell_text = ""
                if ci < len(cells):
                    cell_text = "".join(
                        self._esc(ic.text)
                        for ic in cells[ci].children
                        if isinstance(ic, InlineNode) and ic.text
                    )
                sl_id = self._next_id()
                cp_id = self._next_id()
                tcs += (
                    f'<hp:tc name="" header="0" hasMargin="0" protect="0"'
                    f' editable="0" dirty="0" borderFillIDRef="{self._TABLE_BORDER_FILL_ID}">'
                    f'<hp:subList id="{sl_id}" textDirection="HORIZONTAL"'
                    f' lineWrap="BREAK" vertAlign="CENTER"'
                    f' linkListIDRef="0" linkListNextIDRef="0"'
                    f' textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
                    f'<hp:p id="{cp_id}" paraPrIDRef="0" styleIDRef="0"'
                    f' pageBreak="0" columnBreak="0" merged="0">'
                    f'<hp:run charPrIDRef="0"><hp:t>{cell_text}</hp:t></hp:run>'
                    f'</hp:p>'
                    f'</hp:subList>'
                    f'<hp:cellAddr colAddr="{ci}" rowAddr="{ri}"/>'
                    f'<hp:cellSpan colSpan="1" rowSpan="1"/>'
                    f'<hp:cellSz width="{col_w}" height="{row_h}"/>'
                    f'<hp:cellMargin left="510" right="510" top="141" bottom="141"/>'
                    f'</hp:tc>'
                )
            trs += f'<hp:tr>{tcs}</hp:tr>'

        tbl_id = self._next_id()
        total_h = n_rows * row_h
        tbl = (
            f'<hp:tbl id="{tbl_id}" zOrder="0" numberingType="TABLE"'
            f' textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES"'
            f' lock="0" dropcapstyle="None" pageBreak="CELL"'
            f' repeatHeader="0" rowCnt="{n_rows}" colCnt="{n_cols}"'
            f' cellSpacing="0" borderFillIDRef="{self._TABLE_BORDER_FILL_ID}" noAdjust="0">'
            f'<hp:sz width="{page_w}" widthRelTo="ABSOLUTE"'
            f' height="{total_h}" heightRelTo="ABSOLUTE" protect="0"/>'
            f'<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1"'
            f' allowOverlap="0" holdAnchorAndSO="0"'
            f' vertRelTo="PARA" horzRelTo="COLUMN"'
            f' vertAlign="TOP" horzAlign="LEFT"'
            f' vertOffset="0" horzOffset="0"/>'
            f'<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
            f'<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
            f'{trs}'
            f'</hp:tbl>'
        )

        pid = self._next_id()
        prefix_run = f'<hp:run charPrIDRef="0">{first_prefix}</hp:run>' if first_prefix else ''
        return (
            f'<hp:p id="{pid}" paraPrIDRef="0" styleIDRef="0"'
            f' pageBreak="0" columnBreak="0" merged="0">'
            f'{prefix_run}'
            f'<hp:run charPrIDRef="0">{tbl}</hp:run>'
            f'</hp:p>'
        )

    # ──────────────────────────────────────────────────────────
    # 마크다운 → IR
    # ──────────────────────────────────────────────────────────

    def _markdown_to_ir(self, text: str) -> DocumentIR:
        ir = DocumentIR()
        lines = text.strip().split("\n")
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if not stripped:
                i += 1
                continue

            if stripped.startswith("|") and "|" in stripped[1:]:
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i].strip())
                    i += 1
                block = self._parse_md_table(table_lines)
                if block:
                    ir.blocks.append(block)
                continue

            if stripped.startswith("#"):
                level = len(stripped) - len(stripped.lstrip("#"))
                content = stripped.lstrip("# ").strip()
                block = BlockNode(type=BlockType.HEADING, level=min(level, 6))
                block.children.extend(self._parse_inline(content))
                if level == 1 and not ir.title:
                    ir.title = content
            elif stripped.startswith("---"):
                block = BlockNode(type=BlockType.DIVIDER)
            else:
                block = BlockNode(type=BlockType.PARAGRAPH)
                block.children.extend(self._parse_inline(stripped))
            ir.blocks.append(block)
            i += 1
        return ir

    @staticmethod
    def _parse_inline(text: str) -> list[InlineNode]:
        import re
        nodes: list[InlineNode] = []
        pattern = re.compile(r'(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)')
        last = 0
        for m in pattern.finditer(text):
            if m.start() > last:
                nodes.append(InlineNode(type=InlineType.TEXT, text=text[last:m.start()]))
            if m.group(2):
                nodes.append(InlineNode(type=InlineType.BOLD, text=m.group(2)))
            elif m.group(3):
                nodes.append(InlineNode(type=InlineType.ITALIC, text=m.group(3)))
            elif m.group(4):
                nodes.append(InlineNode(type=InlineType.TEXT, text=m.group(4)))
            last = m.end()
        if last < len(text):
            nodes.append(InlineNode(type=InlineType.TEXT, text=text[last:]))
        if not nodes:
            nodes.append(InlineNode(type=InlineType.TEXT, text=text))
        return nodes  # type: ignore[return-value]

    @staticmethod
    def _parse_md_table(lines: list[str]) -> BlockNode | None:
        if len(lines) < 2:
            return None
        def parse_row(line: str) -> list[str]:
            return [c.strip() for c in line.strip().strip("|").split("|")]
        rows = []
        for line in lines:
            stripped = line.replace("|", "").replace("-", "").replace(":", "").strip()
            if not stripped:
                continue
            rows.append(parse_row(line))
        if not rows:
            return None
        table = BlockNode(type=BlockType.TABLE)
        for row_data in rows:
            row_block = BlockNode(type=BlockType.PARAGRAPH)
            for cell_text in row_data:
                cell_block = BlockNode(
                    type=BlockType.PARAGRAPH,
                    children=[InlineNode(type=InlineType.TEXT, text=cell_text)],
                )
                row_block.children.append(cell_block)  # type: ignore[arg-type]
            table.children.append(row_block)  # type: ignore[arg-type]
        return table

    @staticmethod
    def _esc(text: str) -> str:
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
        )
