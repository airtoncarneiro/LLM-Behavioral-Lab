from __future__ import annotations

from typing import Protocol

from behavioral_lab.domain.models import Action, Observation


class Agent(Protocol):
    agent_id: str

    def decide(self, observation: Observation) -> Action: ...
