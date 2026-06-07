from big_brother.domain.policy import ModelSignal, ModerationDecision
from big_brother.matching.engine import ScanDecision


class DecisionEngine:
    def decide(
        self,
        *,
        known_match: ScanDecision,
        model_signal: ModelSignal | None,
    ) -> ModerationDecision:
        if known_match.decision == "blocked":
            return ModerationDecision(outcome="blocked", reason="known_illegal_match")
        if model_signal is not None:
            return ModerationDecision.from_model_signal(model_signal)
        return ModerationDecision(outcome="allowed", reason="no_known_match")
