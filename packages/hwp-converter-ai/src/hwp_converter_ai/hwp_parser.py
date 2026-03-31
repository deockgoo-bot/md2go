"""HWP 바이너리(.hwp) 파서 — 직접 레코드 파싱.

pyhwp CLI 대신 OLE 스트림을 직접 읽어서 구조 정보(제목/본문/볼드 등)를 보존한다.
역공학 결과는 docs/hwp-format-implementation.md 참조.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

import olefile

from .ir_schema import (
    BlockNode, BlockType, DocumentIR, InlineNode, InlineType, TextStyle,
)

# 태그 ID (HWPTAG_BEGIN = 16)
_T_DOC_PROP   = 0x10
_T_ID_MAP     = 0x11
_T_FACE_NAME  = 0x13
_T_CHAR_SHAPE = 0x15
_T_CTRL_HDR   = 0x47  # CTRL_HEADER (컨트롤 래퍼)
_T_LIST_HDR   = 0x48  # LIST_HEADER (셀 헤더)
_T_TABLE      = 0x4D  # TABLE (표 정의)
_T_PARA_HDR   = 0x42
_T_PARA_TEXT  = 0x43
_T_PARA_CS    = 0x44


def _read_records(data: bytes) -> list[dict]:
    """HWP 레코드 스트림을 파싱하여 리스트로 반환.

    잘못된 레코드를 만나도 가능한 한 계속 파싱한다.
    """
    records = []
    pos = 0
    while pos + 4 <= len(data):
        hdr = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        tag = hdr & 0x3FF
        level = (hdr >> 10) & 0x3FF
        size = hdr >> 20
        if size == 0xFFF:
            if pos + 4 > len(data):
                break
            size = struct.unpack_from('<I', data, pos)[0]
            pos += 4
            # 확장 크기 유효성 검사
            if size > len(data) - pos:
                size = len(data) - pos  # 남은 데이터만큼만 읽기
        elif pos + size > len(data):
            size = len(data) - pos
        records.append({
            'tag': tag, 'level': level, 'size': size,
            'payload': data[pos:pos + size],
        })
        pos += size
    return records


def _extract_text_from_para_text(payload: bytes) -> str:
    """PARA_TEXT 페이로드에서 텍스트 추출 (컨트롤 문자 건너뜀).

    HWP 5.0 컨트롤 문자:
      0x00~0x07: 확장 인라인 컨트롤 (각 8 WCHAR = 16바이트)
      0x08: 제목 표시
      0x09: 탭
      0x0A: 줄 바꿈
      0x0B: 그리기/표 객체 (8 WCHAR = 16바이트)
      0x0C: 예약 (8 WCHAR = 16바이트)
      0x0D: 문단 끝
      0x0E~0x17: 확장 인라인 컨트롤 (각 8 WCHAR = 16바이트)
      0x18~0x1F: 하이픈, 비분리 공백 등 (각 1 WCHAR)
    """
    # 8 WCHAR 차지하는 확장 컨트롤 코드
    _EXTENDED = set(range(0, 8)) | {0x0B, 0x0C} | set(range(0x0E, 0x18))

    chars = []
    i = 0
    while i < len(payload) - 1:
        ch = struct.unpack_from('<H', payload, i)[0]
        if ch in _EXTENDED:
            i += 16  # 8 WCHAR 건너뜀
            continue
        elif ch == 0x09:
            chars.append('\t')
        elif ch == 0x0A:
            chars.append('\n')
        elif ch == 0x0D:
            pass  # 문단 끝 — 무시
        elif ch < 32:
            pass  # 기타 컨트롤 — 무시
        elif 0xD800 <= ch <= 0xDFFF:
            pass  # 서로게이트 문자 — 건너뜀 (JSON 직렬화 에러 방지)
        else:
            chars.append(chr(ch))
        i += 2
    return ''.join(chars)


def _parse_char_shapes(records: list[dict]) -> list[dict]:
    """DocInfo에서 CHAR_SHAPE 레코드를 파싱하여 스타일 정보 추출."""
    shapes = []
    for rec in records:
        if rec['tag'] != _T_CHAR_SHAPE:
            continue
        p = rec['payload']
        if len(p) < 68:
            shapes.append({'bold': False, 'size_pt': 10.0})
            continue
        # basesize at offset 42 (7×2 + 7 + 7 + 7 + 7 = 42)
        basesize = struct.unpack_from('<i', p, 42)[0]
        # charshapeflags at offset 46
        flags = struct.unpack_from('<I', p, 46)[0]
        bold = bool(flags & (1 << 6))
        italic = bool(flags & (1 << 7))
        size_pt = basesize / 100.0
        shapes.append({'bold': bold, 'italic': italic, 'size_pt': size_pt})
    return shapes


def _parse_face_names(records: list[dict]) -> list[str]:
    """DocInfo에서 FACE_NAME 레코드를 파싱하여 글꼴 이름 목록 추출."""
    names = []
    for rec in records:
        if rec['tag'] != _T_FACE_NAME:
            continue
        p = rec['payload']
        if len(p) < 3:
            names.append('')
            continue
        name_len = struct.unpack_from('<H', p, 1)[0]
        if len(p) >= 3 + name_len * 2:
            name = p[3:3 + name_len * 2].decode('utf-16-le', errors='replace')
        else:
            name = ''
        names.append(name)
    return names


def _extract_bindata_images(ole, decompress_fn) -> dict[str, bytes]:
    """OLE 파일의 BinData 스토리지에서 이미지 데이터를 추출.

    HWP 5.0은 이미지를 BinData/BINxxxx.{jpg,png,bmp,gif} 스트림에 저장한다.
    압축된 경우 decompress_fn으로 해제.
    """
    _IMG_SIGS = {
        b'\xff\xd8\xff': '.jpg',
        b'\x89PNG': '.png',
        b'GIF8': '.gif',
        b'BM': '.bmp',
        b'RIFF': '.webp',
    }
    images: dict[str, bytes] = {}
    try:
        for entry in ole.listdir():
            if len(entry) >= 2 and entry[0] == 'BinData':
                stream_path = '/'.join(entry)
                raw = ole.openstream(stream_path).read()
                data = decompress_fn(raw)
                # 파일명 결정: 스트림 이름에 확장자가 있으면 사용
                bin_name = entry[-1]
                if '.' not in bin_name:
                    # 시그니처로 확장자 추론
                    ext = '.bin'
                    for sig, detected_ext in _IMG_SIGS.items():
                        if data[:len(sig)] == sig:
                            ext = detected_ext
                            break
                    bin_name = bin_name + ext
                images[bin_name] = data
    except Exception:
        pass  # BinData 스토리지가 없거나 접근 불가
    return images


import re

_LIST_PATTERNS = [
    re.compile(r'^(\d+)\.\s+(.+)'),          # "1. 텍스트"
    re.compile(r'^(\d+)\)\s+(.+)'),           # "1) 텍스트"
    re.compile(r'^([가-힣])\.\s+(.+)'),       # "가. 텍스트"
    re.compile(r'^([가-힣])\)\s+(.+)'),       # "가) 텍스트"
    re.compile(r'^[-·•]\s+(.+)'),             # "- 텍스트", "· 텍스트"
    re.compile(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*(.+)'),  # "① 텍스트"
]


def _detect_list(text: str) -> str | None:
    """텍스트가 리스트 항목 패턴이면 Markdown 리스트 형식으로 반환."""
    for pat in _LIST_PATTERNS:
        m = pat.match(text)
        if m:
            groups = m.groups()
            if len(groups) == 2:
                return f"- {groups[1]}"  # "1. xxx" → "- xxx"
            elif len(groups) == 1:
                return f"- {groups[0]}"  # "- xxx" → "- xxx"
    return None


def parse_hwp(file_path: Path) -> DocumentIR:
    """HWP 바이너리 파일을 직접 파싱하여 DocumentIR로 반환.

    OLE 스트림에서 DocInfo(폰트/스타일)와 Section0(본문)을 읽고,
    제목/본문/볼드 등 구조 정보를 보존한다.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"파일이 존재하지 않습니다: {file_path}")

    ole = olefile.OleFileIO(str(file_path))

    try:
        # FileHeader 읽기
        fh = ole.openstream('FileHeader').read()
        flags = struct.unpack_from('<I', fh, 36)[0]
        is_compressed = bool(flags & 1)

        def _decompress(raw: bytes) -> bytes:
            if not is_compressed:
                return raw
            try:
                return zlib.decompress(raw, -15)
            except zlib.error:
                try:
                    return zlib.decompress(raw)
                except zlib.error:
                    return raw

        # DocInfo 읽기
        di_data = _decompress(ole.openstream('DocInfo').read())
        di_records = _read_records(di_data)
        char_shapes = _parse_char_shapes(di_records)
        face_names = _parse_face_names(di_records)

        # 모든 Section 읽기 (Section0, Section1, ...)
        import logging
        logger = logging.getLogger(__name__)

        all_section_records = []
        for i in range(100):
            stream_name = f'BodyText/Section{i}'
            if not ole.exists(stream_name):
                break
            raw = ole.openstream(stream_name).read()
            sec_data = _decompress(raw)
            recs = _read_records(sec_data)
            all_section_records.extend(recs)
            logger.warning(
                f"[HWP파서] {stream_name}: compressed={len(raw)}B "
                f"decompressed={len(sec_data)}B records={len(recs)}"
            )

        # PARA_TEXT 레코드 수 카운트
        text_count = sum(1 for r in all_section_records if r['tag'] == _T_PARA_TEXT)
        logger.warning(f"[HWP파서] 총 레코드={len(all_section_records)}, PARA_TEXT={text_count}")

        # BinData 이미지 추출
        images = _extract_bindata_images(ole, _decompress)
        if images:
            logger.warning(f"[HWP파서] BinData 이미지 {len(images)}개 추출")
    finally:
        ole.close()

    # 전체 섹션 레코드를 문단/표 단위로 그룹화
    ir = DocumentIR(title=file_path.stem)
    _build_blocks(ir, all_section_records, char_shapes)

    # 템플릿 잔여 텍스트 제거 ("한글 2005 예제 파일입니다.")
    ir.blocks = [
        b for b in ir.blocks
        if not (b.type == BlockType.PARAGRAPH
                and len(b.children) == 1
                and isinstance(b.children[0], InlineNode)
                and '한글 2005 예제 파일' in b.children[0].text)
    ]

    # 이미지를 IR에 추가
    if images:
        ir.metadata['images'] = images
        for name in images:
            ir.blocks.append(BlockNode(
                type=BlockType.IMAGE,
                metadata={'src': name, 'alt': name.rsplit('.', 1)[0] if '.' in name else name},
            ))

    return ir


