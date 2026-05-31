# Plan: Creating Digital PDF Extraction Scripts

Scripts and document definitions are stored in MySQL. Sample data lives in `DigitalScriptSample/`.

## Database Tables

| Table | Purpose |
|---|---|
| `digitalpdf$script` | DSL script text (`Id`, `Name`, `Commands`) |
| `digitalpdf$documentidentification` | PDF fingerprint → ScriptId mapping |

Multiple document definitions can share one script (e.g. same layout printed from different browsers).

---

## Step 1 — Fingerprint the PDF (Document Definition)

Inspect the PDF metadata and identify unique anchor phrases to build the identification record. All non-null fields are matched as regex patterns.

| Field | What to set |
|---|---|
| `CreatorPattern` | Regex matching the "Creator" metadata field (the app that made the PDF) |
| `ProducerPattern` | Regex matching the "Producer" field (PDF library) |
| `AuthorPattern` | Regex matching the "Author" field |
| `TitlePattern` | Regex matching the "Title" field |
| `Version` | PDF version integer, or NULL for any |
| `PageCount` | Fixed page count, or NULL for any |
| `ContainsText` | `[phrase1,phrase2]` — all must be present; quote multi-word phrases: `["multi word"]` |
| `ExcludesText` | `[phrase1]` — if any match, identification fails (used to disambiguate layouts) |

Use `^$` to require a metadata field to be literally empty. Use NULL to skip the check entirely.

`VerificationRuleSetId` values:
- `2` — basic invoice
- `3` — invoice with VAT / multi-page
- `4` — bank statement

---

## Step 2 — Standard Output Variables by Document Type

### Invoice / Credit Note
```
$invoiceType    "PurchaseInvoice" | "PurchaseCredit"
$name           supplier name
$currency       "GBP" etc.
$vatNumber      VAT registration number
$invoiceNumber  invoice or credit note number
$invoiceDate    document date
$net            net amount
$tax            VAT / tax amount
$total          total amount
$lineItems      line items table
$description    (optional) overall description
$discount       (optional) discount amount
$carriage       (optional) shipping / carriage amount
```

### Bank Statement
```
$source             bank identifier string
$features           space-separated feature flags (see below)
$periodBufferDays   tolerance in days for period date matching (optional)
$accountName        account holder name
$accountNumber      account number
$periodFrom         statement start date
$periodTo           statement end date
$openingBalance     opening balance
$closingBalance     closing balance
$transactions       transactions table
```

**`$features` flags:**

| Flag | Meaning |
|---|---|
| `NO_TRANSACTION_YEAR` | Transaction dates have no year component |
| `NO_OPENING_BALANCE` | Statement does not show an opening balance |
| `SKIP_MISSING_CLOSING_BALANCE_CHECK` | Closing balance may be absent |
| `REVERSE_ORDER` | Transactions are listed newest-first |
| `OPENING_BALANCE_FROM_FIRST_ROW` | First transaction row contains the opening balance |
| `CREDIT_CARD` | Credit card statement (inverts debit/credit sign logic) |

---

## Step 3 — DSL Command Reference

### Constants and settings
```
$invoiceType = "PurchaseInvoice"
$source = "Bank Name"
$features = "NO_TRANSACTION_YEAR"
set negative marker "Dr"       // words ending in "Dr" are treated as negative numbers
set culture "fr-CA"            // use for non-English date parsing
```

### Navigation
```
go to page 1
go to last page
```

### Finding lines
```
get line starting "text"
get line containing "text"
get line "exact full text"
get last line containing "text"
get line below
get line above
get line above 0              // last line on page
=> if not found then blank    // suppress error when line may not exist
```

### Position modifiers (return a Y or X coordinate)
```
=> top      // Y of the top edge of the matched words
=> bottom   // Y of the bottom edge
=> left     // X of the left edge
=> right    // X of the right edge
```

### Coordinate arithmetic
```
add @variable N        // shift coordinate down/right by N points
subtract @variable N   // shift coordinate up/left by N points
```

### Word manipulation (chained after a line find)
```
=> skip words N                  // discard first N words
=> take words N                  // keep only first N words
=> take last words N             // keep only last N words
=> get words after "keyword"     // words to the right of keyword
=> get words before "keyword"    // words to the left of keyword
```

### Value extraction (terminal — ends a chain)
```
=> get text          // raw text string
=> get decimal       // parse as decimal number
=> get date "fmt"    // parse as date (C# format string, e.g. "dd/MM/yyyy")
```

### Coordinate-box extraction
```
get text in box <top> <bottom> <left> <right>
delete text in box <top> <bottom> <left> <right>
delete text in box on every page <top> <bottom> <left> <right>
```

Coordinates are in PDF points from the top-left of the page. Use context variables
`page.top`, `page.bottom`, `page.left`, `page.right`, `page.middleX` in place of literals.

### Deleting unwanted content
```
delete white words
delete tiny words
delete rotated words
delete all lines starting "text"
delete all lines containing "text"
delete all lines ending "text"
delete all pages containing "text"
ignore header above <Y>           // exclude repeating page header
ignore footer below <Y>           // exclude repeating page footer
```

### Table extraction
```
// Explicit column boundaries
$lineItems = get table @top @bottom <col1> <col2> ... <colN>
  => describe table true  - #Units Code Details - #Price *#Net

// Auto-detect columns
$lineItems = get auto table @top @bottom page.left page.right
  => describe table true *Code Details #Units #Price #Net #VatRate

// Multi-page explicit columns
$transactions = get multi page table @top @bottom <col1> ... <colN>
  => describe table false "Date[dd MMM yy]" Details **#Debit **#Credit #Balance

// Multi-page with center-alignment tolerance (for right-aligned numeric columns)
$transactions = get multi page table center aligned @top @bottom <tolerance> <col1> ... <colN>
  => describe table false "Date[d MMM yyyy]" TransactionType Details #Credit #Debit #Balance
```

