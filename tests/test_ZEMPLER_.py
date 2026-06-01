import json
import re
import pytest
from pathlib import Path


# ── Category A: SQL structure ─────────────────────────────────────────────────

def test_script_insert_present(sql_content):
    assert "INSERT INTO `digitalpdf$script`" in sql_content


def test_doc_id_insert_present(sql_content):
    assert "INSERT INTO `digitalpdf$documentidentification`" in sql_content


def test_no_markdown_fences(sql_content):
    assert "```" not in sql_content


def test_is_deleted_zero_script(sql_content):
    # digitalpdf$script INSERT must end with ,0);
    match = re.search(r"INSERT INTO `digitalpdf\$script`.*?;", sql_content, re.DOTALL)
    assert match
    assert re.search(r",\s*0\s*\)\s*;", match.group(0)), "IsDeleted must be 0 in script INSERT"


def test_is_deleted_zero_doc_id(doc_id_insert):
    assert re.search(r",\s*0\s*\)\s*;", doc_id_insert), "IsDeleted must be 0 in documentidentification INSERT"


def test_modification_time_utc_script(sql_content):
    """Both INSERTs must use UTC_TIMESTAMP() not hardcoded literal"""
    match = re.search(r"INSERT INTO `digitalpdf\$script`.*?;", sql_content, re.DOTALL)
    assert match
    script_insert = match.group(0)
    has_utc = "UTC_TIMESTAMP()" in script_insert
    has_hardcoded = re.search(r"'202[0-9]", script_insert)
    assert has_utc, (
        f"ModificationTimeUtc in script INSERT must use UTC_TIMESTAMP() function, "
        f"not hardcoded literal. Found: {has_hardcoded.group(0) if has_hardcoded else 'unknown'}"
    )


def test_modification_time_utc_doc_id(doc_id_insert):
    """Document identification INSERT must use UTC_TIMESTAMP() not hardcoded literal"""
    has_utc = "UTC_TIMESTAMP()" in doc_id_insert
    has_hardcoded = re.search(r"'202[0-9]", doc_id_insert)
    assert has_utc, (
        f"ModificationTimeUtc in documentidentification INSERT must use UTC_TIMESTAMP() function, "
        f"not hardcoded literal. Found: {has_hardcoded.group(0) if has_hardcoded else 'unknown'}"
    )


def test_verification_rule_set_id_is_4(doc_id_insert):
    # VerificationRuleSetId is the 13th field (0-indexed: 12)
    # Easier: just assert ,4, appears near the end of the VALUES
    assert re.search(r",\s*4\s*,\s*UTC_TIMESTAMP\(\)", doc_id_insert) or re.search(r",\s*4\s*,\s*'202", doc_id_insert), \
        "VerificationRuleSetId must be 4 for bank statements"


# ── Category B: Required variable extraction (parametrized) ──────────────────

REQUIRED_VARS = [
    "$source",
    "$accountName",
    "$accountNumber",
    "$periodFrom",
    "$periodTo",
    "$openingBalance",
    "$closingBalance",
    "$transactions",
]


@pytest.mark.parametrize("variable", REQUIRED_VARS)
def test_required_variable_present(commands_text, variable):
    assert variable in commands_text, f"Required variable {variable} not found in Commands"


# ── Category C: DSL quality ───────────────────────────────────────────────────

def test_commands_is_multiline(commands_text):
    assert "\n" in commands_text, "Commands field must contain real newlines"


def test_no_backslash_n_literals_in_commands(commands_text):
    assert "\\n" not in commands_text, "Commands field must not contain \\n literals after normalisation"


def test_ignore_header_above_present(commands_text):
    assert "ignore header above" in commands_text.lower(), \
        "Multi-page bank statement Commands must contain 'ignore header above'"


def test_ignore_footer_below_present(commands_text):
    assert "ignore footer below" in commands_text.lower(), \
        "Multi-page bank statement Commands must contain 'ignore footer below'"


def test_source_variable_assigned(commands_text):
    # $source = "some non-empty string"
    # The commands_text fixture already handles \n normalization
    # Look for $source = followed by quoted text
    match = re.search(r'\$source\s*=\s*"([^"]*)"', commands_text)
    assert match, (
        f"$source must be assigned a non-empty string value in format: "
        f'$source = "BankName". Commands section: {commands_text[:200]}'
    )
    value = match.group(1).strip()
    assert len(value) > 0, "$source value must be non-empty"


# ── Category D: Document identification quality ───────────────────────────────

def test_creator_pattern_not_null(doc_id_insert):
    """CreatorPattern must be set to a pattern (not NULL)"""
    # Check the 5th field (CreatorPattern) is not NULL
    match = re.search(r"VALUES\s*\([^)]+\)", doc_id_insert, re.DOTALL)
    assert match
    values_section = match.group(0)
    # Count fields: split carefully by commas, avoiding those inside quotes
    # Pattern: after NULL,NULL we should see either NULL,NULL for Creator/Producer or a pattern
    creator_is_null = re.search(r"NULL\s*,\s*NULL\s*,\s*NULL\s*,\s*NULL", values_section)
    assert not creator_is_null, (
        "CreatorPattern and ProducerPattern must not both be NULL. "
        "At least one must be set to fingerprint the PDF source."
    )


def test_contains_text_populated(doc_id_insert):
    """ContainsText must be a non-empty JSON array"""
    # Match the JSON array in quotes, handling escaped quotes
    match = re.search(r"'(\[[^\]]*\])'", doc_id_insert)
    assert match, "ContainsText must be populated with a JSON array"

    raw_json_str = match.group(1)
    # Handle escaped quotes within the JSON
    unescaped_json = raw_json_str.replace('\\"', '"')

    try:
        phrases = json.loads(unescaped_json)
        assert isinstance(phrases, list), "ContainsText must be a JSON array"
        assert len(phrases) >= 2, "ContainsText must contain at least 2 identification phrases"
    except json.JSONDecodeError as e:
        pytest.fail(f"ContainsText is not valid JSON (after unescaping): {unescaped_json!r} — {e}")


def test_contains_text_valid_json(doc_id_insert):
    """ContainsText must parse as valid JSON after unescaping"""
    match = re.search(r"'(\[[^\]]*\])'", doc_id_insert)
    assert match, "ContainsText must be a JSON array string"

    raw_json_str = match.group(1)
    unescaped_json = raw_json_str.replace('\\"', '"')

    try:
        phrases = json.loads(unescaped_json)
        assert isinstance(phrases, list)
    except json.JSONDecodeError as e:
        pytest.fail(f"ContainsText is not valid JSON: {unescaped_json!r} — {e}")


def test_verification_rule_set_id_is_4_doc_id(doc_id_values):
    # The VerificationRuleSetId appears as ,4, before the timestamp
    assert re.search(r",\s*4\s*,", doc_id_values), \
        "VerificationRuleSetId must be 4"
