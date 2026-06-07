from __future__ import annotations

from datetime import UTC, datetime

from big_brother.domain.hashes import HashAlgorithm, HashBankEntry, RevocationStatus
from big_brother.matching.engine import KnownContentMatcher, hamming_distance

MATCH_DISTANCE = 2
MISS_DISTANCE = 4


def test_pdq_match_respects_hamming_threshold() -> None:
    query = "0" * 63 + "0"
    stored = "0" * 63 + "3"
    entry = _pdq_entry(hash_value=stored, threshold=MATCH_DISTANCE)

    decision = KnownContentMatcher(entries=(entry,)).scan_pdq(query)

    assert hamming_distance(query, stored) == MATCH_DISTANCE
    assert decision.decision == "blocked"
    assert decision.reason == "known_illegal_match"
    assert decision.matches[0].distance == MATCH_DISTANCE


def test_pdq_match_below_threshold_is_no_match() -> None:
    query = "0" * 63 + "0"
    stored = "0" * 63 + "f"
    entry = _pdq_entry(hash_value=stored, threshold=MATCH_DISTANCE)

    decision = KnownContentMatcher(entries=(entry,)).scan_pdq(query)

    assert hamming_distance(query, stored) == MISS_DISTANCE
    assert decision.decision == "allowed"
    assert decision.matches == ()


def _pdq_entry(*, hash_value: str, threshold: int) -> HashBankEntry:
    return HashBankEntry(
        source="operator_fixture",
        authority="internal_test",
        algorithm=HashAlgorithm.PDQ,
        hash_value=hash_value,
        content_class="synthetic_illegal_fixture",
        threshold=threshold,
        received_at=datetime(2026, 6, 7, tzinfo=UTC),
        version="fixture-v1",
        revocation_status=RevocationStatus.ACTIVE,
        retention_status="active",
    )
