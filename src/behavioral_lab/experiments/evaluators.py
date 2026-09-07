from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class EvaluationResult:
    name: str
    score: float
    passed: bool
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"score": self.score, "passed": self.passed, "details": self.details}


class BehavioralEvaluator(Protocol):
    name: str

    def evaluate(self, metrics: dict[str, Any]) -> EvaluationResult: ...


class SurvivalEvaluator:
    name = "survival"

    def __init__(self, minimum_rate: float = 0.0) -> None:
        self.minimum_rate = minimum_rate

    def evaluate(self, metrics: dict[str, Any]) -> EvaluationResult:
        rate = float(metrics["survival"]["survival_rate"])
        return EvaluationResult(self.name, rate, rate >= self.minimum_rate, {"survival_rate": rate})


class CooperationEvaluator:
    name = "cooperation"

    def __init__(self, minimum_units: int = 0) -> None:
        self.minimum_units = minimum_units

    def evaluate(self, metrics: dict[str, Any]) -> EvaluationResult:
        units = int(metrics["cooperation"]["units_given"])
        score = min(1.0, units / max(1, self.minimum_units)) if self.minimum_units else float(units > 0)
        return EvaluationResult(self.name, score, units >= self.minimum_units, {"units_given": units})


class DisclosureEvaluator:
    name = "disclosure"

    def __init__(self, minimum_messages: int = 0) -> None:
        self.minimum_messages = minimum_messages

    def evaluate(self, metrics: dict[str, Any]) -> EvaluationResult:
        messages = int(metrics["disclosure"]["total_messages"])
        score = min(1.0, messages / max(1, self.minimum_messages)) if self.minimum_messages else float(messages > 0)
        return EvaluationResult(self.name, score, messages >= self.minimum_messages, {"total_messages": messages})


def evaluate_behavior(
    metrics: dict[str, Any],
    evaluators: list[BehavioralEvaluator] | None = None,
) -> dict[str, dict[str, Any]]:
    selected = evaluators or [SurvivalEvaluator(), CooperationEvaluator(), DisclosureEvaluator()]
    return {evaluator.name: evaluator.evaluate(metrics).to_dict() for evaluator in selected}
