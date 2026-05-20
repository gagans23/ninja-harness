"""
Reproducibility manifests.

Captures provenance for a run so it can be audited or reproduced: harness
version, Python/platform, key package versions, git SHA (best effort), the seed
used, and a content hash of the captured trace.

Note: the harness can set a process seed and record the environment, but it
cannot force determinism of an external LLM-backed agent. The manifest is an
honest record of the conditions, not a guarantee of bit-for-bit reproduction.
"""

from __future__ import annotations

import hashlib
import platform
import subprocess
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version

from ninja_harness import __version__
from ninja_harness.schemas import AgentRun, RunManifest

_TRACKED_PACKAGES = ["pydantic", "typer", "rich", "pyyaml"]


def _git_sha() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        sha = out.stdout.strip()
        return sha or None
    except (subprocess.SubprocessError, OSError):
        return None


def _package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for pkg in _TRACKED_PACKAGES:
        try:
            versions[pkg] = version(pkg)
        except PackageNotFoundError:
            continue
    return versions


def trace_hash(run: AgentRun) -> str:
    """Stable SHA-256 over the canonical JSON of the trace."""
    canonical = run.model_dump_json()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_manifest(
    run: AgentRun,
    solver: str,
    sandbox: str,
    seed: int | None = None,
) -> RunManifest:
    """Assemble a RunManifest for a completed run."""
    return RunManifest(
        ninja_harness_version=__version__,
        python_version=platform.python_version(),
        platform=platform.platform(),
        created_at=datetime.now(UTC),
        solver=solver,
        sandbox=sandbox,
        seed=seed,
        git_sha=_git_sha(),
        trace_sha256=trace_hash(run),
        package_versions=_package_versions(),
    )
