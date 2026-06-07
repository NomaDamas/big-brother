from __future__ import annotations

import pytest

from big_brother.domain.policy import (
    IllegalModelOnlyDecisionError,
    ModelSignal,
    ModelSignalAction,
    ModelSignalCategory,
    ModerationDecision,
)


def test_model_only_signal_cannot_be_illegal_when_unknown() -> None:
    signal = ModelSignal(
        category=ModelSignalCategory.EXPLICIT,
        score=0.98,
        action=ModelSignalAction.ILLEGAL,
        model_name="fixture-nsfw",
        model_version="0.1.0",
    )

    with pytest.raises(IllegalModelOnlyDecisionError) as error:
        _ = ModerationDecision.from_model_signal(signal)

    assert "model-only signals cannot produce illegal" in str(error.value)


def test_model_only_signal_routes_to_review() -> None:
    signal = ModelSignal(
        category=ModelSignalCategory.EXPLICIT,
        score=0.91,
        action=ModelSignalAction.REVIEW_REQUIRED,
        model_name="fixture-nsfw",
        model_version="0.1.0",
    )

    decision = ModerationDecision.from_model_signal(signal)

    assert decision.outcome == "review_required"
    assert decision.reason == "policy_model_signal"


def test_model_below_threshold_signal_allows_without_review() -> None:
    signal = ModelSignal(
        category=ModelSignalCategory.EXPLICIT,
        score=0.2,
        action=ModelSignalAction.NO_ACTION,
        model_name="fixture-nsfw",
        model_version="0.1.0",
    )

    decision = ModerationDecision.from_model_signal(signal)

    assert decision.outcome == "allowed"
    assert decision.reason == "model_below_threshold"
