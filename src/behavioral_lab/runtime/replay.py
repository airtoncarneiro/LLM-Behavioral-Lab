from pathlib import Path

from behavioral_lab.domain.models import Action, ActionType
from behavioral_lab.scenarios.food_scarcity import FoodScarcityScenario
from behavioral_lab.scenarios.invariants import validate_invariants
from behavioral_lab.storage.events import Event, EventStore


REPLAY_EVENT_TYPES = {"FOOD_DISCOVERED", "FOOD_TAKEN", "FOOD_STORED", "FOOD_GIVEN", "FOOD_EATEN", "ACTION_EXECUTED", "ROUND_ENDED"}


def replay_jsonl(path: Path) -> tuple[EventStore, dict]:
    original = EventStore.from_jsonl(path)
    initialized = next(e for e in original.events if e.event_type == "SIMULATION_INITIALIZED")
    seed = int(initialized.payload["seed"])
    replay_store = EventStore()
    scenario = FoodScarcityScenario(seed, replay_store)
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
            validate_invariants(scenario.world)
    return replay_store, scenario.snapshot()


def comparable_events(events: tuple[Event, ...]) -> list[tuple]:
    return [(e.round_number, e.agent_id, e.event_type, e.payload) for e in events if e.event_type in REPLAY_EVENT_TYPES]
