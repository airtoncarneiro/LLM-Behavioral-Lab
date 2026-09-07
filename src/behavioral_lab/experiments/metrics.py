from __future__ import annotations

from typing import Any, Iterable

from behavioral_lab.storage.events import Event


def summarize_events(
    events: Iterable[Event],
    snapshot: dict[str, Any],
    *,
    agent_ids: Iterable[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Compute reproducible behavioral metrics from the immutable event log."""
    ids = tuple(agent_ids)
    per_agent: dict[str, dict[str, Any]] = {
        agent_id: {
            "actions": 0,
            "consumed": 0,
            "given": 0,
            "received": 0,
            "public_disclosures": 0,
            "private_disclosures": 0,
        }
        for agent_id in ids
    }
    events = tuple(events)
    gifts = 0
    public_messages = 0
    private_messages = 0
    total_consumed = 0
    for event in events:
        agent_id = event.agent_id
        payload = event.payload
        if agent_id not in per_agent:
            continue
        if event.event_type == "ACTION_EXECUTED":
            per_agent[agent_id]["actions"] += 1
        elif event.event_type == "FOOD_EATEN":
            quantity = int(payload.get("quantity", 0))
            total_consumed += quantity
            per_agent[agent_id]["consumed"] += quantity
        elif event.event_type == "FOOD_GIVEN":
            quantity = int(payload.get("quantity", 0))
            gifts += 1
            per_agent[agent_id]["given"] += quantity
            recipient = payload.get("to")
            if recipient in per_agent:
                per_agent[recipient]["received"] += quantity
        elif event.event_type == "PUBLIC_MESSAGE":
            public_messages += 1
            per_agent[agent_id]["public_disclosures"] += 1
        elif event.event_type == "PRIVATE_MESSAGE":
            private_messages += 1
            per_agent[agent_id]["private_disclosures"] += 1

    agents = snapshot["agents"]
    survivors = [agent_id for agent_id, state in agents.items() if state["alive"]]
    for agent_id, state in agents.items():
        if agent_id in per_agent:
            per_agent[agent_id].update(
                {
                    "alive": state["alive"],
                    "hunger": state["hunger"],
                    "inventory": state["inventory"],
                    "location": state["location"],
                }
            )
    total_agents = len(agents)
    total_resources = sum(state["food"] for state in snapshot["locations"].values()) + sum(
        state["inventory"] for state in agents.values()
    )
    resource_distribution = {
        "agent_inventory": {agent_id: state["inventory"] for agent_id, state in agents.items()},
        "location_food": {
            location: state["food"] for location, state in snapshot["locations"].items()
        },
        "trackable_total": total_resources,
    }
    metrics = {
        "survival": {
            "survivors": len(survivors),
            "survival_rate": len(survivors) / total_agents if total_agents else 0.0,
        },
        "hunger": {
            "mean_final": sum(state["hunger"] for state in agents.values()) / total_agents
            if total_agents
            else 0.0,
            "max_final": max((state["hunger"] for state in agents.values()), default=0),
        },
        "consumption": {
            "total_units": total_consumed,
            "by_agent": {agent_id: value["consumed"] for agent_id, value in per_agent.items()},
        },
        "cooperation": {
            "gifts": gifts,
            "units_given": sum(value["given"] for value in per_agent.values()),
            "by_agent": {agent_id: value["given"] for agent_id, value in per_agent.items()},
        },
        "disclosure": {
            "public_messages": public_messages,
            "private_messages": private_messages,
            "total_messages": public_messages + private_messages,
        },
        "resource_distribution": resource_distribution,
    }
    return per_agent, metrics
