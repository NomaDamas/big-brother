from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_project_metadata_and_license_are_present() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "MIT License" in license_text
    assert "big-brother" in readme_text
    assert "compliance-support tooling" in readme_text
    assert "not legal advice" in readme_text
    assert "basedpyright" in pyproject_text
    assert "ruff" in pyproject_text
    assert "pytest" in pyproject_text


def test_cli_version_reports_project_name_and_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "big_brother", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "big-brother" in result.stdout
    assert "0.1.0" in result.stdout


def test_cli_unknown_argument_prints_usage() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "big_brother", "--unknown"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "usage:" in result.stderr.lower()
