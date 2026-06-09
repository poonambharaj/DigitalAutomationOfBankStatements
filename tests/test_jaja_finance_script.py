"""
Unit tests for JAJA_Finance_20260609.sql — JAJA Finance credit card digital extraction script.

Script under test : output/digital_scripts/JAJA_Finance_20260609.sql
Document type     : bank_statement (credit card)
VRS Id            : 4  (bank_statement / credit card)
IDs               : placeholder 9999 — real Ids assigned at deploy time

Test categories
  A. SQL structure           (7 tests)
  B. Required variables      (9 parametrized tests — $features included)
  C. DSL quality             (8 tests)
  D. Document identification (7 tests)
  E. JAJA-specific checks    (4 tests)

Total: 35 tests

Encoding note
  The SQL file stores DSL line-breaks as the two-character sequence backslash-n
  and double-quote delimiters inside the Commands string as backslash-dquote.
  The commands_text fixture unescapes only \\n -> newline and \\' -> apostrophe.
  Backslash-dquote sequences remain intact.  Regex patterns that match DSL
  string values must therefore use \\\\ \" delimiters, not plain double-quotes.
"""

import json
import re
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Project-level constants
# ---------------------------------------------------------------------------

SQL_PATH = Path("C:/dev/AutomationOfDigitalScripts/output/digital_scripts/JAJA_Finance_20260609.sql")
EXPECTED_SCRIPT_NAME  = "JajaFinance_CreditCard"
EXPECTED_SCRIPT_ID    = 9999   # placeholder — real Id assigned at deploy time
EXPECTED_VRS_ID       = 4      # 4 = bank_statement / credit card
IDS_ARE_PLACEHOLDERS  = True
DOCUMENT_TYPE         = "bank_statement"

# Required variables for bank_statement (credit card uses the same set) plus $features
REQUIRED_VARIABLES = [
    "$source",
    "$features",
    "$accountName",
    "$accountNumber",
    "$periodFrom",
    "$periodTo",
    "$openingBalance",
    "$closingBalance",
    "$transactions",
]

# The three credit-card feature flags mandated in the task brief
REQUIRED_FEATURES_FLAGS = {"CREDIT_CARD", "NO_OPENING_BALANCE", "SKIP_MISSING_CLOSING_BALANCE_CHECK"}

VALID_FEATURES_FLAGS = {
    "NO_TRANSACTION_YEAR",
    "NO_OPENING_BALANCE",
    "SKIP_MISSING_CLOSING_BALANCE_CHECK",
    "REVERSE_ORDER",
    "OPENING_BALANCE_FROM_FIRST_ROW",
    "CREDIT_CARD",
}

# Anchor phrases that must appear in ContainsText to fingerprint a JAJA statement
REQUIRED_CONTAINS_TEXT_PHRASES = [
    "Your credit card statement",
    "jaja.co.uk",
    "Outstanding statement balance",
]

# Transaction column names mandated by the task brief
REQUIRED_TRANSACTION_COLUMNS = ["*Date", "Details", "#Credit"]


# ---------------------------------------------------------------------------
# Parsing helper
# ---------------------------------------------------------------------------

def _parse_definition_fields(doc_id_insert: str) -> list:
    """Return the positional field list from the documentidentification VALUES clause.

    ContainsText and ExcludesText hold single-quoted JSON arrays that contain
    commas.  Those tokens are replaced with placeholders before splitting so that
    inner commas do not corrupt the field count.

    Column order (0-indexed):
      0  Id                    8  SignatureInfo
      1  Name                  9  ContainsText
      2  TitlePattern         10  ExcludesText
      3  AuthorPattern        11  ScriptId
      4  CreatorPattern       12  VerificationRuleSetId
      5  ProducerPattern      13  ModificationTimeUtc
      6  Version              14  IsDeleted
      7  PageCount
    """
    values_match = re.search(r"VALUES\s*\((.+)\)\s*;", doc_id_insert, re.DOTALL)
    if not values_match:
        return []
    raw = values_match.group(1)

    placeholders: dict = {}
    counter = [0]

    def _replace_json_array(m: re.Match) -> str:
        key = f"__JSON_ARRAY_{counter[0]}__"
        counter[0] += 1
        placeholders[key] = m.group(0)
        return key

    protected = re.sub(r"'(\[.*?\])'", _replace_json_array, raw, flags=re.DOTALL)
    fields = [f.strip() for f in protected.split(",")]

    restored = []
    for field in fields:
        for key, original in placeholders.items():
            field = field.replace(key, original)
        restored.append(field)

    return restored


