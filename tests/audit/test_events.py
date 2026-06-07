from __future__ import annotations

from typing import TYPE_CHECKING

from big_brother.audit.log import AuditLog

if TYPE_CHECKING:
    from pathlib import Path


def test_scan_writes_ingest_match_decision_events(tmp_path: Path) -> None:
    audit = AuditLog(path=tmp_path / "audit.jsonl")

    audit.record_scan_flow(
        request_id="req_1",
        user_identifier="raw-user@example.com",
        match_found=True,
    )
    events = audit.export_events()

    assert [event.event_type for event in events] == ["ingest", "scan", "match", "decision"]


def test_audit_log_redacts_raw_user_identifier(tmp_path: Path) -> None:
    audit = AuditLog(path=tmp_path / "audit.jsonl")

    audit.record_scan_flow(
        request_id="req_1",
        user_identifier="raw-user@example.com",
        match_found=True,
    )
    exported = audit.export_jsonl()

    assert "raw-user@example.com" not in exported
    assert "user_pseudo_" in exported
