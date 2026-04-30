"""Unit tests for the rule-engine portion of the anomaly pipeline.

LLM/DB-dependent paths are tested separately in integration."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.pipelines.anomaly import _SEVERITY_ORDER, evaluate_rules
from app.schemas.sensor_log import SensorLog


_RULES_FIXTURE = [
    {
        "rule_id": "temp-high",
        "equipment_id": "eq_test",
        "metric": "temperature_c",
        "operator": ">",
        "threshold": 75.0,
        "severity": "medium",
        "description": "temp over 75",
    },
    {
        "rule_id": "vib-high",
        "equipment_id": "eq_test",
        "metric": "vibration_mm_s",
        "operator": ">",
        "threshold": 4.0,
        "severity": "high",
        "description": "vib over 4",
    },
    {
        "rule_id": "current-overload",
        "equipment_id": "eq_test",
        "metric": "current_a",
        "operator": ">",
        "threshold": 22.0,
        "severity": "critical",
        "description": "current overload",
    },
    # Different equipment — must never fire for eq_test.
    {
        "rule_id": "other-eq-rule",
        "equipment_id": "eq_other",
        "metric": "temperature_c",
        "operator": ">",
        "threshold": 0.0,
        "severity": "low",
        "description": "noise",
    },
]


def _log(**readings) -> SensorLog:
    return SensorLog(
        equipment_id="eq_test",
        timestamp=datetime(2026, 4, 30, tzinfo=timezone.utc),
        readings=readings,
    )


def test_no_rule_fires_returns_normal():
    r = evaluate_rules(_log(temperature_c=60.0, vibration_mm_s=2.0), rules=_RULES_FIXTURE)
    assert r.is_anomaly is False
    assert r.severity is None
    assert r.triggered_rules == []


def test_single_rule_triggers():
    r = evaluate_rules(_log(temperature_c=80.0), rules=_RULES_FIXTURE)
    assert r.is_anomaly is True
    assert r.severity == "medium"
    assert [t.rule_id for t in r.triggered_rules] == ["temp-high"]


def test_multiple_rules_aggregate_max_severity():
    r = evaluate_rules(
        _log(temperature_c=80.0, vibration_mm_s=5.0, current_a=25.0),
        rules=_RULES_FIXTURE,
    )
    assert r.is_anomaly is True
    # critical > high > medium
    assert r.severity == "critical"
    rule_ids = {t.rule_id for t in r.triggered_rules}
    assert rule_ids == {"temp-high", "vib-high", "current-overload"}


def test_rules_for_other_equipment_are_ignored():
    r = evaluate_rules(_log(temperature_c=80.0), rules=_RULES_FIXTURE)
    assert all(t.rule_id != "other-eq-rule" for t in r.triggered_rules)


def test_missing_metric_does_not_trigger():
    # vibration not provided — vib-high rule must not fire.
    r = evaluate_rules(_log(temperature_c=80.0), rules=_RULES_FIXTURE)
    assert all(t.rule_id != "vib-high" for t in r.triggered_rules)


def test_severity_order_constants():
    # Sanity: severity ordering must be strict and ascending.
    levels = ["low", "medium", "high", "critical"]
    values = [_SEVERITY_ORDER[s] for s in levels]
    assert values == sorted(values)
    assert len(set(values)) == len(values)


def test_unknown_operator_raises():
    bad_rules = [
        {
            "rule_id": "bad",
            "equipment_id": "eq_test",
            "metric": "x",
            "operator": "~~",
            "threshold": 0.0,
            "severity": "low",
            "description": "bad",
        }
    ]
    # We test the in-memory path: evaluate_rules accepts pre-loaded rules
    # and skips operator validation (validation lives in _load_rules).
    # So just confirm: evaluate_rules will raise KeyError on the unknown op.
    with pytest.raises(KeyError):
        evaluate_rules(_log(x=1.0), rules=bad_rules)
