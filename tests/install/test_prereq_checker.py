from __future__ import annotations

import os
import subprocess
from pathlib import Path

HTTP_ERROR_EXIT = 1


def test_missing_nvidia_toolkit_explains_fix() -> None:
    env = os.environ.copy()
    env["BIG_BROTHER_FAKE_NO_NVIDIA"] = "1"

    result = subprocess.run(
        ["./scripts/install-linux-nvidia.sh", "--check-only"],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    combined_output = result.stdout + result.stderr
    assert result.returncode == HTTP_ERROR_EXIT
    assert "NVIDIA Container Toolkit" in combined_output
    assert "nvidia-ctk" in combined_output
