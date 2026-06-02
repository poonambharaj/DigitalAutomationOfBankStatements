"""
Unit tests for the JAJA digital extraction SQL script.

Tests are grouped into five categories (25 total):

  A. SQL structure (3 tests)
  B. Script INSERT field checks (4 tests)
  C. Variable extraction from Commands (8 tests)
  D. DSL quality (5 tests)
  E. Document identification checks (5 tests)
"""

import json
import re
import pytest
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SQL_PATH = Path("C:/dev/AutomationOfDigitalScripts/output/digital_scripts/JAJA_20260602_0000.sql")
EXPECTED_SCRIPT_NAME = "JajaFinance_CreditCard"
EXPECTED_SCRIPT_ID = 9999           # placeholder — real ID assigned at deploy
EXPECTED_VRS_ID = 4                 # bank_statement / credit card (VerificationRuleSetId)

# ---------------------------------------------------------------------------
# Shared parsing helpers
# ---------------------------------------------------------------------------


def _parse_definition_fields(doc_id_insert):
    """Parse the VALUES fields from digitalpdf$documentidentification INSERT.

    The ContainsText and ExcludesText columns hold single-quoted JSON arrays
    (e.g. '["a","b"]') that contain commas. A naive comma-split corrupts
    those fields. This function substitutes each JSON array with a placeholder
    before splitting, then restores the original values.

    Returns a list of 15 field strings (stripped of surrounding whitespace).
    Column order (0-indexed):
      0  Id
      1  Name
      2  TitlePattern
      3  AuthorPattern
      4  CreatorPattern
      5  ProducerPattern
      6  Version
      7  PageCount
      8  SignatureInfo
      9  ContainsText   (single-quoted JSON array)
      10 ExcludesText   (single-quoted JSON array or NULL)
      11 ScriptId
      12 VerificationRuleSetId
      13 ModificationTimeUtc
      14 IsDeleted
    """
    # Extract raw VALUES content
    values_match = re.search(r"VALUES\s*\((.+)\)\s*;", doc_id_insert, re.DOTALL)
    if not values_match:
        return []
    raw = values_match.group(1)

    # Replace each single-quoted JSON array with a placeholder to protect
    # commas inside it from the field splitter.
    placeholders = {}
    counter = [0]

    def _replace_json_array(m):
        key = f"__JSON_ARRAY_{counter[0]}__"
        counter[0] += 1
        placeholders[key] = m.group(0)   # the full 'quoted JSON' token
        return key

    protected = re.sub(r"'(\[.*?\])'", _replace_json_array, raw, flags=re.DOTALL)

    # Split on commas not inside the JSON arrays (already replaced)
    fields = [f.strip() for f in protected.split(",")]

    # Restore placeholders
    restored = []
    for f in fields:
        for key, original in placeholders.items():
            f = f.replace(key, original)
        restored.append(f)

    return restored


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sql_content():
    """Read and return the full SQL file as a string."""
    assert SQL_PATH.exists(), f"SQL file not found: {SQL_PATH}"
    return SQL_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def commands_text(sql_content):
    """Extract and unescape the DSL Commands field from the script INSERT.

    The SQL encodes line breaks as backslash-n and double-quotes as backslash-".
    This fixture reverses both so that DSL content comparisons work against the
    actual DSL syntax.
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
    # Unescape in dependency order: \\" -> ", \' -> ', \n -> newline
    unescaped = raw.replace('\\"', '"').replace(r"\'", "'").replace(r"\n", "\n")
    return unescaped


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
def def_fields(doc_id_insert):
    """Parse and return the positional field list from the definition INSERT VALUES."""
    fields = _parse_definition_fields(doc_id_insert)
    assert fields, "Could not parse fields from digitalpdf$documentidentification INSERT"
    return fields


@pytest.fixture(scope="module")
def raw_commands_field(sql_content):
    """Return the raw (still-escaped) Commands string as it appears in the SQL file."""
    match = re.search(
        r"INSERT INTO `digitalpdf\$script`[^)]*\)\s*VALUES\s*\(\s*\d+\s*,\s*'[^']*'\s*,\s*'((?:[^'\\]|\\.)*)'",
        sql_content,
        re.DOTALL | re.IGNORECASE,
    )
    assert match, "Could not extract raw Commands value from SQL"
    return match.group(1)


@pytest.fixture(scope="module")
def script_insert_tail(sql_content):
    """Extract the ModificationTimeUtc and IsDeleted tail of the script INSERT.

    Because the Commands field may contain semicolons (in DSL comments), we
    cannot rely on '.*?;' to find the end of the INSERT.  Instead we locate
    the tail by finding what follows the closing quote of the Commands field.
    Pattern matches:  ...,<ModificationTimeUtc>,<IsDeleted>);
    """
    match = re.search(
        r"INSERT INTO `digitalpdf\$script`[^)]*\)\s*VALUES\s*\(\s*\d+\s*,\s*'[^']*'\s*,"
        r"\s*'(?:[^'\\]|\\.)*'\s*,\s*'([^']*)'\s*,\s*(\d+)\s*\)\s*;",
        sql_content,
        re.DOTALL | re.IGNORECASE,
    )
    assert match, (
        "Could not parse the tail fields (ModificationTimeUtc, IsDeleted) from "
        "digitalpdf$script INSERT. Verify the column order: "
        "Id, Name, Commands, ModificationTimeUtc, IsDeleted."
    )
    return {"modification_time_utc": match.group(1), "is_deleted": match.group(2)}


# ===========================================================================
# Category A — SQL Structure (tests 1-3)
# ===========================================================================


def test_script_insert_present(sql_content):
    """Test 1: File contains INSERT for digitalpdf$script."""
    assert "INSERT INTO `digitalpdf$script`" in sql_content, (
        "INSERT INTO `digitalpdf$script` not found in SQL file. "
        "The script INSERT is mandatory."
    )


def test_definition_insert_present(sql_content):
    """Test 2: File contains INSERT for digitalpdf$documentidentification."""
    assert "INSERT INTO `digitalpdf$documentidentification`" in sql_content, (
        "INSERT INTO `digitalpdf$documentidentification` not found in SQL file. "
        "The document identification INSERT is mandatory."
    )


def test_no_markdown_fences(sql_content):
    """Test 3: No markdown code fences present in the SQL file."""
    assert "```" not in sql_content, (
        "SQL file contains markdown code fences (```). "
        "The output must be pure SQL with no markdown formatting."
    )


# ===========================================================================
# Category B — Script INSERT field checks (tests 4-7)
# ===========================================================================


def test_name_field_is_jaja(sql_content):
    """Test 4: Name field in the script INSERT is 'JajaFinance_CreditCard'."""
    match = re.search(
        r"INSERT INTO `digitalpdf\$script`[^)]*\)\s*VALUES\s*\(\s*\d+\s*,\s*'([^']*)'",
        sql_content,
        re.DOTALL | re.IGNORECASE,
    )
    assert match, (
        "Could not extract Name field from digitalpdf$script INSERT. "
        "Check the column order is: Id, Name, Commands, ModificationTimeUtc, IsDeleted."
    )
    name = match.group(1)
    assert name == EXPECTED_SCRIPT_NAME, (
        f"Script Name is {name!r}, expected {EXPECTED_SCRIPT_NAME!r}. "
        "The name must exactly match the registered JAJA script name."
    )


def test_is_deleted_zero(script_insert_tail):
    """Test 5: IsDeleted = 0 in the script INSERT."""
    is_deleted = script_insert_tail["is_deleted"]
    assert is_deleted == "0", (
        f"IsDeleted is {is_deleted!r} in digitalpdf$script INSERT, expected '0'. "
        "A value of 1 would mark the script as deleted on import."
    )


def test_script_id_is_placeholder(sql_content):
    """Test 6: Id = 9999 (placeholder) in the script INSERT."""
    match = re.search(
        r"INSERT INTO `digitalpdf\$script`[^)]*\)\s*VALUES\s*\(\s*(\d+)",
        sql_content,
        re.DOTALL | re.IGNORECASE,
    )
    assert match, "Could not extract Id from digitalpdf$script INSERT"
    script_id = int(match.group(1))
    assert script_id == EXPECTED_SCRIPT_ID, (
        f"Script Id is {script_id}, expected placeholder {EXPECTED_SCRIPT_ID}. "
        "Placeholder Id 9999 is expected at this stage; real Ids are assigned at deploy time."
    )


def test_commands_field_non_empty(commands_text):
    """Test 7: Commands field is non-empty (length > 50 characters)."""
    assert len(commands_text.strip()) > 50, (
        f"Commands field is too short ({len(commands_text.strip())} chars). "
        "A complete DSL extraction script must be longer than 50 characters."
    )


# ===========================================================================
# Category C — Variable extraction from Commands (tests 8-15)
# ===========================================================================


def test_source_present(commands_text):
    """Test 8: $source is present in Commands."""
    assert "$source" in commands_text, (
        "Required variable '$source' not found in DSL Commands. "
        "The script must assign the bank/provider name to $source."
    )


def test_account_name_or_name_present(commands_text):
    """Test 9: $accountName or $name is present in Commands."""
    has_account_name = "$accountName" in commands_text
    has_name = "$name" in commands_text
    assert has_account_name or has_name, (
        "Neither '$accountName' nor '$name' found in DSL Commands. "
        "At least one account holder name variable must be extracted."
    )


def test_account_number_present(commands_text):
    """Test 10: $accountNumber is present in Commands."""
    assert "$accountNumber" in commands_text, (
        "Required variable '$accountNumber' not found in DSL Commands. "
        "The account number must be extracted from the statement."
    )


def test_period_from_present(commands_text):
    """Test 11: $periodFrom is present in Commands."""
    assert "$periodFrom" in commands_text, (
        "Required variable '$periodFrom' not found in DSL Commands. "
        "The statement period start date must be extracted."
    )


def test_period_to_present(commands_text):
    """Test 12: $periodTo is present in Commands."""
    assert "$periodTo" in commands_text, (
        "Required variable '$periodTo' not found in DSL Commands. "
        "The statement period end date must be extracted."
    )


def test_opening_balance_present_or_feature_flag(commands_text):
    """Test 13: $openingBalance is present OR features contains NO_OPENING_BALANCE."""
    has_opening_balance = "$openingBalance" in commands_text
    has_no_opening_balance_flag = (
        "NO_OPENING_BALANCE" in commands_text
        and "$features" in commands_text
    )
    assert has_opening_balance or has_no_opening_balance_flag, (
        "Neither '$openingBalance' found in Commands nor 'NO_OPENING_BALANCE' set in $features. "
        "Either extract the opening balance or declare it absent via $features."
    )


def test_closing_balance_present(commands_text):
    """Test 14: $closingBalance is present in Commands."""
    assert "$closingBalance" in commands_text, (
        "Required variable '$closingBalance' not found in DSL Commands. "
        "The closing balance must be extracted from the statement."
    )


def test_transactions_present(commands_text):
    """Test 15: $transactions is present in Commands."""
    assert "$transactions" in commands_text, (
        "Required variable '$transactions' not found in DSL Commands. "
        "The transaction table must be extracted from the statement."
    )


# ===========================================================================
# Category D — DSL Quality (tests 16-20)
# ===========================================================================


def test_commands_parsed_newlines_give_enough_lines(raw_commands_field):
    """Test 16: Commands uses backslash-n line break encoding — splitting gives > 5 lines."""
    # The raw SQL string encodes newlines as the two-character sequence \n
    lines = [ln for ln in raw_commands_field.split(r"\n") if ln.strip()]
    assert len(lines) > 5, (
        f"Splitting the raw Commands field by '\\\\n' produced only {len(lines)} non-blank "
        "line(s). The DSL must encode line breaks as \\\\n and contain more than 5 lines."
    )


def test_verification_rule_set_id_is_4(def_fields):
    """Test 17: VerificationRuleSetId = 4 in the identification INSERT."""
    # Index 12 = VerificationRuleSetId
    assert len(def_fields) >= 13, (
        f"Definition INSERT has fewer than 13 fields; cannot extract VerificationRuleSetId. "
        f"Fields found: {len(def_fields)}"
    )
    vrs_id = def_fields[12].strip("'\" ")
    assert vrs_id.isdigit(), (
        f"VerificationRuleSetId field (position 12) is not a digit: {vrs_id!r}. "
        "Check the column order in the INSERT."
    )
    assert int(vrs_id) == EXPECTED_VRS_ID, (
        f"VerificationRuleSetId is {vrs_id}, expected {EXPECTED_VRS_ID} for bank_statement. "
        "Valid values: 2=basic invoice, 3=invoice+VAT, 4=bank statement/credit card."
    )


def test_utc_timestamp_used(sql_content):
    """Test 18: UTC_TIMESTAMP() appears in the SQL (not relying solely on hardcoded timestamps)."""
    assert "UTC_TIMESTAMP()" in sql_content, (
        "UTC_TIMESTAMP() not found in SQL file. "
        "At least one INSERT must use UTC_TIMESTAMP() for ModificationTimeUtc "
        "rather than a hardcoded datetime literal."
    )


def test_modification_time_utc_in_at_least_one_insert(sql_content):
    """Test 19: ModificationTimeUtc uses UTC_TIMESTAMP() in at least one INSERT."""
    utc_count = sql_content.count("UTC_TIMESTAMP()")
    assert utc_count >= 1, (
        f"UTC_TIMESTAMP() found {utc_count} time(s) in SQL file. "
        "At least one INSERT must use UTC_TIMESTAMP() for ModificationTimeUtc."
    )


def test_commands_contains_get_keyword(commands_text):
    """Test 20: Commands contains the 'get' DSL keyword."""
    assert "get " in commands_text.lower(), (
        "The DSL keyword 'get' is not present in Commands. "
        "A valid extraction script must use at least one 'get' command to read data from the PDF."
    )


# ===========================================================================
# Category E — Document Identification checks (tests 21-25)
# ===========================================================================


def test_creator_pattern_is_wildcard(def_fields):
    """Test 21: CreatorPattern = '.*' in the identification INSERT."""
    # Index 4 = CreatorPattern
    assert len(def_fields) >= 5, (
        f"Fewer than 5 fields in definition INSERT; cannot validate CreatorPattern."
    )
    creator = def_fields[4].strip("'")
    assert creator == ".*", (
        f"CreatorPattern is {creator!r}, expected '.*'. "
        "The wildcard pattern '.*' matches all PDF creator tools."
    )


def test_producer_pattern_is_wildcard(def_fields):
    """Test 22: ProducerPattern = '.*' in the identification INSERT."""
    # Index 5 = ProducerPattern
    assert len(def_fields) >= 6, (
        f"Fewer than 6 fields in definition INSERT; cannot validate ProducerPattern."
    )
    producer = def_fields[5].strip("'")
    assert producer == ".*", (
        f"ProducerPattern is {producer!r}, expected '.*'. "
        "The wildcard pattern '.*' matches all PDF producer tools."
    )


def test_contains_text_present_and_non_empty(doc_id_insert):
    """Test 23: ContainsText is present and contains at least one phrase."""
    match = re.search(r"'(\[.*?\])'", doc_id_insert, re.DOTALL)
    assert match, (
        "ContainsText field not found or is NULL in the identification INSERT. "
        "A JSON array of document-identification phrases is required."
    )
    raw_json = match.group(1)
    assert len(raw_json) > 4, (
        f"ContainsText value {raw_json!r} is too short to be a meaningful array. "
        "Include at least one phrase that uniquely identifies JAJA Finance statements."
    )


def test_contains_text_is_valid_json_array(doc_id_insert):
    """Test 24: ContainsText is valid JSON and parses to a non-empty list.

    The ContainsText value is stored in the SQL as a single-quoted string
    containing a JSON array where double-quotes are escaped as backslash-".
    This fixture extracts and unescapes the value before parsing.
    """
    match = re.search(r"'(\[.*?\])'", doc_id_insert, re.DOTALL)
    assert match, (
        "ContainsText field not found or is NULL in the identification INSERT."
    )
    # The SQL encodes embedded double-quotes as \" — unescape before JSON parsing
    raw_json = match.group(1).replace('\\"', '"')
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"ContainsText is not valid JSON after unescaping: {raw_json!r} — {exc}"
        )
    assert isinstance(parsed, list), (
        "ContainsText must parse as a JSON array, not a scalar or object."
    )
    assert len(parsed) >= 1, (
        "ContainsText array must contain at least one document-identification phrase."
    )


def test_definition_script_id_is_9999(def_fields):
    """Test 25: ScriptId = 9999 (placeholder) in the identification INSERT."""
    # Index 11 = ScriptId
    assert len(def_fields) >= 12, (
        f"Definition INSERT has fewer than 12 fields; cannot extract ScriptId. "
        f"Fields found: {len(def_fields)}"
    )
    script_id_val = def_fields[11].strip("'\" ")
    assert script_id_val.isdigit(), (
        f"ScriptId field (position 11) is not a digit: {script_id_val!r}. "
        "Check the column order in the INSERT."
    )
    assert int(script_id_val) == EXPECTED_SCRIPT_ID, (
        f"ScriptId in definition row is {script_id_val}, expected placeholder {EXPECTED_SCRIPT_ID}. "
        "The ScriptId must match the Id in the digitalpdf$script INSERT."
    )
