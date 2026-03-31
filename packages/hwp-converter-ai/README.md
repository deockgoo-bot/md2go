# HWP Converter AI

Python으로 HWP/HWPX 파일을 생성·파싱·변환합니다.
한컴오피스 없이 HWP 문서를 프로그래밍으로 처리할 수 있습니다.

## 설치

```bash
pip install hwp-converter-ai
```

## 3줄이면 HWP 생성

```python
from hwp_converter_ai import HwpWriter

writer = HwpWriter()
writer.from_markdown("# 업무 보고\n\n내용입니다.", "report.hwp")
```

## 주요 기능

### Markdown → HWP (한글 97~2024 호환)

```python
from hwp_converter_ai import HwpWriter

writer = HwpWriter()
writer.from_markdown("""
# 업무 보고서

일반 텍스트 **볼드 강조** 그리고 *이탤릭*.

| 항목 | 상태 |
|------|------|
| 변환 | 완료 |
| 교정 | 진행중 |
""", "report.hwp")
```

### Markdown → HWPX (한글 2014+ 호환)

```python
from hwp_converter_ai import HwpxGenerator

gen = HwpxGenerator()
gen.from_markdown("# 제목\n\n본문 **볼드**", output_path="report.hwpx")
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
|------|-----|------|
| 텍스트/문단 | ✅ | ✅ |
| 제목 (H1~H3) | ✅ | ✅ |
| **볼드**/이탤릭 | ✅ | ✅ |
| 표 (테두리 포함) | ✅ | ✅ |
| 이미지 추출 | ✅ | ✅ |
| 리스트 감지 | ✅ | ✅ |

## 라이선스

MIT License
