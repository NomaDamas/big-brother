from enum import StrEnum
from typing import ClassVar, Self, override

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IllegalModelOnlyDecisionError(Exception):
    @override
    def __str__(self) -> str:
        return "model-only signals cannot produce illegal"


class ModelSignalCategory(StrEnum):
    EXPLICIT = "explicit"
    VIOLENCE = "violence"
    GORE = "gore"


class ModelSignalAction(StrEnum):
    NO_ACTION = "no_action"
    REVIEW_REQUIRED = "review_required"
    POLICY_BLOCKED = "policy_blocked"
    ILLEGAL = "illegal"


class ModelSignal(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    category: ModelSignalCategory
    score: float = Field(ge=0.0, le=1.0)
    action: ModelSignalAction
    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)


class ModerationDecision(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    outcome: str = Field(min_length=1)
    reason: str = Field(min_length=1)

    @classmethod
    def from_model_signal(cls, signal: ModelSignal) -> Self:
        match signal.action:
            case ModelSignalAction.NO_ACTION:
                return cls(outcome="allowed", reason="model_below_threshold")
            case ModelSignalAction.REVIEW_REQUIRED | ModelSignalAction.POLICY_BLOCKED:
                return cls(outcome=signal.action.value, reason="policy_model_signal")
            case ModelSignalAction.ILLEGAL:
                raise IllegalModelOnlyDecisionError


class ModelPolicyRule(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    category: ModelSignalCategory
    minimum_score: float = Field(ge=0.0, le=1.0)
    action: ModelSignalAction


class Policy(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    model_signals: tuple[ModelPolicyRule, ...]
    terms: tuple[str, ...] = ()

    @model_validator(mode="after")
    def reject_model_illegal_action(self) -> Self:
        for rule in self.model_signals:
            match rule.action:
                case (
                    ModelSignalAction.NO_ACTION
                    | ModelSignalAction.REVIEW_REQUIRED
                    | ModelSignalAction.POLICY_BLOCKED
                ):
                    continue
                case ModelSignalAction.ILLEGAL:
                    raise IllegalModelOnlyDecisionError
        return self