**`describe table` column descriptors:**

| Syntax | Meaning |
|---|---|
| `ColumnName` | Plain text |
| `#ColumnName` | Numeric (decimal) |
| `*ColumnName` | Primary identifier |
| `**#ColumnName` | Optional numeric (blank is valid) |
| `-` | Skip / ignore this column |
| `"Date[format]"` | Parse as date |
| `*Date[format]` | Primary date column |

### Combining multiple tables (bank statements with separate sections)
```
@credits = get multi page table @creditsTop @creditsBottom 0 87 500 600
  => describe table false "Date[MM/dd/yy]" Details *#Credit
@debits = get multi page table @debitsTop @debitsBottom 0 87 500 600
  => describe table false "Date[MM/dd/yy]" Details *#Credit

$transactions = combine described tables @credits @debits
```

---

## Step 4 — Multi-Page Cleanup Patterns

**Repeating page headers/footers:**
```
get last line starting "Date Description" => bottom => ignore header above
get line above 0 => top => ignore footer below
```

**Carry-forward / continued rows between pages:**
```
delete all lines starting "BROUGHT FORWARD"
delete all lines starting "CONTINUED"
```

**Table split across pages (clear end of page N, clear start of page N+1):**
```
go to page 1
@cfTop = get line starting "C/F" => top
delete text in box @cfTop page.bottom 0 page.right

go to page 2
@tableStart = get line containing "DESCRIPTION" => bottom
delete text in box page.top @tableStart 0 page.right

go to page 1
```

---

## Step 5 — SQL Insert Template

```sql
-- Insert script
INSERT INTO `digitalpdf$script` (`Id`, `Name`, `Commands`, `ModificationTimeUtc`, `IsDeleted`)
VALUES (
  <next_id>,
  '<ScriptName>',
  '<DSL commands with \n line breaks and \' escaped quotes>',
  UTC_TIMESTAMP(),
  0
);

-- Insert document definition (repeat for each PDF variant / producer combination)
INSERT INTO `digitalpdf$documentidentification`
  (`Id`, `Name`, `TitlePattern`, `AuthorPattern`, `CreatorPattern`, `ProducerPattern`,
   `Version`, `PageCount`, `SignatureInfo`, `ContainsText`, `ExcludesText`,
   `ScriptId`, `VerificationRuleSetId`, `ModificationTimeUtc`, `IsDeleted`)
VALUES (
  <next_id>,
  '<HumanReadableName>',
  NULL,
  '<author regex or NULL>',
  '<creator regex or ^$>',
  '<producer regex>',
  <pdf_version_int or NULL>,
  <page_count or NULL>,
  NULL,
  '[RequiredText1,"Multi Word Phrase"]',
  NULL,                          -- or '[ExcludedText]'
  <ScriptId>,
  4,                             -- 2=basic invoice, 3=invoice+VAT, 4=bank statement
  UTC_TIMESTAMP(),
  0
);
```

---

## Workflow Summary

```
New PDF arrives
  │
  ├─ Inspect PDF metadata (Creator, Producer, Author, Title, Version)
  ├─ Identify unique anchor phrases in the content
  │
  ├─ Does an existing script cover this layout?
  │     YES → Add a new document definition row pointing to the existing ScriptId
  │     NO  → Write new script → insert script row → insert definition row
  │
  └─ Test: run Interpreter against the PDF, verify all $variables extract correctly
```

---

## Step 6 — Agent-Assisted Script Generation

`generate_script.py` automates Steps 1–5 above. It sends the PDF to Claude along with
Plan.md and representative samples from the existing SQL files as cached context, then
streams back ready-to-run MySQL INSERT statements.

### Setup

```bash
# 1. Install dependencies (one-time per machine)
pip install -r requirements.txt

# 2. Create your personal .env file from the template
copy .env.example .env          # Windows
# cp .env.example .env          # Linux / macOS

# 3. Edit .env and set your Anthropic API key
#    ANTHROPIC_API_KEY=sk-ant-...
#    (.env is gitignored — never commit it)
```

### Usage

```bash
# Basic — uses placeholder Id 9999 for both tables
python generate_script.py path/to/statement.pdf

# Supply real next Ids (query MAX(Id)+1 from each table first)
python generate_script.py path/to/statement.pdf --next-script-id 150 --next-def-id 320
```

Output is streamed to stdout so you can pipe it straight into MySQL:

```bash
python generate_script.py statement.pdf --next-script-id 150 --next-def-id 320 | mysql -u root -p mydb
```

### How it works

| Phase | Detail |
|---|---|
| **Cached context** | Plan.md + first ~80 KB of each sample SQL file are sent as `cache_control: ephemeral` system blocks, so repeated calls against different PDFs reuse the same cache entry. |
| **PDF input** | The PDF is base64-encoded and sent as a `document` content block alongside the extraction prompt. |
| **Model** | `claude-opus-4-7` with adaptive thinking — reasons about layout before writing the DSL. |
| **Output** | Raw MySQL `INSERT` statements only; pipe to MySQL or paste into a migration script. |

### Tips

- Always verify the generated script by running the Interpreter against the original PDF before committing the SQL.
- If the PDF contains unusual encodings (rotated text, white-on-white text, tiny footnote text), review the generated `delete` commands and adjust coordinates as needed.
- For PDFs that differ only by Creator/Producer (same bank, different browser), re-run with the same `--next-script-id` but increment `--next-def-id` to generate additional definition rows pointing to the shared script.
- Replace placeholder Id `9999` before inserting if you forget to pass `--next-script-id` / `--next-def-id`.
