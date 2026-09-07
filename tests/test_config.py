import json

from behavioral_lab.__main__ import run
from behavioral_lab.agents.factory import build_agents
from behavioral_lab.agents.llm import LLMAgent
from behavioral_lab.config import load_config, parse_simulation_config
from behavioral_lab.providers.fake import FakeLLMProvider


def test_config_builds_different_provider_instances_per_agent():
    agents = build_agents(
        ["Agent_A", "Agent_B", "Agent_C"],
        mode="llm",
        providers={
            "Agent_A": FakeLLMProvider(['{"action":"wait"}']),
            "Agent_B": FakeLLMProvider(['{"action":"wait"}']),
        },
        llm_agent_ids=["Agent_A", "Agent_B"],
    )

    assert isinstance(agents["Agent_A"], LLMAgent)
    assert isinstance(agents["Agent_B"], LLMAgent)
    assert agents["Agent_A"].provider is not agents["Agent_B"].provider
    assert not isinstance(agents["Agent_C"], LLMAgent)


def test_config_loads_and_cli_rounds_override_file(tmp_path):
    config_path = tmp_path / "experiment.json"
    output_path = tmp_path / "events.jsonl"
    config_path.write_text(
        json.dumps(
            {
                "seed": 7,
                "rounds": 10,
                "output": str(tmp_path / "from-file.jsonl"),
                "food_distribution": {
                    "CENTRAL_ROOM": 1,
                    "KITCHEN": 2,
                    "STORAGE": 3,
                    "ROOM_A": 4,
                    "ROOM_B": 5,
                },
                "agents": {
                    "Agent_A": {"type": "llm", "provider": "fake", "preset": "model-a"},
                    "Agent_B": {"type": "llm", "provider": "fake", "preset": "model-b"},
                    "Agent_C": {"type": "fake"},
                    "Agent_D": {"type": "fake"},
                    "Agent_E": {"type": "fake"},
                },
            }
        ),
        encoding="utf-8",
    )

    result = run(["--config", str(config_path), "--rounds", "1", "--output", str(output_path)])

    assert result["rounds_completed"] == 1
    initialized = json.loads(output_path.read_text(encoding="utf-8").splitlines()[0])
    assert initialized["payload"]["locations"]["ROOM_B"]["food"] == 5


def test_config_rejects_unknown_fields():
    try:
        parse_simulation_config({"unexpected": True})
    except ValueError as exc:
        assert "unknown config fields" in str(exc)
    else:
        raise AssertionError("invalid configuration was accepted")


def test_missing_config_is_reported(tmp_path):
    try:
        load_config(tmp_path / "missing.json")
    except ValueError as exc:
        assert "config file not found" in str(exc)
    else:
        raise AssertionError("missing configuration was accepted")
