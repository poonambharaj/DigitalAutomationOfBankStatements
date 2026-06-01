"""
Unit tests for the Zempler Bank digital extraction SQL script.

Validates:
  A. SQL structure — correct INSERT statements present
  B. Required DSL variable extraction
  C. Document identification quality (ContainsText phrases, patterns)
  D. DSL conventions (source, features, periodBufferDays)
  E. ScriptId consistency and IsDeleted values
"""

import json
import re
import pytest
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────

SQL_PATH = Path(__file__).parent.parent / "output" / "digital_scripts" / "ZEMPLER_.sql"
IDS_ARE_PLACEHOLDERS = True   # Both IDs are 9999 (placeholder — real IDs assigned at deploy time)
EXPECTED_VRS_ID = 4           # bank_statement
DOCUMENT_TYPE = "bank_statement"

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

REQUIRED_CONTAINS_TEXT_PHRASES = [
    "Zempler Bank",
    "Opening Balance:",
    "Closing Balance:",
    "Card ending in",
    "Business Account",
]

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def sql_content():
    assert SQL_PATH.exists(), f"SQL file not found: {SQL_PATH}"
    return SQL_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def commands_text(sql_content):
    """Extract and normalise the DSL Commands field from the script INSERT.

    The SQL file may store Commands as a multi-line string with real newlines
    (when the INSERT spans multiple lines) or with \\n escape sequences.
    This fixture handles both forms and returns a string with real newlines.
    """
    match = re.search(
        r"INSERT INTO `digitalpdf\$script`[^)]*\)\s*VALUES\s*\(\s*\d+\s*,\s*'[^']*'\s*,\s*'((?:[^'\\]|\\.)*)'",
        sql_content,
        re.DOTALL | re.IGNORECASE,
    )
    assert match, (
        "Could not extract Commands field from digitalpdf$script INSERT. "
        "Verify the SQL file is well-formed and the column order is: "
        "Id, Name, Commands, ModificationTimeUtc, IsDeleted."
    )
    raw = match.group(1)
    # Unescape: convert \\n literals to real newlines, and \\' to single quote
    return raw.replace(r"\n", "\n").replace(r"\'", "'")


@pytest.fixture(scope="module")
def doc_id_insert(sql_content):
    """Extract the full digitalpdf$documentidentification INSERT statement."""
    match = re.search(
        r"INSERT INTO `digitalpdf\$documentidentification`.*?;",
        sql_content,
        re.DOTALL,
    )
    assert match, "Could not find digitalpdf$documentidentification INSERT"
    return match.group(0)


@pytest.fixture(scope="module")
def doc_id_values_list(doc_id_insert):
    """Return the raw VALUES content from the definition INSERT as a string."""
    match = re.search(r"VALUES\s*\((.+)\)\s*;", doc_id_insert, re.DOTALL)
    assert match, "Could not extract VALUES content from documentidentification INSERT"
    return match.group(1)


@pytest.fixture(scope="module")
def script_id(sql_content):
    """Extract the Id value from digitalpdf$script INSERT."""
    match = re.search(
        r"INSERT INTO `digitalpdf\$script`[^)]*\)\s*VALUES\s*\(\s*(\d+)",
        sql_content,
        re.DOTALL | re.IGNORECASE,
    )
    assert match, "Could not extract Id from digitalpdf$script INSERT"
    return match.group(1)


# ── Category A: SQL structure ─────────────────────────────────────────────────


def test_sql_file_exists():
    """SQL file must exist at the expected path."""
    assert SQL_PATH.exists(), (
        f"SQL file not found: {SQL_PATH}. "
        "Ensure digital-script-builder has written the file before running tests."
    )


def test_exactly_two_inserts(sql_content):
    """File must contain exactly two INSERT statements — one per table."""
    count = len(re.findall(r"INSERT INTO", sql_content, re.IGNORECASE))
    assert count == 2, (
        f"Expected exactly 2 INSERT statements, found {count}. "
        "File must contain one INSERT for digitalpdf$script and one for "
        "digitalpdf$documentidentification — no more, no less."
    )


