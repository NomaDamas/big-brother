from __future__ import annotations

from datetime import UTC, datetime, timedelta

from big_brother.audit.retention import ArtifactKind, RetentionPolicy


def test_retention_policy_expires_review_artifacts_not_audit_hashes() -> None:
    now = datetime(2026, 6, 7, tzinfo=UTC)
    created_at = now - timedelta(days=31)
    policy = RetentionPolicy(review_artifact_days=30, audit_hash_days=1095)

    assert policy.is_expired(
        artifact=ArtifactKind.REVIEW_ARTIFACT,
        created_at=created_at,
        now=now,
    )
    assert not policy.is_expired(
        artifact=ArtifactKind.AUDIT_HASH,
        created_at=created_at,
        now=now,
    )
