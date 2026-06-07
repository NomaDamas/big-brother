from dataclasses import dataclass
from typing import Protocol

from big_brother.domain.policy import ModelSignal, ModelSignalAction, ModelSignalCategory


@dataclass(frozen=True, slots=True)
class InferencePayload:
    image_bytes: bytes


@dataclass(frozen=True, slots=True)
class TritonInferenceResponse:
    category: str
    score: float
    model_name: str
    model_version: str


class TritonTimeoutError(Exception):
    pass


class TritonInferenceClient(Protocol):
    def infer(self, payload: InferencePayload) -> TritonInferenceResponse: ...


class TritonModelAdapter:
    def __init__(self, *, client: TritonInferenceClient) -> None:
        self._client: TritonInferenceClient = client

    def classify(self, *, image_bytes: bytes) -> ModelSignal:
        payload = InferencePayload(image_bytes=image_bytes)
        try:
            response = self._client.infer(payload)
        except TritonTimeoutError:
            return ModelSignal(
                category=ModelSignalCategory.EXPLICIT,
                score=0.0,
                action=ModelSignalAction.REVIEW_REQUIRED,
                model_name="model_unavailable",
                model_version="unavailable",
            )
        return ModelSignal(
            category=ModelSignalCategory(response.category),
            score=response.score,
            action=ModelSignalAction.REVIEW_REQUIRED,
            model_name=response.model_name,
            model_version=response.model_version,
        )
