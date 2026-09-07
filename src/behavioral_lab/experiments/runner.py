from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from behavioral_lab.agents.factory import build_agents
from behavioral_lab.experiments.evaluators import BehavioralEvaluator, evaluate_behavior
from behavioral_lab.experiments.metrics import summarize_events
from behavioral_lab.experiments.models import ExperimentReport, ExperimentRun, RunSummary
from behavioral_lab.experiments.report import comparison_report
from behavioral_lab.providers.fake import FakeLLMProvider
from behavioral_lab.providers.openrouter import OpenRouterProvider
from behavioral_lab.runtime.engine import SimulationEngine
from behavioral_lab.scenarios.common_pool import CommonPoolScenario
from behavioral_lab.scenarios.food_scarcity import FoodScarcityScenario
from behavioral_lab.storage.events import EventStore


class ExperimentRunner:
    """Run a reproducible matrix of seeds and agent/provider configurations."""

    def __init__(
        self,
        seeds: Iterable[int],
        *,
        max_rounds: int = 20,
        scenario: str = "food_scarcity",
        agent_mode: str = "fake",
        provider: str = "fake",
        preset: str = OpenRouterProvider.DEFAULT_PRESET,
        initial_positions: dict[str, str] | None = None,
        all_llm: bool = False,
        output_dir: Path | None = None,
        evaluators: Sequence[BehavioralEvaluator] | None = None,
    ) -> None:
        self.seeds = tuple(int(seed) for seed in seeds)
        self.max_rounds = max_rounds
        self.scenario_name = scenario
        self.agent_mode = agent_mode
        self.provider_name = provider
        self.preset = preset
        self.initial_positions = dict(initial_positions) if initial_positions is not None else None
        self.all_llm = all_llm
        self.output_dir = Path(output_dir) if output_dir is not None else None
        self.evaluators = list(evaluators) if evaluators is not None else None
        if max_rounds < 0:
            raise ValueError("max_rounds must be non-negative")
        if scenario not in {"food_scarcity", "common_pool"}:
            raise ValueError("scenario must be 'food_scarcity' or 'common_pool'")
        if agent_mode not in {"fake", "llm"}:
            raise ValueError("agent_mode must be 'fake' or 'llm'")
        if provider not in {"fake", "openrouter"}:
            raise ValueError("provider must be 'fake' or 'openrouter'")
        if agent_mode == "fake" and all_llm:
            raise ValueError("all_llm requires agent_mode='llm'")

    def run(self) -> ExperimentReport:
        runs: list[ExperimentRun] = []
        for run_index, seed in enumerate(self.seeds, 1):
            event_path = self._event_path(run_index, seed)
            store = EventStore(event_path)
            scenario_type = CommonPoolScenario if self.scenario_name == "common_pool" else FoodScarcityScenario
            scenario = scenario_type(seed, store, initial_positions=self.initial_positions)
            llm_ids = tuple(scenario.world.agents) if self.all_llm else ("Agent_A",)
            provider = self._provider(len(scenario.world.agents), llm_ids)
            agents = build_agents(
                scenario.world.agents,
                mode=self.agent_mode,
                provider=provider,
                llm_agent_ids=llm_ids,
            )
            result = SimulationEngine(scenario, agents, max_rounds=self.max_rounds).run()
            per_agent, metrics = summarize_events(
                store.events,
                scenario.snapshot(),
                agent_ids=scenario.world.agents,
            )
            provider_names = sorted(
                {
                    response.provider
                    for agent in agents.values()
                    if (response := getattr(agent, "last_response", None)) is not None
                }
            )
            models = sorted(
                {
                    response.model
                    for agent in agents.values()
                    if (response := getattr(agent, "last_response", None)) is not None and response.model
                }
            )
            summary = RunSummary(
                run_index=run_index,
                seed=seed,
                scenario=self.scenario_name,
                agent_mode=self.agent_mode,
                provider=provider_names[0] if provider_names else (self.provider_name if self.agent_mode == "llm" else "none"),
                model=models[0] if models else None,
                rounds_completed=result["rounds_completed"],
                survivors=tuple(result["survivors"]),
                per_agent=per_agent,
                metrics=metrics,
                evaluations=evaluate_behavior(metrics, self.evaluators),
                event_count=len(store.events),
                event_path=event_path,
            )
            runs.append(ExperimentRun(summary=summary, snapshot=scenario.snapshot()))
        summaries = [run.summary for run in runs]
        return ExperimentReport(tuple(runs), comparison_report(summaries))

    def _provider(self, agent_count: int, llm_ids: tuple[str, ...]):
        if self.agent_mode != "llm":
            return None
        if self.provider_name == "openrouter":
            return OpenRouterProvider(preset=self.preset)
        responses = ['{"action":"wait","arguments":{}}'] * max(
            1, self.max_rounds * len(llm_ids) * agent_count
        )
        return FakeLLMProvider(responses)

    def _event_path(self, run_index: int, seed: int) -> Path | None:
        if self.output_dir is None:
            return None
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir / f"run-{run_index:03d}-seed-{seed}.jsonl"
