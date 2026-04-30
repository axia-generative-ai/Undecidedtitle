"""Unit tests for the RAG step parser (no LLM/DB calls)."""

from __future__ import annotations

from app.pipelines.rag import RagPipeline


def _parser_only():
    # construct without calling .build() so we don't touch external services
    return RagPipeline.__new__(RagPipeline)


def test_parse_steps_with_citations():
    text = (
        "1. 공기 압력 게이지를 확인합니다. (출처: pv300_manual.pdf, p.7)\n"
        "2. 압축기 출력을 재기동합니다. (출처: pv300_manual.pdf, p.8)\n"
        "3. 라인 누설을 점검합니다.\n"
    )
    steps = _parser_only()._parse_steps(text)
    assert len(steps) == 3
    assert steps[0].order == 1
    assert steps[0].source.manual == "pv300_manual.pdf"
    assert steps[0].source.page == 7
    assert steps[2].source is None  # citation absent => parsed as None


def test_parse_steps_handles_missing_citation_gracefully():
    text = "1. 안전 수칙을 확인하세요.\n2. 전원을 차단합니다.\n"
    steps = _parser_only()._parse_steps(text)
    assert [s.order for s in steps] == [1, 2]
    assert all(s.source is None for s in steps)


def test_parse_steps_ignores_non_numbered_prose():
    text = "안내: 다음 절차를 따르세요.\n1. 첫 단계입니다.\n"
    steps = _parser_only()._parse_steps(text)
    assert len(steps) == 1
    assert steps[0].action.startswith("첫 단계")
