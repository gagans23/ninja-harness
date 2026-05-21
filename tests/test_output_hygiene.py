"""Tests for the Output Hygiene metric."""

from __future__ import annotations

from ninja_harness.schemas import AgentRun
from ninja_harness.scoring.output_hygiene import OutputHygieneScorer


def run_with(output: str) -> AgentRun:
    return AgentRun(agent_name="A", task="t", final_output=output)


def test_clean_concise_answer_scores_high() -> None:
    scorer = OutputHygieneScorer()
    result = scorer.score(run_with("Tokyo's population is about 14 million."))
    assert result.score >= 0.9
    assert result.passed


def test_noisy_logs_score_low() -> None:
    noisy = (
        "WARNING: deprecated API\n"
        "ERROR: connection reset\n"
        "Traceback (most recent call last):\n"
        '  File "x.py", line 10\n'
        "DeprecationWarning: old\n"
        "2026-05-21 10:00:00 fetched\n"
        "Here are 12 headlines: https://a.com https://b.com https://c.com https://d.com"
    )
    scorer = OutputHygieneScorer()
    result = scorer.score(run_with(noisy))
    assert result.score < 0.7
    assert not result.passed
    assert result.failure_reasons
    assert result.recommendations


def test_ansi_codes_penalized() -> None:
    scorer = OutputHygieneScorer()
    result = scorer.score(run_with("\x1b[31mERROR\x1b[0m something failed"))
    assert result.details["signals"]["ansi_codes"] >= 1
    assert result.score < 1.0


def test_duplicate_lines_detected() -> None:
    scorer = OutputHygieneScorer()
    dup = "line\nline\nline\nline\n"
    result = scorer.score(run_with(dup))
    assert result.details["signals"]["duplicate_lines"] >= 2


def test_very_long_output_penalized() -> None:
    scorer = OutputHygieneScorer()
    long_text = "word " * 1000  # ~5000 chars
    result = scorer.score(run_with(long_text))
    assert result.score < 1.0


def test_empty_output_not_applicable() -> None:
    scorer = OutputHygieneScorer()
    result = scorer.score(run_with("   "))
    assert result.score == -1.0


def test_not_weighted_in_composite() -> None:
    scorer = OutputHygieneScorer()
    result = scorer.score(run_with("WARNING: x"))
    assert result.details["weighted_in_composite"] is False
