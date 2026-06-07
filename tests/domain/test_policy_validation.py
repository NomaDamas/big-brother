from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_validate_policy_script_accepts_default_policy() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate-policy.py",
            "tests/fixtures/policies/default.json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "policy valid" in result.stdout


def test_validate_policy_script_rejects_model_illegal_policy() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate-policy.py",
            "tests/fixtures/policies/model-illegal.json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "model-only signals cannot produce illegal" in result.stderr
