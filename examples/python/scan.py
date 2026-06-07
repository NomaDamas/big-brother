from __future__ import annotations

import sys
from pathlib import Path

import httpx2


def main() -> None:
    image_path = Path("tests/fixtures/images/known_match.bin")
    with httpx2.Client(timeout=10) as client:
        response = client.post(
            "http://localhost:8080/v1/scan",
            files={"image": ("known_match.jpg", image_path.read_bytes(), "image/jpeg")},
        )
    response.raise_for_status()
    _ = sys.stdout.write(f"{response.text}\n")


if __name__ == "__main__":
    main()
