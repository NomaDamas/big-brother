from __future__ import annotations

from pathlib import Path


def test_compose_has_gpu_reservation_for_triton() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "api:" in compose
    assert "triton:" in compose
    assert "driver: nvidia" in compose
    assert "capabilities: [gpu]" in compose
