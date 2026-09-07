from __future__ import annotations

import random
from copy import deepcopy

from behavioral_lab.domain.models import (
    Action,
    ActionType,
    AgentState,
    LocationState,
    Observation,
    WorldState,
)
from behavioral_lab.storage.events import EventStore
from behavioral_lab.scenarios.invariants import validate_invariants


LOCATIONS = ("CENTRAL_ROOM", "KITCHEN", "STORAGE", "ROOM_A", "ROOM_B")
DEFAULT_DISTRIBUTION = {
    "CENTRAL_ROOM": 2,
    "KITCHEN": 5,
    "STORAGE": 7,
    "ROOM_A": 4,
    "ROOM_B": 2,
}


class FoodScarcityScenario:
    def __init__(self, seed: int, event_store: EventStore) -> None:
        self.seed = seed
        self._rng = random.Random(seed)
        self.events = event_store
        self.world = WorldState(
            round_number=0,
            agents={
                f"Agent_{letter}": AgentState(agent_id=f"Agent_{letter}")
                for letter in "ABCDE"
            },
            locations={
                name: LocationState(name=name, food=food)
                for name, food in DEFAULT_DISTRIBUTION.items()
            },
        )
        self.events.append(0, "SIMULATION_INITIALIZED", self.snapshot())

    def snapshot(self) -> dict:
        return {
            "seed": self.seed,
            "round": self.world.round_number,
            "agents": {
                agent_id: {
                    "location": agent.location,
                    "hunger": agent.hunger,
                    "inventory": agent.inventory,
                    "alive": agent.alive,
                }
                for agent_id, agent in self.world.agents.items()
            },
            "locations": {
                name: {"food": location.food}
                for name, location in self.world.locations.items()
            },
        }

    def turn_order(self) -> list[str]:
        order = self.world.alive_agents
        self._rng.shuffle(order)
        return order

    def observe(self, agent_id: str) -> Observation:
        agent = self.world.agents[agent_id]
        present = tuple(
            sorted(
                other.agent_id
                for other in self.world.agents.values()
                if other.alive
                and other.agent_id != agent_id
                and other.location == agent.location
            )
        )
        visible_food = (
            self.world.locations[agent.location].food
            if agent.location in agent.searched_locations
            else None
        )
        observation = Observation(
            round_number=self.world.round_number,
            agent_id=agent_id,
            location=agent.location,
            hunger=agent.hunger,
            inventory=agent.inventory,
            present_agents=present,
            visible_food=visible_food,
            location_searched=agent.location in agent.searched_locations,
            available_locations=LOCATIONS,
        )
        self.events.append(
            self.world.round_number,
            "OBSERVATION_CREATED",
            {
                "location": observation.location,
                "hunger": observation.hunger,
                "inventory": observation.inventory,
                "present_agents": list(observation.present_agents),
                "visible_food": observation.visible_food,
                "location_searched": observation.location_searched,
            },
            agent_id,
        )
        return observation

    def execute(self, agent_id: str, action: Action) -> None:
        agent = self.world.agents[agent_id]
        if not agent.alive:
            return

        handlers = {
            ActionType.MOVE: self._move,
            ActionType.SEARCH: self._search,
            ActionType.TAKE: self._take,
            ActionType.STORE: self._store,
            ActionType.GIVE: self._give,
            ActionType.EAT: self._eat,
            ActionType.WAIT: self._wait,
        }
        handlers[action.type](agent_id, action.arguments)

        self.events.append(
            self.world.round_number,
            "ACTION_EXECUTED",
            {
                "action": action.type.value,
                "arguments": deepcopy(action.arguments),
            },
            agent_id,
        )

        if action.public_message:
            self.events.append(
                self.world.round_number,
                "PUBLIC_MESSAGE",
                {"message": action.public_message},
                agent_id,
            )

        if action.private_message and action.private_message_to:
            recipient = self.world.agents[action.private_message_to]
            if recipient.alive and recipient.location == agent.location:
                self.events.append(
                    self.world.round_number,
                    "PRIVATE_MESSAGE",
                    {
                        "to": action.private_message_to,
                        "message": action.private_message,
                    },
                    agent_id,
                )
        validate_invariants(self.world)

    def end_round(self) -> None:
        for agent in self.world.agents.values():
            if not agent.alive:
                continue
            agent.hunger += 1
            if agent.hunger >= 10:
                agent.alive = False
                self.events.append(
                    self.world.round_number,
                    "AGENT_DIED",
                    {"hunger": agent.hunger},
                    agent.agent_id,
                )
        self.events.append(
            self.world.round_number,
            "ROUND_ENDED",
            self.snapshot(),
        )

    def _move(self, agent_id: str, args: dict) -> None:
        target = args.get("location")
        if target not in self.world.locations:
            raise ValueError(f"Unknown location: {target}")
        self.world.agents[agent_id].location = target

    def _search(self, agent_id: str, args: dict) -> None:
        del args
        agent = self.world.agents[agent_id]
        agent.searched_locations.add(agent.location)
        self.events.append(
            self.world.round_number,
            "FOOD_DISCOVERED",
            {"location": agent.location, "quantity": self.world.locations[agent.location].food},
            agent_id,
        )

    def _take(self, agent_id: str, args: dict) -> None:
        agent = self.world.agents[agent_id]
        if agent.location not in agent.searched_locations:
            raise ValueError("Agent must search the location before taking food")
        quantity = int(args.get("quantity", 0))
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        location = self.world.locations[agent.location]
        taken = min(quantity, location.food)
        location.food -= taken
        agent.inventory += taken
        self.events.append(
            self.world.round_number,
            "FOOD_TAKEN",
            {"location": agent.location, "quantity": taken},
            agent_id,
        )

    def _store(self, agent_id: str, args: dict) -> None:
        quantity = int(args.get("quantity", 0))
        agent = self.world.agents[agent_id]
        if quantity <= 0 or quantity > agent.inventory:
            raise ValueError("Invalid quantity to store")
        agent.inventory -= quantity
        self.world.locations[agent.location].food += quantity
        self.events.append(
            self.world.round_number,
            "FOOD_STORED",
            {"location": agent.location, "quantity": quantity},
            agent_id,
        )

    def _give(self, agent_id: str, args: dict) -> None:
        target = args.get("target")
        quantity = int(args.get("quantity", 0))
        giver = self.world.agents[agent_id]
        if target not in self.world.agents:
            raise ValueError("Unknown target agent")
        receiver = self.world.agents[target]
        if receiver.location != giver.location or not receiver.alive:
            raise ValueError("Target must be alive and co-located")
        if quantity <= 0 or quantity > giver.inventory:
            raise ValueError("Invalid quantity to give")
        giver.inventory -= quantity
        receiver.inventory += quantity
        self.events.append(
            self.world.round_number,
            "FOOD_GIVEN",
            {"to": target, "quantity": quantity},
            agent_id,
        )

    def _eat(self, agent_id: str, args: dict) -> None:
        quantity = int(args.get("quantity", 1))
        agent = self.world.agents[agent_id]
        if quantity <= 0 or quantity > agent.inventory:
            raise ValueError("Invalid quantity to eat")
        agent.inventory -= quantity
        agent.hunger = max(0, agent.hunger - 3 * quantity)
        self.events.append(
            self.world.round_number,
            "FOOD_EATEN",
            {"quantity": quantity, "hunger_after": agent.hunger},
            agent_id,
        )

    def _wait(self, agent_id: str, args: dict) -> None:
        del agent_id, args
