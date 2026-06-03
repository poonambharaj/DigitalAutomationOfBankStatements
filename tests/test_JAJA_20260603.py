"""
Unit tests for JAJA_20260603.sql — JAJA Finance CreditCard digital extraction script.

Manifest context:
  project_name          : YE 2026 (JAJA)
  document_type         : credit_note (credit card bank statement)
  verification_rule_set : 4 (bank_statement / credit card)
  ids_are_placeholders  : True  (script_id = 9999)

Test categories
  A. SQL structure        (6 tests)
  B. Required variables   (8 tests — bank_statement variable set)
  C. DSL quality          (7 tests)
  D. Document identification (7 tests)

Total: 28 tests

Encoding note:
  The SQL file encodes DSL string delimiters as \\\" (backslash-dquote) and line
  breaks as \\n.  The commands_text fixture only unescapes \\n -> newline and
  \\' -> apostrophe; backslash-dquote sequences remain intact.  Regex patterns
  that match DSL string values must therefore use \\\\ \" delimiters, not plain
  double-quote characters.  Similarly, ContainsText JSON arrays stored in the
  definition INSERT use \\\" escaping and must be unescaped before json.loads.
"""

import json
import re
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Project-level constants
# ---------------------------------------------------------------------------

SQL_PATH = Path("C:/dev/AutomationOfDigitalScripts/output/digital_scripts/JAJA_20260603.sql")
EXPECTED_SCRIPT_NAME = "JajaFinance_CreditCard"
EXPECTED_SCRIPT_ID   = 9999   # placeholder — real Id assigned at deploy time
EXPECTED_VRS_ID      = 4      # 4 = bank_statement / credit card
IDS_ARE_PLACEHOLDERS = True

# bank_statement required variables (credit card uses the same set)
REQUIRED_VARIABLES = [
    "$source",
    "$accountName",
    "$accountNumber",
    "$periodFrom",
    "$periodTo",
    "$openingBalance",
    "$closingBalance",
    "$transactions",
]

VALID_FEATURES_FLAGS = {
    "NO_TRANSACTION_YEAR",
    "NO_OPENING_BALANCE",
    "SKIP_MISSING_CLOSING_BALANCE_CHECK",
    "REVERSE_ORDER",
    "OPENING_BALANCE_FROM_FIRST_ROW",
    "CREDIT_CARD",
}


# ---------------------------------------------------------------------------
# Parsing helpers
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
    assert SQL_PATH.exists(), f"SQL file not found: {SQL_PATH}"
    return SQL_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def commands_text(sql_content: str) -> str:
    """Extract and unescape the DSL Commands field from the script INSERT.

    The SQL encodes newlines as the two-character sequence backslash-n and
    single quotes as backslash-apostrophe.  This fixture reverses both so that
    DSL keyword checks work against the actual DSL syntax.

    Note: backslash-dquote sequences (\\") remain in the returned string because
    the DSL itself uses them as string delimiters — they are not a SQL escape
    artefact that needs removing.
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
# Category A — SQL structure  (6 tests)
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


def test_no_markdown_fences(sql_content):
    """A4: SQL file contains no markdown code fences."""
    assert "```" not in sql_content, (
        "Markdown code fence (```) found in the SQL file. "
        "The output must be pure SQL — no markdown formatting."
    )


def test_script_id_is_placeholder(sql_content):
    """A5: Script Id = 9999 (placeholder) because ids_are_placeholders = True."""
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
    """A6: ScriptId in definition row matches Id in script row."""
    script_match = re.search(
        r"INSERT INTO `digitalpdf\$script`[^)]*\)\s*VALUES\s*\(\s*(\d+)",
        sql_content,
        re.DOTALL | re.IGNORECASE,
    )
    # ScriptId is the second-to-last integer before UTC_TIMESTAMP in the definition row:
    # ...ExcludesText, ScriptId, VerificationRuleSetId, UTC_TIMESTAMP(), IsDeleted
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
# Category B — Required variable extraction  (8 tests)
# ===========================================================================

@pytest.mark.parametrize("variable", REQUIRED_VARIABLES)
def test_required_variable_present(variable, commands_text):
    """B: Each required bank_statement variable appears in the DSL Commands."""
    assert variable in commands_text, (
        f"Required variable {variable!r} not found in DSL Commands. "
        "All required variables for a bank_statement / credit card must be extracted. "
        "Check the variable list: $source, $accountName, $accountNumber, "
        "$periodFrom, $periodTo, $openingBalance, $closingBalance, $transactions."
    )


# ===========================================================================
# Category C — DSL quality  (7 tests)
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
    """C3: Commands line breaks are encoded as backslash-n escape sequences."""
    assert r"\n" in raw_commands_field, (
        "Raw Commands field does not contain \\n escape sequences. "
        "DSL line breaks must be encoded as \\n in the SQL string."
    )


def test_footer_exclusion_present(commands_text):
    """C4: 'ignore footer below' is present to prevent page footer contamination."""
    assert "ignore footer below" in commands_text, (
        "No 'ignore footer below' command found in the DSL. "
        "Page footer lines will be appended to the transaction table without this guard."
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
    commands_text fixture unescapes \\n and \\', the backslash-dquote sequences
    remain intact, so the regex must match \\\" rather than plain \".
    """
    if "$features" not in commands_text:
        pytest.skip("$features not used in this script — nothing to validate.")
    # Match $features = \"FLAG1 FLAG2\" (backslash-dquote delimiters)
    match = re.search(r'\$features\s*=\s*\\"([^\\"]*)\\"', commands_text)
    assert match, (
        "$features assignment found but could not parse the flag string. "
        r'Expected format (in DSL): $features = \"FLAG1 FLAG2\"'
    )
    used_flags = set(match.group(1).split())
    unknown = used_flags - VALID_FEATURES_FLAGS
    assert not unknown, (
        f"Unknown $features flag(s) detected: {unknown}. "
        f"Valid flags are: {VALID_FEATURES_FLAGS}"
    )


