from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from big_brother.domain.hashes import HashAlgorithm, HashBankEntry, RevocationStatus


def test_hash_entry_requires_source_and_revocation_status() -> None:
    payload = {
        "algorithm": HashAlgorithm.SHA256,
        "hash_value": "0" * 64,
        "content_class": "synthetic_illegal_fixture",
        "threshold": 0,
        "received_at": datetime(2026, 6, 7, tzinfo=UTC),
        "version": "fixture-v1",
        "retention_status": "active",
    }

    with pytest.raises(ValidationError) as error:
        _ = HashBankEntry.model_validate(payload)

    message = str(error.value)
    assert "source" in message
    assert "revocation_status" in message


def test_hash_entry_accepts_required_provenance() -> None:
    entry = HashBankEntry(
        source="operator_fixture",
        authority="internal_test",
        algorithm=HashAlgorithm.SHA256,
        hash_value="0" * 64,
        content_class="synthetic_illegal_fixture",
        threshold=0,
        received_at=datetime(2026, 6, 7, tzinfo=UTC),
        version="fixture-v1",
        revocation_status=RevocationStatus.ACTIVE,
        retention_status="active",
    )

    assert entry.source == "operator_fixture"
    assert entry.revocation_status is RevocationStatus.ACTIVE
