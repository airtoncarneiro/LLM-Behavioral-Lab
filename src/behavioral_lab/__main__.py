from pathlib import Path

from behavioral_lab.agents.fake import FakeAgent
from behavioral_lab.runtime.engine import SimulationEngine
from behavioral_lab.scenarios.food_scarcity import FoodScarcityScenario
from behavioral_lab.storage.events import EventStore


def main() -> None:
    store = EventStore(Path("events.jsonl"))
    scenario = FoodScarcityScenario(seed=101, event_store=store)
    agents = {agent_id: FakeAgent(agent_id) for agent_id in scenario.world.agents}
    result = SimulationEngine(scenario, agents).run()
    print(result)


if __name__ == "__main__":
    main()
