from __future__ import annotations

from behavioral_lab.domain.models import Action, ActionType, Observation


class FakeAgent:
    """Simple deterministic policy used to validate the simulation engine."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id

    def decide(self, observation: Observation) -> Action:
        if observation.hunger >= 7 and observation.inventory > 0:
            return Action(ActionType.EAT, {"quantity": 1})

        if not observation.location_searched:
            return Action(ActionType.SEARCH)

        if observation.visible_food is not None and observation.visible_food > 0:
            return Action(
                ActionType.TAKE,
                {"quantity": min(1, observation.visible_food)},
                public_message=f"{self.agent_id} found food and declared it.",
            )

        if observation.location not in ("CENTRAL_ROOM",) and observation.inventory > 1:
            return Action(ActionType.MOVE, {"location": "CENTRAL_ROOM"})

        targets = [x for x in observation.available_locations if x != observation.location]
        if not targets:
            return Action(ActionType.WAIT)
        index = (ord(self.agent_id[-1]) + observation.round_number) % len(targets)
        return Action(ActionType.MOVE, {"location": targets[index]})