# ---------------------------------------------------------------------------
# Module-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def sql_content() -> str:
    """Read and return the entire SQL file."""
    assert SQL_PATH.exists(), (
        f"SQL file not found at {SQL_PATH}. "
        "The digital-script-builder must have created this file before tests run."
    )
    return SQL_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def commands_text(sql_content: str) -> str:
    """Extract and unescape the DSL Commands field from the script INSERT.

    The SQL encodes newlines as the two-character sequence backslash-n and
    single quotes as backslash-apostrophe.  This fixture reverses both so that
    DSL keyword checks work against the actual DSL syntax.

    Backslash-dquote sequences (backslash + double-quote) are left intact because
    the DSL uses them as string delimiters — they are not a SQL escape artefact.
    """
    match = re.search(
        r"INSERT INTO `digitalpdf\$script`[^)]*\)\s*VALUES\s*\(\s*\d+\s*,\s*'[^']*'\s*,"
        r"\s*'((?:[^'\\]|\\.)*)'",
        sql_content,
        re.DOTALL | re.IGNORECASE,
    )
    assert match, (
        "Could not extract Commands field from digitalpdf$script INSERT. "
        "Verify the SQL file is well-formed and the column order is: "
        "Id, Name, Commands, ModificationTimeUtc, IsDeleted."
    )
    raw = match.group(1)
    return raw.replace(r"\n", "\n").replace(r"\'", "'")


@pytest.fixture(scope="module")
def raw_commands_field(sql_content: str) -> str:
    """Return the raw (escaped) Commands string exactly as it appears in the SQL."""
    match = re.search(
        r"INSERT INTO `digitalpdf\$script`[^)]*\)\s*VALUES\s*\(\s*\d+\s*,\s*'[^']*'\s*,"
        r"\s*'((?:[^'\\]|\\.)*)'",
        sql_content,
        re.DOTALL | re.IGNORECASE,
    )
    assert match, "Could not extract raw Commands value from SQL."
    return match.group(1)


@pytest.fixture(scope="module")
def doc_id_insert(sql_content: str) -> str:
    """Extract the full digitalpdf$documentidentification INSERT statement."""
    match = re.search(
        r"INSERT INTO `digitalpdf\$documentidentification`.*?;",
        sql_content,
        re.DOTALL,
    )
    assert match, "Could not find digitalpdf$documentidentification INSERT in SQL file."
    return match.group(0)


@pytest.fixture(scope="module")
def def_fields(doc_id_insert: str) -> list:
    """Return the parsed positional field list from the definition INSERT VALUES."""
    fields = _parse_definition_fields(doc_id_insert)
    assert fields, "Could not parse fields from digitalpdf$documentidentification VALUES."
    return fields


@pytest.fixture(scope="module")
def script_insert_tail(sql_content: str) -> dict:
    """Extract ModificationTimeUtc and IsDeleted from the script INSERT tail."""
    match = re.search(
        r"INSERT INTO `digitalpdf\$script`[^)]*\)\s*VALUES\s*\(\s*\d+\s*,\s*'[^']*'\s*,"
        r"\s*'(?:[^'\\]|\\.)*'\s*,\s*(UTC_TIMESTAMP\(\))\s*,\s*(\d+)\s*\)\s*;",
        sql_content,
        re.DOTALL | re.IGNORECASE,
    )
    assert match, (
        "Could not parse the tail fields (ModificationTimeUtc, IsDeleted) from "
        "digitalpdf$script INSERT.  Verify column order: "
        "Id, Name, Commands, ModificationTimeUtc, IsDeleted."
    )
    return {
        "modification_time_utc": match.group(1),
        "is_deleted": match.group(2),
    }


