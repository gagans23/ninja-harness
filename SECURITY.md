# Security Policy

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Instead, report privately via GitHub's **[Report a vulnerability](https://github.com/gagans23/ninja-harness/security/advisories/new)**
(Security → Advisories → Report a vulnerability), or contact the maintainer
directly. We aim to acknowledge reports within a few days.

When reporting, please include:

- A description of the issue and its impact
- Steps to reproduce (a minimal trace or command is ideal)
- Affected version (`ninja-harness --version`)

## Supported versions

This project is pre-1.0; security fixes are applied to the latest released
version. Pin a version and upgrade promptly.

## Scope & threat model

Ninja Harness is a **defensive evaluation tool**. A few important notes:

- The **red-team module is detection-only**. It flags unsafe patterns in agent
  traces (prompt injection, data-exfiltration language, unsafe escalation,
  credential leakage). It does **not** generate or assist with harmful behavior.
- **Safety scores are not a security guarantee.** They are heuristic detectors
  and must be paired with human review in high-risk domains.
- Core scoring is **deterministic and offline** — no network calls, no bundled
  credentials. The optional `serve` playground binds to `127.0.0.1` by default;
  do **not** expose it to untrusted networks. The Pyodide playground runs fully
  client-side.
- The `DockerSandbox` provides host isolation for agent execution; the
  `LocalSandbox` does **not** — treat untrusted agent code accordingly.

## Responsible use

See [`docs/ethics.md`](docs/ethics.md). Do not use Ninja Harness to optimize
agents for deception, evasion, surveillance abuse, credential theft, or
unauthorized access.
