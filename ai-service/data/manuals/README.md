# Equipment Manuals (synthetic)


These 5 PDFs are generated programmatically by `scripts/generate_manuals.py`.
Content is synthetic (no copyrighted material) and pinned so the AI-05
evaluation set can reference exact page numbers.

| Equipment | Equipment ID | Manual file | Pages | Source / License |
|---|---|---|---|---|
| 공압 밸브 PV-300 | `eq_pv300` | `pv300_manual.pdf` | 15 | Synthetic (FactoryGuard internal, MIT for project use) |
| 컨베이어 모터 CV-550 | `eq_cv550` | `cv550_manual.pdf` | 15 | Synthetic (FactoryGuard internal, MIT for project use) |
| 유압 프레스 HP-120 | `eq_hp120` | `hp120_manual.pdf` | 15 | Synthetic (FactoryGuard internal, MIT for project use) |
| 협동 로봇 RB-900 | `eq_rb900` | `rb900_manual.pdf` | 15 | Synthetic (FactoryGuard internal, MIT for project use) |
| CNC 머시닝센터 CN-450 | `eq_cn450` | `cn450_manual.pdf` | 15 | Synthetic (FactoryGuard internal, MIT for project use) |

## Regenerate

```bash
uv run python scripts/generate_manuals.py
```

Regeneration is deterministic — same inputs produce the same PDFs.