def _find_para_char_shape(records: list[dict], text_idx: int) -> list[tuple[int, int]]:
    """PARA_TEXT 다음에 오는 PARA_CHAR_SHAPE를 찾아 엔트리 반환.

    HWP 5.0 레코드 순서: PARA_HEADER → PARA_TEXT → PARA_CHAR_SHAPE → PARA_LINE_SEG
    """
    for j in range(text_idx + 1, min(text_idx + 5, len(records))):
        if records[j]['tag'] == _T_PARA_CS:
            p = records[j]['payload']
            entries: list[tuple[int, int]] = []
            for off in range(0, len(p) - 7, 8):
                pos = struct.unpack_from('<I', p, off)[0]
                cs_id = struct.unpack_from('<I', p, off + 4)[0]
                entries.append((pos, cs_id))
            return entries if entries else [(0, 0)]
        if records[j]['tag'] == _T_PARA_HDR:
            break  # 다음 문단 시작 → 중단
    return [(0, 0)]


def _build_blocks(ir: DocumentIR, records: list[dict],
                  char_shapes: list[dict]) -> None:
    """레코드 목록에서 블록(문단/표)을 추출하여 IR에 추가."""
    i = 0
    current_para_header = None

    while i < len(records):
        rec = records[i]

        if rec['tag'] == _T_PARA_HDR:
            current_para_header = rec['payload']

        elif rec['tag'] == _T_TABLE:
            # ── 표 파싱 ──
            table_block, skip = _parse_table_records(records, i)
            if table_block:
                ir.blocks.append(table_block)
            i += skip
            continue

        elif rec['tag'] == _T_PARA_TEXT and rec['level'] >= 1:
            text = _extract_text_from_para_text(rec['payload'])
            if not text.strip():
                i += 1
                continue

            style_id = 0
            if current_para_header and len(current_para_header) >= 11:
                style_id = current_para_header[10]

            stripped = text.strip()

            # 리스트 감지 (번호/글머리 기호 패턴)
            list_text = _detect_list(stripped)
            if list_text is not None:
                ir.blocks.append(BlockNode(
                    type=BlockType.PARAGRAPH,
                    children=[InlineNode(type=InlineType.TEXT, text=list_text)],
                ))
                i += 1
                continue

            # PARA_TEXT 뒤의 PARA_CHAR_SHAPE에서 엔트리 찾기 (look-ahead)
            cs_entries = _find_para_char_shape(records, i)

            # 다중 charshape 엔트리에서 인라인 노드 생성
            inline_nodes = _split_text_by_char_shapes(
                text, cs_entries, char_shapes
            )

            # 제목 판단: 단일 charshape + 볼드 + 큰 폰트
            block_type = BlockType.PARAGRAPH
            heading_level = None
            if len(cs_entries) == 1:
                cs_id = cs_entries[0][1]
                is_bold, font_size = False, 10.0
                if cs_id < len(char_shapes):
                    is_bold = char_shapes[cs_id].get('bold', False)
                    font_size = char_shapes[cs_id].get('size_pt', 10.0)
                if len(stripped) <= 60 and is_bold and font_size >= 12.0:
                    if font_size >= 18.0:
                        block_type, heading_level = BlockType.HEADING, 1
                    elif font_size >= 14.0:
                        block_type, heading_level = BlockType.HEADING, 2
                    elif font_size >= 12.0:
                        block_type, heading_level = BlockType.HEADING, 3
                    # 제목이면 인라인 타입을 TEXT로 통일
                    for node in inline_nodes:
                        node.type = InlineType.TEXT

            ir.blocks.append(BlockNode(
                type=block_type,
                level=heading_level,
                children=inline_nodes,  # type: ignore[arg-type]
            ))

        i += 1


