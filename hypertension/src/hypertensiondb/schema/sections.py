import re

_SECTION_MAP: list[tuple[re.Pattern, str]] = [
    (re.compile(r"临床要点|Clinical Bottom Line", re.I), "clinical_bottom_line"),
    (re.compile(r"中文摘要|摘要$", re.I),                "abstract_zh"),
    (re.compile(r"English Abstract|Abstract$", re.I),   "abstract_en"),
    (re.compile(r"背景|Background", re.I),               "background"),
    (re.compile(r"方法|Methods?", re.I),                 "methods"),
    (re.compile(r"结果|Results?", re.I),                 "results"),
    (re.compile(r"讨论|Discussion", re.I),               "discussion"),
    (re.compile(r"结论|Conclusions?", re.I),             "conclusion"),
    # --- SmPC drug-safety dimensions (DRUG_SAFETY evidence; openFDA/DailyMed) ---
    # Order matters: boxed-warning before the generic warning pattern, since
    # "黑框警告" contains "警告" and must not fall through to warnings_precautions.
    (re.compile(r"黑框警告|Boxed Warning", re.I),                       "boxed_warning"),
    (re.compile(r"禁忌|Contraindication", re.I),                       "contraindications"),
    (re.compile(r"警告|注意事项|Warning|Precaution", re.I),            "warnings_precautions"),
    (re.compile(r"相互作用|Interaction", re.I),                        "drug_interactions"),
    (re.compile(r"妊娠|哺乳|特殊人群|Pregnan|Lactation|Specific Population", re.I),
                                                                       "pregnancy_lactation"),
    (re.compile(r"不良反应|Adverse", re.I),                            "adverse_reactions"),
    (re.compile(r"参考文献|References?", re.I),          "references"),
]

_HEADING_RE = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)


def split_sections(markdown: str) -> dict[str, str]:
    """Split markdown body into standard section dict.

    Returns a dict with all standard section keys; missing sections → "".
    """
    result: dict[str, str] = {key: "" for _, key in _SECTION_MAP}

    # Strip YAML frontmatter if present
    if markdown.startswith("---"):
        end = markdown.find("\n---", 3)
        if end != -1:
            markdown = markdown[end + 4:]

    parts = re.split(r"(?=^#{1,3}\s)", markdown, flags=re.MULTILINE)
    for part in parts:
        m = _HEADING_RE.match(part.strip())
        if not m:
            continue
        heading = m.group(1)
        body = part[m.end():].strip()
        for pattern, key in _SECTION_MAP:
            if pattern.search(heading):
                result[key] = body
                break

    return result
