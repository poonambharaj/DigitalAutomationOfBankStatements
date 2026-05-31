import json
import re
import pytest
from pathlib import Path

SQL_FILE = Path("output/digital_scripts/ZEMPLER_.sql")


@pytest.fixture(scope="session")
def sql_content():
    return SQL_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def commands_text(sql_content):
    # Extract Commands value from digitalpdf$script INSERT
    # Handles both real newlines and \n literals
    # The Commands field is the 3rd value: VALUES (id,'Name','<commands>',...)
    match = re.search(
        r"INSERT INTO `digitalpdf\$script`[^V]*VALUES\s*\(\s*\d+\s*,\s*'[^']*'\s*,\s*'((?:[^'\\]|\\.)*)'",
        sql_content,
        re.DOTALL,
    )
    assert match, "Could not extract Commands field from digitalpdf$script INSERT"
    raw = match.group(1)
    # Normalise: convert \n literals to real newlines if present
    # Also handle \\n (double backslash-n in raw SQL)
    normalized = raw.replace("\\n", "\n")
    # Handle escaped quotes: \" or \\\"
    normalized = normalized.replace('\\"', '"')
    normalized = normalized.replace("\\'", "'")
    return normalized


@pytest.fixture(scope="session")
def doc_id_insert(sql_content):
    # Extract the full digitalpdf$documentidentification INSERT row
    match = re.search(
        r"INSERT INTO `digitalpdf\$documentidentification`.*?;",
        sql_content,
        re.DOTALL,
    )
    assert match, "Could not find digitalpdf$documentidentification INSERT"
    return match.group(0)


@pytest.fixture(scope="session")
def doc_id_values(doc_id_insert):
    # Extract VALUES (...) content
    match = re.search(r"VALUES\s*\((.+)\)\s*;", doc_id_insert, re.DOTALL)
    assert match, "Could not extract VALUES from documentidentification INSERT"
    return match.group(1)