def test_script_insert_present(sql_content):
    """digitalpdf$script INSERT must be present."""
    assert "INSERT INTO `digitalpdf$script`" in sql_content, (
        "INSERT INTO `digitalpdf$script` not found in SQL file. "
        "The script INSERT is mandatory."
    )


def test_definition_insert_present(sql_content):
    """digitalpdf$documentidentification INSERT must be present."""
    assert "INSERT INTO `digitalpdf$documentidentification`" in sql_content, (
        "INSERT INTO `digitalpdf$documentidentification` not found in SQL file. "
        "The document identification INSERT is mandatory."
    )


def test_no_markdown_fences(sql_content):
    """SQL file must contain no markdown code fences."""
    assert "```" not in sql_content, (
        "SQL file contains markdown code fences (```). "
        "The output must be pure SQL with no markdown formatting."
    )


def test_modification_time_utc_in_script_insert(sql_content):
    """Script INSERT must use UTC_TIMESTAMP() for ModificationTimeUtc."""
    match = re.search(r"INSERT INTO `digitalpdf\$script`.*?;", sql_content, re.DOTALL)
    assert match, "digitalpdf$script INSERT not found"
    assert "UTC_TIMESTAMP()" in match.group(0), (
        "ModificationTimeUtc in digitalpdf$script INSERT must use UTC_TIMESTAMP(), "
        "not a hardcoded datetime literal."
    )


def test_modification_time_utc_in_definition_insert(doc_id_insert):
    """Definition INSERT must use UTC_TIMESTAMP() for ModificationTimeUtc."""
    assert "UTC_TIMESTAMP()" in doc_id_insert, (
        "ModificationTimeUtc in digitalpdf$documentidentification INSERT must use "
        "UTC_TIMESTAMP(), not a hardcoded datetime literal."
    )


# ── Category B: Required variable extraction (parametrized) ──────────────────


@pytest.mark.parametrize("variable", REQUIRED_VARIABLES)
def test_required_variable_present(commands_text, variable):
    """Each required output variable must appear in the DSL Commands."""
    assert variable in commands_text, (
        f"Required variable {variable!r} not found in DSL Commands. "
        f"All required variables for bank_statement document type must be extracted. "
        f"Required: {REQUIRED_VARIABLES}"
    )


def test_commands_not_empty(commands_text):
    """Commands field must not be empty."""
    assert commands_text.strip(), (
        "Commands field is empty — no DSL was generated."
    )


def test_commands_minimum_lines(commands_text):
    """Commands must contain at least 5 non-blank DSL lines."""
    lines = [l for l in commands_text.splitlines() if l.strip()]
    assert len(lines) >= 5, (
        f"Commands field has only {len(lines)} non-blank DSL line(s). "
        "A complete extraction script typically has at least 5 lines."
    )


# ── Category C: Document identification quality ───────────────────────────────


@pytest.mark.parametrize("phrase", REQUIRED_CONTAINS_TEXT_PHRASES)
def test_contains_text_includes_phrase(doc_id_insert, phrase):
    """Each required key phrase must appear in the ContainsText JSON array."""
    assert phrase in doc_id_insert, (
        f"Required identification phrase {phrase!r} not found in ContainsText. "
        f"All five Zempler Bank key phrases must be present: "
        f"{REQUIRED_CONTAINS_TEXT_PHRASES}"
    )


def test_contains_text_is_valid_json(doc_id_insert):
    """ContainsText must be a valid JSON array with at least one element."""
    match = re.search(r"'(\[.*?\])'", doc_id_insert, re.DOTALL)
    assert match, (
        "ContainsText field not found or is NULL. "
        "A JSON array of identification phrases is required."
    )
    raw_json = match.group(1)
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as e:
        pytest.fail(
            f"ContainsText is not valid JSON: {raw_json!r} — {e}"
        )
    assert isinstance(parsed, list), (
        "ContainsText must parse as a JSON array, not a scalar or object."
    )
    assert len(parsed) >= 1, (
        "ContainsText array must contain at least one identification phrase."
    )


