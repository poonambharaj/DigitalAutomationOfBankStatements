# statement-harvester (Codex Runtime)

## Purpose
Extract unprocessed StatementRec projects, detect unsupported banks, download representative PDFs, and return `new_banks_manifest`.

## Required capabilities
- Browser automation (Playwright-compatible MCP or equivalent)
- File read/write
- Directory/file listing

## Inputs
- StatementRec reports URL
- `References/DigitalScriptSample/DigitalScripts.sql`

## Workflow
1. Navigate to reports page and wait for SPA render.
2. Verify authenticated state via presence of **Digital (Not Auto-Processed)** tab.
3. If unauthenticated: stop and request user login/MFA in browser.
4. Open tab and collect all rows across pagination (`name`, `bank`, `pages`).
5. Download Excel report to `output/digital_not_auto_processed_<YYYYMMDD>.xlsx`.
6. Parse `References/DigitalScriptSample/DigitalScripts.sql` to derive supported scripts.
7. Identify unsupported banks with significant-word matching.
8. Download one representative statement PDF per unsupported bank to:
   `References/NewBanksIdentified/<BANK_NAME>/<ProjectName>.pdf`
9. Save and return:
   `output/new_banks_manifest_<YYYYMMDD_HHMM>.json`

## Output
`new_banks_manifest` contract-compliant JSON.

## Safety rules
- No destructive clicks/actions.
- No credential handling/storage.
- Pause for human authentication when required.

https://app-web.statementrec.com/app/index#allreports
