"""Apply migrations against the configured database.

Detects the embedding dimension by probing the configured embedder,
substitutes it into the SQL template, and runs each migration file
in lexicographic order.

Run:
    uv run python scripts/init_db.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import psycopg

from app.config import get_settings
from app.core.vectorstore import _normalise_dsn
from app.pipelines.embedding import embedding_dimension

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"

logging.basicConfig(level="INFO", format="%(levelname)s %(message)s")
log = logging.getLogger("init_db")


def main() -> None:
    settings = get_settings()
    dim = embedding_dimension()
    log.info("embedding dimension probed: %d", dim)

    dsn = _normalise_dsn(settings.database_url)
    with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
        for sql_file in sorted(MIGRATIONS.glob("*.sql")):
            log.info("applying %s", sql_file.name)
            sql = sql_file.read_text(encoding="utf-8").replace(
                "__EMBEDDING_DIM__", str(dim)
            )
            cur.execute(sql)
        cur.execute(
            "SELECT extversion FROM pg_extension WHERE extname='vector'"
        )
        row = cur.fetchone()
        log.info("pgvector version: %s", row[0] if row else "missing")
        cur.execute("SELECT COUNT(*) FROM manual_chunks")
        (n,) = cur.fetchone()
        log.info("manual_chunks rows: %d", n)


if __name__ == "__main__":
    main()
