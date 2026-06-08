from collections.abc import Callable, Sequence

from big_brother.domain.policy import ModelSignalAction
from big_brother.models.config import ModerationInferenceConfig
from big_brother.models.hf_moderation import TransformersImageModerationClient
from big_brother.models.pipeline_types import PipelineImage, PipelinePrediction

EXPECTED_BATCH_SIZE = 4
OOM_MESSAGE = "CUDA out of memory"


class RecordingBatchPipeline:
    def __init__(
        self,
        predictions: tuple[tuple[PipelinePrediction, ...], ...],
    ) -> None:
        self.predictions: tuple[tuple[PipelinePrediction, ...], ...] = predictions
        self.calls: list[tuple[int, int, str, int | None]] = []

    def __call__(
        self,
        image: PipelineImage | Sequence[PipelineImage],
        *,
        top_k: int,
        function_to_apply: str,
        batch_size: int | None = None,
    ) -> tuple[tuple[PipelinePrediction, ...], ...]:
        image_count = len(image) if isinstance(image, Sequence) else 1
        self.calls.append((image_count, top_k, function_to_apply, batch_size))
        return self.predictions


class OomOncePipeline:
    def __init__(self) -> None:
        self.batch_sizes: list[int | None] = []

    def __call__(
        self,
        image: PipelineImage | Sequence[PipelineImage],
        *,
        top_k: int,
        function_to_apply: str,
        batch_size: int | None = None,
    ) -> tuple[tuple[PipelinePrediction, ...], ...]:
        _ = image
        _ = top_k
        _ = function_to_apply
        self.batch_sizes.append(batch_size)
        if batch_size == EXPECTED_BATCH_SIZE * 2:
            raise RuntimeError(OOM_MESSAGE)
        image_count = len(image) if isinstance(image, Sequence) else 1
        return tuple((PipelinePrediction(label="nsfw", score=0.9),) for _ in range(image_count))


def test_classify_many_uses_one_pipeline_call_with_configured_batch_size() -> None:
    pipeline = RecordingBatchPipeline(
        (
            (PipelinePrediction(label="normal", score=0.9),),
            (PipelinePrediction(label="nsfw", score=0.95),),
        ),
    )
    config = ModerationInferenceConfig(
        model_name="fixture/nsfw",
        device="cpu",
        batch_size=EXPECTED_BATCH_SIZE,
        threshold=0.7,
        explicit_labels=("nsfw",),
    )
    client = TransformersImageModerationClient(
        config=config,
        pipeline_factory=_factory(pipeline),
    )

    signals = client.classify_many(
        image_bytes_list=(
            _minimal_png(),
            _minimal_png(),
        ),
    )

    assert [signal.action for signal in signals] == [
        ModelSignalAction.NO_ACTION,
        ModelSignalAction.REVIEW_REQUIRED,
    ]
    assert pipeline.calls == [(2, config.top_k, config.function_to_apply, EXPECTED_BATCH_SIZE)]


def test_classify_many_auto_batch_calibrates_to_largest_safe_batch_size() -> None:
    pipeline = OomOncePipeline()
    config = ModerationInferenceConfig(
        model_name="fixture/nsfw",
        device="cpu",
        batch_size="auto",
        auto_batch_min=2,
        auto_batch_max=16,
        auto_batch_growth_factor=2,
        threshold=0.7,
        explicit_labels=("nsfw",),
    )
    client = TransformersImageModerationClient(
        config=config,
        pipeline_factory=_factory(pipeline),
    )

    signals = client.classify_many(image_bytes_list=(_minimal_png(), _minimal_png()))

    assert [signal.action for signal in signals] == [
        ModelSignalAction.REVIEW_REQUIRED,
        ModelSignalAction.REVIEW_REQUIRED,
    ]
    assert pipeline.batch_sizes == [
        2,
        EXPECTED_BATCH_SIZE,
        EXPECTED_BATCH_SIZE * 2,
        EXPECTED_BATCH_SIZE,
    ]


def _factory(
    pipeline: RecordingBatchPipeline | OomOncePipeline,
) -> Callable[[ModerationInferenceConfig], RecordingBatchPipeline | OomOncePipeline]:
    def create(_: ModerationInferenceConfig) -> RecordingBatchPipeline | OomOncePipeline:
        return pipeline

    return create


def _minimal_png() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
        b"\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe"
        b"\x02\xfeA\xe2!\xbc\x00\x00\x00\x00IEND\xaeB`\x82"
    )
