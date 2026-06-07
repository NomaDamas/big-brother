from __future__ import annotations

import os
import subprocess
from pathlib import Path

HTTP_OK_EXIT = 0


def test_demo_known_match_and_model_review_paths() -> None:
    env = os.environ.copy()
    env["BIG_BROTHER_DEMO_PORT"] = "18080"

    result = subprocess.run(
        ["./scripts/demo.sh"],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == HTTP_OK_EXIT
    assert "known_match=blocked" in result.stdout
    assert "model_signal=review_required" in result.stdout
    assert "PASS" in result.stdout


def test_release_checklist_covers_required_drills() -> None:
    checklist = Path("docs/release-checklist.md").read_text(encoding="utf-8")

    assert "legal-review" in checklist
    assert "model-license" in checklist
    assert "hash-source authorization" in checklist
    assert "GPU prerequisite" in checklist
    assert "false-positive drill" in checklist
    assert "incident response" in checklist
