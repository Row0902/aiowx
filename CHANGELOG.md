# Changelog

All notable changes to **aiowx** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- `docs/RELEASE-NOTES.md` — release notes template for upcoming versions.
- `CHANGELOG.md` — this file.

---

## [0.2.1] — 2026-06-20

### Added

- Full CI/CD pipeline with GitHub Actions:
  - Matrix testing on Python 3.12, 3.13, and 3.14 (`test.yml`).
  - Type checking with `ty`.
  - Linting and formatting with `ruff` (bandit S rules enabled).
  - Test coverage with `pytest --cov=src` (≥80% threshold).
  - Coverage artifact upload per Python version.
  - wxPython system dependencies installed in CI (`libgtk-3-dev`, etc.).
- CodeQL Advanced security scanning (`codeql.yml`).
- Dependency review on every pull request (`dependency-review.yml`).
- Dependabot weekly updates with dev-deps grouped (`dependabot.yml`).
- PyPI publish workflow using `uv build` + `uv publish` with trusted publishing (`publish.yml`).
- Branch protection rules for `main` (PR required, linear history, enforce admins) and `canary` (PR required, linear history).
- `docs/` directory for project documentation.

### Changed

- Upgraded `astral-sh/setup-uv` from v4 to v5 across all workflows.
- `main` branch renamed to `canary` as default development branch.
- Ruff flake8-bandit (S) rules enabled with per-file ignores for test assertions.

### Removed

- Legacy `ci.yml` — superseded by `test.yml`.

---

## [0.2.0] — 2026-06-20

### Added

- `WxAsyncApp` — async-compatible wx App wrapper with configurable sleep interval and cancel callback.
- `StartCoroutine` — launch coroutines bound to a wx.Window lifecycle.
- `AsyncBind` — bind event handlers that automatically clean up on window destroy.
- `AsyncShowDialog` / `AsyncShowDialogModal` — async dialog helpers that yield until the dialog closes.
- `_core.py` single-module implementation with full type annotations.
- `py.typed` marker for PEP 561 compliance.
- `uv_build` build system with `pyproject.toml`.

### Fixed

- **Memory leak A** (On-Task-Completed): empty `RunningTasks` sets no longer left behind after task completion.
- **Memory leak B** (On-Destroy): `BoundObjects` and `RunningTasks` entries fully cleaned up on window destroy.
- **Thread safety** (`ShowModal`): wx `ShowModal` runs via `CallAfter` to avoid cross-thread GUI access.

---

[Unreleased]: https://github.com/Row0902/aiowx/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/Row0902/aiowx/releases/tag/v0.2.1
[0.2.0]: https://github.com/Row0902/aiowx/releases/tag/v0.2.0
