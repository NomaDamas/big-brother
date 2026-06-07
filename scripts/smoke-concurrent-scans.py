#!/usr/bin/env python3
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Annotated

import httpx2
import typer
from pydantic import TypeAdapter

from big_brother.api.app import ScanResponse

HTTP_OK = 200


def main(
    url: Annotated[str, typer.Option("--url")] = "http://127.0.0.1:8080",
    count: Annotated[int, typer.Option("--count", min=1, max=200)] = 20,
) -> None:
    image_bytes = Path("tests/fixtures/images/known_match.bin").read_bytes()

    def scan_once() -> str:
        with httpx2.Client(timeout=10) as client:
            response = client.post(
                f"{url}/v1/scan",
                files={"image": ("known_match.jpg", image_bytes, "image/jpeg")},
            )
        if response.status_code != HTTP_OK:
            raise typer.Exit(code=1)
        body = TypeAdapter(ScanResponse).validate_json(response.content)
        return body.request_id

    def scan_index(_: int) -> str:
        return scan_once()

    with ThreadPoolExecutor(max_workers=min(count, 8)) as executor:
        request_ids = tuple(executor.map(scan_index, range(count)))

    if len(set(request_ids)) != count:
        raise typer.Exit(code=1)
    _ = sys.stdout.write(f"responses={count}\nunique_request_ids={len(set(request_ids))}\nPASS\n")


if __name__ == "__main__":
    typer.run(main)
