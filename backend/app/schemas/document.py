import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    filename: str
    file_type: str


class DocumentRead(DocumentBase):
    id: uuid.UUID
    status: str
    error_message: str | None = None
    doc_metadata: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Draft ----------

class DraftRequest(BaseModel):
    template: str = Field(..., description="공문서 종류 (기안문·보고서·공고문 등 10종)")
    title: str = Field(..., description="문서 제목")
    body_hint: str = Field(..., description="본문 내용 힌트 (자유 텍스트)")
    department: str = Field(default="", description="기안 부서명")
    reference_number: str = Field(default="", description="문서번호")
    format: str = Field(default="hwpx", description="출력 형식: hwpx (기본), hwp, hwp-legacy")


class DraftResponse(BaseModel):
    job_id: str
    status: str
    markdown: str | None = None
    download_url: str | None = None


# ---------- Search ----------

class IndexRequest(BaseModel):
    document_ids: list[uuid.UUID] = Field(..., description="인덱싱할 문서 ID 목록")


class IndexResponse(BaseModel):
    job_id: str
    status: str
    indexed_count: int = 0


class SearchRequest(BaseModel):
    query: str = Field(..., description="자연어 검색 질의")
    top_k: int = Field(default=5, ge=1, le=20)
    document_ids: list[uuid.UUID] | None = Field(default=None, description="검색 범위 제한 (None이면 전체)")


class SearchResult(BaseModel):
    document_id: uuid.UUID
    filename: str
    chunk_index: int
    page_number: int | None
    content: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    elapsed_ms: float


# ---------- Correct ----------

class SummarizeRequest(BaseModel):
    document_id: uuid.UUID | None = None
    text: str | None = None  # document_id 없을 경우 직접 텍스트 전달


class SummarizeResponse(BaseModel):
    job_id: str
    summary: str


class ProofreadRequest(BaseModel):
    document_id: uuid.UUID | None = None
    text: str | None = None


class ProofreadDiff(BaseModel):
    original: str
    corrected: str
    changes: list[dict[str, str]]  # [{type: "replace"|"insert"|"delete", before, after}]


class ProofreadResponse(BaseModel):
    job_id: str
    diff: ProofreadDiff
    download_url: str | None = None
