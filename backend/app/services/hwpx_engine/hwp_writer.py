"""
HWP 5.0 바이너리 파일 직접 생성기.

OLE Compound File Binary (CFB) + HWP 5.0 레코드 포맷을 직접 구현.
모든 레코드 구조는 pyhwp(hwp5.binmodel) 기준으로 검증됨.

지원 블록: HEADING (H1~H3), PARAGRAPH, DIVIDER
"""
from __future__ import annotations

import struct
import zlib
from io import BytesIO
from pathlib import Path

from .ir_schema import DocumentIR, BlockNode, BlockType, InlineNode, InlineType


# ══════════════════════════════════════════════════════════════
#  OLE Compound File Binary — HWP 전용 고정 구조 빌더
# ══════════════════════════════════════════════════════════════

_OLE_MAGIC  = b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'
_SECT_SZ    = 512
_FREESECT   = 0xFFFFFFFF
_ENDOFCHAIN = 0xFFFFFFFE
_FATSECT    = 0xFFFFFFFD
_NOSTREAM   = 0xFFFFFFFF


def _dir_entry(name: str, obj_type: int, color: int = 1,
               left: int = _NOSTREAM, right: int = _NOSTREAM,
               child: int = _NOSTREAM,
               start: int = _ENDOFCHAIN, size: int = 0) -> bytes:
    """128바이트 OLE CFB 디렉터리 항목."""
    name_u = name.encode('utf-16-le') if name else b''
    name_len = len(name_u) + 2 if name else 0
    name_field = (name_u + b'\x00\x00').ljust(64, b'\x00')[:64]
    return (
        name_field
        + struct.pack('<H', name_len)
        + struct.pack('<BB', obj_type, color)
        + struct.pack('<III', left, right, child)
        + b'\x00' * 16          # CLSID
        + struct.pack('<I', 0)   # state bits
        + struct.pack('<QQ', 0, 0)   # created / modified
        + struct.pack('<II', start, size)
        + b'\x00' * 4           # reserved
    )


def _hwp_summary_info() -> bytes:
    """한컴 전용 \x05HwpSummaryInformation OLE Property Set.

    실제 HWP 파일(sample-5017.hwp) 분석 기반.
    FMTID: {9FA2B660-1061-11D4-B4C6-006097C09D8C} (한컴 전용, MS 표준 아님!)
    """
    # 한컴 전용 FMTID (실제 HWP 파일에서 추출)
    fmtid = bytes([0x60, 0xB6, 0xA2, 0x9F, 0x61, 0x10, 0xD4, 0x11,
                   0xB4, 0xC6, 0x00, 0x60, 0x97, 0xC0, 0x9D, 0x8C])

    # Properties: CodePage(1)=1200, Title(2)=""
    # PID 1: CodePage = 1200 (UTF-16LE) — VT_I2
    prop1 = struct.pack('<IhH', 0x0002, 1200, 0)  # VT_I2 + value + pad

    # PID 2: Title = "" (empty) — VT_LPWSTR
    prop2 = struct.pack('<II', 0x001F, 1) + b'\x00\x00\x00\x00'  # VT_LPWSTR, nchars=1, null terminator + pad

    # Section
    num_props = 2
    props_start = 8 + num_props * 8  # section header(8) + PID/offset pairs
    prop1_offset = props_start
    prop2_offset = prop1_offset + len(prop1)

    section = (
        struct.pack('<II', 0, num_props)
        + struct.pack('<II', 1, prop1_offset)  # CodePage
        + struct.pack('<II', 2, prop2_offset)  # Title
        + prop1
        + prop2
    )
    section_size = len(section)
    section = struct.pack('<I', section_size) + section[4:]

    section_offset = 28 + 20
    header = (
        struct.pack('<HH', 0xFFFE, 0x0000)
        + struct.pack('<I', 0x00020105)  # OS (Windows, same as real sample)
        + b'\x00' * 16
        + struct.pack('<I', 1)
        + fmtid
        + struct.pack('<I', section_offset)
    )
    return header + section


def _prv_text(blocks: list) -> bytes:
    """PrvText 스트림: 문서 미리보기 텍스트 (UTF-16LE)."""
    texts = []
    for block in blocks:
        text = ''.join(
            c.text for c in block.children
            if hasattr(c, 'text') and c.text
        )
        if text:
            texts.append(text)
    return '\r\n'.join(texts).encode('utf-16-le')


