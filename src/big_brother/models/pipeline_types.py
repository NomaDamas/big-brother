from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, TypeGuard

if TYPE_CHECKING:
    from collections.abc import Sequence

type PipelineRow = Mapping[str, str | float]


@dataclass(frozen=True, slots=True)
class PipelinePrediction:
    label: str
    score: float


class PipelineImage(Protocol):
    mode: str
    size: tuple[int, int]

    def convert(self, mode: str) -> PipelineImage: ...

    def resize(self, size: tuple[int, int]) -> PipelineImage: ...


class CreatedPipeline(Protocol):
    def __call__(
        self,
        image: PipelineImage | Sequence[PipelineImage],
        *,
        top_k: int,
        function_to_apply: str,
        batch_size: int | None = None,
    ) -> Sequence[PipelineRow] | Sequence[Sequence[PipelineRow]]: ...


def prediction_batches(
    predictions: Sequence[PipelinePrediction] | Sequence[Sequence[PipelinePrediction]],
) -> tuple[Sequence[PipelinePrediction], ...]:
    first_prediction = predictions[0]
    if isinstance(first_prediction, PipelinePrediction):
        return (
            tuple(
                prediction
                for prediction in predictions
                if isinstance(prediction, PipelinePrediction)
            ),
        )
    return tuple(tuple(batch) for batch in predictions if not isinstance(batch, PipelinePrediction))


def row_batches(
    rows: Sequence[PipelineRow] | Sequence[Sequence[PipelineRow]],
) -> tuple[Sequence[PipelineRow], ...]:
    first_row = rows[0]
    if is_pipeline_row(first_row):
        return (tuple(row for row in rows if is_pipeline_row(row)),)
    return tuple(tuple(batch) for batch in rows if is_pipeline_row_sequence(batch))


def is_pipeline_row(value: PipelineRow | Sequence[PipelineRow]) -> TypeGuard[PipelineRow]:
    return isinstance(value, Mapping)


def is_pipeline_row_sequence(
    value: PipelineRow | Sequence[PipelineRow],
) -> TypeGuard[Sequence[PipelineRow]]:
    return not is_pipeline_row(value)


def predictions_from_rows(rows: Sequence[PipelineRow]) -> tuple[PipelinePrediction, ...]:
    return tuple(
        PipelinePrediction(label=str(row["label"]), score=float(row["score"])) for row in rows
    )