# ===========================================================================
# Category A — SQL structure  (7 tests)
# ===========================================================================

def test_sql_file_exists():
    """A1: SQL file is present on disk."""
    assert SQL_PATH.exists(), (
        f"SQL file not found at {SQL_PATH}. "
        "The digital-script-builder must have created this file before tests run."
    )


def test_script_insert_present(sql_content):
    """A2: File contains an INSERT for digitalpdf$script."""
    assert "INSERT INTO `digitalpdf$script`" in sql_content, (
        "INSERT INTO `digitalpdf$script` not found. "
        "This INSERT carries the DSL Commands and is mandatory."
    )


def test_definition_insert_present(sql_content):
    """A3: File contains an INSERT for digitalpdf$documentidentification."""
    assert "INSERT INTO `digitalpdf$documentidentification`" in sql_content, (
        "INSERT INTO `digitalpdf$documentidentification` not found. "
        "This INSERT carries PDF fingerprinting patterns and is mandatory."
    )


def test_exactly_two_inserts(sql_content):
    """A4: File contains exactly two INSERT statements — one per table."""
    count = len(re.findall(r"INSERT INTO", sql_content, re.IGNORECASE))
    assert count == 2, (
        f"Expected exactly 2 INSERT statements, found {count}. "
        "File must contain one INSERT for digitalpdf$script and one for "
        "digitalpdf$documentidentification — no more, no less."
    )


def test_no_markdown_fences(sql_content):
    """A5: SQL file contains no markdown code fences."""
    assert "```" not in sql_content, (
        "Markdown code fence (```) found in the SQL file. "
        "The output must be pure SQL — no markdown formatting."
    )


def test_script_id_is_placeholder(sql_content):
    """A6: Script Id = 9999 (placeholder) because IDS_ARE_PLACEHOLDERS = True."""
    match = re.search(
        r"INSERT INTO `digitalpdf\$script`[^)]*\)\s*VALUES\s*\(\s*(\d+)",
        sql_content,
        re.DOTALL | re.IGNORECASE,
    )
    assert match, "Could not extract Id from digitalpdf$script INSERT."
    script_id = int(match.group(1))
    assert script_id == EXPECTED_SCRIPT_ID, (
        f"Script Id is {script_id}, expected placeholder {EXPECTED_SCRIPT_ID}. "
        "Placeholder Id 9999 is expected at this stage; real Ids are assigned at deploy time."
    )


def test_script_id_matches_definition_script_id(sql_content):
    """A7: ScriptId in the definition row matches Id in the script row."""
    script_match = re.search(
        r"INSERT INTO `digitalpdf\$script`[^)]*\)\s*VALUES\s*\(\s*(\d+)",
        sql_content,
        re.DOTALL | re.IGNORECASE,
    )
    def_script_ids = re.findall(
        r"INSERT INTO `digitalpdf\$documentidentification`.*?VALUES.*?,"
        r"\s*(\d+)\s*,\s*\d+\s*,\s*UTC_TIMESTAMP",
        sql_content,
        re.DOTALL,
    )
    if script_match and def_script_ids:
        expected = script_match.group(1)
        for dsid in def_script_ids:
            assert dsid == expected, (
                f"Definition row ScriptId={dsid} does not match script Id={expected}. "
                "Both rows must reference the same Id to link correctly."
            )


# ===========================================================================
# Category B — Required variable extraction  (9 parametrized tests)
# ===========================================================================

@pytest.mark.parametrize("variable", REQUIRED_VARIABLES)
def test_required_variable_present(variable, commands_text):
    """B: Each required bank_statement / credit card variable appears in the DSL Commands."""
    assert variable in commands_text, (
        f"Required variable {variable!r} not found in DSL Commands. "
        "All required variables for a bank_statement / credit card must be extracted. "
        "Required set: $source, $features, $accountName, $accountNumber, "
        "$periodFrom, $periodTo, $openingBalance, $closingBalance, $transactions."
    )


