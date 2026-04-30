"""Emit tests/eval/test_set.json from error_codes.json + per-code paraphrases.

Why: AI-05 requires (a) one case per error code (>= 20) and (b) at least
5 natural-language paraphrases that don't quote the raw code. We keep the
paraphrase pool here so it stays in lockstep with the code list.

Run:
    uv run python scripts/build_eval_set.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ERR = ROOT / "data" / "error_codes.json"
OUT = ROOT / "tests" / "eval" / "test_set.json"


# 5 paraphrases that intentionally do NOT quote the error code.
# Each maps to one specific record in error_codes.json by (equipment_id, code).
PARAPHRASES: list[dict[str, str]] = [
    {
        "equipment_id": "eq_pv300",
        "error_code": "E-204",
        "natural_language_query": "PV-300 밸브가 OPEN 명령에 늦게 반응하는데 어떻게 조치해야 하나요?",
        "notes": "Paraphrase for E-204 (response timeout). Avoids the raw code.",
    },
    {
        "equipment_id": "eq_cv550",
        "error_code": "E-302",
        "natural_language_query": "컨베이어 모터에서 진동이 4mm/s 이상 측정됩니다. 점검 절차 알려주세요.",
        "notes": "Paraphrase for E-302 (bearing vibration).",
    },
    {
        "equipment_id": "eq_hp120",
        "error_code": "E-402",
        "natural_language_query": "유압 프레스 작동유 온도가 70도를 넘었습니다. 무엇부터 확인해야 하죠?",
        "notes": "Paraphrase for E-402 (oil overheat).",
    },
    {
        "equipment_id": "eq_rb900",
        "error_code": "E-501",
        "natural_language_query": "협동 로봇이 갑자기 멈추면서 충돌 알람이 떴습니다. 안전 리셋 절차?",
        "notes": "Paraphrase for E-501 (collision detected).",
    },
    {
        "equipment_id": "eq_cn450",
        "error_code": "E-601",
        "natural_language_query": "CNC 주축에 부하가 과도하게 걸린다고 표시됩니다. 절삭 조건을 어떻게 조정?",
        "notes": "Paraphrase for E-601 (spindle overload).",
    },
]


def main() -> None:
    if not ERR.exists():
        raise SystemExit(f"missing {ERR}. Run scripts/build_error_codes.py first.")
    records = json.loads(ERR.read_text(encoding="utf-8"))

    # by (equipment_id, code)
    by_key = {(r["equipment_id"], r["code"]): r for r in records}

    cases = []

    # 1) one literal-code case per error code
    for i, r in enumerate(records, start=1):
        cases.append(
            {
                "id": f"eval_{i:03d}",
                "error_code": r["code"],
                "equipment_id": r["equipment_id"],
                "natural_language_query": f"{r['code']} 코드가 떴습니다. 어떻게 조치하나요?",
                "expected_manual_id": Path(r["manual_filename"]).stem,
                "expected_manual_filename": r["manual_filename"],
                "expected_pages": r["expected_pages"],
                "notes": f"Direct code lookup for {r['code']} ({r['description']}).",
            }
        )

    # 2) paraphrase cases — append after the literal block so IDs don't collide
    next_id = len(cases) + 1
    for p in PARAPHRASES:
        r = by_key[(p["equipment_id"], p["error_code"])]
        cases.append(
            {
                "id": f"eval_{next_id:03d}",
                "error_code": r["code"],
                "equipment_id": r["equipment_id"],
                "natural_language_query": p["natural_language_query"],
                "expected_manual_id": Path(r["manual_filename"]).stem,
                "expected_manual_filename": r["manual_filename"],
                "expected_pages": r["expected_pages"],
                "notes": p["notes"],
            }
        )
        next_id += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  wrote {OUT.relative_to(ROOT)}  ({len(cases)} cases, {len(PARAPHRASES)} paraphrases)")


if __name__ == "__main__":
    main()
