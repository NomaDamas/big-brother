from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class ArtifactKind(StrEnum):
    REVIEW_ARTIFACT = "review_artifact"
    AUDIT_HASH = "audit_hash"


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    review_artifact_days: int
    audit_hash_days: int

    def is_expired(self, *, artifact: ArtifactKind, created_at: datetime, now: datetime) -> bool:
        match artifact:
            case ArtifactKind.REVIEW_ARTIFACT:
                max_age = timedelta(days=self.review_artifact_days)
            case ArtifactKind.AUDIT_HASH:
                max_age = timedelta(days=self.audit_hash_days)
        return now - created_at > max_age
