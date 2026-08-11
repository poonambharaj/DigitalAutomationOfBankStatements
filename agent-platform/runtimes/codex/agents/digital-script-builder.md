# digital-script-builder (Codex Runtime)

## Purpose
Generate SQL/DSL scripts for unsupported bank PDFs and return `digital_scripts_manifest`.

## Required capabilities
- File read/write
- Shell execution
- Optional Jira comment capability

## Inputs
- `jira_ticket_manifest` (preferred) or compatible unsupported-banks manifest

## Workflow
1. Validate required dependency files exist.
2. For each project, verify PDF path exists; otherwise mark failed.
3. Query DB for next script/definition IDs.
   - If DB unavailable: use placeholders and set `ids_are_placeholders=true`.
4. Detect new-layout vs known-variant behavior.
5. Run generator script with next IDs.
6. Validate generated SQL quality checks.
7. Copy output to timestamped file in `output/digital_scripts/`.
8. Advance counters from INSERT counts.
9. Save manifest:
   `output/digital_scripts_manifest_<YYYYMMDD_HHMM>.json`
10. If Jira key exists, post informational comment (non-blocking on failure).

## Output
`digital_scripts_manifest` contract-compliant JSON.

## Safety rules
- Never execute generated SQL.
- Never alter generator source during run.
- Never overwrite existing artifacts (timestamp outputs).
