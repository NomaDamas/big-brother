from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from big_brother.api.app import ProductionConfigError, create_default_app
from big_brother.domain.hashes import HashAlgorithm, HashBankEntry, RevocationStatus

HTTP_OK = 200

if TYPE_CHECKING:
    from pathlib import Path


def test_default_app_loads_operator_hashbank_from_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hashbank_path = tmp_path / "operator-known-match.jsonl"
    entry = _hash_entry("a" * 64)
    _ = hashbank_path.write_text(f"{entry.model_dump_json()}\n", encoding="utf-8")
    monkeypatch.setenv("BIG_BROTHER_HASHBANK_PATH", str(hashbank_path))

    client = TestClient(create_default_app())

    response = client.get("/v1/hashbank/import-status")

    assert response.status_code == HTTP_OK
    assert response.json() == {"active_entries": 1, "hashbank_path": str(hashbank_path)}


def test_production_default_app_requires_hashbank_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BIG_BROTHER_DEV_MODE", "false")
    monkeypatch.setenv("BIG_BROTHER_ADMIN_TOKEN", "production-admin-token")
    monkeypatch.delenv("BIG_BROTHER_HASHBANK_PATH", raising=False)

    with pytest.raises(ProductionConfigError) as error:
        _ = create_default_app()

    assert "BIG_BROTHER_HASHBANK_PATH" in str(error.value)


def test_production_default_app_rejects_missing_hashbank_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BIG_BROTHER_DEV_MODE", "false")
    monkeypatch.setenv("BIG_BROTHER_ADMIN_TOKEN", "production-admin-token")
    monkeypatch.setenv("BIG_BROTHER_HASHBANK_PATH", str(tmp_path / "missing-hashbank.jsonl"))

    with pytest.raises(ProductionConfigError) as error:
        _ = create_default_app()

    assert "hashbank" in str(error.value).casefold()


def test_production_default_app_rejects_empty_hashbank(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hashbank_path = tmp_path / "empty.jsonl"
    _ = hashbank_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("BIG_BROTHER_DEV_MODE", "false")
    monkeypatch.setenv("BIG_BROTHER_ADMIN_TOKEN", "production-admin-token")
    monkeypatch.setenv("BIG_BROTHER_HASHBANK_PATH", str(hashbank_path))

    with pytest.raises(ProductionConfigError) as error:
        _ = create_default_app()

    assert "empty" in str(error.value)


def test_production_default_app_rejects_placeholder_admin_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hashbank_path = tmp_path / "operator-known-match.jsonl"
    entry = _hash_entry("b" * 64)
    _ = hashbank_path.write_text(f"{entry.model_dump_json()}\n", encoding="utf-8")
    monkeypatch.setenv("BIG_BROTHER_DEV_MODE", "false")
    monkeypatch.setenv("BIG_BROTHER_ADMIN_TOKEN", "change-this-local-admin-token")
    monkeypatch.setenv("BIG_BROTHER_HASHBANK_PATH", str(hashbank_path))

    with pytest.raises(ProductionConfigError) as error:
        _ = create_default_app()

    assert "BIG_BROTHER_ADMIN_TOKEN" in str(error.value)


def test_production_default_app_rejects_example_admin_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hashbank_path = tmp_path / "operator-known-match.jsonl"
    entry = _hash_entry("c" * 64)
    _ = hashbank_path.write_text(f"{entry.model_dump_json()}\n", encoding="utf-8")
    monkeypatch.setenv("BIG_BROTHER_DEV_MODE", "false")
    monkeypatch.setenv("BIG_BROTHER_ADMIN_TOKEN", "replace-with-random-production-token")
    monkeypatch.setenv("BIG_BROTHER_HASHBANK_PATH", str(hashbank_path))

    with pytest.raises(ProductionConfigError) as error:
        _ = create_default_app()

    assert "BIG_BROTHER_ADMIN_TOKEN" in str(error.value)


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
