from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from big_brother.api.app import ApiSettings, ScanResponse, create_app
from big_brother.domain.hashes import HashAlgorithm, HashBankEntry, RevocationStatus
from big_brother.domain.policy import ModelSignal, ModelSignalAction, ModelSignalCategory
from big_brother.matching.engine import compute_sha256

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "images"
HTTP_OK = 200
HTTP_UNSUPPORTED_MEDIA_TYPE = 415


def test_scan_known_match_returns_blocked_json() -> None:
    image_bytes = (FIXTURES / "known_match.bin").read_bytes()
    settings = ApiSettings(hash_entries=(_hash_entry(compute_sha256(image_bytes)),))
    client = TestClient(create_app(settings=settings))

    response = client.post(
        "/v1/scan",
        files={"image": ("known_match.jpg", image_bytes, "image/jpeg")},
    )

    assert response.status_code == HTTP_OK
    body = TypeAdapter(ScanResponse).validate_json(response.content)
    assert body.decision == "blocked"
    assert body.reason == "known_illegal_match"
    assert body.request_id != ""
    assert body.audit_event_ids != ()


def test_scan_routes_unknown_upload_to_model_review() -> None:
    client = TestClient(
        create_app(
            settings=ApiSettings(model_moderator=FakeModelModerator(action=ModelSignalAction.REVIEW_REQUIRED)),
        ),
    )

    response = client.post(
        "/v1/scan",
        files={"image": ("unknown.jpg", b"unknown", "image/jpeg")},
    )

    assert response.status_code == HTTP_OK
    body = TypeAdapter(ScanResponse).validate_json(response.content)
    assert body.decision == "review_required"
    assert body.reason == "policy_model_signal"


def test_scan_allows_unknown_upload_when_model_below_threshold() -> None:
    client = TestClient(
        create_app(settings=ApiSettings(model_moderator=FakeModelModerator(action=ModelSignalAction.NO_ACTION))),
    )

    response = client.post(
        "/v1/scan",
        files={"image": ("unknown.jpg", b"unknown", "image/jpeg")},
    )

    assert response.status_code == HTTP_OK
    body = TypeAdapter(ScanResponse).validate_json(response.content)
    assert body.decision == "allowed"
    assert body.reason == "model_below_threshold"
    assert "model_signal" in body.audit_event_ids


def test_known_match_blocks_before_model_signal() -> None:
    image_bytes = (FIXTURES / "known_match.bin").read_bytes()
    settings = ApiSettings(
        hash_entries=(_hash_entry(compute_sha256(image_bytes)),),
        model_moderator=FakeModelModerator(action=ModelSignalAction.REVIEW_REQUIRED),
    )
    client = TestClient(create_app(settings=settings))

    response = client.post(
        "/v1/scan",
        files={"image": ("known_match.jpg", image_bytes, "image/jpeg")},
    )

    assert response.status_code == HTTP_OK
    body = TypeAdapter(ScanResponse).validate_json(response.content)
    assert body.decision == "blocked"
    assert body.reason == "known_illegal_match"


def test_scan_rejects_non_image_upload() -> None:
    client = TestClient(create_app(settings=ApiSettings()))

    response = client.post(
        "/v1/scan",
        files={"image": ("README.md", b"not an image", "text/markdown")},
    )

    assert response.status_code == HTTP_UNSUPPORTED_MEDIA_TYPE
    assert response.json()["error_code"] == "unsupported_media_type"


def _hash_entry(hash_value: str) -> HashBankEntry:
    return HashBankEntry(
        source="operator_fixture",
        authority="internal_test",
        algorithm=HashAlgorithm.SHA256,
        hash_value=hash_value,
        content_class="synthetic_illegal_fixture",
        threshold=0,
        received_at=datetime(2026, 6, 7, tzinfo=UTC),
        version="fixture-v1",
        revocation_status=RevocationStatus.ACTIVE,
        retention_status="active",
    )


class FakeModelModerator:
    def __init__(self, *, action: ModelSignalAction) -> None:
        self._action: ModelSignalAction = action

    def classify(self, *, image_bytes: bytes) -> ModelSignal:
        _ = image_bytes
        return ModelSignal(
            category=ModelSignalCategory.EXPLICIT,
            score=0.91,
            action=self._action,
            model_name="fixture-nsfw",
            model_version="0.1.0",
        )
