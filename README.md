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

The default is deterministic and fake-only; it never calls OpenRouter:

```bash
python -m behavioral_lab --seed 101 --rounds 20 --output events.jsonl
```

## Milestone 2

The first LLM slot is `Agent_A`; the other four agents remain deterministic
`FakeAgent` instances. `OpenRouterProvider` uses the `@preset/mais-barato`
preset and reads `OPENROUTER_API_KEY` only from the process environment. Tests
use `FakeLLMProvider` and never call OpenRouter.

To exercise the first LLM slot with the deterministic provider:

```bash
python -m behavioral_lab --agent-mode llm --provider fake --rounds 20
```

An OpenRouter run is always explicit and reads the key only from the process
environment:

```bash
OPENROUTER_API_KEY=... python -m behavioral_lab \
  --agent-mode llm --provider openrouter --preset @preset/mais-barato
```

This configuration uses one real LLM agent (`Agent_A`) and four deterministic
`FakeAgent` instances. The provider validates the strict response schema and
the agent normalizes unused nullable action arguments before domain validation.
Incomplete optional messages are safely discarded while complete messages are
still domain-validated.
The live path requires an OpenRouter model/provider route that supports
Structured Outputs; the standard test suite does not make network calls.

LLM integration details, including the Structured Outputs contract, retries,
failure policy, and message visibility, are documented in
[`docs/llm-integration.md`](docs/llm-integration.md).

## Experimental platform

Run reproducible experiments across multiple seeds with summaries, behavioral
metrics, comparison reports, controlled initial positions, and the optional
five-LLM configuration. See [`docs/experimental-platform.md`](docs/experimental-platform.md).

## Test

```bash
pytest -q
```
