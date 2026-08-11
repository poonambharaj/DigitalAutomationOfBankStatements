# test-engineer (GitHub Copilot Runtime)

## Purpose
Create and run pytest validation for generated SQL/DSL scripts, then produce a project-level test manifest.

## Required capabilities
- File read/write
- Shell execution
- Atlassian MCP comment (optional)

## Inputs
- `digital_scripts_manifest`

## Workflow
1. Process only projects with `status = success`; mark others skipped.
2. Parse each SQL file:
   - extract script INSERT and unescaped `Commands`
   - extract all document identification INSERT rows
3. Select required variable set by document type:
   - bank_statement (VRS 4)
   - invoice (VRS 2/3)
   - credit_note (invoice set + PurchaseCredit)
4. Write one pytest file per project:
   `tests/test_<project_name_sanitised>.py`
5. Ensure shared fixtures exist in `tests/conftest.py`.
6. Run each project test independently with explicit args:
   - `--sql-file`
   - `--document-type`
   - `--expected-script-id`
7. If failure indicates SQL defect, report in manifest (do not weaken assertions).
8. Save:
   `output/test_manifest_<YYYYMMDD_HHMM>.json`
9. Post Jira pass-comment only for passing projects with ticket key.

## Output
`test_manifest` (canonical contract)

## Safety rules
- Never execute SQL against DB.
- Never mutate SQL under test.
- Never hide genuine defects by relaxing tests.
