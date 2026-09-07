import pytest
from datetime import datetime

from behavioral_lab.agents.llm import LLMAgent
from behavioral_lab.domain.models import ActionType, Observation
from behavioral_lab.providers.fake import FakeLLMProvider
from behavioral_lab.agents.fake import FakeAgent
from behavioral_lab.runtime.engine import SimulationEngine
from behavioral_lab.scenarios.food_scarcity import FoodScarcityScenario
from behavioral_lab.storage.events import EventStore


def observation() -> Observation:
    return Observation(
        round_number=1,
        agent_id="Agent_A",
        location="CENTRAL_ROOM",
        hunger=1,
        inventory=0,
        present_agents=("Agent_B",),
        visible_food=None,
        location_searched=False,
        available_locations=("CENTRAL_ROOM", "KITCHEN"),
    )


def test_llm_agent_uses_structured_fake_response_and_memory():
    provider = FakeLLMProvider(['{"action":"search","arguments":{}}'])
    agent = LLMAgent("Agent_A", provider)

    action = agent.decide(observation())

    assert action.type == ActionType.SEARCH
    assert len(provider.calls) == 1
    assert agent.memory[-1]["action"] == "search"
    assert agent.last_response.model == "fake-model"


def test_llm_agent_memory_is_bounded():
    provider = FakeLLMProvider(['{"action":"wait"}'] * 4)
    agent = LLMAgent("Agent_A", provider, max_memory=2)
    for round_number in range(1, 5):
        current = observation()
        current = current.__class__(round_number=round_number, **{
            field: getattr(current, field)
            for field in current.__dataclass_fields__
            if field != "round_number"
        })
        agent.decide(current)
    assert len(agent.memory) == 2


def test_llm_agent_accepts_json_fenced_response():
    provider = FakeLLMProvider(["```json\n{\"action\":\"wait\"}\n```"])
    assert LLMAgent("Agent_A", provider).decide(observation()).type == ActionType.WAIT


def test_llm_agent_parses_private_message_fields():
    provider = FakeLLMProvider(
        ['{"action":"wait","private_message_to":"Agent_B","private_message":"keep watch"}']
    )
    action = LLMAgent("Agent_A", provider).decide(observation())
    assert action.private_message_to == "Agent_B"
    assert action.private_message == "keep watch"


def test_llm_agent_discards_incomplete_optional_messages():
    provider = FakeLLMProvider(
        ['{"action":"wait","public_message":" ","private_message_to":"Agent_B"}']
    )

    action = LLMAgent("Agent_A", provider).decide(observation())

    assert action.public_message is None
    assert action.private_message_to is None
    assert action.private_message is None


def test_llm_agent_discards_invalid_private_recipient_without_discarding_action():
    provider = FakeLLMProvider(
        ['{"action":"search","private_message_to":"Agent_Z","private_message":"search"}']
    )

    action = LLMAgent("Agent_A", provider).decide(observation())

    assert action.type == ActionType.SEARCH
    assert action.private_message_to is None
    assert action.private_message is None


def test_llm_agent_prompt_uses_dynamic_observation_state():
    provider = FakeLLMProvider(['{"action":"wait"}'])
    current = observation().__class__(
        **{
            **observation().__dict__,
            "total_agents": 3,
            "alive_agents": 2,
            "remaining_food": 7,
            "total_food": 12,
        }
    )

    LLMAgent("Agent_A", provider).decide(current)

    prompt = provider.calls[0][1]["content"]
    assert '"total_agents": 3' in prompt
    assert '"alive_agents": 2' in prompt
    assert '"remaining_food": 7' in prompt
    assert '"total_food": 12' in prompt


def test_llm_agent_rejects_invalid_response():
    provider = FakeLLMProvider(["not json"])
    with pytest.raises(ValueError, match="valid action JSON"):
        LLMAgent("Agent_A", provider).decide(observation())


def test_milestone_2_keeps_four_fake_agents_and_one_llm_agent():
    provider = FakeLLMProvider(['{"action":"wait"}'] * 20)
    store = EventStore()
    scenario = FoodScarcityScenario(seed=101, event_store=store)
    agents = {
        agent_id: (LLMAgent(agent_id, provider) if agent_id == "Agent_A" else FakeAgent(agent_id))
        for agent_id in scenario.world.agents
    }

    SimulationEngine(scenario, agents, max_rounds=1).run()

    assert sum(isinstance(agent, LLMAgent) for agent in agents.values()) == 1
    assert sum(isinstance(agent, FakeAgent) for agent in agents.values()) == 4
    metadata = [event for event in store.events if event.event_type == "LLM_RESPONSE_RECEIVED"]
    assert metadata[0].payload["provider"] == "fake"
    assert metadata[0].payload["preset"] == "fake"
    assert metadata[0].payload["model"] == "fake-model"
    assert metadata[0].payload["duration_ms"] >= 0
    datetime.fromisoformat(metadata[0].timestamp.replace("Z", "+00:00"))
