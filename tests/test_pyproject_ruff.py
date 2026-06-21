"""Tests that pyproject.toml configures Ruff as specified and lints pass."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import tomllib

PYPROJECT_PATH = Path(__file__).resolve().parents[1] / "pyproject.toml"
MAX_STATEMENTS_EXPECTED = 40


@pytest.fixture
def pyproject_data() -> dict[str, Any]:
    """Return parsed pyproject.toml data."""
    with PYPROJECT_PATH.open("rb") as handle:
        return tomllib.load(handle)


def test_pyproject_exists() -> None:
    """pyproject.toml must exist at the project root."""
    assert PYPROJECT_PATH.is_file()


def test_ruff_target_version(pyproject_data: dict[str, Any]) -> None:
    """Ruff target-version must be py314."""
    assert pyproject_data["tool"]["ruff"]["target-version"] == "py314"


def test_ruff_rule_groups_enabled(pyproject_data: dict[str, Any]) -> None:
    """Ruff must enable the required rule groups."""
    selected = set(pyproject_data["tool"]["ruff"]["lint"]["extend-select"])
    required = {"S", "UP", "B", "SIM", "A", "RUF", "PL", "D", "FBT", "TCH", "PERF"}
    missing = required - selected
    assert not missing, f"Missing Ruff rule groups: {missing}"


def test_ruff_pydocstyle_convention(pyproject_data: dict[str, Any]) -> None:
    """Ruff pydocstyle convention must be google."""
    assert (
        pyproject_data["tool"]["ruff"]["lint"]["pydocstyle"]["convention"] == "google"
    )


def test_ruff_app_per_file_ignores(pyproject_data: dict[str, Any]) -> None:
    """_app.py must be exempt from A001 and A002 because wx uses id."""
    ignores = pyproject_data["tool"]["ruff"]["lint"]["per-file-ignores"]
    key = "src/aiowx/_app.py"
    assert key in ignores, f"Missing per-file ignore for {key}"
    assert "A001" in ignores[key]
    assert "A002" in ignores[key]


def test_ruff_dialog_per_file_ignores(pyproject_data: dict[str, Any]) -> None:
    """_dialog.py must be exempt from FBT001 and FBT002 for wx dialog flags."""
    ignores = pyproject_data["tool"]["ruff"]["lint"]["per-file-ignores"]
    key = "src/aiowx/_dialog.py"
    assert key in ignores, f"Missing per-file ignore for {key}"
    assert "FBT001" in ignores[key]
    assert "FBT002" in ignores[key]


def test_ruff_pylint_max_statements(pyproject_data: dict[str, Any]) -> None:
    """PLR0915 max-statements must be set to 40."""
    configured = pyproject_data["tool"]["ruff"]["lint"]["pylint"]["max-statements"]
    assert configured == MAX_STATEMENTS_EXPECTED


def test_ruff_check_passes() -> None:
    """Ruff must report zero warnings on the project source."""
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src", "tests"],
        cwd=PYPROJECT_PATH.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"ruff check failed:\n{result.stdout}\n{result.stderr}"
    )
