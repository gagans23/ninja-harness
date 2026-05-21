"""Tests for the local web playground (`serve`)."""

from __future__ import annotations

import socket
import threading
import time
import urllib.parse
import urllib.request

from ninja_harness.serve import (
    PlaygroundHandler,
    _example_trace,
    evaluate_payload,
    run_server,
)

# --------------------------------------------------------------------------
# evaluate_payload — the testable core (no sockets)
# --------------------------------------------------------------------------

def test_example_trace_is_valid_json() -> None:
    import json

    json.loads(_example_trace())  # must not raise


def test_evaluate_payload_success() -> None:
    html, ok = evaluate_payload(_example_trace(), "")
    assert ok is True
    assert "badge" in html  # certification badge rendered
    assert "Trajectory" in html


def test_evaluate_payload_empty_trace() -> None:
    html, ok = evaluate_payload("", "")
    assert ok is False
    assert "Paste a trace" in html


def test_evaluate_payload_bad_json() -> None:
    html, ok = evaluate_payload("{not json", "")
    assert ok is False
    assert "Invalid trace JSON" in html


def test_evaluate_payload_unparseable_trace() -> None:
    # Valid JSON, but no adapter can parse it.
    html, ok = evaluate_payload('{"foo": "bar"}', "")
    assert ok is False
    assert "Could not parse trace" in html


def test_evaluate_payload_with_yaml_case() -> None:
    trace = _example_trace()
    case_yaml = "case_id: c1\ntask: t\nexpected_output: research agent summary\n"
    html, ok = evaluate_payload(trace, case_yaml)
    assert ok is True
    assert "Metrics" in html


def test_evaluate_payload_bad_case() -> None:
    html, ok = evaluate_payload(_example_trace(), "not: : valid: yaml: :")
    assert ok is False
    assert "Invalid eval case" in html


def test_evaluate_payload_escapes_content() -> None:
    trace = '{"agent_name": "A", "task": "t", "final_output": "<script>alert(1)</script>"}'
    html, ok = evaluate_payload(trace, "")
    assert ok is True
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


# --------------------------------------------------------------------------
# Live server integration
# --------------------------------------------------------------------------

def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_handler_exists() -> None:
    assert issubclass(PlaygroundHandler, object)


def test_live_server_get_and_post() -> None:
    port = _free_port()
    thread = threading.Thread(
        target=run_server,
        kwargs={"host": "127.0.0.1", "port": port, "open_browser": False},
        daemon=True,
    )
    thread.start()
    time.sleep(0.4)

    # GET / serves the form
    get_body = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5).read().decode()
    assert "<textarea" in get_body
    assert "Evaluate" in get_body

    # POST /evaluate returns results
    data = urllib.parse.urlencode({"trace": _example_trace(), "case": ""}).encode()
    post_body = urllib.request.urlopen(
        f"http://127.0.0.1:{port}/evaluate", data=data, timeout=5
    ).read().decode()
    assert "Trajectory" in post_body
    assert "badge" in post_body


def test_live_server_404() -> None:
    port = _free_port()
    thread = threading.Thread(
        target=run_server,
        kwargs={"host": "127.0.0.1", "port": port, "open_browser": False},
        daemon=True,
    )
    thread.start()
    time.sleep(0.4)

    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/nope", timeout=5)
        raised = False
    except urllib.error.HTTPError as exc:
        raised = exc.code == 404
    assert raised
