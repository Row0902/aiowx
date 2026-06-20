# aiowx v0.2.1 — Release Notes

> Async I/O bridge for wxPython — run asyncio coroutines with wx GUI.

## What's new

- **Strict TDD mode** — full test suite with pytest + pytest-asyncio + coverage (≥80%).
- **GitHub Actions CI** — matrix testing across Python 3.12, 3.13, and 3.14 with:
  - `ty` for type checking
  - `ruff` for linting and formatting
  - `pytest --cov=src` for test coverage
- **Supply-chain security** — CodeQL Advanced scanning and dependency review on every PR.
- **Dependabot** — weekly automated dependency updates with dev-deps grouped.
- **ruff security rules** — flake8-bandit (S) rules enabled, zero-warnings policy.
- **PyPI publish workflow** — trusted publishing via `uv build` + `uv publish`, triggered on release, tag push, or manual dispatch.

## Branch workflow

- `canary` — default branch, all development goes here via PR.
- `main` — stable only, receives merges exclusively from `canary`.
- Feature/fix branches branch from `canary` and PR back to `canary`.

## What's next

- Documentation and usage guides.
- Extended async API surface.
- Community contributions via PRs to `canary`.
