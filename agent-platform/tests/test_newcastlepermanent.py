import re

VALID_VERIFICATION_RULE_SET_IDS = {2, 3, 4}

REQUIRED_VARIABLES_BY_TYPE = {
    "bank_statement": [
        "$source", "$accountName", "$accountNumber", "$periodFrom",
        "$periodTo", "$openingBalance", "$closingBalance", "$transactions",
    ],
    "invoice": [
        "$invoiceType", "$name", "$currency", "$vatNumber", "$invoiceNumber",
        "$invoiceDate", "$net", "$tax", "$total", "$lineItems",
    ],
    "credit_note": [
        "$invoiceType", "$name", "$currency", "$vatNumber", "$invoiceNumber",
        "$invoiceDate", "$net", "$tax", "$total", "$lineItems",
    ],
}


def test_script_insert_present(script_row):
    assert script_row is not None, "digitalpdf$script INSERT not found in SQL file"


def test_script_id_matches_expected(script_row, expected_script_id):
    assert script_row["id"] == expected_script_id, (
        f"Expected script id {expected_script_id}, found {script_row['id']}"
    )


def test_commands_non_empty(script_row):
    assert script_row["commands"].strip(), "Commands field is empty"


def test_no_markdown_fences(script_row):
    assert "```" not in script_row["commands"], "Commands field contains markdown code fences"


def test_required_variables_present(script_row, document_type):
    required = REQUIRED_VARIABLES_BY_TYPE[document_type]
    missing = [var for var in required if var not in script_row["commands"]]
    assert not missing, f"Missing required variables: {missing}"


def test_identification_rows_present(identification_rows):
    assert identification_rows, "No digitalpdf$documentidentification INSERT rows found"


def test_identification_rows_reference_script(identification_rows, script_row):
    for row in identification_rows:
        assert row["scriptid"] in (None, script_row["id"]), (
            f"documentidentification row {row['id']} references ScriptId "
            f"{row['scriptid']}, expected {script_row['id']}"
        )


def test_verification_rule_set_id_valid(identification_rows):
    for row in identification_rows:
        assert row["vrs"] in VALID_VERIFICATION_RULE_SET_IDS, (
            f"documentidentification row {row['id']} has invalid VerificationRuleSetId {row['vrs']}"
        )


def test_contains_text_present(identification_rows):
    for row in identification_rows:
        assert row["containstext"], (
            f"documentidentification row {row['id']} has no ContainsText anchor"
        )


def test_account_name_not_truncated_by_fixed_word_count(script_row):
    """Regression test: an earlier version used a fixed `take words 7` limit for
    $accountName, truncating multi-word/wrapped business account names (e.g.
    "D & L CONCRETING AND DEMOLITION PTY LTD" -> "...PTY"). The current script
    must instead anchor $accountName on a text box spanning the "Account
    number" line down to the "BSB" line, so a name wrapped onto a second
    physical line is still captured in full. Checked structurally rather than
    by hardcoding internal variable names, since those may be renamed again.
    """
    commands = script_row["commands"]
    assert "take words 7" not in commands, (
        "$accountName extraction has regressed to the fixed 7-word truncation bug"
    )

    # Box-text variable can be either an @anchor or a $result variable.
    box_match = re.search(
        r"([@$]\w+)\s*=\s*get text in box\s+(@\w+)\s+(@\w+)\s+\S+\s+\S+",
        commands,
    )
    assert box_match, (
        "No 'get text in box' extraction found; $accountName should be sourced "
        "from a multi-line box between 'Account number' and 'BSB', not a single line"
    )
    box_var, top_var, bottom_var = box_match.groups()

    assert re.search(
        rf'{re.escape(top_var)}\s*=\s*get line starting "Account number" => top', commands
    ), f"Box top boundary {top_var} is not anchored to the 'Account number' line"
    assert re.search(
        rf'{re.escape(bottom_var)}\s*=\s*get line starting "BSB" => top', commands
    ), f"Box bottom boundary {bottom_var} is not anchored to the 'BSB' line"

    assert f"$accountName = get words after {box_var}" in commands, (
        f"$accountName does not read from the box-extracted text variable {box_var}"
    )


def test_multi_page_table_used_for_transactions(script_row):
    assert "get multi page table" in script_row["commands"], (
        "Transactions should use 'get multi page table' since Newcastle "
        "Permanent statements can span multiple pages"
    )
