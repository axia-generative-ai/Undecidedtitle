"""PDF chunking with metadata preservation.

Default strategy: fixed-size character chunks with overlap, scoped to a
single page so a chunk's `page` is unambiguous. Chunk size and overlap
come from `app.config.Settings`.

Future work: semantic chunking (e.g., split on H1/H2 headings) can replace
the fixed-size step without changing the public surface (`chunk_pdf`).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

import fitz  # PyMuPDF

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    manual_id: str
    equipment_id: str
    page: int
    chunk_index: int
    chunk_text: str
    source_file: str

    def as_dict(self) -> dict:
        return asdict(self)


def _split_text(text: str, size: int, overlap: int) -> list[str]:
    """Naive fixed-size split with overlap. Does not break on word boundaries
    deliberately — Korean text doesn't always have spaces, and the embedding
    model handles partial-word boundaries fine."""
    if not text:
        return []
    if size <= 0:
        raise ValueError("chunk size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be in [0, size)")
    step = size - overlap
    pieces: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        pieces.append(text[i : i + size])
        i += step
    return pieces


def chunk_pdf(
    pdf_path: str | Path,
    *,
    manual_id: str,
    equipment_id: str,
    settings: Settings | None = None,
) -> list[Chunk]:
    """Extract text page by page and split into overlapping chunks."""
    settings = settings or get_settings()
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(path)

    chunks: list[Chunk] = []
    doc = fitz.open(str(path))
    try:
        chunk_index_global = 0
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text().strip()
            if not text:
                logger.warning(
                    "skip empty/OCR-failed page", extra={"file": path.name, "page": page_num + 1}
                )
                continue
            for piece in _split_text(text, settings.chunk_size, settings.chunk_overlap):
                chunks.append(
                    Chunk(
                        chunk_id=str(uuid.uuid4()),
                        manual_id=manual_id,
                        equipment_id=equipment_id,
                        page=page_num + 1,  # 1-indexed
                        chunk_index=chunk_index_global,
                        chunk_text=piece,
                        source_file=path.name,
                    )
                )
                chunk_index_global += 1
    finally:
        doc.close()

    logger.info(
        "chunked manual",
        extra={"file": path.name, "chunks": len(chunks), "manual_id": manual_id},
    )
    return chunks
