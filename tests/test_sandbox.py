"""Tests for the sandbox abstraction."""

from __future__ import annotations

import shutil
import sys

import pytest

from ninja_harness.sandbox import DockerSandbox, LocalSandbox, make_sandbox


def test_local_sandbox_runs_command() -> None:
    sb = LocalSandbox()
    result = sb.exec([sys.executable, "-c", "print('hello')"])
    assert result.ok
    assert "hello" in result.stdout
    assert result.exit_code == 0


def test_local_sandbox_captures_nonzero_exit() -> None:
    sb = LocalSandbox()
    result = sb.exec([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert result.exit_code == 3
    assert not result.ok


def test_local_sandbox_stdin() -> None:
    sb = LocalSandbox()
    result = sb.exec([sys.executable, "-c", "import sys; print(sys.stdin.read().upper())"], stdin="abc")
    assert "ABC" in result.stdout


def test_local_sandbox_timeout() -> None:
    sb = LocalSandbox()
    result = sb.exec([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.5)
    assert result.timed_out
    assert not result.ok


def test_make_sandbox_none() -> None:
    assert make_sandbox("none") is None


def test_make_sandbox_local() -> None:
    assert isinstance(make_sandbox("local"), LocalSandbox)


def test_make_sandbox_invalid() -> None:
    with pytest.raises(ValueError):
        make_sandbox("bogus")


def test_docker_sandbox_requires_docker() -> None:
    if shutil.which("docker") is None:
        with pytest.raises(RuntimeError, match="docker"):
            DockerSandbox()
    else:
        pytest.skip("docker present; skipping absence test.")
