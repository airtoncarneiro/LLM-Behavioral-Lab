from __future__ import annotations

import json
from datetime import datetime, timezone
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
    timestamp: str = ""


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

    @classmethod
    def from_jsonl(cls, path: Path) -> "EventStore":
        """Load an event log without truncating or rewriting the source file."""
        store = cls()
        with path.open(encoding="utf-8") as fh:
            for line_number, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                try:
                    raw = json.loads(line)
                    event = Event(
                        sequence=int(raw["sequence"]),
                        round_number=int(raw["round_number"]),
                        agent_id=raw.get("agent_id"),
                        event_type=str(raw["event_type"]),
                        payload=raw["payload"],
                        timestamp=str(raw.get("timestamp", "")),
                    )
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(f"Invalid event at JSONL line {line_number}") from exc
                store._events.append(event)
        return store

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
            timestamp=datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        )
        self._events.append(event)
        if self._path:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(asdict(event), sort_keys=True) + "\n")
        return event
