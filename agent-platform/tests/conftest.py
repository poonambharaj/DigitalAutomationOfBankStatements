import re

import pytest


def pytest_addoption(parser):
    parser.addoption("--sql-file", action="store", required=True,
                      help="Path to the generated digital script SQL file")
    parser.addoption("--document-type", action="store", required=True,
                      choices=["bank_statement", "invoice", "credit_note"])
    parser.addoption("--expected-script-id", action="store", type=int, required=True)


# Matches an SQL string literal that uses backslash escaping (\' and \n),
# as produced by the digital-script-builder Commands/text fields.
_ESCAPED_STRING = r"'(?:[^'\\]|\\.)*'"

_SCRIPT_ROW_RE = re.compile(
    r"INSERT INTO `digitalpdf\$script`\s*\([^)]*\)\s*VALUES\s*\(\s*"
    r"(?P<id>\d+),\s*"
    r"(?P<name>" + _ESCAPED_STRING + r"),\s*"
    r"(?P<commands>" + _ESCAPED_STRING + r"),\s*"
    r"UTC_TIMESTAMP\(\),\s*(?P<is_deleted>\d)\s*\)\s*;",
    re.DOTALL,
)

_FIELD = r"(?:NULL|" + _ESCAPED_STRING + r")"
_NUM_FIELD = r"(?:NULL|-?\d+)"

_IDENTIFICATION_ROW_RE = re.compile(
    r"INSERT INTO `digitalpdf\$documentidentification`[^;]*?VALUES\s*\(\s*"
    r"(?P<id>\d+),\s*"
    r"(?P<name>" + _FIELD + r"),\s*"
    r"(?P<title>" + _FIELD + r"),\s*"
    r"(?P<author>" + _FIELD + r"),\s*"
    r"(?P<creator>" + _FIELD + r"),\s*"
    r"(?P<producer>" + _FIELD + r"),\s*"
    r"(?P<version>" + _NUM_FIELD + r"),\s*"
    r"(?P<pagecount>" + _NUM_FIELD + r"),\s*"
    r"(?P<signatureinfo>" + _FIELD + r"),\s*"
    r"(?P<containstext>" + _FIELD + r"),\s*"
    r"(?P<excludestext>" + _FIELD + r"),\s*"
    r"(?P<scriptid>" + _NUM_FIELD + r"),\s*"
    r"(?P<vrs>\d+),\s*"
    r"UTC_TIMESTAMP\(\),\s*(?P<is_deleted>\d)\s*\)\s*;",
    re.DOTALL,
)


def _unescape(value):
    if value is None or value == "NULL":
        return None
    inner = value[1:-1]  # strip surrounding quotes
    return inner.replace("\\n", "\n").replace("\\'", "'")


@pytest.fixture(scope="session")
def document_type(request):
    return request.config.getoption("--document-type")


@pytest.fixture(scope="session")
def expected_script_id(request):
    return request.config.getoption("--expected-script-id")


@pytest.fixture(scope="session")
def sql_text(request):
    sql_path = request.config.getoption("--sql-file")
    with open(sql_path, "r", encoding="utf-8") as handle:
        return handle.read()


@pytest.fixture(scope="session")
def script_row(sql_text):
    match = _SCRIPT_ROW_RE.search(sql_text)
    if not match:
        return None
    return {
        "id": int(match.group("id")),
        "name": _unescape(match.group("name")),
        "commands": _unescape(match.group("commands")),
    }


@pytest.fixture(scope="session")
def identification_rows(sql_text):
    rows = []
    for match in _IDENTIFICATION_ROW_RE.finditer(sql_text):
        rows.append({
            "id": int(match.group("id")),
            "scriptid": None if match.group("scriptid") == "NULL" else int(match.group("scriptid")),
            "vrs": int(match.group("vrs")),
            "containstext": _unescape(match.group("containstext")),
            "excludestext": _unescape(match.group("excludestext")),
        })
    return rows
