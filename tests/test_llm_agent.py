import pytest

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


def test_llm_agent_accepts_json_fenced_response():
    provider = FakeLLMProvider(["```json\n{\"action\":\"wait\"}\n```"])
    assert LLMAgent("Agent_A", provider).decide(observation()).type == ActionType.WAIT


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
    assert metadata[0].payload == {
        "provider": "fake",
        "preset": "fake",
        "model": "fake-model",
    }