# ===========================================================================
# Category C — DSL quality  (8 tests)
# ===========================================================================

def test_commands_not_empty(commands_text):
    """C1: Commands field is non-empty."""
    assert commands_text.strip(), (
        "Commands field is empty — no DSL was generated."
    )


def test_commands_minimum_lines(commands_text):
    """C2: Commands field has at least 10 meaningful DSL lines."""
    lines = [ln for ln in commands_text.splitlines() if ln.strip()]
    assert len(lines) >= 10, (
        f"Commands field has only {len(lines)} non-blank line(s). "
        "A complete credit card extraction script must have at least 10 lines."
    )


def test_line_breaks_encoded_as_backslash_n(raw_commands_field):
    """C3: Commands line breaks are encoded as backslash-n escape sequences in the raw SQL."""
    assert r"\n" in raw_commands_field, (
        "Raw Commands field does not contain \\n escape sequences. "
        "DSL line breaks must be encoded as \\n in the SQL string."
    )


def test_footer_exclusion_present(commands_text):
    """C4: 'ignore footer below' is present to prevent page footer contamination."""
    assert "ignore footer below" in commands_text, (
        "No 'ignore footer below' command found in the DSL. "
        "Page footer lines will corrupt the transaction table without this guard."
    )


def test_carry_forward_rows_deleted(commands_text):
    """C5: At least one 'delete all lines' command exists to strip carry-forward rows."""
    has_delete = (
        "delete all lines starting" in commands_text
        or "delete all lines containing" in commands_text
    )
    assert has_delete, (
        "No 'delete all lines' command found. "
        "Carry-forward / continued rows between pages are not being cleaned up. "
        'Add: delete all lines starting "Continued on the next page" (or equivalent).'
    )


def test_features_flags_are_valid(commands_text):
    r"""C6: All tokens in $features are drawn from the known valid flag set.

    The DSL uses backslash-dquote (\\") as string delimiters.  After the
    commands_text fixture unescapes \\n and \\', backslash-dquote sequences
    remain intact, so the regex must match \\" rather than plain ".
    """
    if "$features" not in commands_text:
        pytest.skip("$features not used in this script — nothing to validate.")
    match = re.search(r'\$features\s*=\s*\\"([^\\"]*)\\"', commands_text)
    assert match, (
        "$features assignment found but could not parse the flag string. "
        r'Expected format (in DSL): $features = \"FLAG1 FLAG2\"'
    )
    used_flags = set(match.group(1).split())
    unknown = used_flags - VALID_FEATURES_FLAGS
    assert not unknown, (
        f"Unknown $features flag(s) detected: {unknown}. "
        f"Valid flags are: {sorted(VALID_FEATURES_FLAGS)}"
    )


def test_describe_table_follows_transactions(commands_text):
    """C7: $transactions table extraction is followed by => describe table."""
    lines = commands_text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("$transactions") and "get" in line and "table" in line:
            context = " ".join(lines[i:i + 3])
            assert "=> describe table" in context, (
                f"DSL line {i + 1}: $transactions table extraction is not followed by "
                f"'=> describe table' within the next 2 lines:\n  {line.strip()}"
            )


def test_utc_timestamp_not_hardcoded_literal(sql_content):
    """C8: ModificationTimeUtc in the script INSERT uses UTC_TIMESTAMP(), not a hardcoded date."""
    script_insert_match = re.search(
        r"INSERT INTO `digitalpdf\$script`.*?UTC_TIMESTAMP\(\),\d+\);",
        sql_content,
        re.DOTALL | re.IGNORECASE,
    )
    assert script_insert_match, "digitalpdf$script INSERT not found."
    script_insert = script_insert_match.group(0)
    assert "UTC_TIMESTAMP()" in script_insert, (
        "digitalpdf$script ModificationTimeUtc must be UTC_TIMESTAMP(), "
        "not a hardcoded datetime literal."
    )
    assert not re.search(r"'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'", script_insert), (
        "digitalpdf$script ModificationTimeUtc contains a hardcoded date literal — "
        "must use UTC_TIMESTAMP()."
    )


