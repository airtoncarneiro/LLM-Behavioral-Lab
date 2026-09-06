# LLM Behavioral Lab

Experimental framework for reproducible multi-agent behavioral simulations.

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

## Test

```bash
pytest -q
```
