# Experimental platform

`ExperimentRunner` runs the same simulation for multiple seeds and produces a
machine-readable summary for every run plus an aggregate comparison report.

```python
from behavioral_lab.experiments import ExperimentRunner

report = ExperimentRunner(
    [101, 202, 303],
    scenario="food_scarcity",
    initial_positions={"Agent_A": "KITCHEN", "Agent_B": "KITCHEN"},
).run()
print(report.to_dict())
```

Use `all_llm=True` with `agent_mode="llm"` to create the separate five-LLM
configuration. The default remains four fake agents plus `Agent_A` as the LLM.
The `common_pool` scenario concentrates resources in two shared locations and
uses the same engine and action contracts.

Metrics cover survival, hunger, consumption, cooperation, disclosure, and final
resource distribution. Built-in behavioral evaluators are included in each
`RunSummary`.

Replay preserves the scenario type, custom food distribution, and controlled
initial positions recorded at simulation start. Message context and LLM memory
are bounded for long runs, while the JSONL event log retains the complete audit
trail. Real provider/model comparisons require an explicit OpenRouter run and
are not part of the automated test suite.