# ===========================================================================
# Category D — Document identification quality  (7 tests)
# ===========================================================================

def test_is_deleted_zero_in_script(script_insert_tail):
    """D1: IsDeleted = 0 in the digitalpdf$script INSERT."""
    assert script_insert_tail["is_deleted"] == "0", (
        f"IsDeleted is {script_insert_tail['is_deleted']!r} in digitalpdf$script INSERT, "
        "expected '0'. A value of 1 marks the script as deleted on import."
    )


def test_is_deleted_zero_in_definition(sql_content):
    """D2: IsDeleted = 0 in the digitalpdf$documentidentification INSERT."""
    matches = re.findall(r"UTC_TIMESTAMP\(\)\s*,\s*(\d+)\s*\)", sql_content)
    assert matches, (
        "Could not find IsDeleted field (after UTC_TIMESTAMP()) in SQL."
    )
    for val in matches:
        assert val == "0", (
            f"IsDeleted in an INSERT is {val!r}, expected '0'. "
            "A value of 1 would mark the row as deleted on import."
        )


def test_utc_timestamp_in_definition(doc_id_insert):
    """D3: UTC_TIMESTAMP() appears in the definition INSERT for ModificationTimeUtc."""
    assert "UTC_TIMESTAMP()" in doc_id_insert, (
        "UTC_TIMESTAMP() not found in digitalpdf$documentidentification INSERT. "
        "ModificationTimeUtc must use UTC_TIMESTAMP(), not a hardcoded literal."
    )


def test_verification_rule_set_id_correct(def_fields):
    """D4: VerificationRuleSetId = 4 (bank_statement/credit card) in the identification INSERT."""
    assert len(def_fields) >= 13, (
        f"Definition INSERT has {len(def_fields)} field(s); need at least 13 "
        "to reach VerificationRuleSetId at index 12."
    )
    vrs = def_fields[12].strip("'\" ")
    assert vrs.isdigit(), (
        f"VerificationRuleSetId at position 12 is not an integer: {vrs!r}. "
        "Check the INSERT column order."
    )
    assert int(vrs) == EXPECTED_VRS_ID, (
        f"VerificationRuleSetId is {vrs}, expected {EXPECTED_VRS_ID}. "
        "Use 4 for bank_statement/credit card, 2 for basic invoice, 3 for invoice+VAT."
    )


def test_signature_info_is_null(def_fields):
    """D5: SignatureInfo (index 8) must be NULL."""
    assert len(def_fields) >= 9, (
        f"Fewer than 9 fields found in definition INSERT; cannot validate SignatureInfo. "
        f"Fields found: {len(def_fields)}"
    )
    sig_info = def_fields[8].strip("'\" ").upper()
    assert sig_info == "NULL", (
        f"SignatureInfo is {def_fields[8]!r} — expected NULL. "
        "SignatureInfo is reserved and must not be populated."
    )


def test_creator_or_producer_pattern_set(def_fields):
    """D6: At least one of CreatorPattern (idx 4) or ProducerPattern (idx 5) is non-NULL."""
    assert len(def_fields) >= 6, (
        "Definition INSERT has fewer than 6 fields; cannot validate Creator/ProducerPattern."
    )
    creator  = def_fields[4].strip("'\" ").upper()
    producer = def_fields[5].strip("'\" ").upper()
    assert not (creator == "NULL" and producer == "NULL"), (
        "Both CreatorPattern and ProducerPattern are NULL. "
        "At least one must be set to fingerprint the PDF source application."
    )


