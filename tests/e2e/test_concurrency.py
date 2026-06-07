from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from big_brother.api.app import ApiSettings, ScanResponse, create_app

SCAN_COUNT = 20


def test_concurrent_scans_return_distinct_request_ids() -> None:
    client = TestClient(create_app(settings=ApiSettings()))

    def scan_once() -> str:
        response = client.post(
            "/v1/scan",
            files={"image": ("benign.jpg", b"benign-image", "image/jpeg")},
        )
        _ = response.raise_for_status()
        body = TypeAdapter(ScanResponse).validate_json(response.content)
        return body.request_id

    def scan_index(_: int) -> str:
        return scan_once()

    with ThreadPoolExecutor(max_workers=5) as executor:
        request_ids = tuple(executor.map(scan_index, range(SCAN_COUNT)))

    assert len(request_ids) == SCAN_COUNT
    assert len(set(request_ids)) == SCAN_COUNT
