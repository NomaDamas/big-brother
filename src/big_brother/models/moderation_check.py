from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003 - Typer needs the concrete runtime type.
from typing import Annotated

import typer

from big_brother.models.config import load_moderation_config
from big_brother.models.hf_moderation import (
    CudaRequiredError,
    TransformersImageModerationClient,
    cuda_is_available,
)

app = typer.Typer(add_completion=False)


@app.command()
def main(
    config: Annotated[Path, typer.Option("--config", exists=True, readable=True)],
    image: Annotated[Path, typer.Option("--image", exists=True, readable=True)],
    require_cuda: Annotated[bool, typer.Option("--require-cuda")] = False,  # noqa: FBT002
) -> None:
    cuda_available = cuda_is_available()
    if require_cuda and not cuda_available:
        raise CudaRequiredError
    inference_config = load_moderation_config(config)
    signal = TransformersImageModerationClient(config=inference_config).classify(
        image_bytes=image.read_bytes(),
    )
    typer.echo(
        json.dumps(
            {
                "cuda_available": cuda_available,
                "configured_device": inference_config.device,
                "model_name": signal.model_name,
                "model_version": signal.model_version,
                "category": signal.category.value,
                "score": signal.score,
                "action": signal.action.value,
                "threshold": inference_config.threshold,
                "passed_threshold": signal.score >= inference_config.threshold,
            },
            sort_keys=True,
        ),
    )


if __name__ == "__main__":
    app()
