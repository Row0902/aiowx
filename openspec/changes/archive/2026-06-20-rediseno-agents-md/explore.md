## Exploration: Rediseño de AGENTS.md

### Current State

The current `AGENTS.md` (235 lines) defines code review rules for the aiowx project: a single-module wxPython/asyncio library (3 files, 326-line `_core.py`). It has 12 sections covering All Files, Naming, Packages/Modules/Namespace, Classes, Functions/Methods, Clean Architecture, Clean Code, Async-Specific, Polymorphism/Type Checks, Exception Handling, Testing, and Tools/Authority.

Many rules duplicate what Ruff already enforces (bare `except`, `type(x) is`, naming conventions), the Clean Architecture section is completely irrelevant for a 3-file library, and the 20-line function limit is too tight for GUI code. Modern Python features (PEP 695, 698, 673, `TaskGroup`, `asyncio.timeout()`) are missing.

### Affected Areas

- `AGENTS.md` — entire file to be redesigned
- `pyproject.toml` — Ruff lint rules to extend (add UP, B, A, FBT, TCH, PL relevant subsets)
- No source code changes needed — code review rules only

### Analysis

#### 1. Rules Already Covered by Ruff (duplicate/redundant)

| AGENTS.md Rule | Ruff Rule | Already Enabled? |
|---|---|---|
| Bare `except:` (line 12) | E722 | ✅ Default |
| `type(x) is` / `type(x) ==` (line 15) | E721 | ✅ Default |
| `except Exception: pass` (line 14) | S110 | ✅ (S extension) |
| Naming: PascalCase, snake_case (lines 42-45) | N (pep8-naming) | ✅ Default |
| Built-in shadowing (line 59) | A (flake8-builtins) | ❌ Not enabled |
| Function length (line 84) | PLR0915 | ❌ Not enabled |
| Max args (line 85) | PLR0913 | ❌ Not enabled (but pylint.max_args=5 is set) |
| Boolean parameter trap (line 135) | FBT | ❌ Not enabled |
| `else` after return/break/continue (line 121) | PLR1705 / SIM | ❌ Not enabled |
| Print in library code (line 18) | T20 | ❌ Not enabled |

**Recommendation**: Remove duplicate rules and enable the corresponding Ruff rule groups instead. Keep rules Ruff cannot enforce (semantic decisions, docstring content requirements, architectural patterns, testing conventions).

#### 2. Outdated / Incorrect Rules for Python 3.12+ → 3.14

| Rule | Issue | Action |
|---|---|---|
| `from __future__ import annotations` REQUIRE (line 27) | PEP 649 becomes default in 3.14, making this unnecessary. For 3.12 current min, still needed. | Keep as REQUIRE, add note: "remove once 3.14 is minimum" |
| `collections.abc` over `typing` (line 33-34) | Still valid for 3.12+. | Keep |
| `@singledispatch` PREFER (line 171) | Still valid. | Keep |

#### 3. Rules That Don't Apply

**Clean Architecture section (lines 91-111)**: This is a 3-file library. There are no layers, no domain model, no infrastructure boundary. The library:
- Has no "layers" to invert
- Has no business/domain logic separate from infrastructure
- Exposes a flat API (5 public symbols) from a single module
- The entire section (`REJECT` 4 rules, `REQUIRE` 3 rules, `PREFER` 3 rules) is noise

**Recommendation**: Remove entirely. Replace with **Library API Design** section relevant to a single-module Python library.

#### 4. Rules Too Restrictive

**20-line function limit (line 84)**: The codebase itself violates this:
- `WxAsyncApp.AsyncBind`: 24 lines (event binding setup, validation, registration)
- `AsyncShowDialog`: 34 lines (nested async event handlers, dialog lifecycle)
These are well-structured, normal-length GUI functions. wxPython event plumbing naturally takes more lines.

**Boolean prefix rule (line 48)**: REJECT if boolean doesn't start with `is_/has_/should_/can_/enable_`. This is too rigid:
- `enabled`, `visible`, `running`, `active`, `done` are all valid boolean names
- `ready_flag` is indeed bad, but the prefix list is too narrow
- The real principle: booleans should read as yes/no questions

**Recommendation**: 
- Relax function limit to 30 lines (or prefer PLR0915 with max-statements=40)
- Change boolean prefix from REJECT to PREFER/GUIDE — "boolean names should read as yes/no questions; `is_`/`has_`/`should_` prefixes help but are not required"

#### 5. What's Missing

##### Modern Python Features (3.12+)

| Feature | PEP | Applicability |
|---|---|---|
| `def fn[T](x: T) -> T:` generic syntax | PEP 695 | High — 3.12 min target |
| `type` keyword for type aliases | PEP 695 | High — replaces `TypeAlias` |
| `Self` return type | PEP 673 | High — for class methods returning `Self` |
| `@override` decorator | PEP 698 | Medium — for method overrides |
| `ExceptionGroup` / `except*` | PEP 654 | Low — but should be documented for async error handling |
| `asyncio.TaskGroup` (upgrade from PREFER to REQUIRE) | — | High — TaskGroup is the standard way since 3.11 |
| `asyncio.timeout()` over `wait_for()` | — | High — cleaner API, available since 3.11 |

