"""POST /api/v1/anomaly — anomaly analysis endpoint."""

from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import APIRouter, HTTPException

from app.pipelines.anomaly import AnomalyPipeline
from app.schemas.sensor_log import AnomalyResponse, SensorLog

router = APIRouter(prefix="/api/v1", tags=["anomaly"])
log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _pipeline() -> AnomalyPipeline:
    return AnomalyPipeline.build()


@router.post("/anomaly", response_model=AnomalyResponse)
def analyze(payload: SensorLog) -> AnomalyResponse:
    try:
        return _pipeline().analyze(payload)
    except ConnectionError as exc:
        log.exception("LLM/embedding backend unreachable")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
