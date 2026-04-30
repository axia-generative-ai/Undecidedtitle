"""Unit tests for the AI-16 cache-fallback paths in RagPipeline.

Exercises `_cache_lookup` and `_cached_response` directly so the test
doesn't need a live DB or Ollama.
"""

from __future__ import annotations

import json

import pytest

from app.pipelines import rag as rag_module
from app.pipelines.rag import RagPipeline


def _bare_pipeline() -> RagPipeline:
    # bypass build() because we don't need real backends here
    return RagPipeline.__new__(RagPipeline)


@pytest.fixture
def cache_file(tmp_path, monkeypatch):
    payload = {
        "E-204": {
            "error_code": "E-204",
            "equipment_id": "eq_pv300",
            "answer_text": "1. 압축기 점검",
            "steps": [
                {
                    "order": 1,
                    "action": "압축기 점검",
                    "source": {"manual": "pv300_manual.pdf", "page": 12},
                }
            ],
            "raw_chunks": [
                {
                    "chunk_id": "abc",
                    "manual_id": "pv300_manual",
                    "equipment_id": "eq_pv300",
                    "page": 12,
                    "chunk_text": "샘플",
                    "similarity": 0.9,
                }
            ],
        }
    }
    p = tmp_path / "cached_responses.json"
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(rag_module, "CACHED_RESPONSES_PATH", p)
    return p


def test_cache_lookup_hit_by_error_code(cache_file):
    p = _bare_pipeline()
    hit = p._cache_lookup("E-204 코드 났는데 어떻게 조치하지?")
    assert hit is not None
    assert hit["error_code"] == "E-204"


def test_cache_lookup_miss_when_no_code_in_query(cache_file):
    p = _bare_pipeline()
    assert p._cache_lookup("뭔가 이상해요") is None


def test_cache_lookup_miss_when_code_unknown(cache_file):
    p = _bare_pipeline()
    assert p._cache_lookup("E-999 발생") is None


def test_cache_lookup_no_file(monkeypatch, tmp_path):
    # Point at a path that doesn't exist.
    monkeypatch.setattr(
        rag_module,
        "CACHED_RESPONSES_PATH",
        tmp_path / "definitely-missing.json",
    )
    p = _bare_pipeline()
    assert p._cache_lookup("E-204") is None


def test_cached_response_marks_reason(cache_file):
    p = _bare_pipeline()
    cached = p._cache_lookup("E-204 코드")
    resp = p._cached_response(cached, t0=0.0, reason="llm_unreachable")
    assert "[cached: llm_unreachable]" in resp.answer_text
    assert resp.fallback is False  # we have a parsed step
    assert len(resp.steps) == 1
    assert resp.steps[0].source.manual == "pv300_manual.pdf"
