# statement-harvester (GitHub Copilot Runtime)

## Purpose
Start the pipeline by extracting unprocessed projects from StatementRec, identifying unsupported banks, downloading representative PDFs, and returning a structured manifest.

## Required capabilities
- Playwright MCP browser automation
- File read/write
- File glob/listing

## Inputs
- StatementRec reports page URL
- Local file: `References/DigitalScriptSample/DigitalScripts.sql`
- Report date (optional; defaults to today's date when not specified)

## Workflow
1. Navigate to `https://app-web.statementrec.com/app/index#allreports`.
2. Wait for SPA render and verify auth by checking visibility of **Digital (Not Auto-Processed)**.
3. If unauthenticated, stop and request user login/MFA.
4. Open **Digital (Not Auto-Processed)** tab and apply the report date filter (defaults to today when not specified).
5. Extract all rows across pagination: `name`, `bank`, `pages`.
6. Download Excel report and save under `output/digital_not_auto_processed_<YYYYMMDD>.xlsx`.
7. Read `References/DigitalScriptSample/DigitalScripts.sql` and derive supported script names.
8. Identify unsupported banks using significant-word matching (avoid generic-word false positives).
9. For each unsupported bank, open project page, download statement PDF, and store in:
   `References/NewBanksIdentified/<BANK_NAME>/<ProjectName>.pdf`
10. Save and return manifest:
   `output/new_banks_manifest_<YYYYMMDD_HHMM>.json`

## Output
`new_banks_manifest` (canonical contract)

## Safety rules
- Never perform destructive actions.
- Never enter/store credentials.
- Require explicit user-auth checkpoint when login is needed.
