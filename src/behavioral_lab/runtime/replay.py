from pathlib import Path

from behavioral_lab.domain.models import Action, ActionType
from behavioral_lab.scenarios.food_scarcity import FoodScarcityScenario
from behavioral_lab.scenarios.common_pool import CommonPoolScenario
from behavioral_lab.scenarios.invariants import validate_invariants
from behavioral_lab.storage.events import Event, EventStore


REPLAY_EVENT_TYPES = {"FOOD_DISCOVERED", "FOOD_TAKEN", "FOOD_STORED", "FOOD_GIVEN", "FOOD_EATEN", "ACTION_EXECUTED", "ROUND_ENDED"}
SCENARIO_TYPES = {
    "food_scarcity": FoodScarcityScenario,
    "common_pool": CommonPoolScenario,
}


def replay_jsonl(path: Path) -> tuple[EventStore, dict]:
    original = EventStore.from_jsonl(path)
    initialized = next(e for e in original.events if e.event_type == "SIMULATION_INITIALIZED")
    scenario_name = initialized.payload.get("scenario", "food_scarcity")
    scenario_type = SCENARIO_TYPES.get(scenario_name)
    if scenario_type is None:
        raise ValueError(f"unsupported scenario in event log: {scenario_name}")
    seed = int(initialized.payload["seed"])
    initial_positions = initialized.payload.get("initial_positions")
    distribution = initialized.payload.get("food_distribution")
    replay_store = EventStore()
    kwargs = {"initial_positions": initial_positions}
    if scenario_name == "food_scarcity":
        kwargs["distribution"] = distribution
    scenario = scenario_type(seed, replay_store, **kwargs)
    for event in original.events:
        if event.event_type == "ACTION_EXECUTED" and event.agent_id:
            scenario.world.round_number = event.round_number
            scenario.execute(
                event.agent_id,
                Action(
                    ActionType(event.payload["action"]),
                    event.payload["arguments"],
                    public_message=event.payload.get("public_message"),
                    private_message_to=event.payload.get("private_message_to"),
                    private_message=event.payload.get("private_message"),
                ),
            )
        elif event.event_type == "ROUND_ENDED":
            scenario.world.round_number = event.round_number
            scenario.end_round()
            validate_invariants(scenario.world, total_food=scenario.total_food)
    return replay_store, scenario.snapshot()


def comparable_events(events: tuple[Event, ...]) -> list[tuple]:
    return [(e.round_number, e.agent_id, e.event_type, e.payload) for e in events if e.event_type in REPLAY_EVENT_TYPES]
