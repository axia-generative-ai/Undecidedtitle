"""Unit tests for PDF chunking.

Builds a small in-memory PDF fixture so the test does not depend on the
generated manuals.
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from app.config import Settings
from app.pipelines.chunking import _split_text, chunk_pdf


def _make_fixture_pdf(tmp_path: Path) -> Path:
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((50, 80), "page-one " * 200, fontsize=10)
    p2 = doc.new_page()  # intentionally empty -> should be skipped
    p3 = doc.new_page()
    p3.insert_text((50, 80), "page-three content. " * 100, fontsize=10)
    out = tmp_path / "fixture.pdf"
    doc.save(str(out))
    doc.close()
    return out


def _settings(**overrides) -> Settings:
    base = dict(chunk_size=200, chunk_overlap=20)
    base.update(overrides)
    return Settings(**base)


def test_split_text_overlap():
    pieces = _split_text("abcdefghij", size=4, overlap=1)
    # step = 3 -> starts at 0, 3, 6, 9
    assert pieces == ["abcd", "defg", "ghij", "j"]


def test_split_text_invalid_overlap():
    with pytest.raises(ValueError):
        _split_text("abc", size=2, overlap=2)


def test_chunk_pdf_skips_empty_pages(tmp_path):
    pdf = _make_fixture_pdf(tmp_path)
    chunks = chunk_pdf(
        pdf,
        manual_id="fixture",
        equipment_id="eq_test",
        settings=_settings(),
    )
    pages = {c.page for c in chunks}
    assert pages == {1, 3}, f"page 2 must be skipped, got pages={pages}"


def test_chunk_pdf_metadata(tmp_path):
    pdf = _make_fixture_pdf(tmp_path)
    chunks = chunk_pdf(
        pdf,
        manual_id="fixture",
        equipment_id="eq_test",
        settings=_settings(),
    )
    assert chunks, "expected at least one chunk"
    first = chunks[0]
    assert first.manual_id == "fixture"
    assert first.equipment_id == "eq_test"
    assert first.source_file == "fixture.pdf"
    assert first.chunk_text  # non-empty
    # global chunk_index increases monotonically
    indexes = [c.chunk_index for c in chunks]
    assert indexes == sorted(indexes)
    assert len(set(c.chunk_id for c in chunks)) == len(chunks)


def test_chunk_pdf_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        chunk_pdf(
            tmp_path / "nope.pdf",
            manual_id="x",
            equipment_id="y",
            settings=_settings(),
        )