def test_creator_or_producer_pattern_set(doc_id_insert):
    """At least one of CreatorPattern or ProducerPattern must be non-NULL."""
    # Column order: Id,Name,TitlePattern,AuthorPattern,CreatorPattern,ProducerPattern,...
    # After VALUES( extract first 6 comma-separated values
    match = re.search(r"VALUES\s*\(([^)]+)\)", doc_id_insert, re.DOTALL)
    assert match, "No VALUES clause found in definition INSERT"
    values_str = match.group(1)
    # Split on top-level commas (none of these values contain nested commas)
    fields = [f.strip() for f in re.split(r",\s*", values_str)]
    # Indices: 0=Id,1=Name,2=TitlePattern,3=AuthorPattern,4=CreatorPattern,5=ProducerPattern
    assert len(fields) >= 6, (
        f"Fewer than 6 fields found in definition INSERT VALUES: {fields}"
    )
    creator = fields[4].upper()
    producer = fields[5].upper()
    assert not (creator == "NULL" and producer == "NULL"), (
        "Both CreatorPattern (field 5) and ProducerPattern (field 6) are NULL. "
        "At least one must be set to fingerprint the PDF source application."
    )


def test_verification_rule_set_id_correct(doc_id_insert):
    """VerificationRuleSetId must be 4 for bank_statement document type."""
    matches = re.findall(r",\s*(\d+)\s*,\s*UTC_TIMESTAMP", doc_id_insert)
    assert matches, (
        "Could not find VerificationRuleSetId field (the integer before UTC_TIMESTAMP) "
        "in documentidentification INSERT."
    )
    for vrs in matches:
        assert int(vrs) == EXPECTED_VRS_ID, (
            f"VerificationRuleSetId is {vrs}, expected {EXPECTED_VRS_ID} for bank_statement. "
            "Valid values: 2=basic invoice, 3=invoice+VAT, 4=bank statement."
        )


def test_signature_info_is_null(doc_id_insert):
    """SignatureInfo field (position 9) must be NULL."""
    match = re.search(r"VALUES\s*\(([^)]+)\)", doc_id_insert, re.DOTALL)
    assert match, "No VALUES clause found in definition INSERT"
    fields = [f.strip() for f in re.split(r",\s*", match.group(1))]
    # Index 8 = SignatureInfo (0-based: Id,Name,Title,Author,Creator,Producer,Version,PageCount,SignatureInfo,...)
    assert len(fields) >= 9, (
        f"Fewer than 9 fields found in definition INSERT; cannot validate SignatureInfo. Fields: {fields}"
    )
    sig_info = fields[8].upper()
    assert sig_info == "NULL", (
        f"SignatureInfo is {fields[8]!r} — expected NULL. "
        "SignatureInfo is reserved and must not be populated."
    )


# ── Category D: DSL conventions ───────────────────────────────────────────────


def test_source_variable_assigned(commands_text):
    """$source must be assigned a non-empty quoted string."""
    match = re.search(r'\$source\s*=\s*"([^"]*)"', commands_text)
    assert match, (
        '$source must be assigned using: $source = "BankName". '
        "Assignment not found in Commands."
    )
    value = match.group(1).strip()
    assert len(value) > 0, (
        '$source is assigned an empty string. It must identify the bank, e.g. "Zempler Bank".'
    )


def test_features_includes_reverse_order(commands_text):
    """$features must include the REVERSE_ORDER flag for Zempler Bank."""
    match = re.search(r'\$features\s*=\s*"([^"]*)"', commands_text)
    assert match, (
        "$features variable not found in Commands. "
        "Zempler Bank statements list transactions in reverse chronological order; "
        '$features = "REVERSE_ORDER" is required.'
    )
    flags = match.group(1).split()
    assert "REVERSE_ORDER" in flags, (
        f"REVERSE_ORDER not found in $features flags {flags!r}. "
        "Zempler Bank statements list transactions newest-first; REVERSE_ORDER is required."
    )


def test_period_buffer_days_present(commands_text):
    """$periodBufferDays must be set to allow date-range tolerance."""
    assert "$periodBufferDays" in commands_text, (
        "$periodBufferDays not found in Commands. "
        "This variable allows a tolerance window around the statement period dates "
        "and is required for Zempler Bank scripts."
    )


