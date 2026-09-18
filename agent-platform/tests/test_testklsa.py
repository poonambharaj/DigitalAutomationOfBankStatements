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
