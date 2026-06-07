from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_docs_include_non_legal_advice_and_unknown_ai_limitations() -> None:
    compliance = (ROOT / "docs" / "compliance.md").read_text(encoding="utf-8")
    model_policy = (ROOT / "docs" / "model-policy.md").read_text(encoding="utf-8")

    assert "not legal advice" in compliance
    assert "compliance-support tooling" in compliance
    assert "must not determine illegality" in model_policy
    assert "review_required" in model_policy


def test_docs_include_dated_legal_source_table_and_review_checklist() -> None:
    compliance = (ROOT / "docs" / "compliance.md").read_text(encoding="utf-8")

    assert "| Source | Date checked | Why it matters |" in compliance
    assert "2026-06-07" in compliance
    assert "Legal review checklist" in compliance
    assert "- [ ] Confirm covered-business applicability" in compliance


def test_docs_do_not_make_forbidden_affirmative_claims() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            ROOT / "README.md",
            ROOT / "docs" / "compliance.md",
            ROOT / "docs" / "model-policy.md",
        ]
    )

    assert "guaranteed compliance" not in combined
    assert "AI determines illegality" not in combined
