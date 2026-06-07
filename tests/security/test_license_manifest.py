from __future__ import annotations

from big_brother.security.manifest import default_license_manifest


def test_every_default_model_has_license_entry() -> None:
    manifest = default_license_manifest()
    names = {entry.name for entry in manifest.entries}

    assert "big-brother project code" in names
    assert "NVIDIA Triton Inference Server" in names
    assert "ThreatExchange PDQ reference" in names
    assert "FAISS optional similarity index" in names
    assert "fixture_classifier" in names
    assert manifest.entries_without_license() == ()
