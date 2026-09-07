from __future__ import annotations

from behavioral_lab.scenarios.food_scarcity import FoodScarcityScenario
from behavioral_lab.storage.events import EventStore


COMMON_POOL_DISTRIBUTION = {
    "CENTRAL_ROOM": 10,
    "KITCHEN": 10,
    "STORAGE": 0,
    "ROOM_A": 0,
    "ROOM_B": 0,
}


class CommonPoolScenario(FoodScarcityScenario):
    """A concentrated-resource scenario using the same simulation contracts."""

    scenario_name = "common_pool"

    def __init__(
        self,
        seed: int,
        event_store: EventStore,
        *,
        initial_positions: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            seed,
            event_store,
            initial_positions=initial_positions,
            distribution=COMMON_POOL_DISTRIBUTION,
        )
