# Project Tasks

Operational backlog for the LLM Behavioral Lab. An AI agent should consult
this file before starting work and update only the tasks it actually completes.

## Task status rules

- `[x]` means implemented and validated by code review and/or an automated test.
- `[ ]` means pending, incomplete, or not yet validated.
- Do not mark a task complete based only on documentation or an intention.
- Keep implementation tasks separate from external actions such as opening or
  merging a pull request.

## Current baseline

- Repository: `airtoncarneiro/LLM-Behavioral-Lab`
- Current development branch: `feat/milestone-2-llm-agent`
- Latest local validation: `31 passed`
- Standard CI must not call OpenRouter or require `OPENROUTER_API_KEY`.

## Milestone 1 — Food Scarcity foundation

### Completed

- [x] Define the Food Scarcity v1 research question and fixed environment.
- [x] Model agents, locations, observations, actions, hunger, inventory, and
  survival state.
- [x] Implement 5 agents (`Agent_A` through `Agent_E`).
- [x] Implement 20 food units and 20 simulation rounds.
- [x] Implement seeded turn-order randomization.
- [x] Implement movement, search, take, store, give, eat, and wait actions.
- [x] Implement hunger increase and death at hunger 10.
- [x] Keep ground truth in the environment and expose private observations.
- [x] Implement in-memory event storage with optional JSONL output.
- [x] Implement deterministic `FakeAgent` behavior.
- [x] Add tests for core state transitions and deterministic simulation.

### Still pending from the foundation

- [x] Implement a JSONL reader.
- [x] Implement replay that reapplies recorded actions without calling an LLM.
- [x] Verify replayed events and final state against the original run.
- [x] Add invariant checks for total food, inventory, valid locations, and
  living/dead agents.

## Milestone 2 — First LLM agent

### Completed

- [x] Add `LLMAgent` with a neutral system prompt.
- [x] Convert the observation into a structured prompt.
- [x] Parse JSON actions into the domain `Action` type.
- [x] Add `OpenRouterProvider` using `@preset/mais-barato`.
- [x] Read `OPENROUTER_API_KEY` from the process environment only.
- [x] Capture the provider, preset, and effective model in the event log.
- [x] Add `FakeLLMProvider` for deterministic tests and CI.
- [x] Keep the initial composition at 4 `FakeAgent` plus 1 `LLMAgent`.
- [x] Add tests for valid JSON, fenced JSON, invalid JSON, composition, and
  provider metadata logging.

### Pending implementation — priority P0

- [x] Handle provider failures and invalid LLM responses without aborting the
  entire simulation.
- [x] Add bounded timeout and retry policy.
- [x] Record an explicit `LLM_DECISION_FAILED` event with a safe error summary.
- [x] Define and implement the policy for invalid LLM actions, including a
  configurable fallback such as `WAIT`.
- [x] Add strict per-action argument validation before execution.
- [x] Request and validate structured output at the provider boundary.
- [x] Use OpenRouter Structured Outputs with `response_format.type=json_schema`,
  `strict=true`, required fields, `additionalProperties=false`, descriptive
  properties, and provider routing with `require_parameters=true`.
- [x] Document the Structured Outputs contract, endpoint-specific support,
  local validation, failure policy, and safe fallback.
- [x] Add mock HTTP tests for OpenRouter request and response handling.

### Pending implementation — priority P1

- [x] Deliver public messages to agents in later observations.
- [x] Deliver private messages only to the intended recipient.
- [x] Include communication history in the agent memory model.
- [x] Support `private_message` in the LLM action schema.
- [x] Replace the engine's concrete `FakeAgent | LLMAgent` type with a common
  agent protocol.
- [x] Extract reusable agent composition/configuration from `__main__.py`.
- [x] Add a configurable CLI for seed, rounds, output path, agent mode,
  provider, and preset.
- [x] Make fake-only execution the default so a simple local run never calls
  OpenRouter implicitly.
- [x] Expand tests for MOVE, STORE, GIVE, messages, dead agents, invalid
  quantities, invalid targets, timeouts, and provider failures.
- [x] Document Milestone 2 setup, execution modes, and safe environment
  variable handling.

### External validation and delivery

- [x] Run an optional real OpenRouter smoke test only when the environment
  provides `OPENROUTER_API_KEY`; never run it in standard CI.
- [x] Open the Milestone 2 pull request.
- [x] Confirm the GitHub Actions run for the Milestone 2 pull request passes.
- [x] Merge the Milestone 2 pull request after review.

## Experimental platform — after Milestone 2

- [x] Build an `ExperimentRunner` for multiple seeds.
- [x] Support repeated runs with controlled agent-position assignments.
- [x] Add result summaries per agent and per run.
- [x] Add behavioral metrics for survival, hunger, consumption, cooperation,
  disclosure, and resource distribution.
- [x] Add comparison reports across seeds, providers, and models.
- [x] Support five LLM agents as a separate experiment configuration.
- [x] Add behavioral evaluators.
- [x] Add a second scenario without changing the simulation core.

## Agent handoff checklist

- [ ] Read this file before coding.
- [ ] Inspect the current branch and working tree.
- [ ] Select the smallest pending task that matches the requested scope.
- [ ] Add or update tests for the change.
- [ ] Run the relevant validation and record the result in the final response.
- [ ] Mark a task `[x]` only after the implementation and validation exist.
