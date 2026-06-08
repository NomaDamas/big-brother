from pathlib import Path

import pytest
from pydantic import ValidationError

from big_brother.models.config import load_moderation_config

EXPECTED_AUTO_MIN = 2
EXPECTED_AUTO_MAX = 32
EXPECTED_GROWTH_FACTOR = 2
EXPECTED_QUEUE_BATCH = 16
EXPECTED_QUEUE_WAIT_MS = 25
EXPECTED_QUEUE_PENDING = 512


def test_load_moderation_config_parses_batch_and_queue_settings(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "model-inference.yaml"
    _ = config_path.write_text(
        "\n".join(
            [
                "model_name: Falconsai/nsfw_image_detection",
                "batch_size: auto",
                "auto_batch_min: 2",
                "auto_batch_max: 32",
                "auto_batch_growth_factor: 2",
                "queue_max_batch_size: 16",
                "queue_max_wait_ms: 25",
                "queue_max_pending: 512",
            ],
        ),
        encoding="utf-8",
    )

    config = load_moderation_config(config_path)

    assert config.batch_size == "auto"
    assert config.auto_batch_min == EXPECTED_AUTO_MIN
    assert config.auto_batch_max == EXPECTED_AUTO_MAX
    assert config.auto_batch_growth_factor == EXPECTED_GROWTH_FACTOR
    assert config.queue_max_batch_size == EXPECTED_QUEUE_BATCH
    assert config.queue_max_wait_ms == EXPECTED_QUEUE_WAIT_MS
    assert config.queue_max_pending == EXPECTED_QUEUE_PENDING


def test_load_moderation_config_rejects_zero_batch_size(tmp_path: Path) -> None:
    config_path = tmp_path / "model-inference.yaml"
    _ = config_path.write_text(
        "\n".join(
            [
                "model_name: Falconsai/nsfw_image_detection",
                "batch_size: 0",
            ],
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        _ = load_moderation_config(config_path)
