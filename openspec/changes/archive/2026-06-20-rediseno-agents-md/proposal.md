# Proposal: Rediseño de AGENTS.md — Code Review Rules for aiowx

## Intent

Current AGENTS.md has irrelevant Clean Architecture (21 lines for a 3-file lib), duplicates Ruff-enforced rules, imposes overly restrictive limits (20-line func, boolean prefix REJECT), and misses modern Python features (PEP 695, 698, 673, TaskGroup, asyncio.timeout). Redesign it to produce accurate code quality signals with less noise.

## Scope

### In Scope
- Restructure AGENTS.md: remove Clean Architecture, Polymorphism sections; add Library API Design, Ruff Integration, Modern Python Features, Declarative Naming
- Relax rules: 20→30 line limit (with wx exception for dialog lifecycle code), boolean prefix REJECT→PREFER ("reads as yes/no question")
- Enable Ruff rule groups: UP, B, A, FBT, TCH, PL (R0915/R0913), PERF, RUF, SIM in pyproject.toml
- Update `from __future__ import annotations` REQUIRE with 3.14 deprecation note
- Fix codebase violations from new Ruff rules (add per-file ignores for wx API `id` params)

### Out of Scope
- Renaming `id` parameters in wx API (keeps wx convention)
- CI pipeline changes beyond Ruff config
- Adding/removing library features

## Capabilities

### New Capabilities
- `code-review-rules`: Project code review conventions, linting configuration, and development guidelines for aiowx

### Modified Capabilities
- None

## Approach

- **Phase 1**: Restructure AGENTS.md — reorder sections, remove irrelevant content, add new sections (Library API Design, Ruff Integration Table, Modern Python Features, Declarative Naming)
- **Phase 2**: Update pyproject.toml — enable new Ruff rule groups with per-file ignores for wx API patterns
- **Phase 3**: Run `ruff check --fix`, fix remaining violations, verify tests pass

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `AGENTS.md` | Modified | Full restructure: remove/reorder/add sections |
| `pyproject.toml` | Modified | Enable UP, B, A, FBT, TCH, PL, PERF, RUF, SIM rules |
| `src/aiowx/_core.py` | Modified | Per-file ignore for A rule (`id` params follow wx convention) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| A rule flags `id` params in wx Bind API | High | Per-file ignore `_core.py` for A; document wx convention |
| PLR0915 (max-statements) flags existing methods | Medium | Set max-statements=40; document wx dialog exceptions |
| UP rules change syntax unexpectedly | Low | UP auto-fixes; review `ruff check --fix` diff |
| User disagrees with relaxed naming conventions | Low | Keep as PREFER not REJECT; discuss in review |

## Rollback Plan

Revert `pyproject.toml` to restore old Ruff config; AGENTS.md changes revert via `git checkout`. Changes are file-separated so partial rollback is trivial.

## Dependencies

- `ruff>=0.15.17` (already installed)

## Success Criteria

- [ ] AGENTS.md restructured with all new sections present and old irrelevant sections removed
- [ ] pyproject.toml Ruff config enables UP, B, A, FBT, TCH, PL, PERF, RUF, SIM
- [ ] `ruff check` passes with zero warnings on `src/` and `tests/`
- [ ] `uv run pytest --cov=src` passes with ≥80% coverage
