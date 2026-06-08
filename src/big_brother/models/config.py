from __future__ import annotations

import json
from typing import TYPE_CHECKING, ClassVar, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

if TYPE_CHECKING:
    from pathlib import Path

DeviceName = Literal["cpu", "cuda", "auto"]
ActivationName = Literal["none", "sigmoid", "softmax"]
BatchSize = int | Literal["auto"]
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
    batch_size: BatchSize = Field(default=1)
    auto_batch_min: int = Field(default=1, ge=1)
    auto_batch_max: int = Field(default=64, ge=1)
    auto_batch_growth_factor: int = Field(default=2, ge=2)
    queue_max_batch_size: int = Field(default=16, ge=1)
    queue_max_wait_ms: int = Field(default=25, ge=0)
    queue_max_pending: int = Field(default=1024, ge=1)
    function_to_apply: ActivationName = "softmax"
    explicit_labels: tuple[str, ...] = Field(default=("nsfw", "explicit", "porn", "sexy"))

    @field_validator("batch_size")
    @classmethod
    def _positive_batch_size(cls, value: BatchSize) -> BatchSize:
        match value:
            case "auto":
                return value
            case int() if value >= 1:
                return value
            case int():
                message = "batch_size must be a positive integer or auto"
                raise ValueError(message)

    @model_validator(mode="after")
    def _valid_auto_batch_bounds(self) -> Self:
        if self.auto_batch_min > self.auto_batch_max:
            message = "auto_batch_min must be less than or equal to auto_batch_max"
            raise ValueError(message)
        return self


def load_moderation_config(path: Path) -> ModerationInferenceConfig:
    yaml_adapter: TypeAdapter[YamlValue] = TypeAdapter(YamlValue)
    data = yaml_adapter.validate_json(
        json.dumps(yaml.safe_load(path.read_text(encoding="utf-8"))),
    )
    return TypeAdapter(ModerationInferenceConfig).validate_python(data)
