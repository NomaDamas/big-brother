from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class AuditEvent(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    event_type: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    user_pseudonym: str = Field(min_length=1)
    occurred_at: datetime
    detail: str = Field(min_length=1)


class ScanAuditOutcome(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    match_found: bool
    model_signal_recorded: bool = False
    decision: str | None = None
    decision_reason: str | None = None



class AuditLog:
    def __init__(self, *, path: Path) -> None:
        self._path: Path = path
        self._adapter: TypeAdapter[AuditEvent] = TypeAdapter(AuditEvent)

    def record_scan_flow(
        self,
        *,
        request_id: str,
        user_identifier: str,
        outcome: ScanAuditOutcome,
    ) -> None:
        pseudonym = pseudonymize_user(user_identifier)
        self._append(
            event_type="ingest",
            request_id=request_id,
            user_pseudonym=pseudonym,
            detail="image_received",
        )
        self._append(
            event_type="scan",
            request_id=request_id,
            user_pseudonym=pseudonym,
            detail="hash_and_model_checks_started",
        )
        if outcome.match_found:
            self._append(
                event_type="match",
                request_id=request_id,
                user_pseudonym=pseudonym,
                detail="known_illegal_match",
            )
        if outcome.model_signal_recorded:
            self._append(
                event_type="model_signal",
                request_id=request_id,
                user_pseudonym=pseudonym,
                detail=outcome.decision_reason or "policy_model_signal",
            )
        self._append(
            event_type="decision",
            request_id=request_id,
            user_pseudonym=pseudonym,
            detail=outcome.decision or ("blocked" if outcome.match_found else "allowed"),
        )

    def export_events(self) -> tuple[AuditEvent, ...]:
        if not self._path.exists():
            return ()
        events: list[AuditEvent] = []
        with self._path.open(encoding="utf-8") as lines:
            for line in lines:
                if line.strip() == "":
                    continue
                events.append(self._adapter.validate_json(line))
        return tuple(events)

    def export_jsonl(self) -> str:
        if not self._path.exists():
            return ""
        return self._path.read_text(encoding="utf-8")

    def record_human_override(self, *, review_id: str, decision: str, reason: str) -> None:
        self._append(
            event_type="human_override",
            request_id=review_id,
            user_pseudonym="user_pseudo_system",
            detail=f"{decision}:{reason}",
        )

    def _append(
        self,
        *,
        event_type: str,
        request_id: str,
        user_pseudonym: str,
        detail: str,
    ) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        event = AuditEvent(
            event_type=event_type,
            request_id=request_id,
            user_pseudonym=user_pseudonym,
            occurred_at=datetime.now(tz=UTC),
            detail=detail,
        )
        with self._path.open("a", encoding="utf-8") as audit_file:
            _ = audit_file.write(f"{event.model_dump_json()}\n")


def pseudonymize_user(user_identifier: str) -> str:
    digest = sha256(user_identifier.encode("utf-8")).hexdigest()[:16]
    return f"user_pseudo_{digest}"
