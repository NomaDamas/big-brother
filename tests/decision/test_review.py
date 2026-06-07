from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from big_brother.audit.log import AuditLog
from big_brother.decision.review import HumanReviewWorkflow, MissingOverrideReasonError

if TYPE_CHECKING:
    from pathlib import Path


def test_human_override_requires_reason_and_audit_event(tmp_path: Path) -> None:
    audit = AuditLog(path=tmp_path / "audit.jsonl")
    workflow = HumanReviewWorkflow(audit_log=audit)

    with pytest.raises(MissingOverrideReasonError) as error:
        workflow.override(review_id="review_1", decision="allowed", reason="")

    assert "override reason required" in str(error.value)

    workflow.override(review_id="review_1", decision="allowed", reason="false positive")
    exported = audit.export_jsonl()

    assert "human_override" in exported
    assert "false positive" in exported
