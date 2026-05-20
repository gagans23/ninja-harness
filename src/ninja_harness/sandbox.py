"""
Sandbox abstraction for isolated command execution.

Agents that execute code or shell commands should run inside a sandbox so the
harness can bound time, capture output, and (with Docker) isolate the host.

Two implementations ship:
- LocalSandbox: runs commands as host subprocesses with a timeout. Convenient
  for development; NOT isolation from the host.
- DockerSandbox: runs commands inside a container via the `docker` CLI. Provides
  real host isolation. Raises a clear error if `docker` is unavailable.

This is deliberately a thin, dependency-free layer (no docker SDK). It shells
out to the `docker` binary so there is nothing to fake.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class SandboxResult:
    """Outcome of a sandboxed command execution."""

    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class Sandbox:
    """Base sandbox interface."""

    name = "base"

    def exec(
        self,
        command: list[str],
        stdin: str | None = None,
        timeout: float = 60.0,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:  # pragma: no cover - abstract
        raise NotImplementedError


class LocalSandbox(Sandbox):
    """Runs commands as host subprocesses with a timeout. No host isolation."""

    name = "local"

    def __init__(self, cwd: str | None = None) -> None:
        self._cwd = cwd

    def exec(
        self,
        command: list[str],
        stdin: str | None = None,
        timeout: float = 60.0,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        try:
            proc = subprocess.run(
                command,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self._cwd,
                env=env,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return SandboxResult(
                stdout=exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                stderr=exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
                exit_code=124,
                timed_out=True,
            )
        return SandboxResult(
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            exit_code=proc.returncode,
        )


class DockerSandbox(Sandbox):
    """
    Runs commands inside a container via the `docker` CLI for host isolation.

    Raises RuntimeError immediately if `docker` is not on PATH — there is no
    silent fallback to local execution (that would defeat isolation).
    """

    name = "docker"

    def __init__(self, image: str = "python:3.11-slim", workdir: str = "/work") -> None:
        if shutil.which("docker") is None:
            raise RuntimeError(
                "DockerSandbox requires the `docker` CLI on PATH. Install Docker, "
                "or use sandbox='local'. There is no silent fallback."
            )
        self._image = image
        self._workdir = workdir

    def exec(
        self,
        command: list[str],
        stdin: str | None = None,
        timeout: float = 60.0,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        docker_cmd = ["docker", "run", "--rm", "-i", "--network", "none", "-w", self._workdir]
        for key, value in (env or {}).items():
            docker_cmd += ["-e", f"{key}={value}"]
        docker_cmd += [self._image, *command]

        try:
            proc = subprocess.run(
                docker_cmd,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(stdout="", stderr="docker run timed out", exit_code=124, timed_out=True)
        return SandboxResult(
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            exit_code=proc.returncode,
        )


def make_sandbox(kind: str, image: str | None = None) -> Sandbox | None:
    """Factory: 'none' -> None, 'local' -> LocalSandbox, 'docker' -> DockerSandbox."""
    if kind == "none":
        return None
    if kind == "local":
        return LocalSandbox()
    if kind == "docker":
        return DockerSandbox(image=image or "python:3.11-slim")
    raise ValueError(f"Unknown sandbox kind: {kind!r} (expected none | local | docker)")