def test_describe_table_follows_transactions(commands_text):
    """C7: $transactions table extraction is followed by => describe table."""
    lines = commands_text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("$transactions") and "get" in line and "table" in line:
            context = " ".join(lines[i:i+3])
            assert "=> describe table" in context, (
                f"DSL line {i+1}: $transactions table extraction is not followed by "
                f"'=> describe table' within the next 2 lines:\n  {line.strip()}"
            )


# ===========================================================================
# Category D — Document identification quality  (6 tests)
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
        "Could not find IsDeleted field (after UTC_TIMESTAMP()) in definition INSERT."
    )
    for val in matches:
        assert val == "0", (
            f"IsDeleted in definition INSERT is {val!r}, expected '0'."
        )


def test_utc_timestamp_used_in_definition(sql_content):
    """D3: UTC_TIMESTAMP() appears in the definition INSERT for ModificationTimeUtc."""
    assert "UTC_TIMESTAMP()" in sql_content, (
        "UTC_TIMESTAMP() not found in SQL. "
        "The digitalpdf$documentidentification INSERT must use UTC_TIMESTAMP() "
        "for ModificationTimeUtc."
    )


def test_verification_rule_set_id_correct(def_fields):
    """D4: VerificationRuleSetId = 4 in the identification INSERT."""
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


def test_contains_text_present_and_non_empty(doc_id_insert):
    r"""D5: ContainsText is a non-empty JSON array with at least one anchor phrase.

    The ContainsText value is stored in the SQL with embedded double-quotes
    escaped as \\\" (backslash-dquote).  This test unescapes those before
    calling json.loads so that the JSON parser sees valid syntax.
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
    # Unescape \" -> " before parsing (SQL storage escaping artefact)
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


def test_creator_pattern_set_or_producer_pattern_set(def_fields):
    """D6: At least one of CreatorPattern (idx 4) or ProducerPattern (idx 5) is non-NULL."""
    assert len(def_fields) >= 6, (
        "Definition INSERT has fewer than 6 fields; cannot validate Creator/ProducerPattern."
    )
    creator  = def_fields[4].strip("'\" ").upper()
    producer = def_fields[5].strip("'\" ").upper()
    both_null = (creator == "NULL" and producer == "NULL")
    assert not both_null, (
        "Both CreatorPattern and ProducerPattern are NULL. "
        "At least one must be set to fingerprint the PDF source application."
    )



def test_script_insert_uses_utc_timestamp_not_literal(sql_content):
    """D7: ModificationTimeUtc in digitalpdf$script must be UTC_TIMESTAMP(), not a hardcoded date."""
    # Match the full script INSERT up to its known tail: UTC_TIMESTAMP(),<IsDeleted>);
    # re.DOTALL is required because the Commands value spans multiple lines.
    script_insert_match = re.search(
        r"INSERT INTO `digitalpdf\$script`.*?UTC_TIMESTAMP\(\),\d+\);",
        sql_content,
        re.DOTALL | re.IGNORECASE,
    )
    assert script_insert_match, "digitalpdf$script INSERT not found"
    script_insert = script_insert_match.group(0)
    # The ModificationTimeUtc field must use UTC_TIMESTAMP(), not a quoted date literal
    assert "UTC_TIMESTAMP()" in script_insert, (
        "digitalpdf$script ModificationTimeUtc must be UTC_TIMESTAMP(), "
        f"not a hardcoded literal. Found: {script_insert[-200:]}"
    )
    # Ensure no hardcoded date literal like '2026-01-01 00:00:00' is present
    assert not re.search(r"'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'", script_insert), (
        "digitalpdf$script ModificationTimeUtc contains a hardcoded date literal -- must use UTC_TIMESTAMP()"
    )
