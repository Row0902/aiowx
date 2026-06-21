# Code Review Rules — aiowx

Python 3.12+ · wxPython · asyncio · uv_build

---

## ALL FILES

REJECT if:

- Type hints missing on public function/method signatures (parameters and return type)
- Bare `except:` without a specific exception class
- Empty `except` or `try` blocks (silent error swallowing)
- `except Exception: pass` without at least a `logger.warning` or `warnings.warn`
- `type(x) is` or `type(x) ==` used instead of `isinstance(x, ...)`
- Multiple classes defined in the same `.py` file (one class per file)
- File exceeds **500 lines** (hard limit)
- `print()` in library code — use `warnings.warn` or `logging` instead
- Circular imports between modules in the same package
- **Inline comments** that merely restate what the code does (`# increment i` next to `i += 1`) — comments must explain WHY, not WHAT

REQUIRE:

- Docstring on every class describing its responsibility and usage
- Docstring on every public function/method describing parameters, return value, and behavior
- Docstring on module top describing the module's purpose (first line of file after `from __future__ import annotations`)
- `from __future__ import annotations` at the top of every module (PEP 604/649 forward compat)
- `__all__` declared in every `__init__.py`

PREFER:

- Composition over inheritance
- Explicit `Any` imports from `typing` rather than bare names
- `collections.abc` types (`Callable`, `Coroutine`, `Awaitable`) over `typing` equivalents (Python 3.12+)

Type checks: prefer `isinstance(x, collections.abc.Coroutine)` or `isinstance(x, wx.Window)` over concrete subclasses; avoid `type(x) is`.

---

## Naming

REJECT if:

- Package name is not a short, lowercase, single word (e.g., `aiowx`, not `wx_async_tools`)
- Module name is not lowercase with underscores (`snake_case`) and describes its single responsibility
- Class name is not `PascalCase` and is not a noun phrase describing what it is
- Function/method name is not `snake_case` and is not a verb phrase describing what it does
- Name uses abbreviations, single letters (except loop `_`, index `i`, `j`), or acronyms without expansion in docstring
- Two identifiers in the same scope differ only by case (e.g., `user` vs `User`)

PREFER:

- Boolean variable/parameter name starts with `is_`, `has_`, `should_`, `can_`, `enable_` (e.g., `is_ready`) so it reads as a yes/no question
- Declarative naming: names express WHAT not HOW; implementation-detail names (e.g., `parse_json_then_validate`) MUST NOT leak into the public API
- `@dataclass` or `NamedTuple` for grouping related data instead of dicts or long tuples

### Declarative Naming

Public names describe intent and outcome, not mechanics.

- `fetch_user` over `query_db_and_build_user`
- `parse_config` over `open_file_read_yaml_validate_schema`
- `is_connected` over `has_socket_been_established`

---

## Packages, Modules & Namespace

REJECT if:

- A package or module does more than one thing (SRP violation — e.g., mixing GUI event logic with I/O or data parsing)
- Module is imported solely for side‑effects without a clear `__init__.py` re‑export
- `from module import *` used anywhere (star imports pollute namespace)
- Name shadows a Python built‑in (`id`, `type`, `list`, `dict`, `object`, `str`, etc.)
- Import from a deep internal path when a public API exists (e.g., `from aiowx._core import ...` instead of `from aiowx import ...`)
- Two modules in the same package define the same public name differently (`__init__.py` must be the single source of truth for public API)

REQUIRE:

- `__init__.py` MUST explicitly list public API via `__all__` (already required above)
- Internal modules (prefixed with `_`) MUST NOT appear in `__all__` or be re‑exported as public

---

## Classes

REJECT if:

- Class has **more than 10 public methods** (excluding `__init__`, `__repr__`, `__str__`, and dunders)
- Class violates **Single Responsibility Principle** — more than one reason to change
- Inheritance hierarchy deeper than 3 levels without justification

---

## Functions & Methods

REJECT if:

- Function/method body exceeds **30 lines** (excluding blank lines, docstring, and the `def`/`return`/`decorator` lines)
- Function/method has more than 5 positional parameters
- Function does more than one thing (SRP violation — extract helper)
- Mutating arguments passed by the caller unless the name makes it obvious (e.g., `append_to`, `update`)

---

## Library API Design

REJECT if:

- Internal implementation details are exposed through the public API (leaky abstraction)
- A public name, signature, or behavior changes without a documented compatibility plan
- `__all__` is missing, incomplete, or re‑exports private modules

REQUIRE:

- The public surface is intentional and versioned: every symbol in `__all__` is supported
- Breaking changes require a major version bump or a deprecation cycle with `warnings.warn`
- New public functions/classes start with a stable signature; experiment in private modules first
- Backward compatibility is preserved unless explicitly approved as a breaking change

PREFER:

- Small, focused public modules over one giant facade
- Explicit keyword arguments for optional behavior over boolean flags
- Protocols or abstract base classes for extension points owned by the library, not the caller

---

## Clean Code

REJECT if:

- Function has **side effects** not obvious from its name (e.g., a function called `get_user` that also writes to a file)
- Same magic number, string, or constant appears more than once without being named
- Nested conditionals deeper than **2 levels** — extract guard clauses or early returns
- `else` block after a `return`, `break`, or `continue` when the `else` is unreachable or redundant
- Long chains of method calls on different objects (Law of Demeter violation — e.g., `a.getB().getC().doSomething()`)

Exception: wxPython event handlers may use `else: event.Skip()` after an early return when the `else` is required for event propagation; document the exception with a comment.

