# jira-ticket-creator (GitHub Copilot Runtime)

## Purpose
Create Jira task tickets for unsupported banks discovered by `statement-harvester`, and return an updated manifest with ticket metadata.

## Required capabilities
- Atlassian MCP (create/get issue)
- File read/write

## Inputs
- `new_banks_manifest`

## Workflow
1. Process only projects with `status = unsupported`.
2. Before creating tickets, check for existing open ticket pattern:
   `project = DOC AND summary ~ "DOC-AUTO-{BANKNAME}" AND statusCategory != Done`
3. If existing ticket found:
   - do not create duplicate
   - mark `jira_ticket_status = already_exists`
4. If not found, create Task in project `DOC`:
   - Summary: `DOC-AUTO-{BANKNAME}: Create digital script`
   - Labels: `digital-scripts, auto-generated, new-bank`
   - Priority: Medium
   - Description from shared template with project details
5. Capture `jira_ticket_key`, URL, and status.
6. Continue on per-project failures; do not abort whole batch unless Jira auth fails.
7. Save and return:
   `output/jira_ticket_manifest_<YYYYMMDD_HHMM>.json`

## Output
`jira_ticket_manifest` (canonical contract)

## Safety rules
- Never auto-assign users.
- Never modify/close existing issues.
- Never create duplicates when open ticket exists.
