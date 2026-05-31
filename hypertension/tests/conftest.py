import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SCHEMA_FIXTURES = FIXTURES_DIR / "schema"


@pytest.fixture
def valid_rct_path() -> Path:
    return SCHEMA_FIXTURES / "valid_rct.md"


@pytest.fixture
def invalid_grade_path() -> Path:
    return SCHEMA_FIXTURES / "invalid_bad_grade.md"
