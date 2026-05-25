# Code review & engineering practices

> Adapted from [Google's Engineering Practices Documentation](https://github.com/google/eng-practices)
> (the Code Review Developer Guide), used under [CC-BY 3.0](https://creativecommons.org/licenses/by/3.0/),
> and tailored to Ninja Harness. "CL" (changelist) below means a pull request / commit.

These practices apply to **all our projects** (Ninja Harness and
[agent-os](https://github.com/gagans23/agent-os)). They exist to keep one thing
true over time: **the overall code health of the project improves with every
change.**

## The standard

> **Approve a change once it *definitely improves the overall code health* of the
> system — even if it isn't perfect.**

This is the senior principle. There is no "perfect" code, only *better* code.
Reviewers seek **continuous improvement**, not perfection, and don't block a
change that improves maintainability and readability over days of polishing. The
mirror rule: **never merge a change that worsens overall code health** (except a
genuine emergency).

- **Technical facts and data overrule opinions and personal preferences.**
- **Design is not a style preference** — weigh it on engineering principles; if
  approaches are demonstrably equally valid, the author's choice wins.
- **Style is what the linter says** (`ruff`). Anything it doesn't cover is
  preference — stay consistent with surrounding code.
- Mark optional polish with **"Nit:"**; mark purely educational comments as
  non-blocking.

## What to look for

- **Design** — fits the architecture? (trace → adapters → scorers → NARI →
  certification; judges/solvers/sandboxes are pluggable interfaces.)
- **Functionality** — does it do what's intended; is that good for users?
- **Complexity** — can it be simpler? Will the next person understand it?
- **Tests** — correct, well-designed, and **in the same change**.
- **Naming / Comments** — clear names; comments explain *why*.
- **Style** — `ruff check` is clean; type hints everywhere; Pydantic v2 patterns.
- **Docs** — `docs/`, `README.md`, and `CHANGELOG.md` updated when behavior changes.
- **Project integrity (our additions)** — stays **deterministic-first** (no LLM
  API calls in core scoring; judges are user-supplied); **no fake integrations**;
  **no unsupported benchmark claims**; safety standards IDs (OWASP/MITRE) are real;
  no secrets committed.

## Speed & courtesy

- **Don't let changes sit.** Review within one business day; if you can't fully
  review, send quick feedback or unblock the author.
- Comments are about the **code, not the coder.** Explain *why*; prefer questions
  when the path isn't certain. Resolve disagreements on principles/data; escalate
  rather than stall.

## For change authors

### Write small, self-contained changes

Small changes are reviewed faster and more thoroughly, introduce fewer bugs, and
roll back more easily. Aim for **one self-contained change** that does *just one
thing* (~100 lines is comfortable; ~1000 is usually too large).

- **Separate refactors from behavior changes.**
- **Keep related tests in the same change.** New/changed logic ships with tests;
  refactors keep existing tests green. Tests are expected for all changes.
- **Don't break the build** — CI (`pytest` + `ruff` on 3.11/3.12) must be green.

### Write good change descriptions

Say **what** changed and **why**.

- **First line:** a short, imperative summary that stands alone — e.g. "Add the
  grounding-metric judge", not "judge stuff". Then a blank line.
- **Body:** the problem, the approach and why it's right, any shortcomings, and
  context (issue links, benchmark notes). We use conventional-ish prefixes
  (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`).

### Handling review comments

Assume good intent, reply to every comment (resolve or discuss), and make the case
with data or principles when you disagree. Nits are optional.

## Our enforcement (already wired)

| Practice | How it's enforced |
|---|---|
| Don't break the build | `.github/workflows/ci.yml` — pytest + ruff + CLI smoke on 3.11/3.12 |
| Tests required | new logic lands with tests; CI fails otherwise |
| Style is the linter | `ruff check src/ tests/ examples/ scripts/` |
| Merge gating | the harness can gate itself via `policy.py` / `gate` |
| Good descriptions | `.github/PULL_REQUEST_TEMPLATE.md` |

See [CONTRIBUTING.md](../CONTRIBUTING.md) for setup and the day-to-day workflow,
and [`CLAUDE.md`](../CLAUDE.md) for the core coding rules.
