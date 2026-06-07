from pathlib import Path

import pytest
from pydantic import ValidationError

from big_brother.models.config import load_moderation_config

EXPECTED_TOP_K = 3
EXPECTED_THRESHOLD = 0.7
EXPECTED_IMAGE_SIZE = 224
EXPECTED_TIMEOUT_SECONDS = 30


def test_load_moderation_config_from_yaml_parses_hyperparameters(tmp_path: Path) -> None:
    config_path = tmp_path / "model-inference.yaml"
    _ = config_path.write_text(
        "\n".join(
            [
                "model_name: Falconsai/nsfw_image_detection",
                "device: cuda",
                "top_k: 3",
                "threshold: 0.7",
                "threshold_owner: security",
                'threshold_reviewed_at: "2026-06-07"',
                "threshold_rationale: Route high-confidence explicit classifier output to review.",
                "image_size: 224",
                "timeout_seconds: 30",
                "function_to_apply: sigmoid",
                "explicit_labels:",
                "  - nsfw",
                "  - explicit",
            ],
        ),
        encoding="utf-8",
    )

    config = load_moderation_config(config_path)

    assert config.model_name == "Falconsai/nsfw_image_detection"
    assert config.device == "cuda"
    assert config.top_k == EXPECTED_TOP_K
    assert config.threshold == EXPECTED_THRESHOLD
    assert config.threshold_owner == "security"
    assert config.threshold_reviewed_at == "2026-06-07"
    assert config.threshold_rationale != ""
    assert config.image_size == EXPECTED_IMAGE_SIZE
    assert config.timeout_seconds == EXPECTED_TIMEOUT_SECONDS
    assert config.function_to_apply == "sigmoid"
    assert config.explicit_labels == ("nsfw", "explicit")


def test_load_moderation_config_rejects_invalid_threshold(tmp_path: Path) -> None:
    config_path = tmp_path / "model-inference.yaml"
    _ = config_path.write_text(
        "\n".join(
            [
                "model_name: Falconsai/nsfw_image_detection",
                "threshold: 1.1",
            ],
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        _ = load_moderation_config(config_path)
