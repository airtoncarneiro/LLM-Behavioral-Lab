from behavioral_lab.agents.fake import FakeAgent
from behavioral_lab.domain.models import Action, ActionType
from behavioral_lab.runtime.engine import SimulationEngine
from behavioral_lab.scenarios.food_scarcity import FoodScarcityScenario
from behavioral_lab.storage.events import EventStore
from behavioral_lab.runtime.replay import comparable_events, replay_jsonl


def build(seed: int = 101):
    store = EventStore()
    scenario = FoodScarcityScenario(seed=seed, event_store=store)
    agents = {agent_id: FakeAgent(agent_id) for agent_id in scenario.world.agents}
    return store, scenario, agents


def test_initial_food_is_20():
    _, scenario, _ = build()
    assert scenario.world.remaining_food == 20


def test_same_seed_produces_same_turn_order():
    _, left, _ = build(123)
    _, right, _ = build(123)
    assert left.turn_order() == right.turn_order()


def test_search_then_take_changes_ground_truth():
    _, scenario, _ = build()
    agent_id = "Agent_A"
    scenario.world.agents[agent_id].location = "STORAGE"
    scenario.execute(agent_id, Action(ActionType.SEARCH))
    scenario.execute(agent_id, Action(ActionType.TAKE, {"quantity": 2}))
    assert scenario.world.agents[agent_id].inventory == 2
    assert scenario.world.locations["STORAGE"].food == 5


def test_eating_reduces_hunger_by_three():
    _, scenario, _ = build()
    agent = scenario.world.agents["Agent_A"]
    agent.inventory = 1
    agent.hunger = 7
    scenario.execute("Agent_A", Action(ActionType.EAT, {"quantity": 1}))
    assert agent.hunger == 4
    assert agent.inventory == 0


def test_agent_dies_at_hunger_10():
    _, scenario, _ = build()
    agent = scenario.world.agents["Agent_A"]
    agent.hunger = 9
    scenario.world.round_number = 1
    scenario.end_round()
    assert not agent.alive


def test_full_simulation_is_reproducible():
    def run(seed: int):
        store, scenario, agents = build(seed)
        result = SimulationEngine(scenario, agents).run()
        normalized = [
            (e.round_number, e.agent_id, e.event_type, e.payload)
            for e in store.events
        ]
        return result, normalized

    assert run(999) == run(999)


def test_full_simulation_discovers_and_consumes_food():
    store, scenario, agents = build(101)
    SimulationEngine(scenario, agents).run()
    event_types = [event.event_type for event in store.events]
    assert "FOOD_DISCOVERED" in event_types
    assert "FOOD_TAKEN" in event_types
    assert "FOOD_EATEN" in event_types


def test_jsonl_replay_matches_state_changing_events_and_final_state(tmp_path):
    path = tmp_path / "events.jsonl"
    store = EventStore(path)
    scenario = FoodScarcityScenario(seed=101, event_store=store)
    agents = {agent_id: FakeAgent(agent_id) for agent_id in scenario.world.agents}
    SimulationEngine(scenario, agents).run()

    replay_store, replay_snapshot = replay_jsonl(path)
    original_snapshot = next(
        event.payload for event in reversed(store.events) if event.event_type == "ROUND_ENDED"
    )
    assert replay_snapshot == original_snapshot
    assert comparable_events(store.events) == comparable_events(replay_store.events)
