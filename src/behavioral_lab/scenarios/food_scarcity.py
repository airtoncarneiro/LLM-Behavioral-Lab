from __future__ import annotations

import random
from copy import deepcopy

from behavioral_lab.domain.models import (
    Action,
    ActionType,
    AgentState,
    LocationState,
    Observation,
    Message,
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
    scenario_name = "food_scarcity"

    def __init__(
        self,
        seed: int,
        event_store: EventStore,
        *,
        initial_positions: dict[str, str] | None = None,
        distribution: dict[str, int] | None = None,
        max_message_history: int = 100,
    ) -> None:
        if max_message_history < 1:
            raise ValueError("max_message_history must be positive")
        self.seed = seed
        self._rng = random.Random(seed)
        self.events = event_store
        selected_distribution = dict(
            DEFAULT_DISTRIBUTION if distribution is None else distribution
        )
        if set(selected_distribution) != set(LOCATIONS) or any(
            isinstance(food, bool) or not isinstance(food, int) or food < 0
            for food in selected_distribution.values()
        ):
            raise ValueError("distribution must contain non-negative food for every location")
        self.total_food = sum(selected_distribution.values())
        self.initial_distribution = dict(selected_distribution)
        self.initial_positions = {
            f"Agent_{letter}": "CENTRAL_ROOM" for letter in "ABCDE"
        }
        self.initial_positions.update(initial_positions or {})
        self.max_message_history = max_message_history
        self._public_messages: list[Message] = []
        self._private_messages: dict[str, list[Message]] = {f"Agent_{letter}": [] for letter in "ABCDE"}
        self.world = WorldState(
            round_number=0,
            agents={
                f"Agent_{letter}": AgentState(agent_id=f"Agent_{letter}")
                for letter in "ABCDE"
            },
            locations={
                name: LocationState(name=name, food=food)
                for name, food in selected_distribution.items()
            },
        )
        if initial_positions is not None:
            unknown_agents = set(initial_positions) - set(self.world.agents)
            unknown_locations = set(initial_positions.values()) - set(self.world.locations)
            if unknown_agents or unknown_locations:
                raise ValueError("initial_positions contains an unknown agent or location")
            for agent_id, location in initial_positions.items():
                self.world.agents[agent_id].location = location
        validate_invariants(self.world, total_food=self.total_food)
        self.events.append(0, "SIMULATION_INITIALIZED", self.snapshot())

    def snapshot(self) -> dict:
        return {
            "scenario": self.scenario_name,
            "seed": self.seed,
            "round": self.world.round_number,
            "initial_positions": dict(self.initial_positions),
            "food_distribution": dict(self.initial_distribution),
            "consumed_food": self.world.consumed_food,
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
            public_messages=tuple(self._public_messages),
            private_messages=tuple(self._private_messages[agent_id]),
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
                "public_messages": [self._message_payload(message) for message in observation.public_messages],
                "private_messages": [self._message_payload(message) for message in observation.private_messages],
            },
            agent_id,
        )
        return observation

    def execute(self, agent_id: str, action: Action) -> None:
        agent = self.world.agents[agent_id]
        if not agent.alive:
            return

        self.validate_action(agent_id, action)
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
                "public_message": action.public_message,
                "private_message_to": action.private_message_to,
                "private_message": action.private_message,
            },
            agent_id,
        )

        if action.public_message:
            self._public_messages.append(
                Message(self.world.round_number, agent_id, action.public_message)
            )
            self._public_messages = self._public_messages[-self.max_message_history :]
            self.events.append(
                self.world.round_number,
                "PUBLIC_MESSAGE",
                {"message": action.public_message},
                agent_id,
            )

        if action.private_message and action.private_message_to:
            message = Message(
                self.world.round_number,
                agent_id,
                action.private_message,
                action.private_message_to,
            )
            self._private_messages[action.private_message_to].append(message)
            self._private_messages[action.private_message_to] = self._private_messages[
                action.private_message_to
            ][-self.max_message_history :]
            self.events.append(
                self.world.round_number,
                "PRIVATE_MESSAGE",
                {"to": action.private_message_to, "message": action.private_message},
                agent_id,
            )
        validate_invariants(self.world, total_food=self.total_food)

    def validate_action(self, agent_id: str, action: Action) -> None:
        if not isinstance(action, Action):
            raise ValueError("agent must return an Action")
        if not isinstance(action.arguments, dict):
            raise ValueError("action arguments must be an object")
        try:
            allowed = {
                ActionType.MOVE: {"location"},
                ActionType.SEARCH: set(),
                ActionType.TAKE: {"quantity"},
                ActionType.STORE: {"quantity"},
                ActionType.GIVE: {"target", "quantity"},
                ActionType.EAT: {"quantity"},
                ActionType.WAIT: set(),
            }[action.type]
        except (KeyError, TypeError) as exc:
            raise ValueError("Unknown action type") from exc
        if set(action.arguments) != allowed:
            raise ValueError(f"Invalid arguments for {action.type.value}")

        agent = self.world.agents[agent_id]
        args = action.arguments
        if action.type is ActionType.MOVE:
            if not isinstance(args["location"], str) or args["location"] not in self.world.locations:
                raise ValueError(f"Unknown location: {args['location']}")
        elif action.type is ActionType.SEARCH or action.type is ActionType.WAIT:
            pass
        elif action.type is ActionType.TAKE:
            self._validate_quantity(args["quantity"])
            if agent.location not in agent.searched_locations:
                raise ValueError("Agent must search the location before taking food")
            if args["quantity"] > self.world.locations[agent.location].food:
                raise ValueError("Cannot take more food than is available")
        elif action.type is ActionType.STORE:
            self._validate_quantity(args["quantity"])
            if args["quantity"] > agent.inventory:
                raise ValueError("Invalid quantity to store")
        elif action.type is ActionType.GIVE:
            target = args["target"]
            if not isinstance(target, str) or target not in self.world.agents or target == agent_id:
                raise ValueError("Unknown target agent")
            receiver = self.world.agents[target]
            if receiver.location != agent.location or not receiver.alive:
                raise ValueError("Target must be alive and co-located")
            self._validate_quantity(args["quantity"])
            if args["quantity"] > agent.inventory:
                raise ValueError("Invalid quantity to give")
        elif action.type is ActionType.EAT:
            self._validate_quantity(args["quantity"])
            if args["quantity"] > agent.inventory:
                raise ValueError("Invalid quantity to eat")

        self._validate_messages(agent_id, action)

    @staticmethod
    def _validate_quantity(quantity: object) -> None:
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity must be a positive integer")

    def _validate_messages(self, agent_id: str, action: Action) -> None:
        if action.public_message is not None and (
            not isinstance(action.public_message, str) or not action.public_message.strip()
        ):
            raise ValueError("public_message must be a non-empty string")
        has_recipient = action.private_message_to is not None
        has_content = action.private_message is not None
        if has_recipient != has_content:
            raise ValueError("private_message_to and private_message must be provided together")
        if has_recipient:
            target = action.private_message_to
            if not isinstance(target, str) or target not in self.world.agents or target == agent_id:
                raise ValueError("Unknown private message recipient")
            recipient = self.world.agents[target]
            sender = self.world.agents[agent_id]
            if not recipient.alive or recipient.location != sender.location:
                raise ValueError("Private message recipient must be alive and co-located")
            if not isinstance(action.private_message, str) or not action.private_message.strip():
                raise ValueError("private_message must be a non-empty string")

    @staticmethod
    def _message_payload(message: Message) -> dict[str, object]:
        return {
            "round": message.round_number,
            "sender": message.sender,
            "recipient": message.recipient,
            "message": message.content,
        }

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
        quantity = args["quantity"]
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
        quantity = args["quantity"]
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
        quantity = args["quantity"]
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
        quantity = args["quantity"]
        agent = self.world.agents[agent_id]
        if quantity <= 0 or quantity > agent.inventory:
            raise ValueError("Invalid quantity to eat")
        agent.inventory -= quantity
        self.world.consumed_food += quantity
        agent.hunger = max(0, agent.hunger - 3 * quantity)
        self.events.append(
            self.world.round_number,
            "FOOD_EATEN",
            {"quantity": quantity, "hunger_after": agent.hunger},
            agent_id,
        )

    def _wait(self, agent_id: str, args: dict) -> None:
        del agent_id, args