REQUIRE:

- **DRY**: every piece of knowledge must have a single, unambiguous, authoritative representation
- **Tell, don't ask**: prefer commanding an object over querying its state and deciding externally
- Error handling is not a separate concern — it's part of the function's contract

PREFER:

- Early returns / guard clauses over nested `if`‑`else`
- `@dataclass` or `NamedTuple` for grouping related data instead of dicts or long tuples
- `match`/`case` over chains of `if`/`elif` when pattern matching reads cleaner
- Boolean parameter that changes the function's behavior path — split into two functions only when the boolean adds a genuinely orthogonal concern; a single `is_async: bool` or `read_only: bool` is fine

---

## Async-Specific

REJECT if:

- A coroutine calls a synchronous I/O-bound function without offloading to an executor (`run_in_executor`)

REQUIRE:

- Every public async function MUST use `async def` consistently — do not expose a sync wrapper that hides an async implementation
- `asyncio.get_event_loop()` MUST NOT be used in new code — use `asyncio.get_running_loop()` or `asyncio.run()` instead
- Use `asyncio.TaskGroup` for related concurrent work (Python 3.11+)
- Wrap any await that can hang indefinitely with `asyncio.timeout()`

PREFER:

- Keep `async`/`await` at the boundary; internal helpers can be sync when they don't need the event loop

---

## Exception Handling

REJECT if:

- Bare `except:` — always name the exception type
- `except:` that catches and discards without logging, warning, or re‑raise
- Catching `Exception` when a more specific type (`KeyError`, `ValueError`, `OSError`, `CancelledError`) would do

REQUIRE:

- `CancelledError` handled explicitly in async code (not swallowed by a generic `except Exception`)
- `finally` blocks clean up resources (close handles, re‑enable frames, restore state)

---

## Testing

REJECT if:

- Test function body exceeds 30 lines
- Test function does not follow **Arrange‑Act‑Assert** (Given‑When‑Then) structure
- Mock patches are applied module‑wide when a local patch would work (exception: `tests/conftest.py` may use session‑scope mocks for wxPython, which requires headless infrastructure mocking)
- Test depends on external resources (network, display, filesystem) without a clear skip guard (`@pytest.mark.skipif`)
- Async test is not decorated / configured with `@pytest.mark.asyncio` or `asyncio_mode = auto` is not set

REQUIRE:

- Every public function/method that contains logic (not just delegation) has at least one test
- Coverage report is generated with `--cov=src` and meets ≥80% line coverage

---

## Ruff Integration

The `[tool.ruff]` configuration in `pyproject.toml` is the machine-enforced subset of these rules. Rule groups and their purpose:

| Group | Purpose |
|-------|---------|
| `S` | Security linting (flake8-bandit) |
| `UP` | pyupgrade — modern Python syntax |
| `B` | flake8-bugbear — likely bugs and suspicious patterns |
| `SIM` | flake8-simplify — simplify verbose or redundant constructs |
| `A` | flake8-builtins — avoid shadowing Python builtins |
| `RUF` | Ruff-specific rules |
| `PL` | Pylint — complexity, naming, and design |
| `D` | pydocstyle — docstring conventions (Google convention) |
| `FBT` | flake8-boolean-trap — boolean positional args |
| `TCH` | flake8-type-checking — type-only imports |
| `PERF` | Perflint — performance anti-patterns |

REQUIRE:

- `ruff check` exits with code 0 before merge
- A rule MUST NOT be disabled globally without a justification entry in this table
- When a rule flags existing code that cannot be trivially auto-fixed, add a per-file ignore with an inline comment explaining the exception

---

## Modern Python Features

Use modern syntax where it improves clarity and the project still supports `requires-python`:

| PEP | Feature | Usage |
|-----|---------|-------|
| PEP 695 | Generic type parameters | `def func[T](items: list[T]) -> T:` instead of explicit `TypeVar` |
| PEP 698 | `@override` | Required on methods overriding a parent class method (enabled by RUF rules) |
| PEP 673 | `Self` return type | Use `Self` for methods returning `self` to support fluent/chained APIs |

REQUIRE:

- New generic code uses PEP 695 syntax
- Overrides are explicitly marked with `@override`
- Fluent/chained methods returning `self` use `Self`

---

## Tools & Authority

| Tool | Responsibility | Rule |
|---|---|---|
| `ruff` | Linting + formatting | `ruff check` must pass (zero warnings); `ruff format` is the only style authority |
| `ruff check` | Lint | Zero‑tolerance for any warning; ruff exclusions (`test/`, `src/examples/`) are acceptable |
| `ruff format` | Format | No manual style debates — `ruff format` output is definitive |
| `ty` | Type checking | `ty` is the sole authority on type correctness; all type‑hint related rules defer to `ty` output |
| `pytest` | Testing | `pytest` + `pytest-asyncio` + `pytest-cov` are the only test framework; no other test runner is accepted |
| `pytest --cov=src` | Coverage | Coverage threshold: ≥80% line coverage on `src/` |
| `uv` | Build + deps | `uv build` / `uv sync` / `uv run` are the only build commands; no `pip`, `setuptools`, or `poetry` commands |

---

## Response Format

FIRST LINE must be exactly:

STATUS: PASSED

or

STATUS: FAILED

If FAILED, list each issue as:

`path/to/file.py:line - rule violated - brief description of the problem`

One line per issue. Do not add commentary beyond the status line and the file‑level issue list.
