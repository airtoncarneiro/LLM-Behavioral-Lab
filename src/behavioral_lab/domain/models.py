from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ActionType(StrEnum):
    MOVE = "move"
    SEARCH = "search"
    TAKE = "take"
    STORE = "store"
    GIVE = "give"
    EAT = "eat"
    WAIT = "wait"


@dataclass(frozen=True)
class Message:
    round_number: int
    sender: str
    content: str
    recipient: str | None = None


@dataclass(frozen=True)
class Action:
    type: ActionType
    arguments: dict[str, Any] = field(default_factory=dict)
    public_message: str | None = None
    private_message_to: str | None = None
    private_message: str | None = None


@dataclass
class AgentState:
    agent_id: str
    location: str = "CENTRAL_ROOM"
    hunger: int = 0
    inventory: int = 0
    alive: bool = True
    searched_locations: set[str] = field(default_factory=set)


@dataclass
class LocationState:
    name: str
    food: int


@dataclass
class WorldState:
    round_number: int
    agents: dict[str, AgentState]
    locations: dict[str, LocationState]
    consumed_food: int = 0

    @property
    def alive_agents(self) -> list[str]:
        return [a.agent_id for a in self.agents.values() if a.alive]

    @property
    def remaining_food(self) -> int:
        return sum(location.food for location in self.locations.values())


@dataclass(frozen=True)
class Observation:
    round_number: int
    agent_id: str
    location: str
    hunger: int
    inventory: int
    present_agents: tuple[str, ...]
    visible_food: int | None
    location_searched: bool
    available_locations: tuple[str, ...]
    public_messages: tuple[Message, ...] = ()
    private_messages: tuple[Message, ...] = ()
