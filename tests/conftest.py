"""Shared pytest fixtures for DigitalPDF extraction script tests.

Each project test file is self-contained with its own module-scoped fixtures.
This conftest provides:
  - CLI options consumed by the agent spec (--sql-file, --document-type, etc.)
  - Shared fixtures for any test file that opts in via request.config

Individual project test files override these with module-scoped fixtures bound
to their own SQL_PATH constant, so there is no cross-project state leakage.
"""

import re
import pytest
from pathlib import Path


def pytest_addoption(parser):
    parser.addoption(
        "--sql-file", action="store", default=None,
        help="Path to the SQL file under test",
    )
    parser.addoption(
        "--document-type", action="store", default="bank_statement",
        help="Document type: bank_statement | invoice | credit_note",
    )
    parser.addoption(
        "--expected-script-id", action="store", type=int, default=None,
        help="Expected script Id value in the SQL file",
    )
    parser.addoption(
        "--ids-are-placeholders", action="store_true", default=False,
        help="Set when placeholder Id 9999 is expected in the SQL",
    )


@pytest.fixture(scope="module")
def document_type(request):
    return request.config.getoption("--document-type", default="bank_statement")


@pytest.fixture(scope="module")
def expected_script_id(request):
    return request.config.getoption("--expected-script-id", default=None)


@pytest.fixture(scope="module")
def ids_are_placeholders(request):
    return request.config.getoption("--ids-are-placeholders", default=False)
