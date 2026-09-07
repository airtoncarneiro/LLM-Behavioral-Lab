import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from behavioral_lab.__main__ import run
from behavioral_lab.agents.fake import FakeAgent
from behavioral_lab.agents.llm import LLMAgent
from behavioral_lab.domain.models import Action, ActionType
from behavioral_lab.providers.fake import FakeLLMProvider
from behavioral_lab.providers.openrouter import ACTION_RESPONSE_SCHEMA, OpenRouterProvider
from behavioral_lab.runtime.engine import SimulationEngine
from behavioral_lab.scenarios.food_scarcity import FoodScarcityScenario
from behavioral_lab.storage.events import EventStore
import behavioral_lab.providers.openrouter as openrouter


class FakeHTTPResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._body


def structured_action_response(action="wait", arguments=None):
    full_arguments = {"location": None, "target": None, "quantity": None}
    full_arguments.update(arguments or {})
    return json.dumps(
        {
            "action": action,
            "arguments": full_arguments,
            "public_message": None,
            "private_message_to": None,
            "private_message": None,
        }
    )


def scenario_with_llm(responses):
    store = EventStore()
    scenario = FoodScarcityScenario(seed=101, event_store=store)
    provider = FakeLLMProvider(responses)
    agents = {
        agent_id: LLMAgent(agent_id, provider) if agent_id == "Agent_A" else FakeAgent(agent_id)
        for agent_id in scenario.world.agents
    }
    return store, scenario, agents


def test_provider_requests_strict_structured_outputs_and_validates_response(monkeypatch):
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeHTTPResponse(
            {
                "model": "effective-model",
                "choices": [{"message": {"content": structured_action_response()}}],
            }
        )

    monkeypatch.setattr(openrouter, "urlopen", fake_urlopen)
    response = OpenRouterProvider(api_key="secret", timeout=1.5, max_retries=0).complete([])

    payload = json.loads(requests[0][0].data)
    assert requests[0][1] == 1.5
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["strict"] is True
    assert payload["response_format"]["json_schema"]["schema"] == ACTION_RESPONSE_SCHEMA
    assert payload["provider"] == {"require_parameters": True}
    assert response.model == "effective-model"


def test_provider_retries_transient_http_failure(monkeypatch):
    attempts = []

    def fake_urlopen(request, timeout):
        attempts.append(1)
        if len(attempts) == 1:
            raise HTTPError(request.full_url, 503, "busy", {}, BytesIO())
        return FakeHTTPResponse(
            {"choices": [{"message": {"content": structured_action_response()}}]}
        )

    monkeypatch.setattr(openrouter, "urlopen", fake_urlopen)
    response = OpenRouterProvider(api_key="secret", max_retries=1, retry_backoff=0).complete([])
    assert len(attempts) == 2
    assert response.provider == "openrouter"


def test_provider_retries_bounded_timeouts_and_then_fails(monkeypatch):
    attempts = []

    def fake_urlopen(request, timeout):
        attempts.append(timeout)
        raise TimeoutError("request deadline exceeded")

    monkeypatch.setattr(openrouter, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="could not be completed"):
        OpenRouterProvider(api_key="secret", timeout=0.1, max_retries=1, retry_backoff=0).complete([])
    assert attempts == [0.1, 0.1]


def test_provider_rejects_malformed_response_envelope(monkeypatch):
    monkeypatch.setattr(openrouter, "urlopen", lambda request, timeout: FakeHTTPResponse({"choices": []}))
    with pytest.raises(RuntimeError, match="unexpected response"):
        OpenRouterProvider(api_key="secret", max_retries=0).complete([])


def test_provider_rejects_non_json_structured_content(monkeypatch):
    monkeypatch.setattr(
        openrouter,
        "urlopen",
        lambda request, timeout: FakeHTTPResponse(
            {"choices": [{"message": {"content": "not json"}}]}
        ),
    )
    with pytest.raises(RuntimeError, match="valid JSON"):
        OpenRouterProvider(api_key="secret", max_retries=0).complete([])


