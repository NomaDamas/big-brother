from __future__ import annotations

import importlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from io import BytesIO
from typing import Protocol, runtime_checkable

from big_brother.domain.policy import ModelSignal, ModelSignalAction, ModelSignalCategory
from big_brother.models.batch import BatchCalibrationConfig, calibrate_batch_size
from big_brother.models.config import DeviceName, ModerationInferenceConfig
from big_brother.models.pipeline_types import (
    CreatedPipeline,
    PipelineImage,
    PipelinePrediction,
    is_pipeline_row,
    prediction_batches,
    predictions_from_rows,
    row_batches,
)


class ModerationPipeline(Protocol):
    def __call__(
        self,
        image: PipelineImage | Sequence[PipelineImage],
        *,
        top_k: int,
        function_to_apply: str,
        batch_size: int | None = None,
    ) -> Sequence[PipelinePrediction] | Sequence[Sequence[PipelinePrediction]]: ...


PipelineFactory = Callable[[ModerationInferenceConfig], ModerationPipeline]


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
        message = f"install GPU inference dependencies with `uv sync --group gpu`: {package}"
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
        self._resolved_batch_size: int | None = None

    def classify(self, *, image_bytes: bytes) -> ModelSignal:
        return self.classify_many(image_bytes_list=(image_bytes,))[0]

    def classify_many(self, *, image_bytes_list: Sequence[bytes]) -> tuple[ModelSignal, ...]:
        if not image_bytes_list:
            return ()
        images = tuple(
            _open_image(
                image_bytes=image_bytes,
                image_size=self._config.image_size,
            )
            for image_bytes in image_bytes_list
        )
        predictions = self._pipeline(
            list(images),
            top_k=self._config.top_k,
            function_to_apply=self._config.function_to_apply,
            batch_size=self._batch_size(sample_image=images[0]),
        )
        return tuple(
            _signal_from_predictions(
                predictions=item_predictions,
                config=self._config,
            )
            for item_predictions in prediction_batches(predictions)
        )

    @property
    def resolved_batch_size(self) -> int | None:
        return self._resolved_batch_size

    def _batch_size(self, *, sample_image: PipelineImage) -> int:
        if self._resolved_batch_size is not None:
            return self._resolved_batch_size
        configured_batch_size = self._config.batch_size
        match configured_batch_size:
            case "auto":
                self._resolved_batch_size = calibrate_batch_size(
                    config=BatchCalibrationConfig(
                        minimum=self._config.auto_batch_min,
                        maximum=self._config.auto_batch_max,
                        growth_factor=self._config.auto_batch_growth_factor,
                    ),
                    probe=lambda batch_size: self._probe_batch_size(
                        sample_image=sample_image,
                        batch_size=batch_size,
                    ),
                )
            case int() as explicit_batch_size:
                self._resolved_batch_size = explicit_batch_size
        return self._resolved_batch_size

    def _probe_batch_size(self, *, sample_image: PipelineImage, batch_size: int) -> None:
        _ = self._pipeline(
            [sample_image for _ in range(batch_size)],
            top_k=self._config.top_k,
            function_to_apply=self._config.function_to_apply,
            batch_size=batch_size,
        )


def _signal_from_predictions(
    *,
    predictions: Sequence[PipelinePrediction],
    config: ModerationInferenceConfig,
) -> ModelSignal:
    explicit_prediction = _best_explicit_prediction(
        predictions=predictions,
        explicit_labels=config.explicit_labels,
    )
    action = _action_for_score(
        score=explicit_prediction.score,
        threshold=config.threshold,
    )
    return ModelSignal(
        category=ModelSignalCategory.EXPLICIT,
        score=explicit_prediction.score,
        action=action,
        model_name=config.model_name,
        model_version=config.model_revision,
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
        image: PipelineImage | Sequence[PipelineImage],
        *,
        top_k: int,
        function_to_apply: str,
        batch_size: int | None = None,
    ) -> Sequence[PipelinePrediction] | Sequence[Sequence[PipelinePrediction]]:
        rows = self.created_pipeline(
            image,
            top_k=top_k,
            function_to_apply=function_to_apply,
            batch_size=batch_size,
        )
        batches = row_batches(rows)
        if len(batches) == 1 and is_pipeline_row(rows[0]):
            return predictions_from_rows(batches[0])
        return tuple(predictions_from_rows(batch) for batch in batches)


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
