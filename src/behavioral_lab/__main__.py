from pathlib import Path

from behavioral_lab.agents.fake import FakeAgent
from behavioral_lab.agents.llm import LLMAgent
from behavioral_lab.runtime.engine import SimulationEngine
from behavioral_lab.scenarios.food_scarcity import FoodScarcityScenario
from behavioral_lab.storage.events import EventStore
from behavioral_lab.providers.openrouter import OpenRouterProvider


def main() -> None:
    store = EventStore(Path("events.jsonl"))
    scenario = FoodScarcityScenario(seed=101, event_store=store)
    provider = OpenRouterProvider()
    agents = {
        agent_id: (LLMAgent(agent_id, provider) if agent_id == "Agent_A" else FakeAgent(agent_id))
        for agent_id in scenario.world.agents
    }
    result = SimulationEngine(scenario, agents).run()
    print(result)


if __name__ == "__main__":
    main()