def _split_text_by_char_shapes(
    text: str,
    entries: list[tuple[int, int]],
    char_shapes: list[dict],
) -> list[InlineNode]:
    """PARA_CHAR_SHAPE 엔트리 기준으로 텍스트를 분할하여 InlineNode 리스트 반환."""
    nodes: list[InlineNode] = []
    for idx, (pos, cs_id) in enumerate(entries):
        next_pos = entries[idx + 1][0] if idx + 1 < len(entries) else len(text)
        segment = text[pos:next_pos]
        if not segment:
            continue

        is_bold, is_italic, font_size = False, False, 10.0
        if cs_id < len(char_shapes):
            cs = char_shapes[cs_id]
            is_bold = cs.get('bold', False)
            is_italic = cs.get('italic', False)
            font_size = cs.get('size_pt', 10.0)

        if is_bold:
            inline_type = InlineType.BOLD
        elif is_italic:
            inline_type = InlineType.ITALIC
        else:
            inline_type = InlineType.TEXT

        nodes.append(InlineNode(
            type=inline_type, text=segment,
            style=TextStyle(bold=is_bold, italic=is_italic, font_size=font_size),
        ))

    if not nodes:
        nodes.append(InlineNode(type=InlineType.TEXT, text=text))
    return nodes


def _parse_table_records(records: list[dict], start_idx: int) -> tuple[BlockNode | None, int]:
    """TABLE(0x4D) 레코드부터 표를 파싱.

    TABLE 레코드에서 행/열 수를 읽고,
    이어지는 LIST_HEADER(0x48) 레코드에서 셀 위치(col, row)와 텍스트를 추출하여
    Markdown 표로 변환 가능한 BlockNode를 반환.

    Returns:
        (table_block, skip_count): 표 블록과 건너뛸 레코드 수
    """
    rec = records[start_idx]
    if rec['tag'] != _T_TABLE or len(rec['payload']) < 8:
        return None, 1

    # TABLE 레코드에서 행/열 수 읽기
    # pyhwp TableBody: flags(4) + rows(2) + cols(2) + ...
    p = rec['payload']
    rows = struct.unpack_from('<H', p, 4)[0]
    cols = struct.unpack_from('<H', p, 6)[0]

    if rows == 0 or cols == 0 or rows > 500 or cols > 50:
        return None, 1

    # 셀 데이터 수집: LIST_HEADER(0x48) → TableCell 정보 + 셀 텍스트
    table_level = rec['level']
    cells = {}  # (row, col) → text
    current_cell_row = 0
    current_cell_col = 0
    cell_texts = []
    skip = 1

    i = start_idx + 1
    while i < len(records):
        r = records[i]

        # 표 범위 벗어남: 같은 레벨 이하의 PARA_HEADER = 표 밖 문단
        if r['tag'] == _T_PARA_HDR and r['level'] <= table_level - 1:
            break

        if r['tag'] == _T_LIST_HDR and r['level'] == table_level:
            # 이전 셀 텍스트 저장
            if cell_texts:
                cells[(current_cell_row, current_cell_col)] = ' '.join(cell_texts)
                cell_texts = []

            # LIST_HEADER에서 TableCell 정보 읽기
            # ListHeader(6B) + TableCell: col(2) + row(2) + colspan(2) + rowspan(2)
            lp = r['payload']
            if len(lp) >= 12:
                # ListHeader: paragraphs(2) + unknown1(2) + listflags(4) = 8B
                # TableCell starts at offset 8: col(2) + row(2)
                current_cell_col = struct.unpack_from('<H', lp, 8)[0]
                current_cell_row = struct.unpack_from('<H', lp, 10)[0]

        elif r['tag'] == _T_PARA_TEXT and r['level'] > table_level:
            # 셀 내부 텍스트
            text = _extract_text_from_para_text(r['payload'])
            if text.strip():
                cell_texts.append(text.strip())

        i += 1
        skip += 1

    # 마지막 셀 저장
    if cell_texts:
        cells[(current_cell_row, current_cell_col)] = ' '.join(cell_texts)

    if not cells:
        return None, skip

    # BlockNode 표 구조 생성
    table_block = BlockNode(type=BlockType.TABLE)
    for r in range(rows):
        row_block = BlockNode(type=BlockType.PARAGRAPH)
        for c in range(cols):
            cell_text = cells.get((r, c), '')
            cell_block = BlockNode(
                type=BlockType.PARAGRAPH,
                children=[InlineNode(type=InlineType.TEXT, text=cell_text)],
            )
            row_block.children.append(cell_block)  # type: ignore[arg-type]
        table_block.children.append(row_block)  # type: ignore[arg-type]

    return table_block, skip
