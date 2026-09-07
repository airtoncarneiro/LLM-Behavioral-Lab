from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from behavioral_lab.providers.openrouter import OpenRouterProvider


@dataclass(frozen=True)
class AgentConfig:
    kind: str
    provider: str = "openrouter"
    preset: str = OpenRouterProvider.DEFAULT_PRESET


@dataclass(frozen=True)
class SimulationConfig:
    seed: int = 101
    rounds: int = 20
    output: Path = Path("events.jsonl")
    agent_mode: str = "fake"
    provider: str = "fake"
    preset: str = OpenRouterProvider.DEFAULT_PRESET
    agents: dict[str, AgentConfig] | None = None
    food_distribution: dict[str, int] | None = None
    verbose: bool = False


def load_config(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"config file is not valid JSON: {path}") from exc
    if not isinstance(raw, dict):
        raise ValueError("config root must be a JSON object")
    return raw


def parse_simulation_config(raw: dict[str, Any]) -> SimulationConfig:
    allowed = {"seed", "rounds", "output", "agent_mode", "provider", "preset", "agents", "food_distribution", "verbose"}
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError(f"unknown config fields: {sorted(unknown)}")

    def integer(name: str, default: int) -> int:
        value = raw.get(name, default)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"config field '{name}' must be an integer")
        return value

    seed = integer("seed", 101)
    rounds = integer("rounds", 20)
    if rounds < 0:
        raise ValueError("config field 'rounds' must be non-negative")
    output = raw.get("output", "events.jsonl")
    if not isinstance(output, str) or not output:
        raise ValueError("config field 'output' must be a non-empty string")
    agent_mode = raw.get("agent_mode", "fake")
    provider = raw.get("provider", "fake")
    preset = raw.get("preset", OpenRouterProvider.DEFAULT_PRESET)
    if agent_mode not in {"fake", "llm"}:
        raise ValueError("config field 'agent_mode' must be 'fake' or 'llm'")
    if provider not in {"fake", "openrouter"}:
        raise ValueError("config field 'provider' must be 'fake' or 'openrouter'")
    if not isinstance(preset, str) or not preset:
        raise ValueError("config field 'preset' must be a non-empty string")

    agents_raw = raw.get("agents")
    agents = None
    if agents_raw is not None:
        if not isinstance(agents_raw, dict) or not agents_raw:
            raise ValueError("config field 'agents' must be a non-empty object")
        agents = {}
        for agent_id, value in agents_raw.items():
            if not isinstance(agent_id, str) or not agent_id or not isinstance(value, dict):
                raise ValueError("each agent config must be an object with a string id")
            kind = value.get("type", value.get("kind"))
            if kind not in {"fake", "llm"}:
                raise ValueError(f"agent '{agent_id}' type must be 'fake' or 'llm'")
            agent_provider = value.get("provider", provider)
            agent_preset = value.get("preset", preset)
            if agent_provider not in {"fake", "openrouter"}:
                raise ValueError(f"agent '{agent_id}' provider is invalid")
            if not isinstance(agent_preset, str) or not agent_preset:
                raise ValueError(f"agent '{agent_id}' preset must be a non-empty string")
            agents[agent_id] = AgentConfig(kind, agent_provider, agent_preset)

    distribution = raw.get("food_distribution")
    if distribution is not None:
        if not isinstance(distribution, dict):
            raise ValueError("config field 'food_distribution' must be an object")
        distribution = dict(distribution)

    verbose = raw.get("verbose", False)
    if not isinstance(verbose, bool):
        raise ValueError("config field 'verbose' must be a boolean")

    return SimulationConfig(seed, rounds, Path(output), agent_mode, provider, preset, agents, distribution, verbose)
