"""POST /api/v1/search — action-guide generation endpoint."""

from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import APIRouter, HTTPException

from app.pipelines.rag import RagPipeline
from app.schemas.search import SearchRequest, SearchResponse

router = APIRouter(prefix="/api/v1", tags=["search"])
log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _pipeline() -> RagPipeline:
    return RagPipeline.build()


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    try:
        return _pipeline().search(
            req.query,
            equipment_id=req.equipment_id,
            top_k=req.top_k,
        )
    except ConnectionError as exc:
        log.exception("LLM/embedding backend unreachable")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