def _build_ole(file_header: bytes, doc_info: bytes, section0: bytes,
               prv_text: bytes = b'') -> bytes:
    """
    HWP 전용 OLE CFB 파일 생성 (mini FAT 지원).

    실제 HWP 파일 구조 참고:
    - \x05HwpSummaryInformation (한컴 전용 FMTID)
    - PrvText (미리보기 텍스트)
    섹터: 0=FAT, 1=miniFAT, 2-3=Dir, 4+=mini stream container
    """
    _MINI_SZ = 64
    summary_info = _hwp_summary_info()
    if not prv_text:
        prv_text = b'\x00\x00'  # 최소 UTF-16LE null

    def _pad(data: bytes, unit: int) -> bytes:
        rem = len(data) % unit
        return data + b'\x00' * (unit - rem) if rem else data

    # 스트림 목록: FileHeader, DocInfo, Section0, SummaryInfo, PrvText
    streams = [
        ('fh', file_header),
        ('di', doc_info),
        ('s0', section0),
        ('si', summary_info),
        ('pt', prv_text),
    ]
    padded = [(name, _pad(data, _MINI_SZ), data) for name, data in streams]

    # mini sector 할당
    ms_start = {}
    cur = 0
    for name, padded_data, _ in padded:
        ms_start[name] = cur
        cur += len(padded_data) // _MINI_SZ

    mini_raw = b''.join(p for _, p, _ in padded)
    mini_cont = _pad(mini_raw, _SECT_SZ)
    n_ms_sect = len(mini_cont) // _SECT_SZ

    # mini FAT chain
    mfat = [_FREESECT] * 128
    for name, padded_data, _ in padded:
        ms = ms_start[name]
        n = len(padded_data) // _MINI_SZ
        for i in range(n - 1):
            mfat[ms + i] = ms + i + 1
        mfat[ms + n - 1] = _ENDOFCHAIN
    mfat_bytes = struct.pack('<128I', *mfat)

    FAT_SECT = 0
    MINIFAT  = 1
    DIR1     = 2
    DIR2     = 3
    MS_START_SECT = 4

    fat = [_FREESECT] * 128
    fat[FAT_SECT] = _FATSECT
    fat[MINIFAT]  = _ENDOFCHAIN
    fat[DIR1]     = DIR2
    fat[DIR2]     = _ENDOFCHAIN
    for i in range(n_ms_sect - 1):
        fat[MS_START_SECT + i] = MS_START_SECT + i + 1
    fat[MS_START_SECT + n_ms_sect - 1] = _ENDOFCHAIN
    fat_bytes = struct.pack('<128I', *fat[:128])

    # OLE BST 정렬 (이름 바이트 길이 오름차순):
    #   DocInfo(7) < PrvText(7) < BodyText(8) < FileHeader(10) < \x05Hwp...(25)
    # DocInfo과 PrvText 동일 길이 → 사전순: DocInfo < PrvText
    # 인덱스: 0=Root 1=FileHeader 2=DocInfo 3=BodyText 4=Section0
    #         5=SummaryInfo 6=PrvText
    # BST: Root.child=3(BodyText)
    #      BodyText.left=2(DocInfo)  BodyText.right=1(FileHeader)
    #      DocInfo.right=6(PrvText)
    #      FileHeader.right=5(SummaryInfo)
    #      BodyText.child=4(Section0)
    entries = b''.join([
        _dir_entry('Root Entry', 5, color=1, child=3,
                   start=MS_START_SECT, size=len(mini_raw)),
        _dir_entry('FileHeader', 2, color=1, right=5,
                   start=ms_start['fh'], size=len(file_header)),
        _dir_entry('DocInfo',    2, color=1, right=6,
                   start=ms_start['di'], size=len(doc_info)),
        _dir_entry('BodyText',   1, color=1, left=2, right=1, child=4),
        _dir_entry('Section0',   2, color=1,
                   start=ms_start['s0'], size=len(section0)),
        _dir_entry('\x05HwpSummaryInformation', 2, color=0,
                   start=ms_start['si'], size=len(summary_info)),
        _dir_entry('PrvText',    2, color=0,
                   start=ms_start['pt'], size=len(prv_text)),
        _dir_entry('', 0),
    ])
    dir1 = entries[:_SECT_SZ]
    dir2 = entries[_SECT_SZ:2 * _SECT_SZ]

    difat = struct.pack('<I', FAT_SECT) + struct.pack('<I', _FREESECT) * 108
    header = (
        _OLE_MAGIC
        + b'\x00' * 16
        + struct.pack('<HH', 0x003E, 0x0003)
        + struct.pack('<HH', 0xFFFE, 9)
        + struct.pack('<H', 6)
        + b'\x00' * 6
        + struct.pack('<I', 0)
        + struct.pack('<I', 1)
        + struct.pack('<I', DIR1)
        + struct.pack('<I', 0)
        + struct.pack('<I', 0x1000)
        + struct.pack('<I', MINIFAT)
        + struct.pack('<I', 1)
        + struct.pack('<I', _ENDOFCHAIN)
        + struct.pack('<I', 0)
        + difat
    ).ljust(_SECT_SZ, b'\x00')[:_SECT_SZ]

    out = BytesIO()
    out.write(header)
    out.write(fat_bytes)
    out.write(mfat_bytes)
    out.write(dir1)
    out.write(dir2)
    out.write(mini_cont)
    return out.getvalue()


# ══════════════════════════════════════════════════════════════
#  HWP 5.0 레코드 인코더
#  스펙: tag(10bit) | level(10bit) | size(12bit), little-endian uint32
# ══════════════════════════════════════════════════════════════

# 태그 ID — pyhwp(hwp5.tagids) 기준 HWPTAG_BEGIN=16
_TAG_DOCUMENT_PROPERTIES = 0x10   # 16
_TAG_ID_MAPPINGS         = 0x11   # 17
_TAG_FACE_NAME           = 0x13   # 19
_TAG_CHAR_SHAPE          = 0x15   # 21
_TAG_PARA_SHAPE          = 0x19   # 25
_TAG_STYLE               = 0x1A   # 26
_TAG_PAGE_DEF            = 0x49   # 73
_TAG_PARA_HEADER         = 0x42   # 66
_TAG_PARA_TEXT           = 0x43   # 67
_TAG_PARA_CHAR_SHAPE     = 0x44   # 68
_TAG_PARA_LINE_SEG       = 0x45   # 69


def _rec(tag: int, data: bytes, level: int = 0) -> bytes:
    sz = len(data)
    if sz < 0xFFF:
        hdr = struct.pack('<I', (tag & 0x3FF) | ((level & 0x3FF) << 10) | (sz << 20))
        return hdr + data
    hdr = struct.pack('<I', (tag & 0x3FF) | ((level & 0x3FF) << 10) | (0xFFF << 20))
    return hdr + struct.pack('<I', sz) + data


def _compress(raw: bytes) -> bytes:
    """HWP 스트림 압축: raw deflate (wbits=-15).

    실제 HWP 5.0 파일(pyhwp sample-5017.hwp) 분석 결과 raw deflate 사용 확인.
    """
    co = zlib.compressobj(6, zlib.DEFLATED, -15)
    return co.compress(raw) + co.flush()


# ── FileHeader ────────────────────────────────────────────────

def _file_header() -> bytes:
    sig  = b'HWP Document File\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    ver  = struct.pack('<I', 0x05000107)  # 5.0.1.7 (실제 HWP 샘플과 동일)
    flags = struct.pack('<I', 0x00000001)  # bit0=compressed
    return (sig + ver + flags).ljust(256, b'\x00')[:256]


# ── DocInfo ───────────────────────────────────────────────────

