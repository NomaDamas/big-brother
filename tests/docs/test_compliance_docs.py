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


def test_public_docs_describe_scan_scope_truthfully() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    api = (ROOT / "docs" / "api.md").read_text(encoding="utf-8")

    assert "Upload scanning computes SHA-256 exact matches" in readme
    assert "PDQ support is for precomputed hash-bank entries" in readme
    assert "does not compute PDQ hashes for uploads" in api
    assert "BIG_BROTHER_MODEL_TRIAGE_ENABLED=false" in api


def test_operator_guide_covers_production_configuration() -> None:
    guide = (ROOT / "docs" / "operator-guide.md").read_text(encoding="utf-8")

    assert "BIG_BROTHER_HASHBANK_PATH" in guide
    assert "BIG_BROTHER_DEV_MODE=false" in guide
    assert "BIG_BROTHER_ADMIN_TOKEN" in guide
    assert "read-only" in guide
    assert "missing or empty production hash bank" in guide
