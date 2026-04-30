"""Sensor-log payload schema (AI-11/AI-12).

Mirrors PRD §AI-11 example. `readings` is a free-form mapping from
metric name to numeric value so the same shape covers all 5 equipments
without per-equipment classes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SensorLog(BaseModel):
    equipment_id: str = Field(..., min_length=1)
    timestamp: datetime
    readings: dict[str, float] = Field(default_factory=dict)


# ---- rule engine output ----

Severity = Literal["low", "medium", "high", "critical"]


class TriggeredRule(BaseModel):
    rule_id: str
    metric: str
    operator: str  # ">", ">=", "<", "<=", "=="
    threshold: float
    observed: float
    severity: Severity
    description: str


class RuleResult(BaseModel):
    is_anomaly: bool
    severity: Severity | None = None  # max severity among triggered rules
    triggered_rules: list[TriggeredRule] = Field(default_factory=list)


# ---- LLM-stage output (AI-12) ----

class ManualReference(BaseModel):
    manual: str
    page: int


class AnomalyResponse(BaseModel):
    rule_result: RuleResult
    status: str            # "정상" | "주의" | "이상"
    probable_cause: str
    recommended_action: str
    related_error_codes: list[str] = Field(default_factory=list)
    manual_refs: list[ManualReference] = Field(default_factory=list)
    raw_answer: str
    latency_ms: int
