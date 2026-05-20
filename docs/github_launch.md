# GitHub Launch Checklist

Steps to take the repository from local to public on GitHub.

## Pre-launch Checklist

- [ ] All tests pass (`pytest`)
- [ ] CLI smoke test passes (`ninja-harness validate --trace src/ninja_harness/examples/simple_agent_trace.json`)
- [ ] No secrets or API keys in any file
- [ ] `.env` is in `.gitignore`
- [ ] LICENSE is present (Apache 2.0)
- [ ] README.md is complete
- [ ] docs/ are complete
- [ ] CLAUDE.md is accurate

## Create Repository on GitHub

```bash
# From inside the ninja-harness directory
git init
git add .
git commit -m "Initial release: Ninja Harness v0.1.0"
git branch -M main
git remote add origin https://github.com/gagans23/ninja-harness.git
git push -u origin main
```

## Recommended Repository Settings

- **Description**: Trace-first evals for agents that need to survive production.
- **Topics**: `ai`, `agents`, `evaluation`, `llm`, `safety`, `evals`, `tracing`, `agent-evaluation`
- **Default branch**: `main`
- Enable **Issues**
- Enable **Discussions** (for community questions)
- Add a `CONTRIBUTING.md` (v0.2)
- Add a `CODE_OF_CONDUCT.md` (v0.2)

## First GitHub Release

```bash
git tag v0.1.0
git push origin v0.1.0
```

Then create a GitHub Release with:
- Tag: `v0.1.0`
- Title: `Ninja Harness v0.1.0 — Initial Release`
- Release notes: copy from roadmap v0.1 completed items

## PyPI Publish (optional, v0.2)

```bash
pip install build twine
python -m build
twine upload dist/*
```

## Post-launch

- Share in relevant communities (LangChain Discord, Hugging Face forums, AI safety forums)
- Open a "Good First Issue" for each placeholder adapter
- Pin the issue for "Help wanted: v0.2 framework adapters"
