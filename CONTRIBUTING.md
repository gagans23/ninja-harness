# Contributing to Ninja Harness

Thanks for your interest in improving Ninja Harness! This project is a
trace-first evaluation/certification harness for AI agents. Contributions of all
kinds are welcome — new adapters, metrics, docs, tests, and bug fixes.

## Ground rules (please read)

These come from [`CLAUDE.md`](CLAUDE.md) and keep the project credible:

- **Deterministic-first.** v0.x scoring must be reproducible and run without
  network calls or API keys. LLM-as-judge support is a pluggable interface — the
  model is supplied by the user, never bundled.
- **No fake integrations.** Don't add stubs that pretend to call an external
  service. Real integrations (Slack, Telegram, Docker) shell out / use stdlib and
  are configured by the user.
- **No unsupported benchmark claims.** Don't add leaderboard numbers or "beats X"
  statements. Dataset loaders read on-disk formats; we don't bundle datasets or
  publish scores.
- **Safety stays central.** Red-team checks are detection-only and defensive.
  Standards mappings (OWASP/MITRE) must use accurate, verifiable IDs.

## Development setup

Requires Python 3.11+.

```bash
git clone https://github.com/gagans23/ninja-harness.git
cd ninja-harness
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Before you open a PR

```bash
pytest -q            # all tests must pass
ruff check src/ tests/ examples/ scripts/   # lint must be clean
```

CI runs the same checks plus CLI smoke tests on Python 3.11/3.12.

## How we work

We follow the practices in **[docs/code-review.md](docs/code-review.md)** (adapted
from Google's engineering practices). The short version:

- **Small, self-contained changes** that do one thing (~100 lines is comfortable).
- **Tests in the same change** as the logic they cover (tests are expected for all
  changes); keep refactors separate from behavior changes.
- **Good descriptions:** an imperative first line that stands alone, a blank line,
  then a body explaining *why* (problem, approach, trade-offs, context).
- **Don't break the build** — keep `pytest` + `ruff` green.
- The reviewer's bar is **"does this definitely improve overall code health?"**,
  not perfection.

## How to add things

### A new framework adapter
1. Create `src/ninja_harness/adapters/<framework>.py` implementing `TraceAdapter`
   (`can_parse()` — cheap key-presence checks; `parse()` — pure, deterministic,
   raises `ValueError` on missing required fields).
2. Register it in `adapters/__init__.py` (`ADAPTER_REGISTRY`, `__all__`).
3. Add an example trace under `src/ninja_harness/examples/` and tests.

### A new metric
1. Create `src/ninja_harness/scoring/<metric>.py` subclassing `BaseScorer`.
2. Register it in `scoring/ninja_score.py`. If it should affect the composite
   NARI score, add it to `_WEIGHTS` (weights must sum to 1.0); otherwise leave it
   out of `_WEIGHTS` to report it separately (weight 0).
3. Add tests and document it in `docs/metrics.md`.

## Commit & PR style

- Conventional-ish messages: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`.
- Keep PRs focused. Open an issue first for large changes.
- Update docs and `CHANGELOG.md` when behavior changes.

## Reporting bugs / requesting features

Use the issue templates. For security issues, see [`SECURITY.md`](SECURITY.md)
(do **not** open a public issue for vulnerabilities).

By contributing, you agree your contributions are licensed under the project's
[Apache-2.0 license](LICENSE).
