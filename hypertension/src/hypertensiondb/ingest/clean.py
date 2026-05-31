import re
from collections import Counter


_HYPHEN_LINEEND = re.compile(r"([A-Za-z])-\n([A-Za-z])")
_CJK_RANGE = r"一-鿿"
_BROKEN_LINE_CJK = re.compile(rf"([{_CJK_RANGE}])\n([{_CJK_RANGE}])")
_BROKEN_LINE_LATIN = re.compile(r"([A-Za-z,;:])\n([A-Za-z])")
_PARA_BREAK_TOKEN = "\x00PARA\x00"


def fix_hyphenation(text: str) -> str:
    """Join hyphenated words split across line ends: 'Hyper-\\nten' -> 'Hyperten'."""
    return _HYPHEN_LINEEND.sub(r"\1\2", text)


def merge_broken_lines(text: str) -> str:
    """Merge single line breaks within paragraphs.

    - Latin: join with a space.
    - CJK: join without space.
    - Preserve double newlines (paragraph breaks).
    """
    text = text.replace("\n\n", _PARA_BREAK_TOKEN)
    text = _BROKEN_LINE_CJK.sub(r"\1\2", text)
    text = _BROKEN_LINE_LATIN.sub(r"\1 \2", text)
    text = text.replace("\n", " ")
    text = text.replace(_PARA_BREAK_TOKEN, "\n\n")
    return text


def remove_repeating_lines(pages: list[str], min_occurrences_ratio: float = 0.66) -> list[str]:
    """Drop lines that appear on >= ratio of all pages (header/footer noise)."""
    if len(pages) < 2:
        return list(pages)

    line_counts: Counter[str] = Counter()
    for p in pages:
        for line in p.splitlines():
            line_stripped = line.strip()
            if line_stripped:
                line_counts[line_stripped] += 1

    threshold = max(2, int(len(pages) * min_occurrences_ratio))
    bad = {line for line, count in line_counts.items() if count >= threshold}

    cleaned: list[str] = []
    for p in pages:
        kept_lines = [line for line in p.splitlines() if line.strip() not in bad]
        cleaned.append("\n".join(kept_lines))
    return cleaned


def normalize_whitespace(text: str) -> str:
    """Collapse runs of tabs/spaces; preserve newlines."""
    text = re.sub(r"[ \t]+", " ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return text


def clean_text(pages: list[str]) -> str:
    """Apply the full cleaning pipeline and return a single string."""
    pages = remove_repeating_lines(pages)
    joined = "\n\n".join(pages)
    joined = fix_hyphenation(joined)
    joined = merge_broken_lines(joined)
    joined = normalize_whitespace(joined)
    return joined
