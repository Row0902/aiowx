"""Tests that AGENTS.md follows the redesigned structure and rules."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

AGENTS_PATH = Path(__file__).resolve().parents[1] / "AGENTS.md"


@pytest.fixture
def agents_text() -> str:
    """Return the full text of AGENTS.md."""
    return AGENTS_PATH.read_text(encoding="utf-8")


@pytest.fixture
def agents_lines(agents_text: str) -> list[str]:
    """Return AGENTS.md top-level section header lines."""
    return [
        line.rstrip()
        for line in agents_text.splitlines()
        if line.startswith("## ") and not line.startswith("###")
    ]


def _section(agents_text: str, title: str) -> str:
    """Return the content of a top-level section by its ``##`` title."""
    pattern = rf"^## {re.escape(title)}\b.*?^(?=## |\Z)"
    match = re.search(pattern, agents_text, re.MULTILINE | re.DOTALL)
    if match is None:
        raise AssertionError(f"Section '## {title}' not found in AGENTS.md")
    return match.group(0)


def test_agents_md_exists() -> None:
    """AGENTS.md must exist at the project root."""
    assert AGENTS_PATH.is_file(), "AGENTS.md not found at project root"


def test_required_section_order(agents_lines: list[str]) -> None:
    """Section headers must appear in the spec-defined order."""
    expected = [
        "## ALL FILES",
        "## Naming",
        "## Packages, Modules & Namespace",
        "## Classes",
        "## Functions & Methods",
        "## Library API Design",
        "## Clean Code",
        "## Async-Specific",
        "## Exception Handling",
        "## Testing",
        "## Ruff Integration",
        "## Modern Python Features",
        "## Tools & Authority",
        "## Response Format",
    ]
    assert agents_lines == expected, f"Expected {expected}, got {agents_lines}"


def test_clean_architecture_section_absent(agents_text: str) -> None:
    """The Clean Architecture section must be removed."""
    assert "## Clean Architecture" not in agents_text


def test_polymorphism_section_not_standalone(agents_text: str) -> None:
    """Polymorphism & Type Checks must not be a standalone section."""
    assert "## Polymorphism & Type Checks" not in agents_text
    headings = [line for line in agents_text.splitlines() if line.startswith("## ")]
    assert all("Polymorphism" not in heading for heading in headings)


def test_function_body_limit_is_thirty(agents_text: str) -> None:
    """Functions & Methods must allow 30 body lines, not 20."""
    section = _section(agents_text, "Functions & Methods")
    assert "**30 lines**" in section
    assert "**20 lines**" not in section


def test_event_skip_exception_present(agents_text: str) -> None:
    """Clean Code must exempt wxPython event.Skip() else blocks."""
    section = _section(agents_text, "Clean Code")
    assert "event.Skip()" in section


def test_boolean_prefix_is_prefer_not_reject(agents_text: str) -> None:
    """Boolean prefix rule must live in PREFER, not REJECT."""
    section = _section(agents_text, "Naming")
    assert "Boolean variable/parameter name" in section
    prefer_block = section.split("PREFER:")[1].split("REJECT if:")[0]
    assert "is_" in prefer_block and "has_" in prefer_block
    reject_block = section.split("REJECT if:")[1].split("PREFER:")[0]
    assert "is_" not in reject_block and "has_" not in reject_block


def test_declarative_naming_present(agents_text: str) -> None:
    """Naming section must include Declarative Naming guidance."""
    section = _section(agents_text, "Naming")
    assert "### Declarative Naming" in section
    assert "WHAT not HOW" in section


def test_async_taskgroup_required(agents_text: str) -> None:
    """Async-Specific must require TaskGroup for related concurrent work."""
    section = _section(agents_text, "Async-Specific")
    require_block = section.split("REQUIRE:")[1].split("PREFER:")[0]
    assert "TaskGroup" in require_block


def test_async_timeout_required(agents_text: str) -> None:
    """Async-Specific must require asyncio.timeout for indefinite awaits."""
    section = _section(agents_text, "Async-Specific")
    require_block = section.split("REQUIRE:")[1].split("PREFER:")[0]
    assert "asyncio.timeout()" in require_block


def test_library_api_design_section_present(agents_text: str) -> None:
    """Library API Design section must cover public API and __all__."""
    section = _section(agents_text, "Library API Design")
    assert "__all__" in section
    assert "backward compat" in section.lower()


def test_ruff_integration_section_present(agents_text: str) -> None:
    """Ruff Integration section must map rule groups to purpose."""
    section = _section(agents_text, "Ruff Integration")
    for group in ("UP", "B", "SIM", "A", "RUF", "PL", "D", "FBT", "TCH", "PERF"):
        assert group in section, f"Rule group {group} missing from Ruff Integration"


def test_modern_python_features_present(agents_text: str) -> None:
    """Modern Python Features section must cover PEP 695, 698, 673."""
    section = _section(agents_text, "Modern Python Features")
    assert "PEP 695" in section
    assert "PEP 698" in section
    assert "PEP 673" in section
    assert "@override" in section
    assert "Self" in section
