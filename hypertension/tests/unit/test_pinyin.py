import pytest
from hypertensiondb.utils.pinyin import to_first_author_pinyin


@pytest.mark.unit
@pytest.mark.parametrize("name, expected", [
    ("彭勇",       "PENG"),
    ("张伟",       "ZHANG"),
    ("欧阳明",     "OUYANG"),
    ("Williams B", "WILLIAMS"),
    ("de Luca M",  "DE"),
    ("Wang X",     "WANG"),
    ("CHS",        "CHS"),
    ("ESC",        "ESC"),
])
def test_to_first_author_pinyin(name, expected):
    assert to_first_author_pinyin(name) == expected
