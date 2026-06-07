from __future__ import annotations

from big_brother.decision.engine import DecisionEngine
from big_brother.domain.policy import ModelSignal, ModelSignalAction, ModelSignalCategory
from big_brother.matching.engine import ScanDecision


def test_known_match_blocks_before_model_signal() -> None:
    known_match = ScanDecision(decision="blocked", reason="known_illegal_match", matches=())
    model_signal = ModelSignal(
        category=ModelSignalCategory.EXPLICIT,
        score=0.91,
        action=ModelSignalAction.REVIEW_REQUIRED,
        model_name="fixture-nsfw",
        model_version="0.1.0",
    )

    decision = DecisionEngine().decide(known_match=known_match, model_signal=model_signal)

    assert decision.outcome == "blocked"
    assert decision.reason == "known_illegal_match"


def test_model_signal_routes_to_review_not_illegal() -> None:
    known_match = ScanDecision(decision="allowed", reason="no_known_match", matches=())
    model_signal = ModelSignal(
        category=ModelSignalCategory.EXPLICIT,
        score=0.91,
        action=ModelSignalAction.REVIEW_REQUIRED,
        model_name="fixture-nsfw",
        model_version="0.1.0",
    )

    decision = DecisionEngine().decide(known_match=known_match, model_signal=model_signal)

    assert decision.outcome == "review_required"
    assert decision.reason == "policy_model_signal"