def test_contains_text_present_and_non_empty(doc_id_insert):
    r"""D7: ContainsText is a non-empty JSON array with at least one anchor phrase.

    The ContainsText value may use backslash-dquote (\\") escaping inside the
    single-quoted SQL string.  This test unescapes those before calling json.loads.
    """
    match = re.search(r"'(\[.*?\])'", doc_id_insert, re.DOTALL)
    assert match, (
        "ContainsText field not found or is NULL. "
        "A JSON array of document-identification anchor phrases is required."
    )
    raw_json = match.group(1)
    assert len(raw_json) > 4, (
        f"ContainsText value {raw_json!r} is too short to be a meaningful array."
    )
    json_str = raw_json.replace('\\"', '"')
    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"ContainsText is not valid JSON after unescaping: {json_str!r} — {exc}"
        )
    assert isinstance(parsed, list), "ContainsText must parse as a JSON array."
    assert len(parsed) >= 1, (
        "ContainsText array must contain at least one document-identification phrase."
    )


# ===========================================================================
# Category E — JAJA Finance-specific checks  (4 tests)
# ===========================================================================

def test_credit_card_features_flags_present(commands_text):
    r"""E1: $features includes CREDIT_CARD, NO_OPENING_BALANCE, and SKIP_MISSING_CLOSING_BALANCE_CHECK.

    These three flags are mandatory for a JAJA Finance credit card statement:
    - CREDIT_CARD: enables credit card processing mode
    - NO_OPENING_BALANCE: JAJA statements do not carry a formal opening balance field
    - SKIP_MISSING_CLOSING_BALANCE_CHECK: prevents a false-fail when the
      outstanding balance is not in the expected position

    The DSL encodes string delimiters as backslash-dquote, so the regex matches
    the escaped form (\\"...\\" ) that remains in commands_text after the
    fixture unescapes \\n and \\'.
    """
    assert "$features" in commands_text, (
        "$features variable not found in DSL Commands. "
        "JAJA Finance credit card scripts require $features to be set."
    )
    match = re.search(r'\$features\s*=\s*\\"([^\\"]*)\\"', commands_text)
    assert match, (
        "$features assignment found but flag string could not be parsed. "
        r'Expected DSL format: $features = \"FLAG1 FLAG2 FLAG3\"'
    )
    used_flags = set(match.group(1).split())
    missing = REQUIRED_FEATURES_FLAGS - used_flags
    assert not missing, (
        f"Required $features flag(s) missing: {missing}. "
        f"JAJA Finance credit card scripts must include all of: {REQUIRED_FEATURES_FLAGS}. "
        f"Current flags: {used_flags}"
    )


def test_transactions_uses_get_multi_page_table(commands_text):
    """E2: $transactions extraction uses 'get multi page table' for multi-page statements."""
    assert "$transactions" in commands_text, (
        "$transactions variable not found in DSL Commands."
    )
    assert "get multi page table" in commands_text, (
        "$transactions is present but 'get multi page table' command not found. "
        "JAJA Finance statements span multiple pages; use 'get multi page table' "
        "rather than 'get table' to capture all transactions."
    )


@pytest.mark.parametrize("column", REQUIRED_TRANSACTION_COLUMNS)
def test_transaction_table_maps_required_column(column, commands_text):
    """E3: $transactions describe table includes each of the required column mappings.

    Required columns per task brief: *Date, Details, #Credit.
    - *Date   : transaction date (asterisk prefix = anchor column)
    - Details : transaction description
    - #Credit : monetary amount (hash prefix = numeric column)
    """
    assert column in commands_text, (
        f"Required transaction column {column!r} not found in the DSL Commands. "
        f"The $transactions describe table must map at least: "
        f"{REQUIRED_TRANSACTION_COLUMNS}. "
        f"Check the 'describe table' argument list in the $transactions assignment."
    )


@pytest.mark.parametrize("phrase", REQUIRED_CONTAINS_TEXT_PHRASES)
def test_contains_text_includes_jaja_phrase(phrase, doc_id_insert):
    """E4: Each required JAJA-specific phrase appears in the ContainsText JSON array."""
    assert phrase in doc_id_insert, (
        f"Required JAJA identification phrase {phrase!r} not found in ContainsText. "
        f"All required phrases must be present to correctly fingerprint the document: "
        f"{REQUIRED_CONTAINS_TEXT_PHRASES}"
    )
