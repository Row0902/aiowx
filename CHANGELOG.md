# Changelog

Notable changes to **aiowx**, grouped by release.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · 
Versioning: [SemVer](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Release scaffolding: `CHANGELOG.md`, `RELEASE-NOTES.md`, `docs/`.

---

## [0.2.1] — 2026-06-20 · CI/CD, security & branching

### Added

| Area | What |
|------|------|
| **Testing** | Matrix CI on Python 3.12 / 3.13 / 3.14 — `ty` check, `ruff` lint+format, `pytest --cov=src` (≥80 % threshold) with wx system deps (`libgtk-3-dev` et al.) |
| **Security scanning** | CodeQL Advanced on every push/PR; `ruff` bandit rules (S) in `ruff check` |
| **Supply chain** | `dependency-review-action` on each PR; Dependabot weekly with dev-deps grouped |
| **Publishing** | PyPI trusted publishing via `uv build` + `uv publish` on GitHub Release, tag push `v*`, or manual dispatch |
| **Branching** | `canary` as default dev branch; `main` protected (PR + linear history + enforce admins) |

### Changed
- `astral-sh/setup-uv` upgraded from v4 → v5 (faster caching, cache-python support).
- `ci.yml` deleted — superseded by `test.yml`.

---

## [0.2.0] — 2026-06-20 · Initial release

### Added

| API | Role |
|-----|------|
| `WxAsyncApp` | wx.App wrapper with configurable sleep interval + cancel callback |
| `StartCoroutine` | Launch coroutines bound to a `wx.Window` lifecycle |
| `AsyncBind` | Bind event handlers that auto-clean on window destroy |
| `AsyncShowDialog` / `AsyncShowDialogModal` | Awaitable dialog helpers |
| Infrastructure | Single-module `_core.py`, `py.typed` (PEP 561), `uv_build` build |

### Fixed
- **Memory leak A** — empty `RunningTasks` sets left behind after task completion.
- **Memory leak B** — `BoundObjects` / `RunningTasks` not cleaned on window destroy.
- **Thread safety** — `ShowModal` now routes through `CallAfter` to avoid cross-thread GUI violations.

---

[Unreleased]: https://github.com/Row0902/aiowx/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/Row0902/aiowx/releases/tag/v0.2.1
[0.2.0]: https://github.com/Row0902/aiowx/releases/tag/v0.2.0