def test_features_flags_are_valid(commands_text):
    """All $features tokens must be drawn from the documented valid flag set."""
    valid_flags = {
        "NO_TRANSACTION_YEAR",
        "NO_OPENING_BALANCE",
        "SKIP_MISSING_CLOSING_BALANCE_CHECK",
        "REVERSE_ORDER",
        "OPENING_BALANCE_FROM_FIRST_ROW",
        "CREDIT_CARD",
    }
    match = re.search(r'\$features\s*=\s*"([^"]*)"', commands_text)
    if match:
        used_flags = set(match.group(1).split())
        unknown = used_flags - valid_flags
        assert not unknown, (
            f"Unknown $features flag(s): {unknown}. "
            f"Valid flags are: {sorted(valid_flags)}"
        )


def test_multipage_header_handled(commands_text):
    """Multi-page transaction extraction must define a header exclusion zone."""
    assert "ignore header above" in commands_text.lower(), (
        "No 'ignore header above' command found. "
        "Repeating page headers will corrupt the transaction table on multi-page statements."
    )


def test_multipage_footer_handled(commands_text):
    """Multi-page transaction extraction must define a footer exclusion zone."""
    assert "ignore footer below" in commands_text.lower(), (
        "No 'ignore footer below' command found. "
        "Repeating page footers will corrupt the transaction table on multi-page statements."
    )


def test_carry_forward_rows_deleted(commands_text):
    """Bank statement script must contain a 'delete all lines' command to remove carry-forward rows."""
    has_delete = (
        "delete all lines starting" in commands_text.lower()
        or "delete all lines containing" in commands_text.lower()
    )
    assert has_delete, (
        "No 'delete all lines' command found. "
        "Carry-forward / continued rows between pages must be cleaned up. "
        "Example: delete all lines starting \"BROUGHT FORWARD\""
    )


# ── Category E: ScriptId consistency and IsDeleted ───────────────────────────


def test_is_deleted_zero_in_script_insert(sql_content):
    """IsDeleted must be 0 in the digitalpdf$script INSERT."""
    match = re.search(r"INSERT INTO `digitalpdf\$script`.*?;", sql_content, re.DOTALL)
    assert match, "digitalpdf$script INSERT not found"
    assert re.search(r",\s*0\s*\)\s*;", match.group(0)), (
        "IsDeleted must be 0 in digitalpdf$script INSERT. "
        "A value of 1 would mark the script as deleted on import."
    )


def test_is_deleted_zero_in_definition_insert(doc_id_insert):
    """IsDeleted must be 0 in the digitalpdf$documentidentification INSERT."""
    assert re.search(r",\s*0\s*\)\s*;", doc_id_insert), (
        "IsDeleted must be 0 in digitalpdf$documentidentification INSERT. "
        "A value of 1 would mark the definition as deleted on import."
    )


def test_script_id_matches_definition_script_id(sql_content, script_id):
    """ScriptId in definition row must match Id in the script row."""
    def_script_ids = re.findall(
        r"INSERT INTO `digitalpdf\$documentidentification`.*?VALUES.*?,\s*(\d+)\s*,\s*\d+\s*,\s*UTC_TIMESTAMP",
        sql_content,
        re.DOTALL,
    )
    assert def_script_ids, (
        "Could not extract ScriptId from digitalpdf$documentidentification INSERT. "
        "Verify the column order matches the expected schema."
    )
    for def_script_id in def_script_ids:
        assert def_script_id == script_id, (
            f"ScriptId mismatch: definition row references ScriptId={def_script_id} "
            f"but script row has Id={script_id}. "
            "Both must use the same numeric Id."
        )


def test_placeholder_id_noted(sql_content):
    """Placeholder Id 9999 is expected and acknowledged for this script."""
    ids = re.findall(r"VALUES\s*\(\s*(\d+)", sql_content)
    placeholder_ids = [i for i in ids if int(i) == 9999]
    # This script uses placeholder IDs — assert they ARE present (documents the known state)
    assert placeholder_ids, (
        "Expected placeholder Id 9999 but none found. "
        "If real IDs have been assigned, set IDS_ARE_PLACEHOLDERS = False in this file "
        "and add test_no_placeholder_ids to verify the real IDs."
    )
