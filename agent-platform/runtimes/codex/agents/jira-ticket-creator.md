# jira-ticket-creator (Codex Runtime)

## Purpose
Create/link Jira tasks for unsupported banks and return `jira_ticket_manifest`.

## Required capabilities
- Jira API/MCP create issue
- Jira API/MCP fetch/search issue
- File read/write

## Inputs
- `new_banks_manifest`

## Workflow
1. Process only `status=unsupported` projects.
2. Check for existing open DOC-AUTO ticket for each bank/project.
3. If found: mark `jira_ticket_status=already_exists`.
4. If not found: create Task in project `DOC` using agreed summary/description template.
5. Capture key/url/status per project.
6. Continue through per-project failures (except Jira auth failure, which is blocking).
7. Save and return:
   `output/jira_ticket_manifest_<YYYYMMDD_HHMM>.json`

## Output
`jira_ticket_manifest` contract-compliant JSON.

## Safety rules
- Do not auto-assign users.
- Do not modify/close existing tickets.
- Avoid duplicate tickets.
