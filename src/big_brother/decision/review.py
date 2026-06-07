from typing import override

from big_brother.audit.log import AuditLog


class MissingOverrideReasonError(ValueError):
    @override
    def __str__(self) -> str:
        return "override reason required"


class HumanReviewWorkflow:
    def __init__(self, *, audit_log: AuditLog) -> None:
        self._audit_log: AuditLog = audit_log

    def override(self, *, review_id: str, decision: str, reason: str) -> None:
        if reason.strip() == "":
            raise MissingOverrideReasonError
        self._audit_log.record_human_override(
            review_id=review_id,
            decision=decision,
            reason=reason,
        )
