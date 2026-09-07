# LLM integration

## Structured Outputs

The LLM agent must request decisions through OpenRouter Structured Outputs,
rather than relying only on prompt instructions to return JSON.

The provider request must use:

- `response_format.type = "json_schema"`;
- an explicit schema for the action decision;
- `strict: true`;
- all required fields declared in `required`;
- `additionalProperties: false`;
- clear descriptions for schema properties;
- provider routing with `require_parameters: true`, so requests are sent only
  to endpoints that support the requested parameter.

The action schema must represent the domain contract, including the allowed
action names, an object for action arguments, and the optional public and
private message fields. The schema is not a replacement for domain validation:
the application must validate the decoded response locally before creating an
`Action` or executing it in the simulation.

The current schema is sent by `OpenRouterProvider` with the preset as `model`,
`response_format.type = "json_schema"`, `json_schema.strict = true`, and
`provider.require_parameters = true`. Its top-level required fields are
`action`, `arguments`, `public_message`, `private_message_to`, and
`private_message`; nullable message fields represent the optional values. The
argument object has the explicitly known `location`, `target`, and `quantity`
properties and rejects other keys.

Because strict structured output requires the three argument properties to be
present, unused action arguments are returned as `null` on the wire. The
`LLMAgent` removes those `null` properties before creating the domain `Action`,
so `wait` and `search` receive `{}`, while `move`, `take`, `store`, `give`, and
`eat` receive only the arguments they use. Non-null arguments for the wrong
action are ignored after their types are validated, so models that fill
irrelevant nullable fields do not cause a valid action to fail. Unknown
argument fields and invalid types remain rejected.

Optional messages are normalized independently of the action: a blank public
message is discarded, and an incomplete or blank private-message pair is
discarded. A complete pair is still subject to recipient, co-location, and
non-empty-content domain validation.

The OpenRouter adapter validates the complete response shape before returning
it. Integration tests then exercise every supported action through the agent
and simulation engine with a schema-conforming response.

The provider adapter applies a finite timeout and a finite retry count. It
retries only timeouts, transport failures, HTTP 408, HTTP 429, and 5xx
responses. The response envelope must contain a textual
`choices[0].message.content`; the agent then performs JSON, field, and action
validation locally. A provider error, malformed response, or domain-invalid
action emits `LLM_DECISION_FAILED` and executes the configurable `WAIT`
fallback, allowing the remaining agents and rounds to continue. Error payloads
are bounded and redact credential-like values.

Public messages are included in observations after they are emitted. Private
messages are stored only for the named, alive, co-located recipient. The
scenario keeps a bounded context window for both public and private messages
(100 messages by default), while the event log retains the complete history for
audit and replay. The LLM agent also keeps only its most recent five decision
records by default; `LLMAgent(max_memory=...)` can adjust that research
context.

OpenRouter support is endpoint-specific. A model name alone does not guarantee
Structured Outputs support, so the selected model/provider combination must be
checked before a real experiment. Unsupported models, invalid schemas,
provider errors, timeouts, and responses that fail local validation must be
handled as LLM decision failures. They must not silently change the experiment
protocol.

The runtime policy for such failures must be explicit and configurable. The
default safe fallback is `WAIT`, and the event log must record an
`LLM_DECISION_FAILED` event containing a safe error summary without exposing
API keys or other sensitive data.

Response Healing may be evaluated for non-streaming requests, but it does not
replace schema validation, domain validation, or the failure policy.

## Local validation and endpoint support

The standard test suite uses `FakeLLMProvider` and mock HTTP responses; it does
not require `OPENROUTER_API_KEY` and does not prove that a selected live model
supports Structured Outputs. Before a real experiment, select a model/provider
route that advertises support for the requested parameter and run an explicit
smoke test with the key supplied in the process environment. Unsupported
endpoints are treated as decision failures rather than silently changing the
experiment protocol.

## Per-agent models and configuration files

The main CLI accepts `--config path/to/file.json`. Its `agents` object may
declare a separate `preset` for every LLM agent. Agents declared with
`"type": "fake"` remain deterministic and do not make network calls. See
[`configs/example.json`](../configs/example.json) for a mixed configuration.

Command-line values override the corresponding top-level file values. Secrets
must remain in the process environment; the OpenRouter API key is read from
`OPENROUTER_API_KEY`, never from JSON.

Reference: [OpenRouter Structured Outputs documentation](https://openrouter.ai/docs/guides/features/structured-outputs).
