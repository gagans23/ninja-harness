<!-- Thanks for contributing to Ninja Harness! See CONTRIBUTING.md and docs/code-review.md. -->

## Summary

<!-- First line: a short, imperative summary that stands alone (e.g. "Add the grounding-metric judge"). -->

## Why

<!-- The problem this solves, the approach and why it's right, any trade-offs, and context (issue links, benchmark notes). Even small changes deserve context. -->

## Type of change

- [ ] Bug fix
- [ ] New adapter
- [ ] New / changed metric
- [ ] Docs
- [ ] Tooling / CI
- [ ] Other

## Checklist

- [ ] Small and self-contained — does one thing; refactors separated from behavior changes
- [ ] `pytest -q` passes
- [ ] `ruff check src/ tests/ examples/ scripts/` is clean
- [ ] Added/updated tests
- [ ] Updated docs (`docs/`, `README.md`) if behavior changed
- [ ] Updated `CHANGELOG.md`
- [ ] Stays deterministic-first; no fake integrations; no unsupported benchmark claims
- [ ] Any safety-standard IDs (OWASP/MITRE) are accurate

## Notes for reviewers

<!-- Anything specific you'd like feedback on -->
