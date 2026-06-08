import anyio
import pytest

from big_brother.domain.policy import ModelSignal, ModelSignalAction, ModelSignalCategory
from big_brother.models.batcher import (
    AsyncModerationBatcher,
    BatchCardinalityError,
    BatchInferenceError,
)

EXPECTED_REQUESTS = 3
FAILURE_MESSAGE = "model failed"


class RecordingModerationClient:
    def __init__(self) -> None:
        self.calls: list[tuple[bytes, ...]] = []

    def classify_many(self, *, image_bytes_list: tuple[bytes, ...]) -> tuple[ModelSignal, ...]:
        self.calls.append(image_bytes_list)
        return tuple(
            ModelSignal(
                category=ModelSignalCategory.EXPLICIT,
                score=0.9,
                action=ModelSignalAction.REVIEW_REQUIRED,
                model_name="fixture/nsfw",
                model_version="main",
            )
            for _ in image_bytes_list
        )


class FailingModerationClient:
    def classify_many(self, *, image_bytes_list: tuple[bytes, ...]) -> tuple[ModelSignal, ...]:
        _ = image_bytes_list
        raise RuntimeError(FAILURE_MESSAGE)


class ShortModerationClient:
    def classify_many(self, *, image_bytes_list: tuple[bytes, ...]) -> tuple[ModelSignal, ...]:
        _ = image_bytes_list
        return ()


def test_async_moderation_batcher_coalesces_concurrent_requests() -> None:
    async def scenario() -> None:
        client = RecordingModerationClient()
        batcher = AsyncModerationBatcher(
            client=client,
            max_batch_size=3,
            max_wait_ms=100,
            max_pending=10,
        )

        results: list[ModelSignal] = []
        async with batcher, anyio.create_task_group() as task_group:
            for index in range(EXPECTED_REQUESTS):
                task_group.start_soon(_submit, batcher, f"image-{index}".encode(), results)

        assert len(results) == EXPECTED_REQUESTS
        assert client.calls == [(b"image-0", b"image-1", b"image-2")]

    anyio.run(scenario)


def test_async_moderation_batcher_propagates_worker_failure() -> None:
    async def scenario() -> None:
        batcher = AsyncModerationBatcher(
            client=FailingModerationClient(),
            max_batch_size=2,
            max_wait_ms=100,
            max_pending=10,
        )

        async with batcher:
            with pytest.raises(BatchInferenceError):
                _ = await batcher.classify(image_bytes=b"image")

    anyio.run(scenario)


def test_async_moderation_batcher_rejects_short_result_batch() -> None:
    async def scenario() -> None:
        batcher = AsyncModerationBatcher(
            client=ShortModerationClient(),
            max_batch_size=2,
            max_wait_ms=100,
            max_pending=10,
        )

        async with batcher:
            with pytest.raises(BatchCardinalityError):
                _ = await batcher.classify(image_bytes=b"image")

    anyio.run(scenario)


async def _submit(
    batcher: AsyncModerationBatcher,
    image_bytes: bytes,
    results: list[ModelSignal],
) -> None:
    results.append(await batcher.classify(image_bytes=image_bytes))
