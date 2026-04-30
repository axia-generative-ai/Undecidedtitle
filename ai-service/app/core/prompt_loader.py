"""Prompt template loader.

Reads `.txt` templates from `app/core/prompts/` and renders them with
`{variable}` interpolation. Missing variables raise a clear error so a
silent prompt drift cannot make it to production.
"""

from __future__ import annotations

import string
from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class PromptVariableError(KeyError):
    """Raised when a required {variable} is not supplied."""


class _StrictFormatter(string.Formatter):
    def get_value(self, key, args, kwargs):
        try:
            return super().get_value(key, args, kwargs)
        except (IndexError, KeyError) as exc:
            raise PromptVariableError(f"missing prompt variable: {key!r}") from exc


_FMT = _StrictFormatter()


@lru_cache(maxsize=None)
def _load_template(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


def render(name: str, /, **variables: object) -> str:
    """Render a prompt template by name with {var} interpolation."""
    template = _load_template(name)
    return _FMT.format(template, **variables)


def list_templates() -> list[str]:
    return sorted(p.stem for p in PROMPTS_DIR.glob("*.txt"))