def _doc_info() -> bytes:
    """pyhwp IdMappings 모델 기준 DocInfo 레코드 집합.

    핵심: ID_MAPPINGS는 16×UINT32이며, 폰트는 언어별(ko/en/cn/jp/other/symbol/user)
    각각 별도 카운트 → FACE_NAME 레코드 총 수 = sum(7개 폰트 카운트).
    """
    out = BytesIO()

    # ── DOCUMENT_PROPERTIES (26 bytes) ──
    dp = struct.pack('<HHHHHHH', 1, 1, 1, 1, 1, 1, 1)
    dp += struct.pack('<III', 0, 0, 0)
    out.write(_rec(_TAG_DOCUMENT_PROPERTIES, dp))

    # ── ID_MAPPINGS (64 bytes = 16×UINT32) ──
    # pyhwp IdMappings: bindata, ko_fonts, en_fonts, cn_fonts, jp_fonts,
    #   other_fonts, symbol_fonts, user_fonts, borderfills, charshapes,
    #   tabdefs, numberings, bullets, parashapes, styles, memoshapes
    im = struct.pack('<16I',
        0,    # bindata
        1,    # ko_fonts    → FACE_NAME ×1 for Korean
        1,    # en_fonts    → FACE_NAME ×1 for English
        1,    # cn_fonts    → FACE_NAME ×1 for Chinese
        1,    # jp_fonts    → FACE_NAME ×1 for Japanese
        1,    # other_fonts → FACE_NAME ×1 for Other
        1,    # symbol_fonts→ FACE_NAME ×1 for Symbol
        1,    # user_fonts  → FACE_NAME ×1 for User
        0,    # borderfills
        4,    # charshapes  (0=body, 1=heading bold, 2=body bold, 3=body italic)
        0,    # tabdefs
        0,    # numberings
        0,    # bullets
        1,    # parashapes
        4,    # styles
        0,    # memoshapes
    )
    out.write(_rec(_TAG_ID_MAPPINGS, im))

    # ── FACE_NAME × 7 (한 개씩 × 7개 언어 유형) ──
    # 순서: ko, en, cn, jp, other, symbol, user
    face = '바탕'
    face_u = face.encode('utf-16-le')
    fn_data = b'\x00' + struct.pack('<H', len(face)) + face_u
    for _ in range(7):
        out.write(_rec(_TAG_FACE_NAME, fn_data))

    # ── CHAR_SHAPE (68 bytes) × 2 ──
    # pyhwp CharShape: font_face[7]×UINT16 + letter_width[7]×UINT8
    #   + letter_spacing[7]×INT8 + relative_size[7]×UINT8 + position[7]×INT8
    #   + basesize(INT32) + charshapeflags(UINT32) + shadow_space(2×INT8)
    #   + text_color + underline_color + shade_color + shadow_color (4×UINT32)
    def char_shape(pt_100: int, bold: bool = False, italic: bool = False) -> bytes:
        attr = 0
        if bold:
            attr |= (1 << 6)
        if italic:
            attr |= (1 << 7)
        return (
            struct.pack('<7H', 0, 0, 0, 0, 0, 0, 0)          # font_face[7] (index into per-lang set)
            + struct.pack('<7B', 100, 100, 100, 100, 100, 100, 100)
            + struct.pack('<7b', 0, 0, 0, 0, 0, 0, 0)
            + struct.pack('<7B', 100, 100, 100, 100, 100, 100, 100)
            + struct.pack('<7b', 0, 0, 0, 0, 0, 0, 0)
            + struct.pack('<i', pt_100)
            + struct.pack('<I', attr)
            + struct.pack('<bb', 0, 0)
            + struct.pack('<IIII', 0x00000000, 0x00000000, 0xFFFFFFFF, 0x00B2B2B2)
        )

    out.write(_rec(_TAG_CHAR_SHAPE, char_shape(1000)))                         # 0: 본문 10pt
    out.write(_rec(_TAG_CHAR_SHAPE, char_shape(1400, bold=True)))              # 1: 제목 14pt 볼드
    out.write(_rec(_TAG_CHAR_SHAPE, char_shape(1000, bold=True)))              # 2: 본문 10pt 볼드
    out.write(_rec(_TAG_CHAR_SHAPE, char_shape(1000, italic=True)))            # 3: 본문 10pt 이탤릭

    # ── PARA_SHAPE (42 bytes) × 1 ──
    ps = struct.pack('<iiiiiii', 0, 0, 0, 0, 0, 0, 160)
    ps += struct.pack('<HHH', 0, 0, 0)
    ps += struct.pack('<HHHH', 0, 0, 0, 0)
    out.write(_rec(_TAG_PARA_SHAPE, ps))

    # ── STYLE × 4 ──
    # pyhwp Style: local_name(BSTR) + english_name(BSTR) + flags(BYTE)
    #   + next_style_id(BYTE) + lang_id(INT16) + parashape_id(UINT16)
    #   + charshape_id(UINT16) + unknown(UINT16)
    styles = [
        ('바탕글',  '',           0, 0, 0, 0),
        ('제목 1', 'Heading 1',  0, 0, 0, 1),
        ('제목 2', 'Heading 2',  0, 0, 0, 1),
        ('제목 3', 'Heading 3',  0, 0, 0, 1),
    ]
    for local_name, eng_name, flags, next_s, psi, csi in styles:
        local_u = local_name.encode('utf-16-le')
        eng_u = eng_name.encode('utf-16-le')
        sd = (
            struct.pack('<H', len(local_name)) + local_u
            + struct.pack('<H', len(eng_name)) + eng_u
            + struct.pack('<B', flags)
            + struct.pack('<B', next_s)
            + struct.pack('<h', 0)
            + struct.pack('<H', psi)
            + struct.pack('<H', csi)
            + struct.pack('<H', 0)
        )
        out.write(_rec(_TAG_STYLE, sd))

    return out.getvalue()


# ── BodyText/Section0 ─────────────────────────────────────────

# 섹션 정의 프리픽스: 실제 HWP 5.0 파일(sample-5017.hwp)에서 추출.
# 첫 번째 문단에 0x02 섹션 컨트롤 + PAGE_DEF(A4) + FOOTNOTE_SHAPE + PAGE_BORDER_FILL 포함.
# 이 프리픽스 없이는 한컴 뷰어가 "파일 손상" 에러를 발생시킴.
import base64 as _b64
# 섹션 정의 프리픽스: 첫 문단(0x02 섹션컨트롤 + PAGE_DEF + FOOTNOTE + PAGE_BORDER)
# 원본 템플릿과 동일 바이트 구조, 텍스트만 공백으로 교체 (404 bytes, 12 records)
_SECTION_PREFIX = _b64.b64decode('QgBgASIAAAAEAAAAAAAAAwUAAAABAAAAAABDBEAEAgBkY2VzAAAAAAAAAAACAAIAZGxvYwAAAAAAAAAAAgAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAAIAAgACAADQBEBIACAAAAAAcAAAATAAAACAAAABcAAAAHAAAAGAAAAAkAAAAaAAAABwAAAEUEQAIAAAAAAAAAANAHAADQBwAApAYAALAEAAAAAAAAGKYAAAAABgBHBEACZGNlcwAAAABuBAAAAABAHwAAAQAAAAAAAAAAAAAAAAAAAAAASQiAAojoAADcSAEAOCEAADghAAAkFgAAnBAAAJwQAACcEAAAAAAAAAAAAABKCMABAAAAAAAAAAApAAEA/////1IDNwIbAQEBAAAAAEoIwAEAAAAAAAAAACkAAQD4L+AAUgM3AgAAAQEAAAAASwjgAAEAAACJBYkFiQWJBQAASwjgAAEAAACJBYkFiQWJBQAASwjgAAEAAACJBYkFiQWJBQAARwQAAWRsb2MEEAAAAAAAAAAAAAA=')


