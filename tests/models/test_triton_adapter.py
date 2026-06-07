from __future__ import annotations

from big_brother.domain.policy import ModelSignalAction, ModelSignalCategory
from big_brother.models.triton import (
    InferencePayload,
    TritonInferenceResponse,
    TritonModelAdapter,
    TritonTimeoutError,
)

EXPECTED_EXPLICIT_SCORE = 0.92
SCORE_TOLERANCE = 0.0001


class TimeoutClient:
    def infer(self, payload: InferencePayload) -> TritonInferenceResponse:
        _ = payload
        raise TritonTimeoutError


class ExplicitClient:
    def infer(self, payload: InferencePayload) -> TritonInferenceResponse:
        _ = payload
        return TritonInferenceResponse(
            category="explicit",
            score=EXPECTED_EXPLICIT_SCORE,
            model_name="fixture-nsfw",
            model_version="0.1.0",
        )


def test_triton_timeout_returns_model_unavailable_signal() -> None:
    adapter = TritonModelAdapter(client=TimeoutClient())

    signal = adapter.classify(image_bytes=b"synthetic")

    assert signal.category is ModelSignalCategory.EXPLICIT
    assert signal.score == 0.0
    assert signal.action is ModelSignalAction.REVIEW_REQUIRED
    assert signal.model_name == "model_unavailable"


def test_model_response_maps_to_policy_signal() -> None:
    adapter = TritonModelAdapter(client=ExplicitClient())

    signal = adapter.classify(image_bytes=b"synthetic")

    assert signal.category is ModelSignalCategory.EXPLICIT
    assert abs(signal.score - EXPECTED_EXPLICIT_SCORE) < SCORE_TOLERANCE
    assert signal.action is ModelSignalAction.REVIEW_REQUIRED
    assert signal.model_name == "fixture-nsfw"
