"""Unit tests for the vectorstore helpers that don't require a live DB."""

from __future__ import annotations

from app.core.vectorstore import SearchResult, _normalise_dsn


def test_normalise_dsn_strips_sqlalchemy_prefix():
    assert (
        _normalise_dsn("postgresql+psycopg://u:p@h:5432/d")
        == "postgresql://u:p@h:5432/d"
    )
    assert (
        _normalise_dsn("postgresql+psycopg2://u:p@h:5432/d")
        == "postgresql://u:p@h:5432/d"
    )


def test_normalise_dsn_passes_bare_url_through():
    assert _normalise_dsn("postgresql://u:p@h/d") == "postgresql://u:p@h/d"


def test_search_result_similarity():
    r = SearchResult(
        chunk_id="x",
        manual_id="m",
        equipment_id="e",
        page=1,
        chunk_index=0,
        chunk_text="t",
        distance=0.2,
    )
    assert abs(r.similarity - 0.8) < 1e-9
