from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


class BatchCalibrationError(Exception):
    def __init__(self) -> None:
        super().__init__("auto batch calibration could not find a safe batch size")


@dataclass(frozen=True, slots=True)
class BatchCalibrationConfig:
    minimum: int
    maximum: int
    growth_factor: int


BatchProbe = Callable[[int], None]


def calibrate_batch_size(
    *,
    config: BatchCalibrationConfig,
    probe: BatchProbe,
) -> int:
    safe_batch_size: int | None = None
    candidate = config.minimum
    while candidate <= config.maximum:
        try:
            probe(candidate)
        except RuntimeError as error:
            if _is_out_of_memory_error(error):
                return _safe_batch_size_or_raise(safe_batch_size)
            raise
        safe_batch_size = candidate
        candidate *= config.growth_factor
    return _safe_batch_size_or_raise(safe_batch_size)


def _safe_batch_size_or_raise(value: int | None) -> int:
    if value is None:
        raise BatchCalibrationError
    return value


def _is_out_of_memory_error(error: RuntimeError) -> bool:
    message = str(error).casefold()
    return "out of memory" in message or "cuda oom" in message
