"""
Local web playground — a zero-dependency "canvas" to test traces.

`ninja-harness serve` starts a small local web app (Python standard library
only — no Flask/FastAPI) where you paste an agent trace (and an optional eval
case), click Evaluate, and see the certification, metric breakdown, and the
trajectory rendered inline. It reuses the exact same scoring pipeline and HTML
viewer as the CLI, so there is no second implementation to drift.

Security notes:
- Binds to 127.0.0.1 by default — it is a LOCAL developer tool, not a hosted
  service. Do not expose it to untrusted networks.
- It does not execute trace content; it only parses and scores it. All rendered
  content is HTML-escaped.
"""

from __future__ import annotations

import json
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import parse_qs

import yaml

from ninja_harness.adapters import detect_adapter
from ninja_harness.reporters import VIEWER_CSS, render_fragment
from ninja_harness.schemas import EvaluationCase
from ninja_harness.scoring.ninja_score import NinjaScoreAggregator

_FALLBACK_TRACE = {
    "agent_name": "DemoAgent",
    "task": "Summarize the benefits of retrieval-augmented generation.",
    "final_output": "RAG grounds answers in retrieved documents, reducing hallucination and enabling current, citable responses.",
    "steps": [{"agent_name": "DemoAgent", "step_type": "plan", "output": "Plan the summary."}],
    "tool_calls": [],
}


def _example_trace() -> str:
    """Load the bundled example trace, falling back to an inline sample."""
    try:
        text = files("ninja_harness").joinpath("examples/simple_agent_trace.json").read_text()
        json.loads(text)  # validate
        return text
    except Exception:  # noqa: BLE001 - playground convenience only
        return json.dumps(_FALLBACK_TRACE, indent=2)


def _parse_case(case_str: str) -> EvaluationCase | None:
    case_str = case_str.strip()
    if not case_str:
        return None
    try:
        data = json.loads(case_str)
    except json.JSONDecodeError:
        data = yaml.safe_load(case_str)
    return EvaluationCase.model_validate(data)


def evaluate_payload(trace_str: str, case_str: str = "") -> tuple[str, bool]:
    """
    Evaluate a pasted trace (+ optional case) and return (html_fragment, ok).

    On any parse/validation error, returns an escaped error card and ok=False.
    This is the testable core of the playground — no sockets involved.
    """
    if not trace_str.strip():
        return '<div class="card err">Paste a trace JSON to evaluate.</div>', False
    try:
        raw = json.loads(trace_str)
    except json.JSONDecodeError as exc:
        return f'<div class="card err">Invalid trace JSON: {escape(str(exc))}</div>', False

    try:
        run = detect_adapter(raw).parse(raw)
    except ValueError as exc:
        return f'<div class="card err">Could not parse trace: {escape(str(exc))}</div>', False

    try:
        case = _parse_case(case_str)
    except Exception as exc:  # noqa: BLE001 - surface a friendly message
        return f'<div class="card err">Invalid eval case: {escape(str(exc))}</div>', False

    result = NinjaScoreAggregator().evaluate(run, case)
    return render_fragment(run, result), True


def _page(trace_value: str, case_value: str, results_html: str = "") -> str:
    results_block = (
        f'<div class="results">{results_html}</div>' if results_html else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ninja Harness — Playground</title>
<style>{VIEWER_CSS}
.form-card {{ background:#1e293b; border:1px solid #334155; border-radius:10px; padding:16px; margin:12px 0; }}
textarea {{ width:100%; min-height:160px; background:#0b1120; color:#e2e8f0; border:1px solid #334155;
  border-radius:8px; padding:10px; font-family:ui-monospace,Menlo,monospace; font-size:13px; }}
label {{ display:block; color:#94a3b8; font-size:13px; margin:10px 0 4px; }}
button {{ background:#6366f1; color:#fff; border:0; padding:10px 18px; border-radius:8px; font-weight:700;
  font-size:14px; cursor:pointer; margin-top:12px; }}
button:hover {{ background:#4f46e5; }}
.err {{ border-color:#7f1d1d; color:#fca5a5; }}
.results {{ margin-top:8px; }}
</style></head>
<body><div class="wrap">
  <h1>🥷 Ninja Harness — Playground</h1>
  <div class="sub">Paste an agent trace (Custom JSON, OpenAI Agents, LangGraph, Hermes, CrewAI, AutoGen, or OpenTelemetry) and evaluate it. Local only.</div>
  <form class="form-card" method="POST" action="/evaluate">
    <label for="trace">Trace JSON</label>
    <textarea id="trace" name="trace">{escape(trace_value)}</textarea>
    <label for="case">Eval case (optional — YAML or JSON)</label>
    <textarea id="case" name="case" style="min-height:90px">{escape(case_value)}</textarea>
    <button type="submit">Evaluate &rarr;</button>
  </form>
  {results_block}
  <div class="foot">Local playground · github.com/gagans23/ninja-harness</div>
</div></body></html>"""


class PlaygroundHandler(BaseHTTPRequestHandler):
    """Serves the playground form (GET /) and evaluation results (POST /evaluate)."""

    def log_message(self, *args) -> None:  # silence default request logging
        pass

    def _send_html(self, body: str, status: int = 200) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        if self.path not in ("/", "/index.html"):
            self._send_html('<div class="card err">Not found.</div>', status=404)
            return
        self._send_html(_page(_example_trace(), ""))

    def do_POST(self) -> None:
        if self.path != "/evaluate":
            self._send_html('<div class="card err">Not found.</div>', status=404)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length else ""
        form = parse_qs(body, keep_blank_values=True)
        trace_value = form.get("trace", [""])[0]
        case_value = form.get("case", [""])[0]
        results_html, _ok = evaluate_payload(trace_value, case_value)
        self._send_html(_page(trace_value, case_value, results_html))


def run_server(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True) -> None:
    """Start the playground server (blocking)."""
    server = ThreadingHTTPServer((host, port), PlaygroundHandler)
    url = f"http://{host}:{port}/"
    if open_browser:
        try:
            import webbrowser

            webbrowser.open(url)
        except Exception:  # noqa: BLE001 - headless environments
            pass
    print(f"Ninja Harness playground running at {url}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
