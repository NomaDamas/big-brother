import json
from collections.abc import Sized
from pathlib import Path
from typing import cast, final

import pytest
from typer.testing import CliRunner

from big_brother.domain.policy import ModelSignal, ModelSignalAction, ModelSignalCategory
from big_brother.models import moderation_check
from big_brother.models.config import ModerationInferenceConfig
from big_brother.models.moderation_check import app

EXPECTED_IMAGE_COUNT = 2


@final
class FakeModerationClient:
    def __init__(self, *, config: ModerationInferenceConfig) -> None:
        self.config = config
        self.resolved_batch_size = 2

    def classify_many(self, *, image_bytes_list: tuple[bytes, ...]) -> tuple[ModelSignal, ...]:
        return tuple(
            ModelSignal(
                category=ModelSignalCategory.EXPLICIT,
                score=0.9,
                action=ModelSignalAction.REVIEW_REQUIRED,
                model_name=self.config.model_name,
                model_version=self.config.model_revision,
            )
            for _ in image_bytes_list
        )


def test_moderation_check_accepts_multiple_images(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(moderation_check, "TransformersImageModerationClient", FakeModerationClient)
    monkeypatch.setattr(moderation_check, "cuda_is_available", lambda: False)
    config_path = tmp_path / "model-inference.yaml"
    image_path = tmp_path / "image.png"
    _ = config_path.write_text(
        "\n".join(
            [
                "model_name: fixture/nsfw",
                "device: cpu",
                "batch_size: 2",
            ],
        ),
        encoding="utf-8",
    )
    _ = image_path.write_bytes(_minimal_png())
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "--config",
            str(config_path),
            "--image",
            str(image_path),
            "--image",
            str(image_path),
        ],
    )

    assert result.exit_code == 0
    payload = cast("dict[str, object]", json.loads(result.stdout))
    assert payload["image_count"] == EXPECTED_IMAGE_COUNT
    assert payload["effective_batch_size"] == EXPECTED_IMAGE_COUNT
    results = payload["results"]
    assert isinstance(results, Sized)
    assert len(results) == EXPECTED_IMAGE_COUNT


def test_moderation_check_can_coalesce_cli_requests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(moderation_check, "TransformersImageModerationClient", FakeModerationClient)
    monkeypatch.setattr(moderation_check, "cuda_is_available", lambda: False)
    config_path = tmp_path / "model-inference.yaml"
    image_path = tmp_path / "image.png"
    _ = config_path.write_text(
        "\n".join(
            [
                "model_name: fixture/nsfw",
                "device: cpu",
                "batch_size: 2",
                "queue_max_batch_size: 2",
                "queue_max_wait_ms: 50",
                "queue_max_pending: 10",
            ],
        ),
        encoding="utf-8",
    )
    _ = image_path.write_bytes(_minimal_png())
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "--config",
            str(config_path),
            "--image",
            str(image_path),
            "--image",
            str(image_path),
            "--coalesce-requests",
        ],
    )

    assert result.exit_code == 0
    payload = cast("dict[str, object]", json.loads(result.stdout))
    assert payload["coalesced_requests"] is True
    assert payload["image_count"] == EXPECTED_IMAGE_COUNT
    results = payload["results"]
    assert isinstance(results, Sized)
    assert len(results) == EXPECTED_IMAGE_COUNT


def _minimal_png() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
        b"\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe"
        b"\x02\xfeA\xe2!\xbc\x00\x00\x00\x00IEND\xaeB`\x82"
    )
