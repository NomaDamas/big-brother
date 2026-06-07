from collections.abc import Callable

from big_brother.domain.policy import ModelSignalAction, ModelSignalCategory
from big_brother.models.config import ModerationInferenceConfig
from big_brother.models.hf_moderation import (
    PipelineImage,
    PipelinePrediction,
    TransformersImageModerationClient,
)

EXPECTED_TOP_K = 5
EXPECTED_NSFW_SCORE = 0.91
BELOW_THRESHOLD_NSFW_SCORE = 0.2
EXPECTED_IMAGE_SIZE = 64


class RecordingPipeline:
    def __init__(self, predictions: tuple[PipelinePrediction, ...]) -> None:
        self.predictions: tuple[PipelinePrediction, ...] = predictions
        self.calls: list[tuple[PipelineImage, int, str]] = []

    def __call__(
        self,
        image: PipelineImage,
        *,
        top_k: int,
        function_to_apply: str,
    ) -> tuple[PipelinePrediction, ...]:
        self.calls.append((image, top_k, function_to_apply))
        return self.predictions


def test_transformers_moderation_client_passes_configured_hyperparameters_to_pipeline() -> None:
    pipeline = RecordingPipeline((PipelinePrediction(label="safe", score=0.95),))
    config = ModerationInferenceConfig(
        model_name="fixture/model",
        device="cpu",
        top_k=5,
        threshold=0.8,
        image_size=EXPECTED_IMAGE_SIZE,
        function_to_apply="softmax",
    )
    client = TransformersImageModerationClient(
        config=config,
        pipeline_factory=_factory(pipeline),
    )

    _ = client.classify(image_bytes=_minimal_png())

    assert pipeline.calls
    image, top_k, function_to_apply = pipeline.calls[0]
    assert image.size == (EXPECTED_IMAGE_SIZE, EXPECTED_IMAGE_SIZE)
    assert top_k == EXPECTED_TOP_K
    assert function_to_apply == "softmax"


def test_transformers_moderation_client_maps_nsfw_label_above_threshold_to_review_signal() -> None:
    pipeline = RecordingPipeline(
        (
            PipelinePrediction(label="normal", score=0.2),
            PipelinePrediction(label="nsfw", score=EXPECTED_NSFW_SCORE),
        ),
    )
    config = ModerationInferenceConfig(
        model_name="fixture/nsfw",
        model_revision="abc123",
        device="cpu",
        top_k=2,
        threshold=0.7,
        explicit_labels=("nsfw",),
    )
    client = TransformersImageModerationClient(
        config=config,
        pipeline_factory=_factory(pipeline),
    )

    signal = client.classify(image_bytes=_minimal_png())

    assert signal.category is ModelSignalCategory.EXPLICIT
    assert signal.score == EXPECTED_NSFW_SCORE
    assert signal.action is ModelSignalAction.REVIEW_REQUIRED
    assert signal.model_name == "fixture/nsfw"
    assert signal.model_version == "abc123"


def test_transformers_moderation_client_maps_nsfw_label_below_threshold_to_no_action() -> None:
    pipeline = RecordingPipeline(
        (PipelinePrediction(label="nsfw", score=BELOW_THRESHOLD_NSFW_SCORE),),
    )
    config = ModerationInferenceConfig(
        model_name="fixture/nsfw",
        device="cpu",
        threshold=0.7,
        explicit_labels=("nsfw",),
    )
    client = TransformersImageModerationClient(
        config=config,
        pipeline_factory=_factory(pipeline),
    )

    signal = client.classify(image_bytes=_minimal_png())

    assert signal.category is ModelSignalCategory.EXPLICIT
    assert signal.score == BELOW_THRESHOLD_NSFW_SCORE
    assert signal.action is ModelSignalAction.NO_ACTION


def _factory(
    pipeline: RecordingPipeline,
) -> Callable[[ModerationInferenceConfig], RecordingPipeline]:
    def create(_: ModerationInferenceConfig) -> RecordingPipeline:
        return pipeline

    return create


def _minimal_png() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
        b"\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe"
        b"\x02\xfeA\xe2!\xbc\x00\x00\x00\x00IEND\xaeB`\x82"
    )
