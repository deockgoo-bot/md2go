"""
HWPX ↔ Markdown 변환을 위한 JSON IR (Intermediate Representation) 스키마.
모든 변환은 이 IR을 경유한다: HWPX → IR → Markdown, Markdown → IR → HWPX
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BlockType(str, Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TABLE = "table"
    LIST = "list"
    LIST_ITEM = "list_item"
    IMAGE = "image"
    CODE = "code"
    DIVIDER = "divider"


class InlineType(str, Enum):
    TEXT = "text"
    BOLD = "bold"
    ITALIC = "italic"
    UNDERLINE = "underline"
    LINK = "link"


@dataclass
class TextStyle:
    font_name: str = "바탕"
    font_size: float = 10.0          # pt
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: str = "#000000"


@dataclass
class ParagraphStyle:
    alignment: str = "left"          # left | center | right | justify
    line_height: float = 1.6
    indent_left: float = 0.0         # mm
    indent_right: float = 0.0
    space_before: float = 0.0
    space_after: float = 0.0


@dataclass
class InlineNode:
    type: InlineType
    text: str
    style: TextStyle = field(default_factory=TextStyle)
    href: str | None = None          # link 타입일 경우

    def to_markdown(self) -> str:
        """인라인 노드를 Markdown 텍스트로 변환."""
        t = self.text
        if not t:
            return ""
        if self.type == InlineType.BOLD:
            return f"**{t}**"
        elif self.type == InlineType.ITALIC:
            return f"*{t}*"
        elif self.type == InlineType.UNDERLINE:
            return f"<u>{t}</u>"
        elif self.type == InlineType.LINK and self.href:
            return f"[{t}]({self.href})"
        return t


@dataclass
class BlockNode:
    type: BlockType
    children: list[InlineNode | BlockNode] = field(default_factory=list)
    style: ParagraphStyle = field(default_factory=ParagraphStyle)
    level: int | None = None         # heading level (1~6)
    metadata: dict[str, Any] = field(default_factory=dict)

    def _inline_text(self) -> str:
        """자식 인라인 노드를 Markdown 텍스트로 결합."""
        return "".join(
            c.to_markdown() if isinstance(c, InlineNode) else c.text
            for c in self.children
            if isinstance(c, InlineNode) or (isinstance(c, BlockNode) and hasattr(c, 'text'))
        )

    def to_markdown(self) -> str:
        """IR 블록을 Markdown 텍스트로 변환."""
        if self.type == BlockType.HEADING:
            prefix = "#" * (self.level or 1)
            text = self._inline_text()
            return f"{prefix} {text}\n"

        elif self.type == BlockType.PARAGRAPH:
            text = self._inline_text()
            return f"{text}\n" if text.strip() else ""

        elif self.type == BlockType.DIVIDER:
            return "---\n"

        elif self.type == BlockType.TABLE:
            return self._table_to_markdown()

        elif self.type == BlockType.LIST:
            return self._list_to_markdown()

        elif self.type == BlockType.LIST_ITEM:
            text = self._inline_text()
            return f"- {text}\n"

        elif self.type == BlockType.CODE:
            text = self._inline_text()
            return f"```\n{text}\n```\n"

        elif self.type == BlockType.IMAGE:
            src = self.metadata.get("src", "")
            alt = self.metadata.get("alt", "이미지")
            return f"![{alt}]({src})\n"

        return ""

    def _table_to_markdown(self) -> str:
        rows = [c for c in self.children if isinstance(c, BlockNode)]
        if not rows:
            return ""
        lines = []
        for i, row in enumerate(rows):
            cells = [c for c in row.children if isinstance(c, BlockNode)]
            line = "| " + " | ".join(
                "".join(
                    ic.to_markdown() if isinstance(ic, InlineNode) else ""
                    for ic in cell.children
                ).strip()
                for cell in cells
            ) + " |"
            lines.append(line)
            if i == 0:
                sep = "| " + " | ".join("---" for _ in cells) + " |"
                lines.append(sep)
        return "\n".join(lines) + "\n"

    def _list_to_markdown(self) -> str:
        parts = []
        for child in self.children:
            if isinstance(child, BlockNode) and child.type == BlockType.LIST_ITEM:
                text = child._inline_text()
                parts.append(f"- {text}")
        return "\n".join(parts) + "\n" if parts else ""


@dataclass
class DocumentIR:
    """HWPX 문서 전체의 중간 표현."""
    title: str = ""
    author: str = ""
    created_at: str = ""
    document_type: str = "default"   # 기안문 | 보고서 | 공고문 | ...
    blocks: list[BlockNode] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """전체 문서를 Markdown으로 변환."""
        parts = []
        if self.title:
            parts.append(f"# {self.title}\n")
        for block in self.blocks:
            md = block.to_markdown()
            if md:
                parts.append(md)
        return "\n".join(parts)

    def to_plain_text(self) -> str:
        """RAG 인덱싱용 순수 텍스트 반환 (마크업 제거)."""
        lines = []
        if self.title:
            lines.append(self.title)
        for block in self.blocks:
            text = "".join(
                c.text for c in block.children if isinstance(c, InlineNode)
            )
            if text.strip():
                lines.append(text)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """JSON 직렬화용 딕셔너리 반환."""
        import dataclasses
        return dataclasses.asdict(self)
