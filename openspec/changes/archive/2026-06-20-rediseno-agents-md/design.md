# Design: Rediseño de AGENTS.md

## Technical Approach

Refactor the code review rules document (`AGENTS.md`) and the Ruff configuration (`pyproject.toml`) so the rules are clearer, more actionable, and enforced automatically. No runtime code changes are required unless Ruff surfaces violations that must be fixed or selectively ignored.

The redesign:

1. Replaces the generic **Clean Architecture** section with a focused **Library API Design** section suited to a single-module library.
2. Adds sections for **Ruff Integration**, **Modern Python**, and **Declarative Naming**.
3. Relaxes overly strict rules (20-line function limit, boolean prefix REJECT) and upgrades modern Python guidance to PEP 695/698/673.
4. Expands `pyproject.toml` Ruff rules from `S` only to `UP+B+SIM+A+RUF+PL+D+FBT+TCH+PERF`.
5. Runs `ruff check`, fixes violations, and adds per-file ignores for wxPython API conventions (e.g., `id` parameter in `_core.py`).

## Architecture Decisions

| Decision | Alternatives | Rationale |
|----------|--------------|-----------|
| Replace Clean Architecture with Library API Design | Keep Clean Architecture | Clean Architecture is designed for layered enterprise apps. `aiowx` is a single-module bridge library; the new section focuses on stable facades and SRP without forcing irrelevant layering. |
| Relax function limit from 20 to 30 lines | Keep 20, remove limit | 20 lines is too restrictive for wx dialog helpers and event handlers. 30 lines keeps readability while accommodating legitimate wx boilerplate. |
| Boolean prefix REJECT → PREFER | Keep REJECT | Prefix rules improve clarity but are not always meaningful (e.g., `warn_on_cancel_callback`). PREFER preserves intent without blocking valid wx/Python naming. |
| Target `py314` in Ruff | Target `py312` | `requires-python = ">=3.12"`, but the project already uses 3.12+ features. Targeting `py314` lets `UP` suggest the newest modern syntax without breaking 3.12 compatibility as long as we only adopt rules compatible with 3.12. |
| Enable `D` (pydocstyle) | Skip `D` to avoid noise | Docstrings are already required by AGENTS.md. Enabling `D` automates that requirement. Use `convention = "google"` to keep noise low. |
| Per-file ignore `A001`/`A002` in `_core.py` | Rename `id` parameter | `id` is the wxPython API convention for event binding. Renaming would break API parity with wx, so per-file ignore is the pragmatic choice. |

## Data Flow

No runtime data flow changes. The change is a document and configuration refactor:

```
AGENTS.md ──(human review rules)──┐
                                  ├──→ ruff check ──→ fixes/per-file ignores
pyproject.toml ──(Ruff config)────┘
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `AGENTS.md` | Modify | Restructure sections, add Library API Design, Ruff Integration, Modern Python, Declarative Naming; relax boolean/length rules. |
| `pyproject.toml` | Modify | Expand `[tool.ruff]` target version and `[tool.ruff.lint] extend-select`; add `per-file-ignores` for `_core.py`. |
| `src/aiowx/_core.py` | Modify (conditional) | Fix Ruff violations or keep with per-file ignores if they follow wxPython conventions. |
| `src/aiowx/__init__.py` | Modify (conditional) | Add missing docstrings or fix `D` violations if surfaced. |

## Interfaces / Contracts

The public API contract remains unchanged. The new contract is the review policy itself:

- `ruff check` must exit with code 0.
- `ruff format` is the sole formatting authority.
- `AGENTS.md` is the human-readable source of truth; `pyproject.toml` is the machine-enforced subset.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Lint | `ruff check` passes | Run `ruff check` after each configuration change. |
| Format | `ruff format` is idempotent | Run `ruff format --check`. |
| Type | No type regressions | Run `ty` on `src/aiowx`. |
| Unit/Integration | Existing pytest suite | Run `pytest --cov=src` to confirm no behavioral changes. |

## Migration / Rollout

1. Update `AGENTS.md` first so humans have the new rules before enforcement.
2. Update `pyproject.toml` Ruff configuration.
3. Run `ruff check` to surface violations.
4. Fix straightforward violations; add per-file ignores only for wxPython API conventions.
5. Run `ruff format`, `ruff check`, `ty`, and `pytest --cov=src` to verify.

No data migration or feature flags are required.

## Open Questions

- [ ] Should `D` convention be `google`, `numpy`, or `pep257`? Proposal suggests `google`.
- [ ] Should `PLR0913` (too many arguments) be disabled for wx callback signatures that mirror wx API?
