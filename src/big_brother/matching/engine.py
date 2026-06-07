from dataclasses import dataclass
from hashlib import sha256

from big_brother.domain.hashes import HashAlgorithm, HashBankEntry, RevocationStatus


@dataclass(frozen=True, slots=True)
class MatchResult:
    algorithm: HashAlgorithm
    hash_value: str
    distance: int
    threshold: int
    source: str


@dataclass(frozen=True, slots=True)
class ScanDecision:
    decision: str
    reason: str
    matches: tuple[MatchResult, ...]


class KnownContentMatcher:
    def __init__(self, *, entries: tuple[HashBankEntry, ...]) -> None:
        self._entries: tuple[HashBankEntry, ...] = entries

    def scan(self, image_bytes: bytes) -> ScanDecision:
        sha_result = self.scan_sha256(compute_sha256(image_bytes))
        if sha_result.matches:
            return sha_result
        return ScanDecision(decision="allowed", reason="no_known_match", matches=())

    def scan_sha256(self, hash_value: str) -> ScanDecision:
        matches = tuple(
            MatchResult(
                algorithm=entry.algorithm,
                hash_value=entry.hash_value,
                distance=0,
                threshold=entry.threshold,
                source=entry.source,
            )
            for entry in self._entries
            if entry.algorithm is HashAlgorithm.SHA256
            and entry.hash_value == hash_value
            and entry.revocation_status is RevocationStatus.ACTIVE
        )
        return _decision_from_matches(matches)

    def scan_pdq(self, hash_value: str) -> ScanDecision:
        matches = tuple(
            MatchResult(
                algorithm=entry.algorithm,
                hash_value=entry.hash_value,
                distance=distance,
                threshold=entry.threshold,
                source=entry.source,
            )
            for entry in self._entries
            if entry.algorithm is HashAlgorithm.PDQ
            and entry.revocation_status is RevocationStatus.ACTIVE
            and (distance := hamming_distance(hash_value, entry.hash_value)) <= entry.threshold
        )
        return _decision_from_matches(matches)


def compute_sha256(image_bytes: bytes) -> str:
    return sha256(image_bytes).hexdigest()


def hamming_distance(left_hex: str, right_hex: str) -> int:
    left = int(left_hex, 16)
    right = int(right_hex, 16)
    return (left ^ right).bit_count()


def _decision_from_matches(matches: tuple[MatchResult, ...]) -> ScanDecision:
    if matches:
        return ScanDecision(decision="blocked", reason="known_illegal_match", matches=matches)
    return ScanDecision(decision="allowed", reason="no_known_match", matches=())
