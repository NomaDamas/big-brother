import json
from pathlib import Path
from typing import ClassVar, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

DeviceName = Literal["cpu", "cuda", "auto"]
ActivationName = Literal["none", "sigmoid", "softmax"]
type YamlValue = str | int | float | bool | None | list[YamlValue] | dict[str, YamlValue]


class ModerationInferenceConfig(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    model_name: str = Field(min_length=1)
    model_revision: str = Field(default="main", min_length=1)
    device: DeviceName = "cuda"
    top_k: int = Field(default=2, ge=1, le=20)
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    threshold_owner: str = Field(default="security", min_length=1)
    threshold_reviewed_at: str = Field(default="2026-06-07", min_length=1)
    threshold_rationale: str = Field(
        default=(
            "Route high-confidence explicit classifier output to human review; "
            "below-threshold output records no_action."
        ),
        min_length=1,
    )
    image_size: int = Field(default=224, ge=1)
    timeout_seconds: int = Field(default=60, ge=1)
    function_to_apply: ActivationName = "softmax"
    explicit_labels: tuple[str, ...] = Field(default=("nsfw", "explicit", "porn", "sexy"))


def load_moderation_config(path: Path) -> ModerationInferenceConfig:
    yaml_adapter: TypeAdapter[YamlValue] = TypeAdapter(YamlValue)
    data = yaml_adapter.validate_json(
        json.dumps(yaml.safe_load(path.read_text(encoding="utf-8"))),
    )
    return TypeAdapter(ModerationInferenceConfig).validate_python(data)
