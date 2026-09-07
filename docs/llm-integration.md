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

Reference: [OpenRouter Structured Outputs documentation](https://openrouter.ai/docs/guides/features/structured-outputs).
