from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003 - Typer needs the concrete runtime type.
from typing import TYPE_CHECKING, Annotated

import anyio
import typer

from big_brother.models.batcher import AsyncModerationBatcher
from big_brother.models.config import load_moderation_config
from big_brother.models.hf_moderation import (
    CudaRequiredError,
    TransformersImageModerationClient,
    cuda_is_available,
)

if TYPE_CHECKING:
    from big_brother.domain.policy import ModelSignal

app = typer.Typer(add_completion=False)


@app.command()
def main(
    config: Annotated[Path, typer.Option("--config", exists=True, readable=True)],
    image: Annotated[list[Path], typer.Option("--image", exists=True, readable=True)],
    require_cuda: Annotated[bool, typer.Option("--require-cuda")] = False,  # noqa: FBT002
    coalesce_requests: Annotated[bool, typer.Option("--coalesce-requests")] = False,  # noqa: FBT002
) -> None:
    cuda_available = cuda_is_available()
    if require_cuda and not cuda_available:
        raise CudaRequiredError
    inference_config = load_moderation_config(config)
    if not image:
        message = "at least one --image path is required"
        raise typer.BadParameter(message)
    client = TransformersImageModerationClient(config=inference_config)
    image_bytes_list = tuple(path.read_bytes() for path in image)
    if coalesce_requests:
        signals = anyio.run(
            _classify_with_coalescing,
            client,
            image_bytes_list,
            inference_config.queue_max_batch_size,
            inference_config.queue_max_wait_ms,
            inference_config.queue_max_pending,
        )
    else:
        signals = client.classify_many(image_bytes_list=image_bytes_list)
    typer.echo(
        json.dumps(
            {
                "coalesced_requests": coalesce_requests,
                "cuda_available": cuda_available,
                "configured_device": inference_config.device,
                "configured_batch_size": inference_config.batch_size,
                "effective_batch_size": client.resolved_batch_size,
                "image_count": len(image),
                "model_name": inference_config.model_name,
                "model_version": (
                    signals[0].model_version if signals else inference_config.model_revision
                ),
                "results": tuple(
                    {
                        "action": signal.action.value,
                        "category": signal.category.value,
                        "image": str(path),
                        "passed_threshold": signal.score >= inference_config.threshold,
                        "score": signal.score,
                    }
                    for path, signal in zip(image, signals, strict=True)
                ),
                "threshold": inference_config.threshold,
            },
            sort_keys=True,
        ),
    )


async def _classify_with_coalescing(
    client: TransformersImageModerationClient,
    image_bytes_list: tuple[bytes, ...],
    max_batch_size: int,
    max_wait_ms: int,
    max_pending: int,
) -> tuple[ModelSignal, ...]:
    results: list[ModelSignal | None] = [None for _ in image_bytes_list]
    async with (
        AsyncModerationBatcher(
            client=client,
            max_batch_size=max_batch_size,
            max_wait_ms=max_wait_ms,
            max_pending=max_pending,
        ) as batcher,
        anyio.create_task_group() as task_group,
    ):
        for index, image_bytes in enumerate(image_bytes_list):
            task_group.start_soon(_classify_one, batcher, image_bytes, results, index)
    return tuple(result for result in results if result is not None)


async def _classify_one(
    batcher: AsyncModerationBatcher,
    image_bytes: bytes,
    results: list[ModelSignal | None],
    index: int,
) -> None:
    results[index] = await batcher.classify(image_bytes=image_bytes)


if __name__ == "__main__":
    app()