def _build_para_char_shape(block: BlockNode,
                           cs_normal: int = 0,
                           cs_bold: int = 2,
                           cs_italic: int = 3) -> bytes:
    """인라인 노드 타입별 PARA_CHAR_SHAPE 데이터 생성.

    각 엔트리: (char_position: UINT32, charshape_id: UINT32)
    """
    entries: list[tuple[int, int]] = []
    char_pos = 0
    for child in block.children:
        if not isinstance(child, InlineNode) or not child.text:
            continue
        child_text = child.text.replace('\t', '    ')
        if child.type == InlineType.BOLD:
            cs_id = cs_bold
        elif child.type == InlineType.ITALIC:
            cs_id = cs_italic
        else:
            cs_id = cs_normal
        entries.append((char_pos, cs_id))
        char_pos += len(child_text)
    if not entries:
        return struct.pack('<II', 0, cs_normal)
    # 연속 동일 charshape 병합
    merged = [entries[0]]
    for pos, cs_id in entries[1:]:
        if cs_id != merged[-1][1]:
            merged.append((pos, cs_id))
    return b''.join(struct.pack('<II', pos, cs_id) for pos, cs_id in merged)


def _section(blocks: list[BlockNode],
             cs_normal: int = 0, cs_heading: int = 1,
             cs_bold: int = 2, cs_italic: int = 3) -> bytes:
    """HWP 5.0 Section0 스트림 생성.

    구조:
    1. 섹션 정의 프리픽스 (첫 문단: 0x02 컨트롤 + PAGE_DEF + FOOTNOTE_SHAPE 등)
    2. 텍스트 문단들 (각각 PARA_TEXT + 0x0D 끝마커)
    3. 마지막 문단의 nchars에 0x80000000 플래그 (섹션 끝 표시)
    """
    out = BytesIO()

    # 섹션 정의 프리픽스 (PAGE_DEF, 각주, 테두리 등 포함)
    out.write(_SECTION_PREFIX)

    # 블록 필터링 (TABLE은 텍스트 없어도 포함)
    text_blocks = []
    for block in blocks:
        if block.type == BlockType.TABLE:
            text_blocks.append((block, ''))
            continue
        text = ''.join(
            c.text for c in block.children
            if hasattr(c, 'text') and c.text
        )
        if block.type == BlockType.DIVIDER:
            text = '\u2500' * 20
        if text:
            text_blocks.append((block, text))

    for i, (block, text) in enumerate(text_blocks):
        # 텍스트 전처리: HWP 인라인 컨트롤 문자를 일반 문자로 변환
        # TAB(0x09)은 HWP에서 8 WCHAR 인라인 컨트롤이므로 공백으로 대체
        if text:
            text = text.replace('\t', '    ')

        # 표 블록 처리
        if block.type == BlockType.TABLE:
            table_rows = []
            for row_block in block.children:
                if isinstance(row_block, BlockNode):
                    row = []
                    for cell_block in row_block.children:
                        if isinstance(cell_block, BlockNode):
                            cell_text = ''.join(
                                c.text for c in cell_block.children
                                if hasattr(c, 'text') and c.text
                            )
                            row.append(cell_text)
                    if row:
                        table_rows.append(row)
            if table_rows:
                out.write(_table_paragraph(table_rows))
            continue

        is_heading = block.type == BlockType.HEADING
        level      = min(block.level or 1, 3) if is_heading else 0
        style_id   = level if is_heading else 0
        is_last    = (i == len(text_blocks) - 1)

        # PARA_TEXT: UTF-16LE + 0x0D (문단 끝 마커)
        text_utf16 = text.encode('utf-16-le') + b'\x0D\x00'
        char_count = len(text) + 1

        # PARA_HEADER: 마지막 문단에 0x80000000 플래그
        nchars = char_count | (0x80000000 if is_last else 0)
        ph = struct.pack('<II', nchars, 0)
        ph += struct.pack('<H', 0)
        ph += struct.pack('<BB', style_id, 0)
        ph += struct.pack('<HHH', 1, 0, 1)
        ph += struct.pack('<I', 0)
        out.write(_rec(_TAG_PARA_HEADER, ph))

        out.write(_rec(_TAG_PARA_TEXT, text_utf16, level=1))

        # PARA_CHAR_SHAPE: 인라인 타입별 charshape 엔트리 생성
        if is_heading:
            pcs = struct.pack('<II', 0, cs_heading)
        else:
            pcs = _build_para_char_shape(block, cs_normal, cs_bold, cs_italic)
        out.write(_rec(_TAG_PARA_CHAR_SHAPE, pcs, level=1))

        text_h = 1400 if is_heading else 1000
        line_h = int(text_h * 1.6)
        page_w = 59528 - 4252 - 4252
        pls = struct.pack('<iiiiiiiiI',
            0, 0, line_h, text_h, text_h // 4, line_h, 0, page_w, 0)
        out.write(_rec(_TAG_PARA_LINE_SEG, pls, level=1))

    # 마지막 블록이 표인 경우 섹션 끝 문단이 없으므로 추가
    if text_blocks and text_blocks[-1][0].type == BlockType.TABLE:
        _pw = 59528 - 4252 - 4252  # A4 텍스트 영역
        ph = struct.pack('<II', 1 | 0x80000000, 0)
        ph += struct.pack('<H', 0) + struct.pack('<BB', 0, 0)
        ph += struct.pack('<HHH', 0, 0, 1) + struct.pack('<I', 0)
        out.write(_rec(_TAG_PARA_HEADER, ph))
        out.write(_rec(_TAG_PARA_CHAR_SHAPE, struct.pack('<II', 0, 0), level=1))
        out.write(_rec(_TAG_PARA_LINE_SEG, struct.pack('<iiiiiiiiI',
            0, 0, 1600, 1000, 250, 1600, 0, _pw, 0), level=1))

    return out.getvalue()


def _empty_para() -> bytes:
    """빈 문단 (nchars=1, 0x0D만). Section0 패딩용."""
    ph = struct.pack('<II', 1, 0)
    ph += struct.pack('<H', 0) + struct.pack('<BB', 0, 0)
    ph += struct.pack('<HHH', 1, 0, 1) + struct.pack('<I', 0)
    result = _rec(_TAG_PARA_HEADER, ph)
    result += _rec(_TAG_PARA_CHAR_SHAPE, struct.pack('<II', 0, 0), level=1)
    result += _rec(_TAG_PARA_LINE_SEG, struct.pack('<iiiiiiiiI',
        0, 0, 1600, 1000, 250, 1600, 0, 51024, 0), level=1)
    return result


# ── 표(Table) 생성 ─────────────────────────────────────────────

_TAG_CTRL_HEADER = 0x47   # 71
_TAG_LIST_HEADER = 0x48   # 72
_TAG_TABLE       = 0x4D   # 77


def _table_paragraph(rows: list[list[str]], base_level: int = 0) -> bytes:
    """Markdown 표 데이터 → HWP 표 레코드.

    실제 HWP 파일(sample-5017.hwp)에서 추출한 CTRL_HEADER/LIST_HEADER 바이트를
    템플릿으로 사용하여 한컴 뷰어 호환성 보장.
    """
    if not rows or not rows[0]:
        return b''

    n_rows = len(rows)
    n_cols = len(rows[0])
    page_w = 42520  # A4 텍스트 영역 (실제 HWP 기준, 150mm ≈ 42520 HWPUNIT)
    col_w = page_w // n_cols

    out = BytesIO()

    # 실제 파일에서 추출한 템플릿 바이트
    CTRL_HDR_TPL = _b64.b64decode('IGxidBEjKggAAAAAAAAAAAaeAABEEAAAAAAAABsBGwEbARsB7a2iVgAAAAA=')
    INLINE_0B = _b64.b64decode('CwAgbGJ0AAAAAAAAAAALAA==')

    # 1) PARA_HEADER — 0x0B 컨트롤 포함
    nchars = 8 + 1  # 0x0B(8) + 0x0D(1)
    ph = struct.pack('<II', nchars, 0x00000800)  # controlmask bit11=0x800 (0x0B=표 컨트롤)
    ph += struct.pack('<H', 0) + struct.pack('<BB', 0, 0)
    ph += struct.pack('<HHH', 1, 0, 1) + struct.pack('<I', 0)
    out.write(_rec(_TAG_PARA_HEADER, ph, level=base_level))

    # 2) PARA_TEXT — 0x0B(16B) + 0x0D(2B) = 18B
    para_text = INLINE_0B + struct.pack('<H', 0x0D)
    out.write(_rec(_TAG_PARA_TEXT, para_text, level=base_level + 1))

    out.write(_rec(_TAG_PARA_CHAR_SHAPE, struct.pack('<II', 0, 0),
                   level=base_level + 1))
    out.write(_rec(_TAG_PARA_LINE_SEG, struct.pack('<iiiiiiiiI',
        0, 0, 1600, 1000, 250, 1600, 0, page_w, 0),
        level=base_level + 1))

    # 3) CTRL_HEADER — 실제 파일 템플릿 사용 (44B)
    ctrl = bytearray(CTRL_HDR_TPL)
    # width 업데이트 (offset 16-19)
    struct.pack_into('<I', ctrl, 16, page_w)
    out.write(_rec(_TAG_CTRL_HEADER, bytes(ctrl), level=base_level + 1))

    # 4) TABLE — 행/열 정의
    table_data = struct.pack('<I', 0x04000006)
    table_data += struct.pack('<HH', n_rows, n_cols)
    table_data += struct.pack('<H', 0)  # cellspacing
    table_data += struct.pack('<4H', 141, 141, 141, 141)
    for _ in range(n_rows):
        table_data += struct.pack('<H', n_cols)
    table_data += struct.pack('<H', 1)  # borderfill_id
    table_data += struct.pack('<H', 0)  # Valid Zone Info Size (v5.0.1.0+)
    out.write(_rec(_TAG_TABLE, table_data, level=base_level + 2))

    # 5) 각 셀
    for r in range(n_rows):
        for c in range(n_cols):
            cell_text = (rows[r][c] if c < len(rows[r]) else '').replace('\t', '    ')

            # LIST_HEADER (38B) — 셀 정의
            lh = struct.pack('<H', 1)       # paragraphs
            lh += struct.pack('<H', 0)      # unknown1
            lh += struct.pack('<I', 0x20)   # listflags (from real: 0x00000020)
            lh += struct.pack('<HH', c, r)  # col, row
            lh += struct.pack('<HH', 1, 1)  # colspan, rowspan
            lh += struct.pack('<i', col_w)  # width
            lh += struct.pack('<i', 282)    # height (from real)
            lh += struct.pack('<4H', 141, 141, 141, 141)
            lh += struct.pack('<H', 1)      # borderfill_id
            lh += struct.pack('<i', col_w)  # unknown_width
            out.write(_rec(_TAG_LIST_HEADER, lh, level=base_level + 2))

            # PARA_HEADER — 셀 내 마지막(유일) 문단이므로 0x80000000 플래그
            has_text = bool(cell_text.strip())
            if has_text:
                cell_utf16 = cell_text.encode('utf-16-le') + b'\x0D\x00'
                cell_nchars = (len(cell_text) + 1) | 0x80000000
            else:
                # 빈 셀: nchars=1 (0x0D만), PARA_TEXT 생략 (실제 HWP 방식)
                cell_nchars = 1 | 0x80000000

            cph = struct.pack('<II', cell_nchars, 0)
            cph += struct.pack('<H', 0) + struct.pack('<BB', 0, 0)
            cph += struct.pack('<HHH', 1 if has_text else 0, 0, 1)
            cph += struct.pack('<I', 0)
            out.write(_rec(_TAG_PARA_HEADER, cph, level=base_level + 2))

            if has_text:
                out.write(_rec(_TAG_PARA_TEXT, cell_utf16, level=base_level + 3))

            out.write(_rec(_TAG_PARA_CHAR_SHAPE, struct.pack('<II', 0, 0),
                           level=base_level + 3))
            out.write(_rec(_TAG_PARA_LINE_SEG, struct.pack('<iiiiiiiiI',
                0, 0, 1600, 1000, 250, 1600, 0, col_w, 0),
                level=base_level + 3))

    return out.getvalue()


# ══════════════════════════════════════════════════════════════
#  공개 인터페이스
# ══════════════════════════════════════════════════════════════

def _patch_docinfo_add_charshapes(di_data: bytes) -> bytes:
    """템플릿 DocInfo에 볼드/이탤릭 charshape를 추가 (기존 레코드 보존).

    ID_MAPPINGS의 charshapes 카운트를 +2 하고,
    마지막 CHAR_SHAPE 뒤에 body-bold, body-italic 레코드를 삽입한다.
    """
    records = []
    pos = 0
    while pos + 4 <= len(di_data):
        hdr = struct.unpack_from('<I', di_data, pos)[0]
        rec_start = pos
        pos += 4
        tag = hdr & 0x3FF
        sz = hdr >> 20
        if sz == 0xFFF:
            if pos + 4 > len(di_data):
                break
            sz = struct.unpack_from('<I', di_data, pos)[0]
            pos += 4
        if pos + sz > len(di_data):
            sz = len(di_data) - pos
        records.append({'tag': tag, 'start': rec_start, 'payload_start': pos, 'size': sz})
        pos += sz

    # 마지막 CHAR_SHAPE 레코드 위치 찾기
    last_cs_end = None
    for rec in records:
        if rec['tag'] == _TAG_CHAR_SHAPE:
            last_cs_end = rec['payload_start'] + rec['size']

    if last_cs_end is None:
        return di_data  # charshape 없으면 패치 불가

    # ID_MAPPINGS 패치: charshapes 카운트 +2
    id_map_rec = None
    for rec in records:
        if rec['tag'] == _TAG_ID_MAPPINGS:
            id_map_rec = rec
            break

    out = bytearray(di_data)

    if id_map_rec:
        cs_offset = id_map_rec['payload_start'] + 9 * 4  # 10번째 UINT32 = charshapes (0-indexed: 9)
        old_count = struct.unpack_from('<I', out, cs_offset)[0]
        struct.pack_into('<I', out, cs_offset, old_count + 2)

    # 새 charshape 레코드 2개 생성
    def _make_cs(pt_100: int, bold: bool = False, italic: bool = False) -> bytes:
        attr = 0
        if bold:
            attr |= (1 << 6)
        if italic:
            attr |= (1 << 7)
        payload = (
            struct.pack('<7H', 0, 0, 0, 0, 0, 0, 0)
            + struct.pack('<7B', 100, 100, 100, 100, 100, 100, 100)
            + struct.pack('<7b', 0, 0, 0, 0, 0, 0, 0)
            + struct.pack('<7B', 100, 100, 100, 100, 100, 100, 100)
            + struct.pack('<7b', 0, 0, 0, 0, 0, 0, 0)
            + struct.pack('<i', pt_100)
            + struct.pack('<I', attr)
            + struct.pack('<bb', 0, 0)
            + struct.pack('<IIII', 0x00000000, 0x00000000, 0xFFFFFFFF, 0x00B2B2B2)
        )
        return _rec(_TAG_CHAR_SHAPE, payload)

    new_records = _make_cs(1000, bold=True) + _make_cs(1000, italic=True)

    # 마지막 CHAR_SHAPE 뒤에 삽입
    result = bytes(out[:last_cs_end]) + new_records + bytes(out[last_cs_end:])
    return result


class HwpBinaryWriter:
    """DocumentIR → HWP 5.0 바이너리 파일 생성."""

    # HWP 템플릿 파일 경로 (실제 HWP 5.0 파일 기반)
    _TEMPLATE = Path(__file__).parent / 'hwp_template.hwp'
    _MAX_PADDING = 150  # zero 패딩 최대 바이트 (뷰어 호환 한계)

    def from_ir(self, ir: DocumentIR, output_path: Path) -> Path:
        """DocumentIR → HWP 5.0 생성 (템플릿 기반).

        실제 HWP 파일을 템플릿으로 사용하여 OLE 컨테이너 구조를 보장.
        DocInfo에 볼드/이탤릭 charshape를 패치 삽입 (기존 레코드 보존).
        """
        import olefile
        import shutil

        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self._TEMPLATE, output_path)

        ole = olefile.OleFileIO(str(output_path), write_mode=True)

        # DocInfo 패치: 템플릿 원본에 charshape 2개만 추가 (BORDER_FILL 등 보존)
        tpl_di_comp = ole.openstream('DocInfo').read()
        tpl_di_size = len(tpl_di_comp)
        try:
            tpl_di_raw = zlib.decompress(tpl_di_comp, -15)
        except zlib.error:
            tpl_di_raw = tpl_di_comp

        # 기존 charshape 개수 파악 → 새 ID 결정
        tpl_cs_count = 0
        _pos = 0
        while _pos + 4 <= len(tpl_di_raw):
            _hdr = struct.unpack_from('<I', tpl_di_raw, _pos)[0]
            _pos += 4
            _tag = _hdr & 0x3FF
            _sz = _hdr >> 20
            if _sz == 0xFFF:
                if _pos + 4 > len(tpl_di_raw):
                    break
                _sz = struct.unpack_from('<I', tpl_di_raw, _pos)[0]
                _pos += 4
            if _tag == _TAG_CHAR_SHAPE:
                tpl_cs_count += 1
            _pos += _sz
        cs_bold_id = tpl_cs_count       # 첫 번째 추가 charshape = bold body
        cs_italic_id = tpl_cs_count + 1  # 두 번째 추가 charshape = italic body

        patched_di = _patch_docinfo_add_charshapes(tpl_di_raw)
        di_comp = _compress(patched_di)
        if len(di_comp) <= tpl_di_size:
            ole.write_stream('DocInfo', di_comp.ljust(tpl_di_size, b'\x00'))

        # Section0 생성 + 압축 (동적 charshape ID 사용)
        s0_raw = _section(ir.blocks,
                          cs_normal=0, cs_heading=1,
                          cs_bold=cs_bold_id, cs_italic=cs_italic_id)
        co = zlib.compressobj(6, zlib.DEFLATED, -15)
        s0_comp = co.compress(s0_raw) + co.flush()

        tpl_size = len(ole.openstream('BodyText/Section0').read())

        if len(s0_comp) <= tpl_size:
            # 작은 문서: 빈 문단 추가로 패딩 최소화
            while tpl_size - len(s0_comp) > self._MAX_PADDING:
                s0_raw += _empty_para()
                co = zlib.compressobj(6, zlib.DEFLATED, -15)
                new_comp = co.compress(s0_raw) + co.flush()
                if len(new_comp) > tpl_size:
                    break
                s0_comp = new_comp
            ole.write_stream('BodyText/Section0', s0_comp.ljust(tpl_size, b'\x00'))
            ole.close()
        else:
            ole.close()
            # 큰 문서: regular sector에 직접 배치
            # OLE mini stream cutoff = 4096 → 압축 데이터가 4096 이상이어야 함
            # 제로 패딩은 뷰어가 잘못된 데이터로 인식 → 빈 문단 추가로 실제 데이터 확장
            while len(s0_comp) < 4096:
                s0_raw += _empty_para()
                co = zlib.compressobj(6, zlib.DEFLATED, -15)
                s0_comp = co.compress(s0_raw) + co.flush()
            self._write_large_section(output_path, s0_comp, actual_size=len(s0_comp))

        return output_path

    @staticmethod
    def _write_large_section(output_path: Path, s0_data: bytes,
                             actual_size: int | None = None) -> None:
        """큰 Section0을 regular sector에 직접 배치.

        mini stream 대신 파일 끝에 regular sector로 추가하고
        디렉터리/FAT를 업데이트한다.
        """
        SECT = 512
        data = bytearray(output_path.read_bytes())

        # OLE 헤더 파싱
        first_dir = struct.unpack_from('<I', data, 48)[0]
        fat_sector = struct.unpack_from('<I', data, 76)[0]
        fat_offset = SECT + fat_sector * SECT

        # FAT 읽기
        fat = list(struct.unpack_from('<128I', data, fat_offset))

        # 디렉터리 찾기
        dir_sectors = []
        s = first_dir
        while s < 0xFFFFFFFE and len(dir_sectors) < 20:
            dir_sectors.append(s)
            s = fat[s] if s < len(fat) else 0xFFFFFFFE

        dir_data = bytearray()
        for ds in dir_sectors:
            dir_data.extend(data[SECT + ds * SECT:SECT + ds * SECT + SECT])

        # Section0 디렉터리 엔트리 찾기
        s0_idx = None
        for i in range(len(dir_data) // 128):
            entry = dir_data[i * 128:(i + 1) * 128]
            nl = struct.unpack_from('<H', entry, 64)[0]
            if nl > 2:
                name = entry[:nl - 2].decode('utf-16-le', errors='replace')
                if name == 'Section0':
                    s0_idx = i
                    break

        if s0_idx is None:
            raise RuntimeError("Section0 not found")

        # Section0 데이터를 512바이트 경계로 패딩
        s0_padded = s0_data + b'\x00' * (SECT - len(s0_data) % SECT) \
            if len(s0_data) % SECT else s0_data
        n_new_sectors = len(s0_padded) // SECT

        # 파일 끝에 새 섹터 추가
        first_new = len(data) // SECT - 1  # 0-based sector index (subtract header)
        # 실제로는 (file_size - header_512) / 512
        first_new = (len(data) - SECT) // SECT

        for i in range(n_new_sectors):
            data.extend(s0_padded[i * SECT:(i + 1) * SECT])

        # FAT 확장 + 체인 설정
        while len(fat) <= first_new + n_new_sectors:
            fat.append(0xFFFFFFFF)
        for i in range(n_new_sectors - 1):
            fat[first_new + i] = first_new + i + 1
        fat[first_new + n_new_sectors - 1] = 0xFFFFFFFE  # ENDOFCHAIN

        # Section0 디렉터리 엔트리 업데이트: regular sector 참조
        entry_off = s0_idx * 128
        struct.pack_into('<I', dir_data, entry_off + 116, first_new)  # start sector
        struct.pack_into('<I', dir_data, entry_off + 120, actual_size or len(s0_data))

        # 디렉터리 다시 쓰기
        for i, ds in enumerate(dir_sectors):
            offset = SECT + ds * SECT
            data[offset:offset + SECT] = dir_data[i * SECT:(i + 1) * SECT]

        # FAT 다시 쓰기
        fat_bytes = struct.pack(f'<{min(len(fat), 128)}I', *fat[:128])
        data[fat_offset:fat_offset + len(fat_bytes)] = fat_bytes

        output_path.write_bytes(bytes(data))

    @staticmethod
    def _write_section_raw(output_path: Path, s0_data: bytes) -> None:
        """OLE 파일의 mini stream에서 Section0을 직접 교체 (크기 제한 없음).

        mini FAT 체인과 디렉터리 엔트리의 size 필드를 갱신한다.
        """
        data = bytearray(output_path.read_bytes())
        SECT = 512
        MINI = 64

        # OLE 헤더에서 디렉터리/miniFAT 위치
        first_dir = struct.unpack_from('<I', data, 48)[0]
        first_minifat = struct.unpack_from('<I', data, 60)[0]

        # 디렉터리 섹터 체인 따라가기
        fat_start = struct.unpack_from('<I', data, 76)[0]
        fat_offset = SECT + fat_start * SECT
        fat = list(struct.unpack_from('<128I', data, fat_offset))

        # 디렉터리 엔트리 읽기 (체인 따라감)
        dir_sectors = []
        s = first_dir
        while s != 0xFFFFFFFE and s != 0xFFFFFFFF and len(dir_sectors) < 20:
            dir_sectors.append(s)
            s = fat[s]

        dir_data = bytearray()
        for ds in dir_sectors:
            offset = SECT + ds * SECT
            dir_data.extend(data[offset:offset + SECT])

        # Section0 디렉터리 엔트리 찾기
        s0_entry_idx = None
        for i in range(len(dir_data) // 128):
            entry = dir_data[i * 128:(i + 1) * 128]
            name_len = struct.unpack_from('<H', entry, 64)[0]
            if name_len > 2:
                name = entry[:name_len - 2].decode('utf-16-le', errors='replace')
                if name == 'Section0':
                    s0_entry_idx = i
                    break

        if s0_entry_idx is None:
            raise RuntimeError("Section0 디렉터리 엔트리를 찾을 수 없습니다")

        entry_offset_in_dir = s0_entry_idx * 128
        old_start = struct.unpack_from('<I', dir_data, entry_offset_in_dir + 116)[0]
        old_size = struct.unpack_from('<I', dir_data, entry_offset_in_dir + 120)[0]

        # Root Entry에서 mini stream 위치
        root_start = struct.unpack_from('<I', dir_data, 116)[0]
        root_size = struct.unpack_from('<I', dir_data, 120)[0]

        # mini stream 데이터 추출
        ms_sectors = []
        s = root_start
        while s != 0xFFFFFFFE and s != 0xFFFFFFFF and len(ms_sectors) < 200:
            ms_sectors.append(s)
            s = fat[s]

        mini_stream = bytearray()
        for ms in ms_sectors:
            offset = SECT + ms * SECT
            mini_stream.extend(data[offset:offset + SECT])

        # mini FAT 읽기
        mfat_sectors = []
        s = first_minifat
        while s != 0xFFFFFFFE and s != 0xFFFFFFFF and len(mfat_sectors) < 20:
            mfat_sectors.append(s)
            s = fat[s]

        mfat_data = bytearray()
        for ms in mfat_sectors:
            offset = SECT + ms * SECT
            mfat_data.extend(data[offset:offset + SECT])
        mfat = list(struct.unpack_from(f'<{len(mfat_data) // 4}I', mfat_data))

        # Section0의 mini sector 체인 찾기
        old_mini_sectors = []
        ms = old_start
        while ms != 0xFFFFFFFE and ms != 0xFFFFFFFF and len(old_mini_sectors) < 500:
            old_mini_sectors.append(ms)
            ms = mfat[ms] if ms < len(mfat) else 0xFFFFFFFE

        # 새 데이터를 mini sector 크기로 패딩
        padded = s0_data + b'\x00' * (MINI - len(s0_data) % MINI) if len(s0_data) % MINI else s0_data
        new_mini_count = len(padded) // MINI

        # 기존 mini sector에 데이터 쓰기
        for i in range(min(new_mini_count, len(old_mini_sectors))):
            ms_idx = old_mini_sectors[i]
            offset = ms_idx * MINI
            mini_stream[offset:offset + MINI] = padded[i * MINI:(i + 1) * MINI]

        # 필요하면 추가 mini sector 할당 (mini stream 끝에 추가)
        if new_mini_count > len(old_mini_sectors):
            current_total = len(mini_stream) // MINI
            for i in range(len(old_mini_sectors), new_mini_count):
                ms_idx = current_total + (i - len(old_mini_sectors))
                # mini stream 확장
                while len(mini_stream) <= ms_idx * MINI + MINI:
                    mini_stream.extend(b'\x00' * MINI)
                offset = ms_idx * MINI
                mini_stream[offset:offset + MINI] = padded[i * MINI:(i + 1) * MINI]

                # mini FAT 체인 업데이트
                if i > 0:
                    prev_ms = old_mini_sectors[i - 1] if i < len(old_mini_sectors) + 1 else ms_idx - 1
                    if i == len(old_mini_sectors):
                        prev_ms = old_mini_sectors[-1]
                    while len(mfat) <= ms_idx:
                        mfat.append(0xFFFFFFFF)
                    mfat[prev_ms] = ms_idx
                old_mini_sectors.append(ms_idx)

        # 마지막 mini sector를 ENDOFCHAIN으로
        if old_mini_sectors:
            last_ms = old_mini_sectors[new_mini_count - 1]
            while len(mfat) <= last_ms:
                mfat.append(0xFFFFFFFF)
            mfat[last_ms] = 0xFFFFFFFE
            # 남은 기존 sector 해제
            for i in range(new_mini_count, len(old_mini_sectors)):
                if old_mini_sectors[i] < len(mfat):
                    mfat[old_mini_sectors[i]] = 0xFFFFFFFF

        # 디렉터리 엔트리 size 업데이트
        struct.pack_into('<I', dir_data, entry_offset_in_dir + 120, len(s0_data))

        # Root Entry size 업데이트
        new_root_size = len(mini_stream)
        struct.pack_into('<I', dir_data, 120, new_root_size)

        # mini stream을 regular sectors에 다시 쓰기
        needed_sectors = (len(mini_stream) + SECT - 1) // SECT
        ms_padded = mini_stream + b'\x00' * (needed_sectors * SECT - len(mini_stream))

        # 기존 mini stream sectors에 쓰기
        for i, sec in enumerate(ms_sectors):
            if i < needed_sectors:
                offset = SECT + sec * SECT
                data[offset:offset + SECT] = ms_padded[i * SECT:(i + 1) * SECT]

        # 필요시 추가 sectors (파일 끝에 추가)
        if needed_sectors > len(ms_sectors):
            last_ms_sec = ms_sectors[-1]
            for i in range(len(ms_sectors), needed_sectors):
                new_sec = len(data) // SECT
                data.extend(ms_padded[i * SECT:(i + 1) * SECT])
                fat[last_ms_sec] = new_sec
                while len(fat) <= new_sec:
                    fat.append(0xFFFFFFFF)
                fat[new_sec] = 0xFFFFFFFE
                last_ms_sec = new_sec

        # 디렉터리 데이터 다시 쓰기
        for i, ds in enumerate(dir_sectors):
            offset = SECT + ds * SECT
            data[offset:offset + SECT] = dir_data[i * SECT:(i + 1) * SECT]

        # mini FAT 다시 쓰기
        mfat_bytes = struct.pack(f'<{len(mfat)}I', *mfat)
        mfat_padded = mfat_bytes + b'\xFF' * 4 * (128 * len(mfat_sectors) - len(mfat))
        for i, ms in enumerate(mfat_sectors):
            offset = SECT + ms * SECT
            data[offset:offset + SECT] = mfat_padded[i * SECT:(i + 1) * SECT]

        # FAT 다시 쓰기
        fat_bytes = struct.pack(f'<{min(len(fat), 128)}I', *fat[:128])
        data[SECT + fat_start * SECT:SECT + fat_start * SECT + len(fat_bytes)] = fat_bytes

        output_path.write_bytes(bytes(data))

    def from_markdown(self, markdown_text: str, output_path: Path) -> Path:
        from .generator import HwpxGenerator
        ir = HwpxGenerator()._markdown_to_ir(markdown_text)
        return self.from_ir(ir, output_path)
