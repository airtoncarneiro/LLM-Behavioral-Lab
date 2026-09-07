from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunSummary:
    run_index: int
    seed: int
    scenario: str
    agent_mode: str
    provider: str
    model: str | None
    rounds_completed: int
    survivors: tuple[str, ...]
    per_agent: dict[str, dict[str, Any]]
    metrics: dict[str, Any]
    evaluations: dict[str, Any]
    event_count: int
    event_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["survivors"] = list(self.survivors)
        value["event_path"] = str(self.event_path) if self.event_path else None
        return value


@dataclass(frozen=True)
class ExperimentRun:
    summary: RunSummary
    snapshot: dict[str, Any]


@dataclass(frozen=True)
class ExperimentReport:
    runs: tuple[ExperimentRun, ...]
    comparison: tuple[dict[str, Any], ...]

    @property
    def summaries(self) -> tuple[RunSummary, ...]:
        return tuple(run.summary for run in self.runs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "runs": [run.summary.to_dict() for run in self.runs],
            "comparison": list(self.comparison),
        }

    def compare(self, *reports: "ExperimentReport") -> tuple[dict[str, Any], ...]:
        from behavioral_lab.experiments.report import compare_reports

        return compare_reports(self, *reports)
