from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pydantic import TypeAdapter

from big_brother.domain.hashes import HashAlgorithm, HashBankEntry

HTTP_OK_EXIT = 0


def test_demo_seed_creates_known_match_fixture(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "big_brother",
            "demo",
            "seed",
            "--output-dir",
            str(tmp_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )

    image_path = tmp_path / "known_match.jpg"
    hashbank_path = tmp_path / "known-match.jsonl"
    entry = TypeAdapter(HashBankEntry).validate_json(hashbank_path.read_bytes())

    assert result.returncode == HTTP_OK_EXIT
    assert image_path.exists()
    assert entry.algorithm is HashAlgorithm.SHA256
    assert entry.hash_value != ""
