from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Event:
    sequence: int
    round_number: int
    agent_id: str | None
    event_type: str
    payload: dict[str, Any]


class EventStore:
    def __init__(self, path: Path | None = None) -> None:
        self._events: list[Event] = []
        self._path = path
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")

    @property
    def events(self) -> tuple[Event, ...]:
        return tuple(self._events)

    def append(
        self,
        round_number: int,
        event_type: str,
        payload: dict[str, Any],
        agent_id: str | None = None,
    ) -> Event:
        event = Event(
            sequence=len(self._events) + 1,
            round_number=round_number,
            agent_id=agent_id,
            event_type=event_type,
            payload=payload,
        )
        self._events.append(event)
        if self._path:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(asdict(event), sort_keys=True) + "\n")
        return event
