# Runtime Router (Claude | GitHub Copilot | Codex)

## Purpose
Provide one consistent entrypoint for teammates to run the same multi-agent pipeline using their preferred runtime:
- `claude`
- `github-copilot`
- `codex`

This router enforces shared contracts and stage behavior so outputs are consistent across runtimes.

---

## Runtime selection

## Accepted values
- `runtime=claude`
- `runtime=github-copilot`
- `runtime=codex`

If no runtime is specified, default to:
- `github-copilot`

## Selection policy
1. If user explicitly names a runtime, use it.
2. Else if environment variable `AGENT_RUNTIME` is set, use it.
3. Else default to `github-copilot`.

If selected runtime is unavailable, fail fast with a clear fallback recommendation.

---

## Canonical pipeline (applies to all runtimes)

1. `statement-harvester`
2. `jira-ticket-creator` (optional only if user/policy disables)
3. `digital-script-builder`
4. `test-engineer`
5. `code-guardian`
6. `github-deployer`

Do not reorder or skip stages unless explicitly requested.

---

## Dispatch map

| Runtime | Orchestrator path |
|---|---|
| claude | `runtimes/claude/orchestrator.md` |
| github-copilot | `runtimes/github-copilot/orchestrator.md` |
| codex | `runtimes/codex/orchestrator.md` |

Each runtime orchestrator must:
- enforce `contracts/workflow.md`
- validate against `contracts/manifests.md`
- respect `contracts/tool-capability-matrix.md`

---

## Behavioral parity rules (critical)

All runtimes MUST preserve:

1. Same stage order and gate logic.
2. Same manifest schemas and required keys.
3. Same severity model in review:
   - `critical`
   - `warning`
   - `suggestion`
4. Same deployment safety rules:
   - no force-push to protected branches
   - stop on non-fast-forward conflict
5. Same auth checkpoint behavior for StatementRec MFA.
6. Same policy that generated SQL is never executed automatically.

Only runtime-specific differences allowed:
- tool invocation syntax
- model/provider configuration
- capability fallback wording

---

## Capability preflight

Before stage execution, orchestrator must verify required capabilities for selected runtime.

If a required capability is missing, return:
- `stage`
- `missing_capability`
- `impact`
- `manual_fallback`
- `retryable`

Do not silently skip capability checks.

---

## Standard run profile

## Inputs
- `runtime` (optional)
- user task/instruction
- optional policy flags:
  - `jira_enabled=true|false`
  - `deploy_enabled=true|false`

## Outputs
- stage-by-stage status
- latest manifest path per stage
- final outcome:
  - `COMPLETED`
  - `BLOCKED`
  - `PARTIAL`
- next action recommendation

---

## Policy flags

## `jira_enabled`
- `true` (default): run Jira stage
- `false`: skip Jira stage and annotate downstream manifests with `jira_skipped=true`

## `deploy_enabled`
- `true` (default): run deploy if gates pass
- `false`: stop after review with “ready-to-deploy” status

---

## Error contract (router + orchestrators)

Use this common structure:

```json
{
  "runtime": "github-copilot",
  "stage": "test-engineer",
  "error_type": "contract_invalid",
  "message": "Missing required key: projects[].sql_file",
  "recommended_next_action": "Regenerate digital_scripts_manifest with required fields",
  "retryable": true
}
```

`error_type` enum:
- `capability_missing`
- `contract_invalid`
- `runtime_failure`
- `policy_block`

---

## Example invocation patterns

## Minimal
`Run pipeline for newly unsupported banks using runtime=github-copilot.`

## Explicit with flags
`Run pipeline runtime=codex jira_enabled=true deploy_enabled=false.`

## Teammate choice
`Use runtime=claude for this run and keep all standard stage gates.`

---

## Acceptance criteria for cross-runtime consistency

A run is considered equivalent across runtimes when:
1. Same projects are classified unsupported.
2. Generated manifest keys and semantics match canonical contracts.
3. Gate decisions are identical (pass/fail/block).
4. Final deploy decision is identical under same inputs and flags.

If results diverge, open a parity issue and attach both manifests for comparison.

---

## Notes for maintainers

- Keep business logic in `contracts/*`, not runtime prompts.
- Update this router when adding/removing runtimes.
- Treat runtime adapters as thin wrappers around shared policy.
