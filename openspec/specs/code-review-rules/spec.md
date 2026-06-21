# Code Review Rules Specification

## Purpose

Defines the AGENTS.md structure, Ruff configuration, and Python style rules for aiowx — a single-module wxPython/asyncio library targeting Python 3.14+. Replaces irrelevant Clean Architecture rules with library-focused API design guidance and modern Python feature requirements.

## Requirements

### Requirement: AGENTS.md Section Structure

The code review rules document MUST contain sections in this order: ALL FILES, Naming, Packages Modules & Namespace, Classes, Functions & Methods, Library API Design, Clean Code, Async-Specific, Exception Handling, Testing, Ruff Integration, Modern Python Features, Tools & Authority, Response Format.

| Rule | RFC 2119 | Detail |
|------|----------|--------|
| Clean Architecture section | MUST NOT | MUST NOT appear — irrelevant for single-module library |
| Polymorphism & Type Checks | MUST NOT | Standalone section MUST NOT exist; replaced by 2-3 line pointer under ALL FILES |
| Library API Design | MUST | New section: public API surface, `__all__` enforcement, backward compat, leaky abstraction prohibition |
| Ruff Integration | MUST | New section with table mapping rule groups to purpose |
| Modern Python Features | MUST | New section covering PEP 695, 698, 673 |
| Declarative Naming | MUST | New subsection under Naming: names express WHAT not HOW |

#### Scenario: Clean Architecture section absent after redesign
- GIVEN the redesigned AGENTS.md
- WHEN scanning section headers
- THEN no "Clean Architecture" header exists

#### Scenario: Library API Design section present
- GIVEN the redesigned AGENTS.md
- WHEN scanning section headers
- THEN "Library API Design" exists and covers `__all__` enforcement and backward compat

### Requirement: Function and Method Limits

The Functions and Methods section MUST set the function body limit to 30 lines (excluding blank lines, docstring, and def/return/decorator lines). wxPython event handlers using `event.Skip()` in an `else` block MUST NOT be rejected for the else-after-return rule when the else is required for wx event propagation.

| Rule | RFC 2119 | Detail |
|------|----------|--------|
| Body limit | MUST | 30 lines (excl. blanks, docstring, def/return/decorator) — relaxed from 20 |
| wx event.Skip() exception | MUST NOT | Handlers with `else: event.Skip()` MUST NOT be rejected for else-after-return |

#### Scenario: 28-line function accepted under new limit
- GIVEN a function with 28 body lines (excl. blanks, docstring, def/return)
- WHEN checked against the Functions and Methods rule
- THEN accepted under the 30-line limit; no REJECT

#### Scenario: wxPython event handler with else event.Skip() not rejected
- GIVEN a wx event handler with early return plus `else: event.Skip()` for propagation
- WHEN checked against the Clean Code else-after-return rule
- THEN NOT rejected; the wx event propagation exception applies

### Requirement: Naming Conventions

The Naming section MUST downgrade boolean prefix enforcement from REJECT to PREFER. The section MUST add declarative naming rules.

| Rule | RFC 2119 | Detail |
|------|----------|--------|
| Boolean prefix | SHOULD | Names start with `is_`, `has_`, `should_`, `can_`, `enable_` (reads as yes/no question) |
| Declarative naming | MUST | Names express WHAT not HOW; implementation-detail names MUST NOT leak into public API |

#### Scenario: Boolean without prefix is PREFER not REJECT
- GIVEN a boolean parameter named `ready` instead of `is_ready`
- WHEN the reviewer checks against Naming rules
- THEN a PREFER note is issued, not a REJECT; merge not blocked

### Requirement: Async Conventions

The Async-Specific section MUST upgrade `asyncio.TaskGroup` from PREFER to REQUIRE for related concurrent work. The section MUST add `asyncio.timeout()` as a REQUIRE for any await that can hang indefinitely.

| Rule | RFC 2119 | Detail |
|------|----------|--------|
| TaskGroup | MUST | Used for related concurrent work (upgraded from PREFER) |
| asyncio.timeout() | MUST | Used for any await that can hang indefinitely |

### Requirement: Ruff Configuration

pyproject.toml MUST enable the specified Ruff rule groups and configure per-file ignores.

| Rule | RFC 2119 | Detail |
|------|----------|--------|
| Rule groups enabled | MUST | UP, B, SIM, A, RUF, PL, D, FBT, TCH, PERF under `[tool.ruff.lint]` |
| Target version | MUST | `py314` |
| Per-file ignore: `_core.py` | MUST | Exempt from `A` rules (wx API uses `id` parameter by convention) |
| max-statements threshold | MUST | Set to 40 for PLR0915 to accommodate wx dialog lifecycle methods |

#### Scenario: Ruff catches built-in shadowing on new PR
- GIVEN a PR adds a function with `id` parameter in a module other than `_core.py`
- WHEN the reviewer runs `ruff check`
- THEN A002 flags the built-in shadowing; PR blocked until renamed or justified per-file ignore added

### Requirement: Modern Python Features

The Modern Python Features section MUST specify usage of PEP 695, PEP 698, and PEP 673.

| Feature | RFC 2119 | Detail |
|---------|----------|--------|
| PEP 695 | MUST | Use `def func[T](...)` over `TypeVar` for new generic type parameters |
| PEP 698 | MUST | `@override` decorator on methods overriding a parent class method |
| PEP 673 | MUST | `Self` return type for methods returning `self` for chaining |

#### Scenario: @override decorator produces no lint warning
- GIVEN a method decorated with `@override` (PEP 698) overriding a parent method
- WHEN `ruff check` runs with UP rules enabled
- THEN no missing-override warning is emitted; the override is validated

### Requirement: Error Handling for Ruff Violations

When a new Ruff rule flags existing code that cannot be trivially auto-fixed, the developer MUST add a per-file ignore with an inline comment explaining the exception, or refactor the code. A rule MUST NOT be disabled globally without justification documented in the Ruff Integration table. When a user disagrees with naming convention changes, the convention stays as PREFER — the reviewer SHOULD discuss in PR review but MUST NOT block merge solely on a PREFER naming convention.

| Condition | RFC 2119 | Action |
|-----------|----------|--------|
| Rule flags unfixable existing code | MUST | Add per-file ignore with inline comment OR refactor |
| Rule disabled globally | MUST NOT | Without justification in Ruff Integration table |
| User disagrees with naming convention | SHOULD | Discuss in PR; MUST NOT block merge on PREFER rules alone |

#### Scenario: Unfixable Ruff violation handled with justified ignore
- GIVEN a new Ruff rule flags existing code that cannot be auto-fixed
- WHEN the developer addresses the violation
- THEN a per-file ignore with inline comment is added OR the code is refactored; the rule is not globally disabled without justification
