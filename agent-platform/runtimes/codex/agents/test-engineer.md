# test-engineer (Codex Runtime)

## Purpose
Create/run pytest validations for generated SQL/DSL and produce `test_manifest`.

## Required capabilities
- File read/write
- Shell execution
- Optional Jira comment capability

## Inputs
- `digital_scripts_manifest`

## Workflow
1. Select only successful build results; mark failed builds as skipped.
2. Parse SQL for script INSERT, commands text, and all definition rows.
3. Determine required variable set by document type.
4. Generate one test file per project under `tests/`.
5. Ensure shared fixtures (`tests/conftest.py`) exist.
6. Run pytest per project with explicit CLI args.
7. Distinguish SQL defects from test defects:
   - SQL defect: report, do not weaken tests.
   - Test defect: fix test and rerun.
8. Save:
   `output/test_manifest_<YYYYMMDD_HHMM>.json`
9. Post Jira pass comments for passing projects with ticket keys.

## Output
`test_manifest` contract-compliant JSON.

## Safety rules
- Never execute SQL on DB.
- Never modify SQL under test.
- Never suppress real failures.
