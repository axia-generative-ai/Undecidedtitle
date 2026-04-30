"""Request/response models for the action-guide search endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Error code or natural-language question.")
    equipment_id: str | None = Field(
        default=None,
        description="Optional scope filter; matches data/error_codes.json equipment_id.",
    )
    top_k: int | None = Field(default=None, ge=1, le=20)


class SourceRef(BaseModel):
    manual: str
    page: int


class GuideStep(BaseModel):
    order: int
    action: str
    source: SourceRef | None = None


class RawChunk(BaseModel):
    chunk_id: str
    manual_id: str
    equipment_id: str
    page: int
    chunk_text: str
    similarity: float


class SearchResponse(BaseModel):
    steps: list[GuideStep]
    raw_chunks: list[RawChunk]
    answer_text: str
    fallback: bool
    latency_ms: int