def test_schema_conforming_openrouter_response_reaches_the_engine(monkeypatch):
    monkeypatch.setattr(
        openrouter,
        "urlopen",
        lambda request, timeout: FakeHTTPResponse(
            {
                "model": "effective-model",
                "choices": [{"message": {"content": structured_action_response()}}],
            }
        ),
    )
    store = EventStore()
    scenario = FoodScarcityScenario(seed=101, event_store=store)
    agents = {
        agent_id: LLMAgent(
            agent_id,
            OpenRouterProvider(api_key="secret", max_retries=0),
        )
        if agent_id == "Agent_A"
        else FakeAgent(agent_id)
        for agent_id in scenario.world.agents
    }

    SimulationEngine(scenario, agents, max_rounds=1).run()

    assert not [event for event in store.events if event.event_type == "LLM_DECISION_FAILED"]
    metadata = [event for event in store.events if event.event_type == "LLM_RESPONSE_RECEIVED"]
    assert metadata[0].payload["model"] == "effective-model"


@pytest.mark.parametrize(
    ("action", "arguments", "inventory", "searched", "initial_positions"),
    [
        ("move", {"location": "KITCHEN"}, 0, False, {}),
        (
            "search",
            {"location": "CENTRAL_ROOM", "target": "Agent_A", "quantity": 1},
            0,
            False,
            {"Agent_A": "KITCHEN"},
        ),
        ("take", {"quantity": 1}, 0, True, {"Agent_A": "KITCHEN"}),
        ("store", {"quantity": 1}, 1, False, {"Agent_A": "KITCHEN"}),
        (
            "give",
            {"target": "Agent_B", "quantity": 1},
            1,
            False,
            {"Agent_A": "KITCHEN", "Agent_B": "KITCHEN"},
        ),
        ("eat", {"quantity": 1}, 1, False, {"Agent_A": "KITCHEN"}),
        ("wait", {}, 0, False, {}),
    ],
)
def test_schema_conforming_actions_execute_without_fallback(
    action, arguments, inventory, searched, initial_positions
):
    store = EventStore()
    scenario = FoodScarcityScenario(
        seed=101,
        event_store=store,
        initial_positions=initial_positions,
    )
    agent_a = scenario.world.agents["Agent_A"]
    agent_a.inventory = inventory
    if inventory:
        scenario.world.locations[agent_a.location].food -= inventory
    if searched:
        agent_a.searched_locations.add(agent_a.location)
    provider = FakeLLMProvider([structured_action_response(action, arguments)])
    agents = {
        agent_id: LLMAgent(agent_id, provider) if agent_id == "Agent_A" else FakeAgent(agent_id)
        for agent_id in scenario.world.agents
    }

    SimulationEngine(scenario, agents, max_rounds=1).run()

    assert not [event for event in store.events if event.event_type == "LLM_DECISION_FAILED"]
    executed = [
        event
        for event in store.events
        if event.event_type == "ACTION_EXECUTED" and event.agent_id == "Agent_A"
    ]
    assert executed and executed[0].payload["action"] == action


def test_llm_provider_failure_is_recorded_and_falls_back_to_wait():
    store, scenario, agents = scenario_with_llm([])
    result = SimulationEngine(scenario, agents, max_rounds=1).run()
    failures = [event for event in store.events if event.event_type == "LLM_DECISION_FAILED"]
    assert result["rounds_completed"] == 1
    assert len(failures) == 1
    assert failures[0].payload["fallback_action"] == "wait"
    assert any(event.event_type == "ACTION_EXECUTED" and event.agent_id == "Agent_A" for event in store.events)


def test_invalid_llm_action_is_recorded_without_aborting_simulation():
    store, scenario, agents = scenario_with_llm(['{"action":"take","arguments":{"quantity":0}}'])
    SimulationEngine(scenario, agents, max_rounds=1).run()
    failure = next(event for event in store.events if event.event_type == "LLM_DECISION_FAILED")
    assert failure.payload["action"] == "take"
    assert failure.payload["fallback_action"] == "wait"


