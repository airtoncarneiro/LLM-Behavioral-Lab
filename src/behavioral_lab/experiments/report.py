from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from behavioral_lab.experiments.models import RunSummary


def comparison_report(summaries: Iterable[RunSummary]) -> tuple[dict[str, Any], ...]:
    """Aggregate comparable runs by scenario, agent mode, provider, and model."""
    groups: dict[tuple[str, str, str, str | None], list[RunSummary]] = defaultdict(list)
    for summary in summaries:
        groups[(summary.scenario, summary.agent_mode, summary.provider, summary.model)].append(summary)
    rows: list[dict[str, Any]] = []
    for (scenario, agent_mode, provider, model), items in sorted(groups.items(), key=str):
        rates = [item.metrics["survival"]["survival_rate"] for item in items]
        consumed = [item.metrics["consumption"]["total_units"] for item in items]
        given = [item.metrics["cooperation"]["units_given"] for item in items]
        messages = [item.metrics["disclosure"]["total_messages"] for item in items]
        rows.append(
            {
                "scenario": scenario,
                "agent_mode": agent_mode,
                "provider": provider,
                "model": model,
                "runs": len(items),
                "seeds": [item.seed for item in items],
                "mean_survival_rate": sum(rates) / len(rates),
                "mean_consumed_units": sum(consumed) / len(consumed),
                "mean_units_given": sum(given) / len(given),
                "mean_disclosures": sum(messages) / len(messages),
            }
        )
    return tuple(rows)


def compare_reports(*reports) -> tuple[dict[str, Any], ...]:
    """Compare runs collected from separate provider/model experiments."""
    summaries = [summary for report in reports for summary in report.summaries]
    return comparison_report(summaries)
