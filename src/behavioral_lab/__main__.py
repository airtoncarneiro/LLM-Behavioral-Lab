import argparse
from pathlib import Path

from behavioral_lab.agents.factory import build_agents
from behavioral_lab.providers.fake import FakeLLMProvider
from behavioral_lab.providers.openrouter import OpenRouterProvider
from behavioral_lab.runtime.engine import SimulationEngine
from behavioral_lab.scenarios.food_scarcity import FoodScarcityScenario
from behavioral_lab.storage.events import EventStore


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the LLM Behavioral Lab simulation")
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--rounds", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path("events.jsonl"))
    parser.add_argument("--agent-mode", choices=("fake", "llm"), default="fake")
    parser.add_argument("--provider", choices=("fake", "openrouter"), default="fake")
    parser.add_argument("--preset", default=OpenRouterProvider.DEFAULT_PRESET)
    return parser.parse_args(argv)


def _provider(name: str, preset: str, rounds: int):
    if name == "fake":
        return FakeLLMProvider(['{"action":"wait","arguments":{}}'] * max(1, rounds))
    return OpenRouterProvider(preset=preset)


def run(argv: list[str] | None = None) -> dict:
    args = parse_args(argv)
    if args.rounds < 0:
        raise SystemExit("--rounds must be non-negative")
    store = EventStore(args.output)
    scenario = FoodScarcityScenario(seed=args.seed, event_store=store)
    provider = _provider(args.provider, args.preset, args.rounds)
    agents = build_agents(scenario.world.agents, mode=args.agent_mode, provider=provider)
    return SimulationEngine(scenario, agents, max_rounds=args.rounds).run()


def main(argv: list[str] | None = None) -> None:
    print(run(argv))


if __name__ == "__main__":
    main()
