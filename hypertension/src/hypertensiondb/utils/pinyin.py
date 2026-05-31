from pypinyin import pinyin, Style

_COMPOUND_SURNAMES = {
    "欧阳", "司马", "诸葛", "上官", "东方", "夏侯",
    "独孤", "长孙", "宇文", "公孙", "慕容", "皇甫",
}


def to_first_author_pinyin(name: str) -> str:
    """Return UPPER-CASE pinyin of the first author's surname.

    For Chinese names, handles compound surnames.
    For English names, returns the first whitespace-delimited token uppercased.
    For institution abbreviations (all-caps, no spaces), returns as-is.
    """
    name = name.strip()
    if not name:
        raise ValueError("name must not be empty")

    # Institution abbreviation: all-caps + no spaces
    if name.isupper() and " " not in name:
        return name

    # English name: first char is ASCII letter
    if name[0].isascii() and name[0].isalpha():
        return name.split()[0].upper()

    # Chinese name: check compound surname
    if len(name) >= 2 and name[:2] in _COMPOUND_SURNAMES:
        surname = name[:2]
    else:
        surname = name[0]

    py = pinyin(surname, style=Style.NORMAL)
    return "".join(part[0] for part in py).upper()
