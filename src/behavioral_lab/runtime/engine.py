from __future__ import annotations

import re
import time

from behavioral_lab.agents.protocol import Agent
from behavioral_lab.domain.models import Action, ActionType
from behavioral_lab.scenarios.invariants import validate_invariants


class SimulationEngine:
    def __init__(
        self,
        scenario,
        agents: dict[str, Agent],
        max_rounds: int = 20,
        llm_failure_fallback: Action | None = None,
        verbose: bool = False,
    ) -> None:
        self.scenario = scenario
        self.agents = agents
        self.max_rounds = max_rounds
        self.llm_failure_fallback = llm_failure_fallback or Action(ActionType.WAIT)
        self.verbose = verbose

    def run(self) -> dict:
        if self.verbose:
            print(
                f"Iniciando simulação: {self.max_rounds} rodadas, "
                f"{len(self.agents)} agentes",
                flush=True,
            )
        for round_number in range(1, self.max_rounds + 1):
            self.scenario.world.round_number = round_number
            if self.verbose:
                print(f"Rodada {round_number}/{self.max_rounds} iniciada", flush=True)
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
                is_llm = bool(getattr(agent, "is_llm", False))
                if self.verbose and is_llm:
                    print(f"  {agent_id}: aguardando decisão LLM...", flush=True)
                decision_started = time.perf_counter() if is_llm else None
                try:
                    action = agent.decide(observation)
                except Exception as exc:
                    if not is_llm:
                        raise
                    self._record_llm_response(round_number, agent_id, agent)
                    self._record_llm_failure(
                        round_number, agent_id, exc, None, self._duration_ms(decision_started)
                    )
                    if self.verbose:
                        print(
                            f"  {agent_id}: falha LLM; usando fallback "
                            f"{self.llm_failure_fallback.type.value}",
                            flush=True,
                        )
                    self._execute_fallback(round_number, agent_id)
                    continue

                duration_ms = self._duration_ms(decision_started)
                self._record_llm_response(round_number, agent_id, agent, duration_ms)
                if self.verbose:
                    print(f"  {agent_id}: {action.type.value}", flush=True)
                try:
                    self.scenario.execute(agent_id, action)
                except ValueError as exc:
                    if is_llm:
                        self._record_llm_failure(round_number, agent_id, exc, action, duration_ms)
                        if self.verbose:
                            print(
                                f"  {agent_id}: ação inválida; usando fallback "
                                f"{self.llm_failure_fallback.type.value}",
                                flush=True,
                            )
                        self._execute_fallback(round_number, agent_id)
                        continue
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
            validate_invariants(
                self.scenario.world,
                total_food=getattr(self.scenario, "total_food", 20),
            )
            if not self.scenario.world.alive_agents:
                break
            if self.verbose:
                print(
                    f"Rodada {round_number}/{self.max_rounds} concluída — "
                    f"vivos: {len(self.scenario.world.alive_agents)}, "
                    f"alimentos restantes: {self.scenario.world.remaining_food}",
                    flush=True,
                )

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
        if self.verbose:
            print(
                f"Simulação concluída — rodadas: {result['rounds_completed']}, "
                f"sobreviventes: {len(result['survivors'])}, "
                f"alimentos restantes: {result['remaining_food']}",
                flush=True,
            )
        return result

    def _record_llm_response(
        self, round_number: int, agent_id: str, agent: Agent, duration_ms: float | None = None
    ) -> None:
        response = getattr(agent, "last_response", None)
        if response is None:
            return
        payload = {
            "provider": response.provider,
            "preset": response.preset,
            "model": response.model,
        }
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms
        self.scenario.events.append(
            round_number,
            "LLM_RESPONSE_RECEIVED",
            payload,
            agent_id,
        )

    def _record_llm_failure(
        self,
        round_number: int,
        agent_id: str,
        error: Exception,
        action: Action | None,
        duration_ms: float | None = None,
    ) -> None:
        payload = {
            "error": self._safe_error_summary(error),
            "fallback_action": self.llm_failure_fallback.type.value,
        }
        if action is not None:
            payload["action"] = getattr(action.type, "value", str(action.type))
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms
        self.scenario.events.append(round_number, "LLM_DECISION_FAILED", payload, agent_id)

    @staticmethod
    def _duration_ms(started: float | None) -> float | None:
        if started is None:
            return None
        return round((time.perf_counter() - started) * 1000, 3)

    def _execute_fallback(self, round_number: int, agent_id: str) -> None:
        try:
            self.scenario.execute(agent_id, self.llm_failure_fallback)
        except ValueError as exc:
            self.scenario.events.append(
                round_number,
                "FALLBACK_ACTION_FAILED",
                {"error": self._safe_error_summary(exc)},
                agent_id,
            )

    @staticmethod
    def _safe_error_summary(error: Exception) -> str:
        message = " ".join(str(error).split())
        message = re.sub(
            r"(?i)(api[_ -]?key|authorization|bearer)\s*[:=]?\s*\S+",
            r"\1=[redacted]",
            message,
        )
        message = message[:240]
        return f"{type(error).__name__}: {message}" if message else type(error).__name__
