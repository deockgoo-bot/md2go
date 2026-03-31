# HWP Converter AI

[![PyPI](https://img.shields.io/pypi/v/hwp-converter-ai)](https://pypi.org/project/hwp-converter-ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/hwp-converter-ai)](https://pypi.org/project/hwp-converter-ai/)

Python으로 HWP/HWPX 파일을 생성·파싱·변환합니다.
한컴오피스 없이 HWP 문서를 프로그래밍으로 처리할 수 있습니다.

> 웹에서 바로 체험하기: [https://www.hwpsome.com](https://www.hwpsome.com)

## 설치

```bash
pip install hwp-converter-ai
```

## 빠른 시작

### Markdown → HWP (한글 97~2024)

```python
from hwp_converter_ai import HwpWriter

HwpWriter().from_markdown("# 업무 보고\n\n내용입니다.", "report.hwp")
```

### Markdown → HWPX (한글 2014+)

```python
from hwp_converter_ai import HwpxGenerator

HwpxGenerator().from_markdown("# 제목\n\n**볼드** 텍스트", output_path="report.hwpx")
```

### HWP → Markdown

```python
from hwp_converter_ai import HwpParser

ir = HwpParser.parse("document.hwp")
print(ir.to_markdown())
```

### HWPX → Markdown

```python
from hwp_converter_ai import HwpxParser

ir = HwpxParser().parse("document.hwpx")
print(ir.to_markdown())
```

## 지원 기능

| 기능 | HWP | HWPX |
|------|:---:|:----:|
| 텍스트/문단 | ✅ | ✅ |
| 제목 (H1~H3) | ✅ | ✅ |
| **볼드**/*이탤릭* | ✅ | ✅ |
| 표 (테두리 포함) | ✅ | ✅ |
| 이미지 추출 | ✅ | ✅ |
| 리스트 감지 | ✅ | ✅ |
| 긴 문서 | ✅ | ✅ |

## 예제

### 볼드/이탤릭 포함 문서

```python
from hwp_converter_ai import HwpWriter

md = """# 업무 보고서

일반 텍스트 **볼드 강조** 그리고 *이탤릭 참고*.

| 항목 | 상태 |
|------|------|
| 변환 | 완료 |
| 교정 | 진행중 |
"""

HwpWriter().from_markdown(md, "report.hwp")
```

### HWP 파싱 후 텍스트 추출

```python
from hwp_converter_ai import HwpParser

ir = HwpParser.parse("input.hwp")

# Markdown으로
print(ir.to_markdown())

# 순수 텍스트로 (검색/인덱싱용)
print(ir.to_plain_text())
```

### IR(중간 표현) 직접 조작

```python
from hwp_converter_ai import HwpWriter, DocumentIR, BlockNode, InlineNode, BlockType, InlineType

ir = DocumentIR(title="보고서")
ir.blocks.append(BlockNode(
    type=BlockType.HEADING, level=1,
    children=[InlineNode(type=InlineType.TEXT, text="제목")]
))
ir.blocks.append(BlockNode(
    type=BlockType.PARAGRAPH,
    children=[
        InlineNode(type=InlineType.TEXT, text="일반 "),
        InlineNode(type=InlineType.BOLD, text="강조"),
    ]
))

HwpWriter().from_ir(ir, "custom.hwp")
```

## 요구사항

- Python 3.10+
- `olefile` (자동 설치)

## 웹 서비스

코드 없이 브라우저에서 바로 변환하려면:

**[https://www.hwpsome.com](https://www.hwpsome.com)**

- HWP ↔ Markdown 변환
- AI 공문서 초안 생성
- 맞춤법·행정 문체 교정 (Pro)
- RAG 문서 검색 (Pro)

## 라이선스

MIT License
