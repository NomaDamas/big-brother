from __future__ import annotations

import importlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from io import BytesIO
from typing import Protocol, runtime_checkable

from big_brother.domain.policy import ModelSignal, ModelSignalAction, ModelSignalCategory
from big_brother.models.config import DeviceName, ModerationInferenceConfig


@dataclass(frozen=True, slots=True)
class PipelinePrediction:
    label: str
    score: float


class PipelineImage(Protocol):
    mode: str
    size: tuple[int, int]

    def convert(self, mode: str) -> PipelineImage: ...

    def resize(self, size: tuple[int, int]) -> PipelineImage: ...


class ModerationPipeline(Protocol):
    def __call__(
        self,
        image: PipelineImage,
        *,
        top_k: int,
        function_to_apply: str,
    ) -> Sequence[PipelinePrediction]: ...


PipelineFactory = Callable[[ModerationInferenceConfig], ModerationPipeline]


class PipelineRow(Protocol):
    def __getitem__(self, key: str) -> str | float: ...


class CreatedPipeline(Protocol):
    def __call__(
        self,
        image: PipelineImage,
        *,
        top_k: int,
        function_to_apply: str,
    ) -> Sequence[PipelineRow]: ...


@runtime_checkable
class TransformersModule(Protocol):
    def pipeline(
        self,
        *,
        task: str,
        model: str,
        revision: str,
        device: int,
    ) -> CreatedPipeline: ...


@runtime_checkable
class CudaModule(Protocol):
    def is_available(self) -> bool: ...


@runtime_checkable
class TorchModule(Protocol):
    cuda: CudaModule


@runtime_checkable
class ImageModule(Protocol):
    def open(self, fp: BytesIO) -> PipelineImage: ...


class OptionalModelDependencyError(Exception):
    def __init__(self, *, package: str) -> None:
        self.package: str = package
        message = (
            "install GPU inference dependencies with `uv sync --group gpu`: "
            f"{package}"
        )
        super().__init__(message)


class CudaRequiredError(Exception):
    def __init__(self) -> None:
        super().__init__("CUDA was required for model moderation but is not available")


class TransformersImageModerationClient:
    def __init__(
        self,
        *,
        config: ModerationInferenceConfig,
        pipeline_factory: PipelineFactory | None = None,
    ) -> None:
        self._config: ModerationInferenceConfig = config
        factory = pipeline_factory or default_pipeline_factory
        self._pipeline: ModerationPipeline = factory(config)

    def classify(self, *, image_bytes: bytes) -> ModelSignal:
        image = _open_image(
            image_bytes=image_bytes,
            image_size=self._config.image_size,
        )
        predictions = self._pipeline(
            image,
            top_k=self._config.top_k,
            function_to_apply=self._config.function_to_apply,
        )
        explicit_prediction = _best_explicit_prediction(
            predictions=predictions,
            explicit_labels=self._config.explicit_labels,
        )
        action = _action_for_score(
            score=explicit_prediction.score,
            threshold=self._config.threshold,
        )
        return ModelSignal(
            category=ModelSignalCategory.EXPLICIT,
            score=explicit_prediction.score,
            action=action,
            model_name=self._config.model_name,
            model_version=self._config.model_revision,
        )


def default_pipeline_factory(config: ModerationInferenceConfig) -> ModerationPipeline:
    try:
        module = importlib.import_module("transformers.pipelines")
    except ModuleNotFoundError as error:
        raise OptionalModelDependencyError(package="transformers") from error
    if not isinstance(module, TransformersModule):
        raise OptionalModelDependencyError(package="transformers.pipeline")

    device = _pipeline_device(config.device)
    created_pipeline = module.pipeline(
        task="image-classification",
        model=config.model_name,
        revision=config.model_revision,
        device=device,
    )
    return HuggingFacePipeline(created_pipeline=created_pipeline)


@dataclass(frozen=True, slots=True)
class HuggingFacePipeline:
    created_pipeline: CreatedPipeline

    def __call__(
        self,
        image: PipelineImage,
        *,
        top_k: int,
        function_to_apply: str,
    ) -> Sequence[PipelinePrediction]:
        rows = self.created_pipeline(
            image,
            top_k=top_k,
            function_to_apply=function_to_apply,
        )
        return tuple(
            PipelinePrediction(label=str(row["label"]), score=float(row["score"]))
            for row in rows
        )


def cuda_is_available() -> bool:
    try:
        module = importlib.import_module("torch")
    except ModuleNotFoundError:
        return False
    if not isinstance(module, TorchModule):
        return False
    return module.cuda.is_available()


def _pipeline_device(device: DeviceName) -> int:
    match device:
        case "cpu":
            return -1
        case "cuda":
            if not cuda_is_available():
                raise CudaRequiredError
            return 0
        case "auto":
            if cuda_is_available():
                return 0
            return -1


def _open_image(*, image_bytes: bytes, image_size: int) -> PipelineImage:
    try:
        module = importlib.import_module("PIL.Image")
    except ModuleNotFoundError as error:
        raise OptionalModelDependencyError(package="pillow") from error
    if not isinstance(module, ImageModule):
        raise OptionalModelDependencyError(package="PIL.Image")
    image = module.open(BytesIO(image_bytes)).convert("RGB")
    return image.resize((image_size, image_size))


def _best_explicit_prediction(
    *,
    predictions: Sequence[PipelinePrediction],
    explicit_labels: tuple[str, ...],
) -> PipelinePrediction:
    explicit_label_set = frozenset(label.casefold() for label in explicit_labels)
    explicit_predictions = tuple(
        prediction
        for prediction in predictions
        if prediction.label.casefold() in explicit_label_set
    )
    if explicit_predictions:
        return max(explicit_predictions, key=lambda prediction: prediction.score)
    return PipelinePrediction(label="no_explicit_label", score=0.0)


def _action_for_score(*, score: float, threshold: float) -> ModelSignalAction:
    if score >= threshold:
        return ModelSignalAction.REVIEW_REQUIRED
    return ModelSignalAction.NO_ACTION
