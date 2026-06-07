from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from big_brother.domain.hashes import HashAlgorithm, HashBankEntry, RevocationStatus
from big_brother.matching.engine import KnownContentMatcher, compute_sha256

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "images"


def test_exact_sha256_match_blocks_seeded_benign_fixture() -> None:
    image_bytes = (FIXTURES / "known_match.bin").read_bytes()
    entry = HashBankEntry(
        source="operator_fixture",
        authority="internal_test",
        algorithm=HashAlgorithm.SHA256,
        hash_value=compute_sha256(image_bytes),
        content_class="synthetic_illegal_fixture",
        threshold=0,
        received_at=datetime(2026, 6, 7, tzinfo=UTC),
        version="fixture-v1",
        revocation_status=RevocationStatus.ACTIVE,
        retention_status="active",
    )

    decision = KnownContentMatcher(entries=(entry,)).scan(image_bytes)

    assert decision.decision == "blocked"
    assert decision.reason == "known_illegal_match"
    assert decision.matches[0].algorithm is HashAlgorithm.SHA256
