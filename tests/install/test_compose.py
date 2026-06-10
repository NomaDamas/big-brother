from __future__ import annotations

from pathlib import Path


def test_compose_has_gpu_reservation_for_triton() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "api:" in compose
    assert "triton:" in compose
    assert "driver: nvidia" in compose
    assert "capabilities: [gpu]" in compose


def test_compose_mounts_operator_hashbank_read_only() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "BIG_BROTHER_HASHBANK_PATH" in compose
    assert "./data/hashbanks:/data/hashbanks:ro" in compose
    assert "BIG_BROTHER_MODEL_CONFIG_PATH" in compose


def test_dockerfile_does_not_copy_test_hashbanks() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "tests/fixtures/hashbanks" not in dockerfile