def test_invalid_domain_action_does_not_mutate_state():
    store = EventStore()
    scenario = FoodScarcityScenario(seed=101, event_store=store)
    with pytest.raises(ValueError):
        scenario.execute("Agent_A", Action(ActionType.STORE, {"quantity": 1}))
    assert scenario.world.agents["Agent_A"].inventory == 0
    assert not [event for event in store.events if event.event_type == "FOOD_STORED"]


def test_move_store_and_give_are_validated_and_executed():
    store = EventStore()
    scenario = FoodScarcityScenario(seed=101, event_store=store)
    scenario.world.agents["Agent_B"].location = "KITCHEN"
    scenario.execute("Agent_A", Action(ActionType.MOVE, {"location": "KITCHEN"}))
    scenario.execute("Agent_A", Action(ActionType.SEARCH))
    scenario.execute("Agent_A", Action(ActionType.TAKE, {"quantity": 2}))
    scenario.execute("Agent_A", Action(ActionType.STORE, {"quantity": 1}))
    scenario.execute("Agent_A", Action(ActionType.GIVE, {"target": "Agent_B", "quantity": 1}))
    assert scenario.world.agents["Agent_A"].inventory == 0
    assert scenario.world.agents["Agent_B"].inventory == 1
    assert scenario.world.locations["KITCHEN"].food == 4


def test_invalid_quantity_and_target_are_rejected():
    store = EventStore()
    scenario = FoodScarcityScenario(seed=101, event_store=store)
    scenario.world.agents["Agent_A"].inventory = 1
    invalid_actions = (
        Action(ActionType.EAT, {"quantity": 0}),
        Action(ActionType.STORE, {"quantity": 2}),
        Action(ActionType.GIVE, {"target": "Agent_Z", "quantity": 1}),
    )
    for action in invalid_actions:
        with pytest.raises(ValueError):
            scenario.execute("Agent_A", action)


def test_dead_agents_do_not_receive_turns_or_execute_actions():
    store = EventStore()
    scenario = FoodScarcityScenario(seed=101, event_store=store)
    scenario.world.agents["Agent_A"].alive = False
    scenario.world.agents["Agent_A"].hunger = 10
    agents = {agent_id: FakeAgent(agent_id) for agent_id in scenario.world.agents}
    SimulationEngine(scenario, agents, max_rounds=1).run()
    assert not [event for event in store.events if event.agent_id == "Agent_A" and event.event_type == "OBSERVATION_CREATED"]


def test_messages_are_visible_publicly_but_private_messages_are_scoped():
    store = EventStore()
    scenario = FoodScarcityScenario(seed=101, event_store=store)
    scenario.execute(
        "Agent_A",
        Action(
            ActionType.WAIT,
            public_message="food is in the kitchen",
            private_message_to="Agent_B",
            private_message="meet me here",
        ),
    )
    observation_b = scenario.observe("Agent_B")
    observation_c = scenario.observe("Agent_C")
    assert [message.content for message in observation_b.public_messages] == ["food is in the kitchen"]
    assert [message.content for message in observation_b.private_messages] == ["meet me here"]
    assert [message.content for message in observation_c.public_messages] == ["food is in the kitchen"]
    assert observation_c.private_messages == ()


def test_cli_defaults_to_fake_only_and_accepts_configuration(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    output = tmp_path / "events.jsonl"
    result = run(["--rounds", "1", "--output", str(output)])
    assert result["rounds_completed"] == 1
    assert output.exists()
    assert not [line for line in output.read_text().splitlines() if "LLM_RESPONSE_RECEIVED" in line]

    llm_output = tmp_path / "llm-events.jsonl"
    run(["--agent-mode", "llm", "--provider", "fake", "--rounds", "1", "--output", str(llm_output)])
    assert any("LLM_RESPONSE_RECEIVED" in line for line in llm_output.read_text().splitlines())
