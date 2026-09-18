# digital-script-builder (GitHub Copilot Runtime)

## Purpose
Generate SQL/DSL extraction scripts for unsupported-bank PDFs and return a structured generation manifest.

## Required capabilities
- File read/write
- Shell execution
- Atlassian MCP comment (optional)

## Inputs
- `jira_ticket_manifest` (or `new_banks_manifest` if Jira stage skipped)

## Workflow
1. Verify runtime dependencies exist:
   - `References/generate_script.py`
   - `References/Plan.md`
   - `requirements.txt`
   - `References/DigitalScriptSample/DigitalScripts.sql`
   - `References/DigitalScriptSample/DigitalDocDefination.sql`

   `References/.env` (`ANTHROPIC_API_KEY`) is NOT required for this runtime — the
   GitHub Copilot model authors the script directly from the PDF; it never shells
   out to `generate_script.py`'s Anthropic call. Only the Claude runtime needs it.
2. For each unsupported project:
   - validate `pdf_saved` exists
   - if missing: mark failed and continue
3. Query DB for next IDs (`digitalpdf$script`, `digitalpdf$documentidentification`).
   - on DB failure: use placeholder `9999`, set `ids_are_placeholders = true`
4. Determine whether layout is new or known variant:
   - new layout: create script+definition rows
   - known layout: definition rows only pointing to existing ScriptId
5. Run generator:
   `py References/generate_script.py "<pdf_saved>" --next-script-id X --next-def-id Y`
6. Validate output SQL:
   - required INSERTs present (per layout case)
   - no markdown fences
   - no invalid placeholders (if real IDs used)
   - non-empty Commands
   - valid VerificationRuleSetId (2/3/4)
7. Copy SQL to timestamped destination:
   `output/digital_scripts/<project_name>_<YYYYMMDD_HHMM>.sql`
8. Increment ID counters based on INSERT row counts.
9. Save manifest:
   `output/digital_scripts_manifest_<YYYYMMDD_HHMM>.json`
10. If `jira_ticket_key` exists, post success comment; on Jira failure, record warning only.

## Output
`digital_scripts_manifest` (canonical contract)

## Safety rules
- Never execute generated SQL.
- Never modify generator source.
- Never overwrite existing SQL; always timestamp.
