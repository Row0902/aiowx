# Tasks: Rediseño de AGENTS.md

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 150-280 (AGENTS.md ~120, pyproject.toml ~12, fixes ~50-150) |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR (phases coupled: policy ↔ config ↔ enforcement) |
| Delivery strategy | single-pr (approved by user) |
| Chain strategy | not-applicable |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: not-applicable
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | AGENTS.md restructure + pyproject.toml config + ruff fixes | PR 1 | base=main; phases coupled — policy unenforced without config, config red without fixes |

## Phase 1: AGENTS.md Restructure

- [x] 1.1 Remove Clean Architecture section (lines 91-111) — irrelevant for single-module lib
- [x] 1.2 Remove Polymorphism & Type Checks section (lines 157-171); add 2-3 line `isinstance` pointer under ALL FILES referencing `collections.abc` / `wx.Window`
- [x] 1.3 Functions & Methods: change 20→30 line limit (line 84); add wxPython `event.Skip()` exception to Clean Code else-after-return rule (line 121)
- [x] 1.4 Naming: move boolean prefix rule from REJECT (line 48) to PREFER — "reads as yes/no question"
- [x] 1.5 Naming: add Declarative Naming subsection — names express WHAT not HOW; impl-detail names MUST NOT leak into public API
- [x] 1.6 Async-Specific: upgrade `asyncio.TaskGroup` from PREFER (line 153) to REQUIRE; add `asyncio.timeout()` as REQUIRE for awaits that can hang indefinitely
- [x] 1.7 Add Library API Design section in Clean Architecture slot — public API surface, `__all__` enforcement, backward compat, no leaky abstractions
- [x] 1.8 Add Ruff Integration section — table mapping rule groups (UP, B, SIM, A, RUF, PL, D, FBT, TCH, PERF, S) to purpose
- [x] 1.9 Add Modern Python Features section — PEP 695 (`def func[T]`), PEP 698 (`@override`), PEP 673 (`Self`)
- [x] 1.10 Add declarative naming examples; verify final section order matches spec (ALL FILES → Naming → Packages → Classes → Functions → Library API Design → Clean Code → Async → Exception → Testing → Ruff Integration → Modern Python → Tools → Response Format)

## Phase 2: pyproject.toml Ruff Configuration

- [x] 2.1 Set `target-version = "py314"` under `[tool.ruff]`
- [x] 2.2 Expand `extend-select` from `["S"]` to `["S", "UP", "B", "SIM", "A", "RUF", "PL", "D", "FBT", "TCH", "PERF"]`
- [x] 2.3 Add `[tool.ruff.lint.pydocstyle]` with `convention = "google"` (design decision — keeps D noise low)
- [x] 2.4 Add per-file ignore: `"src/aiowx/_core.py" = ["A001", "A002"]` (wx API uses `id` parameter by convention)
- [x] 2.5 Add `[tool.ruff.lint.pylint]` with `max-statements = 40` for PLR0915 (wx dialog lifecycle methods)

## Phase 3: Fix Violations

- [x] 3.1 Run `ruff check` and document all violations from new rules (focus: `_core.py`, `__init__.py`)
- [x] 3.2 Fix violations or add justified per-file ignores with inline comments; MUST NOT disable a rule globally without Ruff Integration table entry
- [x] 3.3 Run `ruff format` to ensure formatting is clean and idempotent
- [x] 3.4 Run `ruff check` (zero warnings), `ty` (no type regressions), `pytest --cov=src` (≥80%, no behavioral changes)
