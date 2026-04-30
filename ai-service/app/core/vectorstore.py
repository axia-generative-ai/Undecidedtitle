"""pgvector-backed vectorstore for manual chunks.

Uses psycopg directly rather than SQLAlchemy because the queries we need
are narrow (insert + cosine-similarity Top-K) and the pgvector adapter is
straightforward.

Connection strings are read from `Settings.database_url`. We accept both
SQLAlchemy-style (`postgresql+psycopg://...`) and bare (`postgresql://...`)
URLs and normalise to the bare form for psycopg.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import Settings, get_settings
from app.pipelines.chunking import Chunk

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    manual_id: str
    equipment_id: str
    page: int
    chunk_index: int
    chunk_text: str
    distance: float

    @property
    def similarity(self) -> float:
        # pgvector cosine distance is 1 - cosine_similarity.
        return 1.0 - self.distance


def _normalise_dsn(url: str) -> str:
    """Strip SQLAlchemy-style driver prefix for psycopg."""
    if url.startswith("postgresql+psycopg://"):
        return "postgresql://" + url.split("://", 1)[1]
    if url.startswith("postgresql+psycopg2://"):
        return "postgresql://" + url.split("://", 1)[1]
    return url


class VectorStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._dsn = _normalise_dsn(self.settings.database_url)

    # ----- helpers -----

    def _connect(self) -> psycopg.Connection:
        conn = psycopg.connect(self._dsn, autocommit=True)
        register_vector(conn)
        return conn

    # ----- write -----

    def insert_chunks(self, pairs: Iterable[tuple[Chunk, list[float]]]) -> int:
        """Bulk insert (chunk, vector) pairs. Returns rows inserted."""
        rows = [
            (
                c.chunk_id,
                c.manual_id,
                c.equipment_id,
                c.page,
                c.chunk_index,
                c.chunk_text,
                vec,
                Jsonb({"source_file": c.source_file}),
            )
            for c, vec in pairs
        ]
        if not rows:
            return 0
        with self._connect() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO manual_chunks
                    (id, manual_id, equipment_id, page, chunk_index,
                     chunk_text, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                rows,
            )
        logger.info("inserted chunks", extra={"count": len(rows)})
        return len(rows)

    def truncate(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE manual_chunks")

    # ----- read -----

    def similarity_search(
        self,
        query_vector: list[float],
        *,
        k: int | None = None,
        equipment_id: str | None = None,
    ) -> list[SearchResult]:
        """Return Top-K chunks by cosine distance, optionally scoped."""
        k = k or self.settings.retrieval_top_k
        # Cast the bind parameter to `vector` explicitly. psycopg's default
        # adapter sends Python lists as `double precision[]`, and pgvector's
        # `<=>` operator has no overload for that type — leading to
        # "operator does not exist: vector <=> double precision[]".
        sql = """
            SELECT id::text AS chunk_id,
                   manual_id, equipment_id, page, chunk_index, chunk_text,
                   embedding <=> %s::vector AS distance
              FROM manual_chunks
             {where}
          ORDER BY embedding <=> %s::vector
             LIMIT %s
        """
        params: list[Any]
        if equipment_id:
            sql = sql.format(where="WHERE equipment_id = %s")
            params = [query_vector, equipment_id, query_vector, k]
        else:
            sql = sql.format(where="")
            params = [query_vector, query_vector, k]

        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [SearchResult(**r) for r in rows]

    # ----- diagnostics -----

    def count(self) -> int:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM manual_chunks")
            (n,) = cur.fetchone()
            return n
