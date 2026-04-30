"""Emit data/error_codes.json from the same source-of-truth as the manuals.

Re-uses `scripts.generate_manuals.EQUIPMENTS` and the page index produced
by `generate_manuals.py` so the dataset, manuals, and eval set never drift.

Run:
    uv run python scripts/build_error_codes.py
"""

from __future__ import annotations

import json
from pathlib import Path

from generate_manuals import EQUIPMENTS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PAGE_INDEX = DATA / "manuals" / "_page_index.json"
OUT = DATA / "error_codes.json"
SCHEMA = DATA / "error_codes.schema.json"


def main() -> None:
    if not PAGE_INDEX.exists():
        raise SystemExit(
            f"missing {PAGE_INDEX}. Run scripts/generate_manuals.py first."
        )
    page_index = json.loads(PAGE_INDEX.read_text(encoding="utf-8"))

    records = []
    for eq in EQUIPMENTS:
        per_eq = page_index[eq.equipment_id]
        for ec in eq.error_codes:
            records.append(
                {
                    "code": ec.code,
                    "equipment_name": eq.equipment_name,
                    "equipment_id": eq.equipment_id,
                    "manual_filename": eq.filename,
                    "expected_pages": per_eq[ec.code],
                    "severity": ec.severity,
                    "description": ec.title,
                }
            )

    # sanity: 20 unique codes
    codes = [r["code"] for r in records]
    assert len(codes) == 20, f"expected 20 codes, got {len(codes)}"
    assert len(set(codes)) == 20, "duplicate codes detected"

    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  wrote {OUT.relative_to(ROOT)}  ({len(records)} records)")

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "FactoryGuard error code records",
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "code",
                "equipment_name",
                "equipment_id",
                "manual_filename",
                "expected_pages",
                "severity",
                "description",
            ],
            "properties": {
                "code": {"type": "string", "pattern": "^E-\\d{3}$"},
                "equipment_name": {"type": "string", "minLength": 1},
                "equipment_id": {"type": "string", "pattern": "^eq_[a-z0-9]+$"},
                "manual_filename": {"type": "string", "pattern": "\\.pdf$"},
                "expected_pages": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "integer", "minimum": 1},
                },
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "description": {"type": "string", "minLength": 1},
            },
        },
    }
    SCHEMA.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  wrote {SCHEMA.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
