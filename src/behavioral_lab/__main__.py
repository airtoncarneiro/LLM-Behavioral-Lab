import argparse
from pathlib import Path
from typing import Any

from behavioral_lab.agents.factory import build_agents
from behavioral_lab.config import SimulationConfig, load_config, parse_simulation_config
from behavioral_lab.providers.fake import FakeLLMProvider
from behavioral_lab.providers.openrouter import OpenRouterProvider
from behavioral_lab.runtime.engine import SimulationEngine
from behavioral_lab.scenarios.food_scarcity import FoodScarcityScenario
from behavioral_lab.storage.events import EventStore


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the LLM Behavioral Lab simulation")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--rounds", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--agent-mode", choices=("fake", "llm"))
    parser.add_argument("--provider", choices=("fake", "openrouter"))
    parser.add_argument("--preset")
    return parser.parse_args(argv)


def _provider(name: str, preset: str, rounds: int):
    if name == "fake":
        return FakeLLMProvider(['{"action":"wait","arguments":{}}'] * max(1, rounds))
    return OpenRouterProvider(preset=preset)


def _config(args: argparse.Namespace) -> SimulationConfig:
    raw: dict[str, Any] = load_config(args.config) if args.config else {}
    for name in ("seed", "rounds", "output", "agent_mode", "provider", "preset"):
        value = getattr(args, name)
        if value is not None:
            raw[name] = str(value) if name == "output" else value
    return parse_simulation_config(raw)


def _configured_agents(config: SimulationConfig, provider, agent_ids: list[str]):
    if config.agents is None:
        return build_agents(agent_ids, mode=config.agent_mode, provider=provider)
    unknown = set(config.agents) - set(agent_ids)
    if unknown:
        raise ValueError(f"config contains unknown agents: {sorted(unknown)}")
    providers = {}
    llm_ids = []
    for agent_id, agent_config in config.agents.items():
        if agent_config.kind == "llm":
            llm_ids.append(agent_id)
            if agent_config.provider == "openrouter":
                providers[agent_id] = OpenRouterProvider(preset=agent_config.preset)
            else:
                providers[agent_id] = FakeLLMProvider(['{"action":"wait"}'] * max(1, config.rounds))
    return build_agents(
        agent_ids,
        mode="llm" if llm_ids else "fake",
        provider=provider,
        providers=providers,
        llm_agent_ids=llm_ids,
    )


def run(argv: list[str] | None = None) -> dict:
    args = parse_args(argv)
    config = _config(args)
    store = EventStore(config.output)
    scenario = FoodScarcityScenario(seed=config.seed, event_store=store, distribution=config.food_distribution)
    provider = _provider(config.provider, config.preset, config.rounds)
    agents = _configured_agents(config, provider, list(scenario.world.agents))
    return SimulationEngine(scenario, agents, max_rounds=config.rounds).run()


def main(argv: list[str] | None = None) -> None:
    print(run(argv))


if __name__ == "__main__":
    main()
