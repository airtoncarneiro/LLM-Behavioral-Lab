from __future__ import annotations

from behavioral_lab.agents.llm import LLMAgent
from behavioral_lab.agents.fake import FakeAgent
from behavioral_lab.scenarios.food_scarcity import FoodScarcityScenario
from behavioral_lab.scenarios.invariants import validate_invariants


class SimulationEngine:
    def __init__(
        self,
        scenario: FoodScarcityScenario,
        agents: dict[str, FakeAgent | LLMAgent],
        max_rounds: int = 20,
    ) -> None:
        self.scenario = scenario
        self.agents = agents
        self.max_rounds = max_rounds

    def run(self) -> dict:
        for round_number in range(1, self.max_rounds + 1):
            self.scenario.world.round_number = round_number
            order = self.scenario.turn_order()
            self.scenario.events.append(
                round_number,
                "TURN_ORDER_SELECTED",
                {"order": order},
            )

            for agent_id in order:
                if not self.scenario.world.agents[agent_id].alive:
                    continue
                observation = self.scenario.observe(agent_id)
                agent = self.agents[agent_id]
                action = agent.decide(observation)
                if isinstance(agent, LLMAgent) and agent.last_response is not None:
                    response = agent.last_response
                    self.scenario.events.append(
                        round_number,
                        "LLM_RESPONSE_RECEIVED",
                        {
                            "provider": response.provider,
                            "preset": response.preset,
                            "model": response.model,
                        },
                        agent_id,
                    )
                try:
                    self.scenario.execute(agent_id, action)
                except ValueError as exc:
                    self.scenario.events.append(
                        round_number,
                        "INVALID_ACTION",
                        {
                            "action": action.type.value,
                            "arguments": action.arguments,
                            "error": str(exc),
                        },
                        agent_id,
                    )

            self.scenario.end_round()
            validate_invariants(self.scenario.world)
            if not self.scenario.world.alive_agents:
                break

        result = {
            "rounds_completed": self.scenario.world.round_number,
            "survivors": self.scenario.world.alive_agents,
            "remaining_food": self.scenario.world.remaining_food,
            "event_count": len(self.scenario.events.events),
        }
        self.scenario.events.append(
            self.scenario.world.round_number,
            "SIMULATION_FINISHED",
            result,
        )
        return result
