"""
Self-contained static HTML trace viewer.

Renders an AgentRun (and optional EvaluationResult) into a single, dependency-
free HTML file: no server, no external assets, no JavaScript libraries. Open it
in any browser to explore the trajectory.

All trace content is HTML-escaped before rendering, so untrusted trace text
cannot inject markup.
"""

from __future__ import annotations

from html import escape

from ninja_harness.schemas import AgentRun, EvaluationResult

_STEP_COLORS = {
    "plan": "#6366f1",
    "action": "#0ea5e9",
    "observation": "#10b981",
    "handoff": "#f59e0b",
    "guardrail": "#ef4444",
    "final": "#8b5cf6",
}
_CERT_COLORS = {"PASS": "#16a34a", "WARN": "#d97706", "FAIL": "#dc2626"}

_CSS = """
* { box-sizing: border-box; }
body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
.wrap { max-width: 960px; margin: 0 auto; padding: 24px; }
h1 { font-size: 20px; margin: 0 0 4px; }
.sub { color: #94a3b8; font-size: 13px; margin-bottom: 16px; }
.badge { display: inline-block; padding: 4px 10px; border-radius: 999px; color: #fff; font-weight: 700; font-size: 13px; }
.card { background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 14px 16px; margin: 12px 0; }
.metrics { width: 100%; border-collapse: collapse; font-size: 13px; }
.metrics td, .metrics th { padding: 6px 8px; border-bottom: 1px solid #334155; text-align: left; }
.metrics th { color: #94a3b8; font-weight: 600; }
.pass { color: #4ade80; } .fail { color: #f87171; } .skip { color: #64748b; }
.step { border-left: 3px solid #475569; padding: 8px 12px; margin: 8px 0; background: #16213a; border-radius: 0 8px 8px 0; }
.step .type { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; font-weight: 700; }
.step .who { color: #94a3b8; font-size: 12px; }
.step pre { white-space: pre-wrap; word-break: break-word; margin: 6px 0 0; font-size: 13px; color: #cbd5e1; }
.tool { background: #0b1120; border: 1px solid #334155; border-radius: 8px; padding: 8px 12px; margin: 6px 0; font-size: 13px; }
.tool .name { font-weight: 700; color: #38bdf8; }
.k { color: #94a3b8; }
.final { background: #052e2b; border: 1px solid #134e4a; }
.foot { color: #64748b; font-size: 12px; margin-top: 24px; text-align: center; }
"""


def _step_block(step) -> str:
    color = _STEP_COLORS.get(step.step_type, "#475569")
    status_cls = "fail" if step.status == "failed" else ""
    body = ""
    if step.input:
        body += f'<pre><span class="k">in:</span> {escape(step.input)}</pre>'
    if step.output:
        body += f"<pre>{escape(step.output)}</pre>"
    if step.error:
        body += f'<pre class="fail">error: {escape(step.error)}</pre>'
    return (
        f'<div class="step" style="border-left-color:{color}">'
        f'<span class="type" style="color:{color}">{escape(step.step_type)}</span> '
        f'<span class="who">· {escape(step.agent_name)} '
        f'<span class="{status_cls}">[{escape(step.status)}]</span></span>'
        f"{body}</div>"
    )


def _tool_block(tc) -> str:
    status_cls = "fail" if tc.status == "failed" else "pass"
    args = ", ".join(f"{escape(str(k))}={escape(str(v))}" for k, v in tc.arguments.items())
    result = f'<pre>{escape(tc.result)}</pre>' if tc.result else ""
    err = f'<pre class="fail">error: {escape(tc.error)}</pre>' if tc.error else ""
    return (
        f'<div class="tool"><span class="name">{escape(tc.tool_name)}</span> '
        f'<span class="{status_cls}">[{escape(tc.status)}]</span>'
        f'<div class="k">args: {args}</div>{result}{err}</div>'
    )


def _handoff_block(h) -> str:
    return (
        f'<div class="tool"><span class="name">{escape(h.source_agent)} → {escape(h.target_agent)}</span>'
        f'<div class="k">reason: {escape(h.reason)}</div>'
        f'<div class="k">context: {escape(h.context_summary)}</div>'
        f'<div class="k">next: {escape(h.expected_next_action)}</div></div>'
    )


def _metrics_table(result: EvaluationResult) -> str:
    rows = ""
    for m in result.metric_results:
        if not m.is_applicable:
            score, cls, status = "N/A", "skip", "SKIP"
        else:
            score, cls, status = f"{m.score:.3f}", ("pass" if m.passed else "fail"), ("PASS" if m.passed else "FAIL")
        finding = escape(m.failure_reasons[0]) if m.failure_reasons else ""
        rows += (
            f"<tr><td>{escape(m.name)}</td><td>{score}</td>"
            f'<td class="{cls}">{status}</td><td>{finding}</td></tr>'
        )
    return (
        '<table class="metrics"><tr><th>Metric</th><th>Score</th><th>Status</th><th>Finding</th></tr>'
        f"{rows}</table>"
    )


# Public alias so other modules (e.g. the web playground) can reuse the styles.
VIEWER_CSS = _CSS


def render_fragment(run: AgentRun, result: EvaluationResult | None = None) -> str:
    """
    Render just the trace content (cards), without the surrounding <html>/<style>
    wrapper. Useful for embedding the result inside another page (e.g. `serve`).
    """
    header_badge = ""
    metrics = ""
    if result is not None:
        color = _CERT_COLORS.get(result.certification, "#475569")
        header_badge = (
            f'<span class="badge" style="background:{color}">'
            f"{escape(result.certification)} · {result.ninja_score:.1f}/100 · {escape(result.grade)}</span>"
        )
        metrics = f'<div class="card"><h1>Metrics</h1>{_metrics_table(result)}</div>'

    steps_html = "".join(_step_block(s) for s in run.steps) or '<div class="k">No steps recorded.</div>'
    tools_html = "".join(_tool_block(t) for t in run.tool_calls)
    handoffs_html = "".join(_handoff_block(h) for h in run.handoffs)

    tools_section = f'<div class="card"><h1>Tool Calls ({len(run.tool_calls)})</h1>{tools_html}</div>' if run.tool_calls else ""
    handoffs_section = f'<div class="card"><h1>Handoffs ({len(run.handoffs)})</h1>{handoffs_html}</div>' if run.handoffs else ""

    return (
        f'<h1>🥷 {escape(run.agent_name)} {header_badge}</h1>'
        f'<div class="sub">Run <code>{escape(run.run_id)}</code> · {escape(run.task)}</div>'
        f"{metrics}"
        f'<div class="card"><h1>Trajectory ({len(run.steps)} steps)</h1>{steps_html}</div>'
        f"{tools_section}{handoffs_section}"
        f'<div class="card final"><h1>Final Output</h1><pre>{escape(run.final_output)}</pre></div>'
    )


def render_html(run: AgentRun, result: EvaluationResult | None = None) -> str:
    """Render a self-contained HTML page for a trace (+ optional evaluation)."""
    fragment = render_fragment(run, result)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ninja Harness — {escape(run.agent_name)}</title>
<style>{_CSS}</style></head>
<body><div class="wrap">
  {fragment}
  <div class="foot">Generated by Ninja Harness — github.com/gagans23/ninja-harness</div>
</div></body></html>"""
