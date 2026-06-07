from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HTTP_OK_EXIT = 0


def test_cli_import_outputs_count(tmp_path: Path) -> None:
    db_path = tmp_path / "hashbank.sqlite"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "big_brother",
            "hashbank",
            "import",
            "tests/fixtures/hashbanks/benign.jsonl",
            "--db",
            str(db_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == HTTP_OK_EXIT
    assert "imported 1 hash entries" in result.stdout
