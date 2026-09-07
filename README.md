# LLM Behavioral Lab

Experimental framework for reproducible multi-agent behavioral simulations.

The implementation backlog and agent handoff checklist are maintained in
[`docs/tasks.md`](docs/tasks.md).

## Milestone 1

Food Scarcity v1 without LLMs:
- 5 deterministic fake agents
- 20 rounds
- 20 food units
- seeded turn-order randomization
- hunger/survival mechanics
- private observations
- immutable JSONL event log
- deterministic replay-oriented execution

## Run

```bash
python -m behavioral_lab
```

## Milestone 2

The first LLM slot is `Agent_A`; the other four agents remain deterministic
`FakeAgent` instances. `OpenRouterProvider` uses the `@preset/mais-barato`
preset and reads `OPENROUTER_API_KEY` only from the process environment. Tests
use `FakeLLMProvider` and never call OpenRouter.

LLM integration details, including the planned Structured Outputs contract and
failure policy, are documented in
[`docs/llm-integration.md`](docs/llm-integration.md).

## Test

```bash
pytest -q
```
