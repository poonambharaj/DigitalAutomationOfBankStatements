# Codex Runtime Scaffold (Phase 2)

## Purpose
This directory mirrors the GitHub Copilot runtime so your team can run the same multi-agent pipeline on Codex with minimal adaptation.

## Migration strategy
1. Keep all business logic in `agent-platform/contracts/*`.
2. Reuse the same agent names and stage order.
3. Replace only runtime/tooling instructions per agent.

## Planned structure

runtimes/codex/
- README.md
- orchestrator.md
- agents/
  - statement-harvester.md
  - jira-ticket-creator.md
  - digital-script-builder.md
  - test-engineer.md
  - code-guardian.md
  - github-deployer.md

## Required parity with GitHub runtime
Each Codex agent must preserve:
- identical input/output manifest contracts
- identical pass/fail gate semantics
- identical safety rules
- identical severity model (critical/warning/suggestion)

Only these may differ:
- tool invocation syntax
- runtime-specific execution notes
- capability fallback behavior

## Adapter checklist (per agent)

- [ ] Replace GitHub/Copilot tool references with Codex-compatible tools
- [ ] Keep stage workflow steps semantically identical
- [ ] Keep output schema exactly unchanged
- [ ] Keep Jira/GitHub integration behavior unchanged
- [ ] Re-run golden task comparisons against GitHub runtime outputs

## Golden test pack (recommended)
Before enabling Codex runtime in production, validate with at least:
1. Unsupported bank discovery case
2. Known layout variant case (definition-only output)
3. Build with DB unavailable (`ids_are_placeholders=true`)
4. Test failure due to missing required variables
5. Review blocked due to critical schema/security issue
6. Deploy non-fast-forward conflict handling

## Runtime selector contract
Your top-level orchestrator/router should accept:
- `runtime=claude`
- `runtime=github-copilot`
- `runtime=codex`

and dispatch to the corresponding runtime orchestrator while preserving the same contracts.

## Next step
Copy `runtimes/github-copilot/orchestrator.md` into `runtimes/codex/orchestrator.md`, then replace runtime-specific capability/tooling sections only.
