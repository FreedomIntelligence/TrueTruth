import re


STANDARD_SECTIONS = [
    "clinical_bottom_line",
    "abstract_zh",
    "abstract_en",
    "background",
    "methods",
    "results",
    "discussion",
    "conclusion",
]


_HEADING_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^[ \t]*(临床要点|Clinical Bottom Line)[ \t]*[/／]?[ \t]*.*$",
                re.MULTILINE | re.IGNORECASE), "clinical_bottom_line"),
    (re.compile(r"^[ \t]*(中文摘要|摘要)[ \t]*$", re.MULTILINE), "abstract_zh"),
    (re.compile(r"^[ \t]*(English Abstract|Abstract)[ \t]*[/／]?[ \t]*.*$",
                re.MULTILINE | re.IGNORECASE), "abstract_en"),
    (re.compile(r"^[ \t]*(背景|引言|Background|Introduction)[ \t]*[/／]?[ \t]*.*$",
                re.MULTILINE | re.IGNORECASE), "background"),
    (re.compile(r"^[ \t]*(方法|方法学|材料与方法|Methods?|Methodology|Materials and Methods)[ \t]*[/／]?[ \t]*.*$",
                re.MULTILINE | re.IGNORECASE), "methods"),
    (re.compile(r"^[ \t]*(结果|Results?|Findings?)[ \t]*[/／]?[ \t]*.*$",
                re.MULTILINE | re.IGNORECASE), "results"),
    (re.compile(r"^[ \t]*(讨论|Discussion)[ \t]*[/／]?[ \t]*.*$",
                re.MULTILINE | re.IGNORECASE), "discussion"),
    (re.compile(r"^[ \t]*(结论|总结|Conclusions?|Summary)[ \t]*[/／]?[ \t]*.*$",
                re.MULTILINE | re.IGNORECASE), "conclusion"),
]


def detect_sections(text: str) -> dict[str, str]:
    """Heuristically split text into the 8 standard sections.

    Returns a dict with all 8 keys; un-detected ones map to empty string.
    Fallback: if NO headings are detected, the entire text goes into 'results'.
    """
    hits: list[tuple[int, int, str]] = []
    for pattern, key in _HEADING_RULES:
        for m in pattern.finditer(text):
            hits.append((m.start(), m.end(), key))

    hits.sort(key=lambda t: t[0])

    sections: dict[str, str] = {k: "" for k in STANDARD_SECTIONS}

    if not hits:
        sections["results"] = text.strip()
        return sections

    for i, (start, end, key) in enumerate(hits):
        body_start = end
        body_end = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        body = text[body_start:body_end].strip()
        if body:
            if sections[key]:
                sections[key] = sections[key] + "\n\n" + body
            else:
                sections[key] = body

    return sections
