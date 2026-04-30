"""Unit tests for the prompt loader and template contracts."""

from __future__ import annotations

import pytest

from app.core import prompt_loader


def test_action_guide_template_required_variables():
    out = prompt_loader.render(
        "action_guide",
        context="ctx",
        query="q",
    )
    assert "ctx" in out and "q" in out
    # contract: must mention 출처 (citation requirement)
    assert "출처" in out
    # fallback string per AI-09 AC
    assert "관련 매뉴얼을 찾지 못했습니다" in out


def test_anomaly_analysis_template_required_variables():
    out = prompt_loader.render(
        "anomaly_analysis",
        rule_result="r",
        sensor_log="s",
        context="c",
    )
    assert "r" in out and "s" in out and "c" in out
    assert "출처" in out


def test_missing_variable_raises():
    with pytest.raises(prompt_loader.PromptVariableError, match="query"):
        prompt_loader.render("action_guide", context="ctx")


def test_missing_template_raises():
    prompt_loader._load_template.cache_clear()
    with pytest.raises(FileNotFoundError):
        prompt_loader.render("does_not_exist", x=1)


def test_list_templates_includes_known():
    names = prompt_loader.list_templates()
    assert "action_guide" in names
    assert "anomaly_analysis" in names
