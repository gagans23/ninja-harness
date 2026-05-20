"""Tests for reproducibility manifests."""

from __future__ import annotations

from ninja_harness.provenance import build_manifest, trace_hash
from ninja_harness.schemas import AgentRun


def make_run(output: str = "done") -> AgentRun:
    return AgentRun(run_id="r", agent_name="A", task="t", final_output=output)


def test_trace_hash_is_deterministic() -> None:
    run = make_run()
    assert trace_hash(run) == trace_hash(run)
    assert len(trace_hash(run)) == 64


def test_trace_hash_changes_with_content() -> None:
    assert trace_hash(make_run("a")) != trace_hash(make_run("b"))


def test_build_manifest_fields() -> None:
    manifest = build_manifest(make_run(), solver="scripted", sandbox="none", seed=11)
    assert manifest.solver == "scripted"
    assert manifest.sandbox == "none"
    assert manifest.seed == 11
    assert manifest.ninja_harness_version
    assert manifest.python_version
    assert manifest.platform
    assert len(manifest.trace_sha256) == 64


def test_build_manifest_tracks_packages() -> None:
    manifest = build_manifest(make_run(), solver="s", sandbox="none")
    assert "pydantic" in manifest.package_versions
