from __future__ import annotations

from collections.abc import Iterable
from collections.abc import Mapping

from behavioral_lab.agents.fake import FakeAgent
from behavioral_lab.agents.llm import LLMAgent, LLMProvider
from behavioral_lab.agents.protocol import Agent


def build_agents(
    agent_ids: Iterable[str],
    *,
    mode: str = "fake",
    provider: LLMProvider | None = None,
    providers: Mapping[str, LLMProvider] | None = None,
    llm_agent_ids: Iterable[str] | None = None,
) -> dict[str, Agent]:
    """Build a deterministic composition or an explicitly selected LLM set."""
    ids = list(agent_ids)
    if mode not in {"fake", "llm"}:
        raise ValueError("mode must be 'fake' or 'llm'")
    if mode == "llm" and provider is None:
        if not providers:
            raise ValueError("an LLM provider or providers are required in llm mode")
    selected_llm_ids = set(llm_agent_ids or ("Agent_A",)) if mode == "llm" else set()
    unknown = selected_llm_ids - set(ids)
    if unknown:
        raise ValueError(f"unknown LLM agent ids: {sorted(unknown)}")
    missing_providers = selected_llm_ids - set((providers or {}).keys())
    if provider is None and missing_providers:
        raise ValueError(f"missing provider for LLM agents: {sorted(missing_providers)}")
    return {
        agent_id: LLMAgent(agent_id, (providers or {}).get(agent_id, provider))
        if agent_id in selected_llm_ids
        else FakeAgent(agent_id)
        for agent_id in ids
    }