The codebase currently uses `TypeAlias` (line 16 of `_core.py`):
```python
CoroutineFn: TypeAlias = Callable[..., Coroutine[Any, Any, Any]]
```
This could be:
```python
type CoroutineFn = Callable[..., Coroutine[Any, Any, Any]]
```

##### Naming: WHAT not HOW (Declarative Names)

The current AGENTS.md says function/method names must be "a verb phrase describing what it does" (line 45). This is correct but incomplete. The deeper principle: **names should express WHAT (the intent/contract), not HOW (the implementation)**. For example:
- `StartCoroutine` — good: expresses what (start a coroutine), not how
- `OnTaskCompleted` — good: expresses what, not how  
- `ShowModalInExecutor` — borderline: describes HOW (in executor), could be just `ShowModalAsync`

This principle should be added as a PREFER/GUIDE.

##### Ruff Integration Table

A new section documenting which Ruff rule groups are enabled and what they enforce. This lets reviewers know what's automated and what they need to catch manually.

#### 6. Ruff Rules to Enable in pyproject.toml

| Rule Group | Priority | Rationale |
|---|---|---|
| **UP** (pyupgrade) | **Strong** | Modernizes Python 3.12+ syntax automatically |
| **B** (flake8-bugbear) | **Strong** | Catches real bugs: mutable defaults, `except(Exception)`, `remove` misuse |
| **A** (flake8-builtins) | **Strong** | Detects `id`, `type`, `list` as parameter names — current code uses `id` in `AsyncBind` (wx convention) |
| **FBT** (flake8-boolean-trap) | **Medium** | Replaces manual boolean-prefix rule with automated enforcement |
| **PL** (specific subsets) | **Medium** | PLR0915 (max-statements) replaces 20-line limit; PLR0913 (max-args) is already configured |
| **TCH** (flake8-type-checking) | **Medium** | Optimizes TYPE_CHECKING import blocks automatically |
| **PERF** (perflint) | **Low** | Performance patterns — low priority but useful |
| **RUF** (ruff-specific) | **Low** | RUF012 for mutable class defaults |

**Not recommended**: D (pydocstyle — too noisy), SLF (flake8-self — irrelevant), PTH (use-pathlib — wx uses OS paths), ANN fully (too strict, but individual rules like ANN201 for public functions could help).

**Important note**: Enabling `A` (flake8-builtins) will flag `id` parameters in `AsyncBind` and `on_button`. This is a wxPython API convention (`wx.EvtHandler.Bind` uses `id`). We need either:
- A per-file ignore for `src/aiowx/_core.py` for A rules, or
- Accept the warnings and rename to `wx_id` or `evt_id` — but this would break wxPython's Bind signature convention, so per-file ignore is better.

#### 7. Current Ruff Configuration Gap

Current `pyproject.toml` only adds `S` (flake8-bandit) beyond defaults. For a Python 3.12+ library using wxPython, this is underconfigured. The `T20` (flake8-print) rule alone would replace the manual `print()` rejection rule.

### Recommendation

Replace the AGENTS.md with a restructured document that:

1. **Keeps and cleans**: Tools & Authority table, Response Format, Testing section, Exception Handling
2. **Removes**: Clean Architecture (entirely), duplicate rules (replaced by Ruff)
3. **Relaxes**: 20-line → 30 lines (or PLR0915 delegation), boolean prefix REJECT → PREFER
4. **Adds**:
   - Ruff Integration table (which rule groups cover which concerns)
   - Library API Design section (replaces Clean Architecture)
   - Modern Python Features section (PEP 695, 698, 673, 654, TaskGroup, timeout)
   - Declarative naming guidance (WHAT not HOW)
5. **Updates pyproject.toml**: Enable UP, B, A, FBT, TCH, PLR0915/PLR0913 subsets, PERF
6. **Addresses**: `from __future__ import annotations` with a note about 3.14 deprecation, `id` built-in shadowing exception for wxPython API compatibility

### Risks

- **Built-in shadowing + wxPython API**: Enabling `A` (flake8-builtins) will flag `id` parameters. Must configure per-file ignores for wx-compatible code patterns. Without this, enabling A will cause noise.
- **Too many new rules at once**: Adding UP, B, A, FBT, TCH, PL simultaneously might overwhelm if the codebase needs fixes. Suggest enabling in two phases: (1) UP + B first, (2) A + FBT + TCH + PL second.
- **`from __future__ import annotations` removal timing**: If someone drops the requirement too early (before 3.14 is min), it breaks code that relies on string-based forward references for type checking.

### Ready for Proposal

Yes. Clear mapping between current issues and proposed changes.

### Next Phase Input

The proposal should:
- Propose a complete restructured AGENTS.md outline
- Propose specific Ruff `extend-select` additions to pyproject.toml
- Proceed through spec → design → tasks for the changes
