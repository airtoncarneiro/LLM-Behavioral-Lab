from __future__ import annotations

from collections.abc import Iterable

from behavioral_lab.agents.fake import FakeAgent
from behavioral_lab.agents.llm import LLMAgent, LLMProvider


def build_agents(
    agent_ids: Iterable[str],
    *,
    mode: str = "fake",
    provider: LLMProvider | None = None,
) -> dict[str, FakeAgent | LLMAgent]:
    """Build the supported Milestone 2 composition."""
    ids = list(agent_ids)
    if mode not in {"fake", "llm"}:
        raise ValueError("mode must be 'fake' or 'llm'")
    if mode == "llm" and provider is None:
        raise ValueError("an LLM provider is required in llm mode")
    return {
        agent_id: LLMAgent(agent_id, provider) if mode == "llm" and agent_id == "Agent_A" else FakeAgent(agent_id)
        for agent_id in ids
    }
