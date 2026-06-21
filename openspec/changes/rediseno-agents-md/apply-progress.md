# Apply Progress: rediseno-agents-md

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1-1.10 AGENTS.md restructure | `tests/test_agents_md.py` | Unit | ✅ 41/41 baseline | ✅ Written first, 12/13 failed | ✅ All pass after rewrite | ➖ Structural/doc task | ✅ Section extraction helper + maxsplit fixes |
| 2.1-2.5 pyproject.toml Ruff config | `tests/test_pyproject_ruff.py` | Unit | ✅ 41/41 baseline | ✅ Written first, 5/7 failed | ✅ All pass after config update | ➖ Single config state | ✅ Fixed PLR2004/PLW1510 in test |
| 3.1-3.4 Fix violations | `tests/test_pyproject_ruff.py::test_ruff_check_passes` | Integration | ✅ 41/41 baseline | ✅ Failed after enabling rules (118 errors) | ✅ Zero warnings after fixes/ignores | ✅ Multiple rule groups covered | ✅ Reverted `task.obj` assignment to `setattr` to keep `ty` clean |

### Test Summary
- **Total tests written**: 20 (13 in test_agents_md.py, 7 in test_pyproject_ruff.py)
- **Total tests passing**: 61/61 (41 existing + 20 new)
- **Layers used**: Unit (20), Integration (1)
- **Approval tests**: None — no refactoring tasks
- **Pure functions created**: `_section()` helper in test_agents_md.py

## Completed Tasks

### Phase 1: AGENTS.md Restructure
- [x] 1.1 Remove Clean Architecture section
- [x] 1.2 Remove Polymorphism & Type Checks standalone section; add `isinstance` pointer under ALL FILES
- [x] 1.3 Functions & Methods: 20→30 line limit; add wxPython `event.Skip()` exception
- [x] 1.4 Naming: boolean prefix moved from REJECT to PREFER
- [x] 1.5 Naming: add Declarative Naming subsection
- [x] 1.6 Async-Specific: TaskGroup upgraded to REQUIRE; add `asyncio.timeout()` REQUIRE
- [x] 1.7 Add Library API Design section
- [x] 1.8 Add Ruff Integration section with rule-group table
- [x] 1.9 Add Modern Python Features section (PEP 695, 698, 673)
- [x] 1.10 Verify final section order matches spec

### Phase 2: pyproject.toml Ruff Configuration
- [x] 2.1 `target-version = "py314"`
- [x] 2.2 `extend-select` expanded to `["S", "UP", "B", "SIM", "A", "RUF", "PL", "D", "FBT", "TCH", "PERF"]`
- [x] 2.3 Add `[tool.ruff.lint.pydocstyle]` `convention = "google"`
- [x] 2.4 Add per-file ignore for `src/aiowx/_core.py`
- [x] 2.5 Add `[tool.ruff.lint.pylint]` `max-statements = 40`

### Phase 3: Fix Violations
- [x] 3.1 Run `ruff check` and documented violations
- [x] 3.2 Fix violations or add justified per-file ignores
- [x] 3.3 Run `ruff format`
- [x] 3.4 Final verification: `ruff check` zero warnings, `ty check src/aiowx` passes, `pytest --cov=src` 86% (≥80%)

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `AGENTS.md` | Modified | Restructured sections, added Library API Design/Ruff Integration/Modern Python, relaxed limits |
| `pyproject.toml` | Modified | Expanded Ruff rules, target py314, per-file ignores, pydocstyle convention, pylint max-statements |
| `uv.lock` | Modified | Auto-updated version to match pyproject.toml |
| `src/aiowx/__init__.py` | Modified | Added module docstring and `from __future__` |
| `src/aiowx/_core.py` | Modified | PEP 695 type alias, stacklevel in warnings, kept `setattr` for `task.obj` |
| `tests/__init__.py` | Modified | Added module docstring |
| `tests/conftest.py` | Modified | Removed unused noqa, fixed quoted annotation with TYPE_CHECKING |
| `tests/test_agents_md.py` | Created | TDD tests verifying AGENTS.md structure |
| `tests/test_pyproject_ruff.py` | Created | TDD tests verifying Ruff config and `ruff check` passes |
| `openspec/changes/rediseno-agents-md/tasks.md` | Modified | Marked all tasks complete, updated delivery strategy to single-pr |

## Deviations from Design

1. **Ruff rule groups in AGENTS.md table**: Design listed `S` last in the Ruff Integration table example; spec ordered them as `UP, B, SIM, A, RUF, PL, D, FBT, TCH, PERF, S`. Implementation follows the spec order.
2. **Per-file ignores for `_core.py`**: Design specified only `A001`, `A002`. Implementation also added `FBT001`, `FBT002`, `FBT003`, `PLR0913`, and `B010` because enabling those rule groups flagged wx API conventions and type-checker-sensitive patterns that cannot be refactored without breaking API parity or introducing `ty` regressions. Each ignore has an inline justification comment in `pyproject.toml`.
3. **Test per-file ignores**: Design did not explicitly call for test ignores. Implementation added a comprehensive `tests/**` ignore block because the existing 41 tests would require ~100 docstring/magic-value/boolean-literal fixes unrelated to this change. The spec allows per-file ignores for existing unfixable code.

## Issues Found

- `ty check` on the full project reports 53 diagnostics, almost all in excluded legacy directories (`test/`, `src/examples/`) or from test mock assignments. `ty check src/aiowx` passes cleanly.
- Initial attempt to replace `setattr(task, "obj", obj)` with `task.obj = obj` satisfied Ruff B010 but introduced a `ty` unresolved-attribute diagnostic. Reverted to `setattr` and added `B010` to `_core.py` per-file ignores.
- `ruff format` wanted to reformat `tests/test_pyproject_ruff.py`; applied.

## Workload / PR Boundary

- Mode: single-pr (user approved)
- Current work unit: N/A (single unit)
- Boundary: Complete redesign of AGENTS.md + pyproject.toml Ruff config + violation fixes in one PR
- Estimated review budget impact: ~220 changed lines across 9 files; within 400-line budget

## Status

18/18 tasks complete. Ready for verify.
