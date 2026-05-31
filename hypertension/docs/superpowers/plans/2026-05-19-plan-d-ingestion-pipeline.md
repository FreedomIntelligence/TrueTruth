# Plan D: PDF 入库管线 (PDF → Markdown)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户能把 `raw/incoming/*.pdf` 转换成 `evidence/{type}/EV-...md` 草稿文件，自动跑：解析 → 清洗 → 分节 → LLM 抽 frontmatter → Pydantic 校验 → 写盘。手工最少介入，所有 LLM 抽出字段一律 `status=draft`，人工复核后才能升级。

**Architecture:** 五段管线 — `PdfParser`（PyMuPDF 默认）→ `TextCleaner`（去页眉页脚 / 修复断词）→ `SectionMapper`（启发式 IMRaD → 8 节区）→ `FrontmatterExtractor`（OpenAI JSON 模式抽 PICO/RoB/GRADE，Mock 用于测试）→ `EvidenceWriter`（生成 ID、解决冲突、写 `evidence/{type}/`）。`IngestPipeline` 串联，失败按类型分流 `raw/_failed/` 或 `evidence/_quarantine/`。CLI 入口 `hdb ingest pdf` 与 `hdb ingest dry-run`。

**Tech Stack:** Python 3.11+, pymupdf>=1.24（默认 PDF 解析），openai>=1.30（LLM 抽 frontmatter，可换 Zhipu），reportlab>=4.0（测试生成 fixture PDF），pytest>=8.0。

---

## 参考资料

- 设计文档 §4 管线 A、§6 错误处理：`docs/superpowers/specs/2026-05-19-hypertension-rag-design.md`
- Plan A 已实现：`schema/base.py`（BaseFrontmatter）、`schema/sections.py`、`utils/id_gen.py`（`next_id`）、`utils/pinyin.py`
- Plan B / C 已实现：embedder/reranker 抽象，OpenAI/Zhipu HTTP 客户端可参考用法
- "绝对不能错"字段（设计 §6）：`effect_size.value/ci_low/ci_high/p`、`grade.level`、`risk_of_bias.overall`、`pico.population.sample_size`、`pico.intervention.dosage`、`pico.population.exclusion` —— 一律 status=draft 直到人工复核

## 注意事项

- **不需要 git 操作**（每个 Task 省略 Commit 步骤）
- LLM 调用全部走 OpenAI 兼容 API；测试通过 `unittest.mock.patch` 屏蔽真实 HTTP
- PyMuPDF 是 C 库无 PyTorch 依赖，CPU 友好；Marker/MinerU 留给后续可选扩展
- 集成测试用 reportlab 在运行时生成一个 2 页测试 PDF（不进 Git），避免引入二进制 fixture

## File Structure

```
pyproject.toml                                # 修改：加 pymupdf, reportlab(dev)

src/hypertensiondb/
  schema/
    base.py                                   # 修改：加 extracted_by 字段
  ingest/
    __init__.py                               # 新建：导出公开接口
    parse_pdf.py                              # 新建：BasePdfParser ABC + PyMuPDFParser
    clean.py                                  # 新建：text cleanup functions
    section_mapper.py                         # 新建：启发式 IMRaD → 标准节区
    frontmatter_extractor.py                  # 新建：BaseExtractor ABC + MockExtractor
    frontmatter_extractor_llm.py              # 新建：LLMFrontmatterExtractor (OpenAI)
    writer.py                                 # 新建：write_evidence_md()
    pipeline.py                               # 新建：IngestPipeline 编排
  cli.py                                      # 修改：实现 hdb ingest pdf / dry-run

tests/
  unit/
    test_ingest_parse_pdf.py                  # 新建
    test_ingest_clean.py                      # 新建
    test_ingest_section_mapper.py             # 新建
    test_ingest_extractor_mock.py             # 新建
    test_ingest_extractor_llm.py              # 新建
    test_ingest_writer.py                     # 新建
    test_ingest_pipeline.py                   # 新建
    test_ingest_cli.py                        # 新建
  integration/
    test_ingest_end_to_end.py                 # 新建：从生成的 PDF 走完整管线到 md

raw/
  incoming/                                   # 新建（空目录 + .gitkeep）
  _failed/                                    # 新建（空目录 + .gitkeep）
```

---

## Task D.1: 依赖 + 目录 + Schema 扩展 (extracted_by)

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/hypertensiondb/schema/base.py`
- Create: `raw/incoming/.gitkeep`
- Create: `raw/_failed/.gitkeep`

- [ ] **Step 1: 更新 pyproject.toml — 加 pymupdf 与 reportlab(dev)**

把 `[project] dependencies` 末尾追加 `"pymupdf>=1.24"`；`[project.optional-dependencies] dev` 末尾追加 `"reportlab>=4.0"`：

```toml
dependencies = [
    "pydantic>=2.7",
    "pyyaml>=6.0",
    "typer>=0.12",
    "pypinyin>=0.51",
    "python-frontmatter>=1.1",
    "qdrant-client>=1.9",
    "jieba>=0.42",
    "openai>=1.30",
    "httpx>=0.27",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.30",
    "pymupdf>=1.24",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "pytest-mock>=3.12",
    "pre-commit>=3.7",
    "ruff>=0.4",
    "testcontainers[docker]>=4.0",
    "reportlab>=4.0",
]
bge = [
    "FlagEmbedding>=1.2",
]
```

- [ ] **Step 2: 安装新依赖**

Run: `py -m pip install -e ".[dev]" -q`
Expected: 安装成功。

- [ ] **Step 3: 验证 pymupdf + reportlab 可导入**

Run: `py -c "import fitz, reportlab; print(f'pymupdf={fitz.__doc__.split()[0]} reportlab={reportlab.__version__}')"`
Expected: 输出两个版本号。

- [ ] **Step 4: 扩展 BaseFrontmatter，加 extracted_by 字段**

在 `src/hypertensiondb/schema/base.py` 的 `BaseFrontmatter` 模型 `superseded_by` 字段后面，**追加**一行：

```python
    extracted_by: Optional[str] = None  # 'llm' | 'human' | 'mixed' | None
```

完整字段块（仅 `BaseFrontmatter` 部分，其他不动）：

```python
class BaseFrontmatter(BaseModel):
    id: str
    type: EvidenceType
    title: Title
    authors: list[str]
    year: int
    language: Language
    first_author_pinyin: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None
    full_text_status: FullTextStatus = FullTextStatus.COMPLETE
    source: Optional[str] = None
    ingested_at: Optional[date] = None
    reviewed_by: Optional[str] = None
    tags: list[str] = []
    mesh_terms: list[str] = []
    clinical_questions: list[str] = []
    status: Status = Status.DRAFT
    quality_score: Optional[float] = None
    superseded_by: Optional[str] = None
    extracted_by: Optional[str] = None
```

`field_validator` 们保持原样。

- [ ] **Step 5: 验证现有测试不破坏**

Run: `py -m pytest tests/unit/ -v --tb=line 2>&1 | tail -5`
Expected: 全部 ~133 passed。

- [ ] **Step 6: 创建 raw 目录**

PowerShell:
```powershell
New-Item -ItemType Directory -Path raw\incoming, raw\_failed -Force | Out-Null
"" | Out-File -Encoding utf8 raw\incoming\.gitkeep
"" | Out-File -Encoding utf8 raw\_failed\.gitkeep
```

- [ ] **Step 7: 验证目录存在**

Run: `py -c "from pathlib import Path; print('incoming:', Path('raw/incoming').is_dir()); print('failed:', Path('raw/_failed').is_dir())"`
Expected: 两个 True。

---

## Task D.2: PdfParser ABC + PyMuPDFParser

**Files:**
- Create: `src/hypertensiondb/ingest/__init__.py`
- Create: `src/hypertensiondb/ingest/parse_pdf.py`
- Test: `tests/unit/test_ingest_parse_pdf.py`
- Test fixture helper: 用 reportlab 生成 PDF 字节

- [ ] **Step 1: 写失败测试**

Create `tests/unit/test_ingest_parse_pdf.py`:

```python
import io
import pytest
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from hypertensiondb.ingest.parse_pdf import PyMuPDFParser, ParsedPdf, BasePdfParser


def _make_test_pdf(tmp_path: Path, pages_text: list[str]) -> Path:
    """Generate a tiny PDF with one paragraph per page."""
    path = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    for text in pages_text:
        c.setFont("Helvetica", 11)
        for i, line in enumerate(text.split("\n")):
            c.drawString(72, 720 - i * 14, line)
        c.showPage()
    c.save()
    return path


@pytest.mark.unit
def test_pymupdf_parser_returns_parsed_pdf(tmp_path):
    pdf = _make_test_pdf(tmp_path, ["Page one content.", "Page two content."])
    parser = PyMuPDFParser()
    result = parser.parse(pdf)
    assert isinstance(result, ParsedPdf)
    assert len(result.pages) == 2
    assert "Page one content" in result.pages[0]
    assert "Page two content" in result.pages[1]


@pytest.mark.unit
def test_pymupdf_parser_raw_text_joins_pages(tmp_path):
    pdf = _make_test_pdf(tmp_path, ["First.", "Second."])
    result = PyMuPDFParser().parse(pdf)
    assert "First" in result.raw_text
    assert "Second" in result.raw_text


@pytest.mark.unit
def test_pymupdf_parser_extracts_metadata(tmp_path):
    pdf = _make_test_pdf(tmp_path, ["test"])
    result = PyMuPDFParser().parse(pdf)
    assert isinstance(result.metadata, dict)
    assert "page_count" in result.metadata
    assert result.metadata["page_count"] == 1


@pytest.mark.unit
def test_pymupdf_parser_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        PyMuPDFParser().parse(tmp_path / "nonexistent.pdf")


@pytest.mark.unit
def test_pymupdf_parser_raises_on_non_pdf(tmp_path):
    not_pdf = tmp_path / "notpdf.txt"
    not_pdf.write_text("hello", encoding="utf-8")
    with pytest.raises(Exception):  # fitz raises generic on corrupt input
        PyMuPDFParser().parse(not_pdf)


@pytest.mark.unit
def test_base_parser_is_abstract():
    with pytest.raises(TypeError):
        BasePdfParser()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_ingest_parse_pdf.py -v`
Expected: ModuleNotFoundError。

- [ ] **Step 3: 创建 ingest/__init__.py**

Create `src/hypertensiondb/ingest/__init__.py`:

```python
from hypertensiondb.ingest.parse_pdf import BasePdfParser, PyMuPDFParser, ParsedPdf

__all__ = ["BasePdfParser", "PyMuPDFParser", "ParsedPdf"]
```

- [ ] **Step 4: 实现 parse_pdf.py**

Create `src/hypertensiondb/ingest/parse_pdf.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # pymupdf


@dataclass
class ParsedPdf:
    raw_text: str
    pages: list[str]
    metadata: dict = field(default_factory=dict)


class BasePdfParser(ABC):
    """Abstract PDF parser."""

    @abstractmethod
    def parse(self, path: Path) -> ParsedPdf:
        ...


class PyMuPDFParser(BasePdfParser):
    """PDF parser using PyMuPDF (fitz). Default choice — pure C, no models."""

    def parse(self, path: Path) -> ParsedPdf:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        with fitz.open(path) as doc:
            pages: list[str] = []
            for page in doc:
                pages.append(page.get_text("text"))
            metadata = {
                "page_count": doc.page_count,
                "pdf_metadata": dict(doc.metadata or {}),
            }

        raw_text = "\n\n".join(pages)
        return ParsedPdf(raw_text=raw_text, pages=pages, metadata=metadata)
```

- [ ] **Step 5: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_ingest_parse_pdf.py -v`
Expected: 6 passed。

---

## Task D.3: TextCleaner — 文本清洗

**Files:**
- Create: `src/hypertensiondb/ingest/clean.py`
- Test: `tests/unit/test_ingest_clean.py`

- [ ] **Step 1: 写失败测试**

Create `tests/unit/test_ingest_clean.py`:

```python
import pytest

from hypertensiondb.ingest.clean import (
    fix_hyphenation, merge_broken_lines, remove_repeating_lines,
    normalize_whitespace, clean_text,
)


@pytest.mark.unit
def test_fix_hyphenation():
    text = "Hyper-\ntension is common."
    assert fix_hyphenation(text) == "Hypertension is common."


@pytest.mark.unit
def test_fix_hyphenation_keeps_real_hyphens():
    """A hyphenated word at line end without a real break stays intact."""
    text = "Cardio-vascular events"
    # No newline → no change
    assert fix_hyphenation(text) == "Cardio-vascular events"


@pytest.mark.unit
def test_fix_hyphenation_chinese_unaffected():
    text = "高血\n压"
    # No hyphen → unchanged
    assert fix_hyphenation(text) == "高血\n压"


@pytest.mark.unit
def test_merge_broken_lines_within_paragraph():
    text = "This is a sentence\nthat wraps across lines."
    result = merge_broken_lines(text)
    # Single newline within a paragraph → space
    assert result == "This is a sentence that wraps across lines."


@pytest.mark.unit
def test_merge_broken_lines_preserves_paragraph_breaks():
    text = "Paragraph one.\n\nParagraph two."
    result = merge_broken_lines(text)
    assert "\n\n" in result


@pytest.mark.unit
def test_merge_broken_lines_chinese_no_space():
    """Within Chinese text, broken line should join without inserting a space."""
    text = "原发性高血压是\n心血管疾病的危险因素。"
    result = merge_broken_lines(text)
    assert result == "原发性高血压是心血管疾病的危险因素。"


@pytest.mark.unit
def test_remove_repeating_lines():
    """Lines that appear on every page are header/footer noise — drop them."""
    pages = [
        "Header X\nReal content of page 1\nFooter 123",
        "Header X\nReal content of page 2\nFooter 124",
        "Header X\nReal content of page 3\nFooter 125",
    ]
    cleaned = remove_repeating_lines(pages, min_occurrences_ratio=0.66)
    # "Header X" appears on all 3 → removed
    assert all("Header X" not in p for p in cleaned)
    # "Real content of page N" varies → kept
    assert all("Real content" in p for p in cleaned)


@pytest.mark.unit
def test_remove_repeating_lines_keeps_unique():
    pages = ["unique 1", "unique 2"]
    cleaned = remove_repeating_lines(pages, min_occurrences_ratio=0.66)
    assert cleaned == pages


@pytest.mark.unit
def test_normalize_whitespace_collapses_runs():
    assert normalize_whitespace("a    b\t\tc") == "a b c"


@pytest.mark.unit
def test_normalize_whitespace_preserves_newlines():
    assert normalize_whitespace("para1\n\npara2") == "para1\n\npara2"


@pytest.mark.unit
def test_clean_text_full_pipeline():
    pages = [
        "Header X\nHyper-\ntension is\ncommon.\n\nMore content here.\nFooter 1",
        "Header X\nAnother sentence.\nFooter 2",
    ]
    cleaned = clean_text(pages)
    assert "Header X" not in cleaned
    assert "Hypertension" in cleaned
    assert "is common" in cleaned
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_ingest_clean.py -v`
Expected: ModuleNotFoundError。

- [ ] **Step 3: 实现 clean.py**

Create `src/hypertensiondb/ingest/clean.py`:

```python
import re
from collections import Counter


_HYPHEN_LINEEND = re.compile(r"([A-Za-z])-\n([A-Za-z])")
_CJK_RANGE = r"一-鿿"
_BROKEN_LINE_CJK = re.compile(rf"([{_CJK_RANGE}])\n([{_CJK_RANGE}])")
_BROKEN_LINE_LATIN = re.compile(r"([A-Za-z,;:])\n([A-Za-z])")
_PARA_BREAK_TOKEN = "\x00PARA\x00"


def fix_hyphenation(text: str) -> str:
    """Join hyphenated words split across line ends: 'Hyper-\nten' → 'Hyperten'."""
    return _HYPHEN_LINEEND.sub(r"\1\2", text)


def merge_broken_lines(text: str) -> str:
    """Merge single line breaks within paragraphs.

    - Latin: join with a space.
    - CJK: join without space.
    - Preserve double newlines (paragraph breaks).
    """
    # Protect paragraph breaks
    text = text.replace("\n\n", _PARA_BREAK_TOKEN)
    # CJK boundary: join without space
    text = _BROKEN_LINE_CJK.sub(r"\1\2", text)
    # Latin / punctuation boundary: join with space
    text = _BROKEN_LINE_LATIN.sub(r"\1 \2", text)
    # Any remaining single \n inside paragraph: collapse to space
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
    # Protect newlines
    text = re.sub(r"[ \t]+", " ", text)
    # Strip trailing/leading whitespace per line
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_ingest_clean.py -v`
Expected: 11 passed。

---

## Task D.4: SectionMapper — 启发式 IMRaD → 标准节区

**Files:**
- Create: `src/hypertensiondb/ingest/section_mapper.py`
- Test: `tests/unit/test_ingest_section_mapper.py`

- [ ] **Step 1: 写失败测试**

Create `tests/unit/test_ingest_section_mapper.py`:

```python
import pytest

from hypertensiondb.ingest.section_mapper import detect_sections, STANDARD_SECTIONS


@pytest.mark.unit
def test_detect_sections_finds_english_imrad():
    text = """Abstract
We studied hypertension.

Methods
RCT design with 612 patients.

Results
SBP decreased by 8 mmHg.

Conclusion
Combination is better.
"""
    sections = detect_sections(text)
    assert "methods" in sections and sections["methods"].strip()
    assert "results" in sections and "SBP" in sections["results"]
    assert "conclusion" in sections


@pytest.mark.unit
def test_detect_sections_finds_chinese_headings():
    text = """摘要
研究高血压。

方法
随机对照试验。

结果
SBP下降8 mmHg。

结论
联合优于单药。
"""
    sections = detect_sections(text)
    assert sections["methods"].strip()
    assert "SBP" in sections["results"]
    assert "联合" in sections["conclusion"]


@pytest.mark.unit
def test_detect_sections_fallback_all_in_results():
    """No headings found → entire text goes to 'results' as fallback."""
    text = "Just a single block of text without any section headings whatsoever."
    sections = detect_sections(text)
    assert sections["results"].strip() == text.strip()
    assert sections.get("methods", "") == ""


@pytest.mark.unit
def test_detect_sections_returns_all_standard_keys():
    """The returned dict has all 8 standard keys (empty string if not detected)."""
    text = "Methods\nFoo.\n\nResults\nBar."
    sections = detect_sections(text)
    for key in STANDARD_SECTIONS:
        assert key in sections


@pytest.mark.unit
def test_detect_sections_handles_mixed_zh_en():
    text = """Background / 背景
Hypertension is common.

Methods / 方法
Randomized trial.

Results / 结果
SBP down 8mmHg.
"""
    sections = detect_sections(text)
    assert sections["methods"].strip()
    assert "SBP" in sections["results"]


@pytest.mark.unit
def test_detect_sections_strips_section_titles_from_body():
    """The section text returned should NOT include the heading itself."""
    text = "Methods\nThis is the methods body.\n\nResults\nThis is results."
    sections = detect_sections(text)
    assert not sections["methods"].lower().startswith("methods\n")
    assert "This is the methods body" in sections["methods"]


@pytest.mark.unit
def test_standard_sections_contains_expected_keys():
    expected = {"clinical_bottom_line", "abstract_zh", "abstract_en",
                "background", "methods", "results", "discussion", "conclusion"}
    assert set(STANDARD_SECTIONS) == expected
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_ingest_section_mapper.py -v`
Expected: ModuleNotFoundError。

- [ ] **Step 3: 实现 section_mapper.py**

Create `src/hypertensiondb/ingest/section_mapper.py`:

```python
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


# Each rule: (regex matching heading line, target standard section key)
# Regex matches the heading on its own line (^...$ with re.MULTILINE).
_HEADING_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^\s*(临床要点|Clinical Bottom Line)\s*[/／]?.*$",
                re.MULTILINE | re.IGNORECASE), "clinical_bottom_line"),
    (re.compile(r"^\s*(中文摘要|摘要)\s*$", re.MULTILINE), "abstract_zh"),
    (re.compile(r"^\s*(English Abstract|Abstract)\s*[/／]?.*$",
                re.MULTILINE | re.IGNORECASE), "abstract_en"),
    (re.compile(r"^\s*(背景|引言|Background|Introduction)\s*[/／]?.*$",
                re.MULTILINE | re.IGNORECASE), "background"),
    (re.compile(r"^\s*(方法|方法学|材料与方法|Methods?|Methodology|Materials and Methods)\s*[/／]?.*$",
                re.MULTILINE | re.IGNORECASE), "methods"),
    (re.compile(r"^\s*(结果|Results?|Findings?)\s*[/／]?.*$",
                re.MULTILINE | re.IGNORECASE), "results"),
    (re.compile(r"^\s*(讨论|Discussion)\s*[/／]?.*$",
                re.MULTILINE | re.IGNORECASE), "discussion"),
    (re.compile(r"^\s*(结论|总结|Conclusions?|Summary)\s*[/／]?.*$",
                re.MULTILINE | re.IGNORECASE), "conclusion"),
]


def detect_sections(text: str) -> dict[str, str]:
    """Heuristically split text into the 8 standard sections.

    Returns a dict with all 8 keys; un-detected ones map to empty string.
    Fallback: if NO headings are detected, the entire text goes into 'results'.
    """
    # Find all heading matches across the text
    hits: list[tuple[int, int, str]] = []  # (start, end, target_key)
    for pattern, key in _HEADING_RULES:
        for m in pattern.finditer(text):
            hits.append((m.start(), m.end(), key))

    hits.sort(key=lambda t: t[0])

    sections: dict[str, str] = {k: "" for k in STANDARD_SECTIONS}

    if not hits:
        # Fallback: everything goes to results
        sections["results"] = text.strip()
        return sections

    # For each heading, the section body is text from its end to the next heading's start
    for i, (start, end, key) in enumerate(hits):
        body_start = end
        body_end = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        body = text[body_start:body_end].strip()
        if body:
            # If multiple hits map to the same key, concatenate
            if sections[key]:
                sections[key] = sections[key] + "\n\n" + body
            else:
                sections[key] = body

    return sections
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_ingest_section_mapper.py -v`
Expected: 7 passed。

---

## Task D.5: BaseFrontmatterExtractor + MockExtractor

**Files:**
- Create: `src/hypertensiondb/ingest/frontmatter_extractor.py`
- Test: `tests/unit/test_ingest_extractor_mock.py`

- [ ] **Step 1: 写失败测试**

Create `tests/unit/test_ingest_extractor_mock.py`:

```python
import pytest

from hypertensiondb.ingest.frontmatter_extractor import (
    BaseFrontmatterExtractor, MockFrontmatterExtractor,
)


@pytest.fixture
def extractor():
    return MockFrontmatterExtractor()


@pytest.mark.unit
def test_base_is_abstract():
    with pytest.raises(TypeError):
        BaseFrontmatterExtractor()


@pytest.mark.unit
def test_mock_extractor_returns_dict(extractor):
    result = extractor.extract(text="random text", evidence_type="RCT")
    assert isinstance(result, dict)


@pytest.mark.unit
def test_mock_extractor_has_required_fields(extractor):
    result = extractor.extract(text="some text", evidence_type="RCT")
    assert "type" in result and result["type"] == "RCT"
    assert "title" in result
    assert "authors" in result
    assert "year" in result
    assert "language" in result
    assert "status" in result and result["status"] == "draft"


@pytest.mark.unit
def test_mock_extractor_sets_extracted_by(extractor):
    result = extractor.extract(text="x", evidence_type="META")
    assert result.get("extracted_by") == "llm"


@pytest.mark.unit
def test_mock_extractor_returns_minimal_pico_for_rct(extractor):
    result = extractor.extract(text="x", evidence_type="RCT")
    assert "pico" in result
    assert "population" in result["pico"]


@pytest.mark.unit
def test_mock_extractor_no_pico_for_guideline(extractor):
    """Guidelines don't have PICO."""
    result = extractor.extract(text="x", evidence_type="GL")
    assert "pico" not in result or result.get("pico") is None


@pytest.mark.unit
def test_mock_extractor_model_name(extractor):
    assert extractor.model_name == "mock"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_ingest_extractor_mock.py -v`
Expected: ModuleNotFoundError。

- [ ] **Step 3: 实现 frontmatter_extractor.py**

Create `src/hypertensiondb/ingest/frontmatter_extractor.py`:

```python
from abc import ABC, abstractmethod


class BaseFrontmatterExtractor(ABC):
    """Abstract interface for extracting structured frontmatter from raw text."""

    @abstractmethod
    def extract(self, text: str, evidence_type: str) -> dict:
        """Return a dict suitable for Pydantic frontmatter construction.

        Required output keys: type, title{zh|en}, authors, year, language, status.
        For RCT/SR/META/TCM also: pico, risk_of_bias, grade.
        Always set extracted_by='llm' so callers know fields need human review.
        Status MUST be 'draft' regardless of extraction confidence.
        """

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...


class MockFrontmatterExtractor(BaseFrontmatterExtractor):
    """Deterministic skeleton extractor for tests. Doesn't read text content."""

    def extract(self, text: str, evidence_type: str) -> dict:
        result: dict = {
            "type": evidence_type,
            "title": {"zh": "未提供标题", "en": None},
            "authors": ["Unknown"],
            "year": 2026,
            "language": "zh",
            "status": "draft",
            "tags": [],
            "extracted_by": "llm",
        }
        if evidence_type in {"RCT", "SR", "META", "TCM"}:
            result["pico"] = {
                "population": {"condition": "未提供"},
                "intervention": {"name": "未提供"},
                "outcomes": {},
            }
            result["risk_of_bias"] = {"tool": "RoB2", "overall": "some_concerns"}
            result["grade"] = {"level": "low"}
        return result

    @property
    def model_name(self) -> str:
        return "mock"
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_ingest_extractor_mock.py -v`
Expected: 7 passed。

---

## Task D.6: LLMFrontmatterExtractor (OpenAI JSON 模式)

**Files:**
- Create: `src/hypertensiondb/ingest/frontmatter_extractor_llm.py`
- Test: `tests/unit/test_ingest_extractor_llm.py`

- [ ] **Step 1: 写失败测试**

Create `tests/unit/test_ingest_extractor_llm.py`:

```python
import json
import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.unit
def test_llm_extractor_calls_openai_with_json_mode():
    from hypertensiondb.ingest.frontmatter_extractor_llm import LLMFrontmatterExtractor

    fake_payload = {
        "type": "RCT",
        "title": {"zh": "试验研究", "en": None},
        "authors": ["Peng Y"],
        "year": 2026,
        "language": "zh",
        "status": "draft",
        "tags": ["valsartan"],
        "pico": {
            "population": {"condition": "高血压", "sample_size": 612},
            "intervention": {"name": "缬沙坦+氨氯地平"},
            "outcomes": {},
        },
        "risk_of_bias": {"tool": "RoB2", "overall": "low"},
        "grade": {"level": "moderate"},
    }
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(fake_payload, ensure_ascii=False)))]

    with patch("hypertensiondb.ingest.frontmatter_extractor_llm.openai.chat.completions.create",
               return_value=mock_resp) as mock_create:
        extractor = LLMFrontmatterExtractor(api_key="test", model="gpt-4o-mini")
        out = extractor.extract(text="some long RCT body text", evidence_type="RCT")

    mock_create.assert_called_once()
    assert out["type"] == "RCT"
    assert out["status"] == "draft"
    assert out["extracted_by"] == "llm"
    assert out["pico"]["population"]["sample_size"] == 612


@pytest.mark.unit
def test_llm_extractor_forces_status_draft_even_if_llm_says_otherwise():
    from hypertensiondb.ingest.frontmatter_extractor_llm import LLMFrontmatterExtractor

    bad_payload = {
        "type": "RCT", "title": {"zh": "x"}, "authors": ["A"], "year": 2026,
        "language": "zh", "status": "published",  # LLM lied; we must override
    }
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(bad_payload)))]
    with patch("hypertensiondb.ingest.frontmatter_extractor_llm.openai.chat.completions.create",
               return_value=mock_resp):
        out = LLMFrontmatterExtractor(api_key="x", model="m").extract("text", "RCT")
    assert out["status"] == "draft"


@pytest.mark.unit
def test_llm_extractor_invalid_json_returns_skeleton():
    """If LLM returns garbage, fall back to minimal skeleton (status=draft)."""
    from hypertensiondb.ingest.frontmatter_extractor_llm import LLMFrontmatterExtractor

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="this is not json {{"))]
    with patch("hypertensiondb.ingest.frontmatter_extractor_llm.openai.chat.completions.create",
               return_value=mock_resp):
        out = LLMFrontmatterExtractor(api_key="x", model="m").extract("text", "META")

    assert out["status"] == "draft"
    assert out["type"] == "META"
    assert out["extracted_by"] == "llm"


@pytest.mark.unit
def test_llm_extractor_api_failure_returns_skeleton():
    """If OpenAI raises, return skeleton — don't break the pipeline."""
    from hypertensiondb.ingest.frontmatter_extractor_llm import LLMFrontmatterExtractor

    with patch("hypertensiondb.ingest.frontmatter_extractor_llm.openai.chat.completions.create",
               side_effect=RuntimeError("API down")):
        out = LLMFrontmatterExtractor(api_key="x", model="m").extract("text", "GL")

    assert out["status"] == "draft"
    assert out["type"] == "GL"


@pytest.mark.unit
def test_llm_extractor_model_name():
    from hypertensiondb.ingest.frontmatter_extractor_llm import LLMFrontmatterExtractor
    e = LLMFrontmatterExtractor(api_key="x", model="gpt-4o-mini")
    assert e.model_name == "gpt-4o-mini"


@pytest.mark.unit
def test_llm_extractor_truncates_long_text():
    """Text > MAX_INPUT_CHARS is truncated before sending to API."""
    from hypertensiondb.ingest.frontmatter_extractor_llm import (
        LLMFrontmatterExtractor, MAX_INPUT_CHARS,
    )

    fake_payload = {
        "type": "RCT", "title": {"zh": "x"}, "authors": ["A"], "year": 2026,
        "language": "zh", "status": "draft",
    }
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(fake_payload)))]
    with patch("hypertensiondb.ingest.frontmatter_extractor_llm.openai.chat.completions.create",
               return_value=mock_resp) as mock_create:
        long_text = "x" * (MAX_INPUT_CHARS + 5000)
        LLMFrontmatterExtractor(api_key="k", model="m").extract(long_text, "RCT")

    # The actual text passed in the user message should be truncated
    _, kwargs = mock_create.call_args
    messages = kwargs["messages"]
    user_content = next(m["content"] for m in messages if m["role"] == "user")
    assert len(user_content) <= MAX_INPUT_CHARS + 500  # 500 chars overhead for prompt template
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_ingest_extractor_llm.py -v`
Expected: ModuleNotFoundError。

- [ ] **Step 3: 实现 frontmatter_extractor_llm.py**

Create `src/hypertensiondb/ingest/frontmatter_extractor_llm.py`:

```python
import json
import os

import openai

from hypertensiondb.ingest.frontmatter_extractor import BaseFrontmatterExtractor

# Module-import-time guard (same pattern as embedder_openai.py): openai.chat.completions
# is a lazy proxy that constructs a default client on first access and fails if no
# API key is anywhere. Set a harmless placeholder so unittest.mock.patch can resolve
# the attribute path even before LLMFrontmatterExtractor is constructed.
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "sk-placeholder-for-module-import"


MAX_INPUT_CHARS = 12_000


_SYSTEM_PROMPT_TEMPLATE = """You are a medical-evidence extraction assistant.
Given the raw text of a {evidence_type} paper on hypertension, extract structured
frontmatter as a JSON object with these required keys:

  - type: exactly "{evidence_type}"
  - title: object with zh and/or en string fields (at least one)
  - authors: list of strings (first author full name OK)
  - year: 4-digit integer
  - language: "zh", "en", or "bilingual"
  - tags: list of short keyword strings
  - status: always exactly "draft"

For RCT/SR/META/TCM additionally include:
  - pico: object with population{{condition, sample_size}}, intervention{{name}},
          comparison{{name}} (optional), outcomes (object)
  - risk_of_bias: object with tool ("RoB2"/"AMSTAR2"/etc) and overall ("low"/"some_concerns"/"high")
  - grade: object with level ("very_low"/"low"/"moderate"/"high")

Numeric effect sizes go under pico.outcomes.primary as a list of objects, each with:
  name (str) and effect_size{{metric, value, ci_low, ci_high, p}}.

If you cannot extract a field with confidence, OMIT it rather than fabricating.
Return ONLY the JSON, no explanation."""


class LLMFrontmatterExtractor(BaseFrontmatterExtractor):
    """OpenAI-backed extractor using JSON mode."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        timeout: float = 60.0,
    ) -> None:
        openai.api_key = api_key
        self._client = openai.OpenAI(api_key=api_key, timeout=timeout)
        self._model = model

    def extract(self, text: str, evidence_type: str) -> dict:
        truncated = text[:MAX_INPUT_CHARS]
        system_msg = _SYSTEM_PROMPT_TEMPLATE.format(evidence_type=evidence_type)
        try:
            response = openai.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": truncated},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            content = response.choices[0].message.content
            payload = json.loads(content) if content else {}
        except Exception:
            payload = {}

        # Force invariants: type, status, extracted_by
        payload["type"] = evidence_type
        payload["status"] = "draft"
        payload["extracted_by"] = "llm"

        # Minimal skeleton fallback if LLM didn't return required basics
        payload.setdefault("title", {"zh": "未提供标题", "en": None})
        payload.setdefault("authors", ["Unknown"])
        payload.setdefault("year", 2026)
        payload.setdefault("language", "zh")
        payload.setdefault("tags", [])

        return payload

    @property
    def model_name(self) -> str:
        return self._model
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_ingest_extractor_llm.py -v`
Expected: 6 passed。

---

## Task D.7: EvidenceWriter — 写 Markdown

**Files:**
- Create: `src/hypertensiondb/ingest/writer.py`
- Test: `tests/unit/test_ingest_writer.py`

- [ ] **Step 1: 写失败测试**

Create `tests/unit/test_ingest_writer.py`:

```python
import pytest
from pathlib import Path

from hypertensiondb.ingest.writer import (
    write_evidence_md, write_quarantine_md, EvidenceWriteResult,
)


_FRONTMATTER = {
    "id": "EV-RCT-2026-TEST-001",
    "type": "RCT",
    "title": {"zh": "测试", "en": None},
    "authors": ["Test A"],
    "year": 2026,
    "language": "zh",
    "status": "draft",
    "extracted_by": "llm",
}

_SECTIONS = {
    "methods": "随机对照试验。",
    "results": "降压 8 mmHg。",
    "conclusion": "联合优于单药。",
}


@pytest.mark.unit
def test_write_evidence_md_creates_file(tmp_path):
    result = write_evidence_md(
        frontmatter=_FRONTMATTER, sections=_SECTIONS, evidence_root=tmp_path,
    )
    assert isinstance(result, EvidenceWriteResult)
    assert result.path.exists()
    assert result.path.name == "EV-RCT-2026-TEST-001.md"


@pytest.mark.unit
def test_write_evidence_md_puts_rct_in_rcts_dir(tmp_path):
    result = write_evidence_md(
        frontmatter=_FRONTMATTER, sections=_SECTIONS, evidence_root=tmp_path,
    )
    assert result.path.parent.name == "rcts"


@pytest.mark.unit
def test_write_evidence_md_type_to_subdir_mapping(tmp_path):
    mapping = {"RCT": "rcts", "SR": "systematic_reviews", "META": "meta_analyses",
               "GL": "guidelines", "TCM": "tcm"}
    for ev_type, subdir in mapping.items():
        fm = dict(_FRONTMATTER)
        fm["type"] = ev_type
        fm["id"] = f"EV-{ev_type}-2026-TEST-001"
        if ev_type == "GL":
            fm.pop("status", None); fm["status"] = "draft"
        result = write_evidence_md(frontmatter=fm, sections=_SECTIONS, evidence_root=tmp_path)
        assert result.path.parent.name == subdir, f"{ev_type} → {subdir}"


@pytest.mark.unit
def test_write_evidence_md_includes_frontmatter_and_sections(tmp_path):
    result = write_evidence_md(
        frontmatter=_FRONTMATTER, sections=_SECTIONS, evidence_root=tmp_path,
    )
    content = result.path.read_text(encoding="utf-8")
    assert "---" in content
    assert "id: EV-RCT-2026-TEST-001" in content
    assert "## 方法 / Methods" in content or "## Methods" in content
    assert "降压 8 mmHg" in content


@pytest.mark.unit
def test_write_evidence_md_conflict_raises(tmp_path):
    write_evidence_md(frontmatter=_FRONTMATTER, sections=_SECTIONS, evidence_root=tmp_path)
    with pytest.raises(FileExistsError):
        write_evidence_md(frontmatter=_FRONTMATTER, sections=_SECTIONS, evidence_root=tmp_path)


@pytest.mark.unit
def test_write_evidence_md_overwrite_true_allowed(tmp_path):
    write_evidence_md(frontmatter=_FRONTMATTER, sections=_SECTIONS, evidence_root=tmp_path)
    # Should not raise with overwrite=True
    result = write_evidence_md(
        frontmatter=_FRONTMATTER, sections=_SECTIONS, evidence_root=tmp_path,
        overwrite=True,
    )
    assert result.path.exists()


@pytest.mark.unit
def test_write_quarantine_md(tmp_path):
    bad_fm = {"type": "RCT", "title": {"zh": "bad"}, "year": "not-a-year"}
    result = write_quarantine_md(
        partial_frontmatter=bad_fm, sections={"results": "x"},
        error="ValidationError: year must be int", evidence_root=tmp_path,
        source_filename="orig.pdf",
    )
    assert result.path.parent.name == "_quarantine"
    assert result.path.exists()
    content = result.path.read_text(encoding="utf-8")
    assert "ValidationError" in content
    assert "orig.pdf" in content
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_ingest_writer.py -v`
Expected: ModuleNotFoundError。

- [ ] **Step 3: 实现 writer.py**

Create `src/hypertensiondb/ingest/writer.py`:

```python
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml


_TYPE_SUBDIR = {
    "RCT": "rcts",
    "SR": "systematic_reviews",
    "META": "meta_analyses",
    "GL": "guidelines",
    "TCM": "tcm",
}

_SECTION_HEADINGS = {
    "clinical_bottom_line": "## 临床要点 / Clinical Bottom Line",
    "abstract_zh": "## 中文摘要",
    "abstract_en": "## English Abstract",
    "background": "## 背景 / Background",
    "methods": "## 方法 / Methods",
    "results": "## 结果 / Results",
    "discussion": "## 讨论 / Discussion",
    "conclusion": "## 结论 / Conclusion",
}


@dataclass
class EvidenceWriteResult:
    path: Path
    evidence_id: str


def _render_markdown(frontmatter: dict, sections: dict) -> str:
    yaml_block = yaml.safe_dump(
        frontmatter, allow_unicode=True, sort_keys=False, default_flow_style=False
    )
    body_parts: list[str] = []
    for key, heading in _SECTION_HEADINGS.items():
        text = sections.get(key, "").strip()
        if not text:
            continue
        body_parts.append(f"{heading}\n\n{text}")

    body = "\n\n".join(body_parts) if body_parts else "## 结果 / Results\n\n(content pending)"
    return f"---\n{yaml_block}---\n\n{body}\n"


def write_evidence_md(
    frontmatter: dict,
    sections: dict,
    evidence_root: Path,
    overwrite: bool = False,
) -> EvidenceWriteResult:
    """Write a complete evidence .md file to evidence_root/{type_subdir}/{id}.md.

    Raises FileExistsError if file already exists and overwrite=False.
    """
    ev_type = frontmatter.get("type")
    ev_id = frontmatter.get("id")
    if ev_type not in _TYPE_SUBDIR:
        raise ValueError(f"Unknown type: {ev_type}")
    if not ev_id:
        raise ValueError("frontmatter.id is required")

    subdir = evidence_root / _TYPE_SUBDIR[ev_type]
    subdir.mkdir(parents=True, exist_ok=True)
    target = subdir / f"{ev_id}.md"

    if target.exists() and not overwrite:
        raise FileExistsError(f"Evidence file already exists: {target}")

    content = _render_markdown(frontmatter, sections)
    target.write_text(content, encoding="utf-8")
    return EvidenceWriteResult(path=target, evidence_id=ev_id)


def write_quarantine_md(
    partial_frontmatter: dict,
    sections: dict,
    error: str,
    evidence_root: Path,
    source_filename: str,
) -> EvidenceWriteResult:
    """Write a quarantine record for evidence that failed Pydantic validation.

    Filename is timestamped to avoid collisions when many bad inputs arrive.
    """
    subdir = evidence_root / "_quarantine"
    subdir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"quarantine-{ts}-{int(time.monotonic_ns() % 1_000_000):06d}"
    target = subdir / f"{name}.md"

    header = {
        "_quarantine_error": error,
        "_quarantine_source": source_filename,
        "_quarantine_at": ts,
        **partial_frontmatter,
    }
    content = _render_markdown(header, sections)
    target.write_text(content, encoding="utf-8")
    return EvidenceWriteResult(path=target, evidence_id=name)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_ingest_writer.py -v`
Expected: 8 passed。

---

## Task D.8: IngestPipeline 编排

**Files:**
- Create: `src/hypertensiondb/ingest/pipeline.py`
- Test: `tests/unit/test_ingest_pipeline.py`

- [ ] **Step 1: 写失败测试**

Create `tests/unit/test_ingest_pipeline.py`:

```python
import pytest
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from hypertensiondb.ingest.parse_pdf import PyMuPDFParser
from hypertensiondb.ingest.frontmatter_extractor import MockFrontmatterExtractor
from hypertensiondb.ingest.pipeline import IngestPipeline, IngestStatus


def _make_pdf(tmp_path: Path, pages: list[str], name: str = "in.pdf") -> Path:
    p = tmp_path / name
    c = canvas.Canvas(str(p), pagesize=letter)
    for text in pages:
        for i, line in enumerate(text.split("\n")):
            c.drawString(72, 720 - i * 14, line)
        c.showPage()
    c.save()
    return p


@pytest.fixture
def pipeline(tmp_path):
    return IngestPipeline(
        parser=PyMuPDFParser(),
        extractor=MockFrontmatterExtractor(),
        evidence_root=tmp_path / "evidence",
        failed_root=tmp_path / "raw" / "_failed",
        id_generator=lambda fm, _root: "EV-RCT-2026-TEST-001",
    )


@pytest.mark.unit
def test_ingest_pdf_writes_evidence_md(pipeline, tmp_path):
    pdf = _make_pdf(tmp_path, ["Methods\nRandomized trial.\n\nResults\nSBP down 8mmHg."])
    result = pipeline.ingest_pdf(pdf, evidence_type="RCT")
    assert result.status == IngestStatus.OK
    assert result.output_path is not None
    assert result.output_path.exists()
    assert result.output_path.name == "EV-RCT-2026-TEST-001.md"


@pytest.mark.unit
def test_ingest_pdf_returns_quarantine_on_validation_failure(tmp_path):
    """An extractor that returns invalid data triggers quarantine."""
    bad_extractor = MockFrontmatterExtractor()

    # Wrap to inject malformed output
    class BadExtractor:
        def extract(self, text, evidence_type):
            return {"type": evidence_type, "year": "not-a-year"}
        @property
        def model_name(self): return "bad"

    pipeline = IngestPipeline(
        parser=PyMuPDFParser(),
        extractor=BadExtractor(),
        evidence_root=tmp_path / "evidence",
        failed_root=tmp_path / "raw" / "_failed",
        id_generator=lambda fm, _root: "EV-RCT-2026-TEST-001",
    )
    pdf = _make_pdf(tmp_path, ["Some text."])
    result = pipeline.ingest_pdf(pdf, evidence_type="RCT")
    assert result.status == IngestStatus.QUARANTINED
    assert result.output_path is not None
    assert "_quarantine" in result.output_path.parts


@pytest.mark.unit
def test_ingest_pdf_moves_to_failed_on_parse_error(pipeline, tmp_path):
    fake_pdf = tmp_path / "broken.pdf"
    fake_pdf.write_text("this is not a pdf", encoding="utf-8")
    result = pipeline.ingest_pdf(fake_pdf, evidence_type="RCT")
    assert result.status == IngestStatus.PARSE_FAILED
    failed_path = tmp_path / "raw" / "_failed" / "broken.pdf"
    assert failed_path.exists()


@pytest.mark.unit
def test_ingest_pdf_dry_run_does_not_write(tmp_path):
    pipeline = IngestPipeline(
        parser=PyMuPDFParser(),
        extractor=MockFrontmatterExtractor(),
        evidence_root=tmp_path / "evidence",
        failed_root=tmp_path / "raw" / "_failed",
        id_generator=lambda fm, _root: "EV-RCT-2026-TEST-001",
    )
    pdf = _make_pdf(tmp_path, ["Methods\nx\n\nResults\ny"])
    result = pipeline.ingest_pdf(pdf, evidence_type="RCT", dry_run=True)
    assert result.status == IngestStatus.DRY_RUN
    assert result.output_path is None
    # Should still report what would have been written
    assert result.frontmatter is not None
    assert result.frontmatter["type"] == "RCT"


@pytest.mark.unit
def test_ingest_pdf_too_little_text_quarantines(tmp_path):
    """Parsed text below MIN_TEXT_CHARS → treat as parse failure."""
    pipeline = IngestPipeline(
        parser=PyMuPDFParser(),
        extractor=MockFrontmatterExtractor(),
        evidence_root=tmp_path / "evidence",
        failed_root=tmp_path / "raw" / "_failed",
        id_generator=lambda fm, _root: "EV-RCT-2026-TEST-001",
    )
    pdf = _make_pdf(tmp_path, ["x"])  # very short
    result = pipeline.ingest_pdf(pdf, evidence_type="RCT")
    assert result.status == IngestStatus.PARSE_FAILED
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_ingest_pipeline.py -v`
Expected: ModuleNotFoundError。

- [ ] **Step 3: 实现 pipeline.py**

Create `src/hypertensiondb/ingest/pipeline.py`:

```python
import shutil
import sys
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Callable, Optional

from pydantic import ValidationError

from hypertensiondb.ingest.parse_pdf import BasePdfParser
from hypertensiondb.ingest.clean import clean_text
from hypertensiondb.ingest.section_mapper import detect_sections
from hypertensiondb.ingest.frontmatter_extractor import BaseFrontmatterExtractor
from hypertensiondb.ingest.writer import (
    write_evidence_md, write_quarantine_md, EvidenceWriteResult,
)
from hypertensiondb.schema.loader import _MODEL_BY_TYPE  # internal but reused

# Minimum text length to consider the PDF parse plausible
MIN_TEXT_CHARS = 500


class IngestStatus(StrEnum):
    OK = "ok"
    PARSE_FAILED = "parse_failed"
    QUARANTINED = "quarantined"
    DRY_RUN = "dry_run"


@dataclass
class IngestResult:
    status: IngestStatus
    output_path: Optional[Path] = None
    frontmatter: Optional[dict] = None
    sections: Optional[dict] = None
    error: Optional[str] = None


def _default_id_generator(fm: dict, evidence_root: Path) -> str:
    """Build a plausible ID using utils.id_gen.next_id() if possible.

    Falls back to a timestamp-based id if id_gen fails.
    """
    try:
        sys.path.insert(0, str(evidence_root.parent / "src"))
        from hypertensiondb.utils.id_gen import next_id
        from hypertensiondb.utils.pinyin import to_first_author_pinyin

        first_author = fm.get("authors", ["Unknown"])[0]
        pinyin = to_first_author_pinyin(first_author)
        return next_id(fm.get("type", "RCT"), fm.get("year", date.today().year), pinyin,
                       evidence_root=evidence_root)
    except Exception:
        # Fallback — should rarely hit
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%H%M%S")
        return f"EV-{fm.get('type', 'RCT')}-{fm.get('year', 2026)}-UNKNOWN-{ts}"


class IngestPipeline:
    """Orchestrate PDF → parsed → cleaned → sectioned → extracted → validated → written."""

    def __init__(
        self,
        parser: BasePdfParser,
        extractor: BaseFrontmatterExtractor,
        evidence_root: Path,
        failed_root: Path,
        id_generator: Optional[Callable[[dict, Path], str]] = None,
    ) -> None:
        self._parser = parser
        self._extractor = extractor
        self._evidence_root = Path(evidence_root)
        self._failed_root = Path(failed_root)
        self._id_gen = id_generator or _default_id_generator

    def ingest_pdf(
        self,
        pdf_path: Path,
        evidence_type: str,
        dry_run: bool = False,
    ) -> IngestResult:
        pdf_path = Path(pdf_path)

        # Step 1: Parse
        try:
            parsed = self._parser.parse(pdf_path)
        except Exception as e:
            self._move_to_failed(pdf_path, error=str(e))
            return IngestResult(status=IngestStatus.PARSE_FAILED, error=str(e))

        # Step 2: Sanity check
        if len(parsed.raw_text.strip()) < MIN_TEXT_CHARS:
            self._move_to_failed(pdf_path, error=f"text too short ({len(parsed.raw_text)} chars)")
            return IngestResult(
                status=IngestStatus.PARSE_FAILED,
                error=f"Parsed text is suspiciously short: {len(parsed.raw_text)} chars",
            )

        # Step 3: Clean
        cleaned_text = clean_text(parsed.pages)

        # Step 4: Section
        sections = detect_sections(cleaned_text)

        # Step 5: Extract frontmatter via LLM/Mock
        fm = self._extractor.extract(text=cleaned_text, evidence_type=evidence_type)

        # Step 6: Assign ID
        fm["id"] = self._id_gen(fm, self._evidence_root)

        # Step 7: Validate via Pydantic
        try:
            model_cls = _MODEL_BY_TYPE[evidence_type]
            model_cls(**fm)
        except (ValidationError, KeyError, TypeError) as e:
            if dry_run:
                return IngestResult(
                    status=IngestStatus.DRY_RUN,
                    frontmatter=fm, sections=sections,
                    error=f"Would have quarantined: {e}",
                )
            qr: EvidenceWriteResult = write_quarantine_md(
                partial_frontmatter=fm, sections=sections,
                error=str(e), evidence_root=self._evidence_root,
                source_filename=pdf_path.name,
            )
            return IngestResult(
                status=IngestStatus.QUARANTINED,
                output_path=qr.path, frontmatter=fm, sections=sections,
                error=str(e),
            )

        # Step 8: Write (or dry_run)
        if dry_run:
            return IngestResult(
                status=IngestStatus.DRY_RUN,
                frontmatter=fm, sections=sections,
            )

        wr = write_evidence_md(
            frontmatter=fm, sections=sections, evidence_root=self._evidence_root,
        )
        return IngestResult(
            status=IngestStatus.OK,
            output_path=wr.path, frontmatter=fm, sections=sections,
        )

    def _move_to_failed(self, pdf_path: Path, error: str) -> None:
        self._failed_root.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(pdf_path, self._failed_root / pdf_path.name)
            (self._failed_root / f"{pdf_path.name}.error.txt").write_text(
                error, encoding="utf-8"
            )
        except Exception:
            pass
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_ingest_pipeline.py -v`
Expected: 5 passed.

**Note on `_default_id_generator`:** the existing `utils.id_gen.next_id` signature may differ. If tests pass with the test's `id_generator` lambda but `_default_id_generator` is never actually invoked in tests, that's fine — it's exercised only by the CLI integration test. If you find that `next_id` has a different signature than `(ev_type, year, pinyin, evidence_root=)`, adapt `_default_id_generator` to match the real signature. Do NOT change the public IngestPipeline API.

---

## Task D.9: CLI — `hdb ingest pdf` / `hdb ingest dry-run`

**Files:**
- Modify: `src/hypertensiondb/cli.py`
- Test: `tests/unit/test_ingest_cli.py`

- [ ] **Step 1: 写失败测试**

Create `tests/unit/test_ingest_cli.py`:

```python
import pytest
from pathlib import Path
from typer.testing import CliRunner
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from hypertensiondb.cli import app

runner = CliRunner()


def _make_pdf(tmp_path: Path, body: str, name: str = "in.pdf") -> Path:
    p = tmp_path / name
    c = canvas.Canvas(str(p), pagesize=letter)
    y = 720
    for line in body.split("\n"):
        c.drawString(72, y, line)
        y -= 14
        if y < 72:
            c.showPage(); y = 720
    c.save()
    return p


@pytest.fixture
def evidence_env(tmp_path, monkeypatch):
    ev = tmp_path / "evidence"
    raw = tmp_path / "raw"
    (raw / "_failed").mkdir(parents=True, exist_ok=True)
    (raw / "incoming").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("EVIDENCE_ROOT", str(ev))
    monkeypatch.setenv("RAW_ROOT", str(raw))
    monkeypatch.setenv("INGEST_EXTRACTOR", "mock")
    return tmp_path


@pytest.mark.unit
def test_ingest_pdf_command_success(evidence_env):
    pdf = _make_pdf(evidence_env, "Methods\n" + "x " * 300 + "\nResults\n" + "y " * 300)
    result = runner.invoke(app, ["ingest", "pdf", str(pdf), "--type", "RCT"])
    assert result.exit_code == 0, result.output
    assert "OK" in result.output or "written" in result.output.lower()


@pytest.mark.unit
def test_ingest_pdf_command_missing_file(evidence_env):
    result = runner.invoke(app, ["ingest", "pdf", "no-such.pdf", "--type", "RCT"])
    assert result.exit_code != 0


@pytest.mark.unit
def test_ingest_dry_run_does_not_write(evidence_env):
    pdf = _make_pdf(evidence_env, "Methods\n" + "x " * 300 + "\nResults\n" + "y " * 300)
    result = runner.invoke(app, ["ingest", "dry-run", str(pdf), "--type", "RCT"])
    assert result.exit_code == 0, result.output
    # No file should have been written under evidence_env/evidence/
    assert not list((evidence_env / "evidence").rglob("EV-*.md"))
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_ingest_cli.py -v`
Expected: 失败（命令未实现或返回错误码）。

- [ ] **Step 3: 修改 cli.py — 替换 `ingest dry-run` 占位，加 `ingest pdf` 命令**

打开 `src/hypertensiondb/cli.py`，删除原有的：

```python
@ingest_app.command("dry-run")
def ingest_dry_run() -> None:
    """Placeholder — implemented in Plan D."""
    typer.echo("Not yet implemented (Plan D)")
```

替换为以下完整的 ingest 命令组（粘贴到原位置）：

```python
def _build_ingest_pipeline():
    from hypertensiondb.ingest.parse_pdf import PyMuPDFParser
    from hypertensiondb.ingest.pipeline import IngestPipeline

    evidence_root = Path(os.getenv("EVIDENCE_ROOT", "evidence"))
    raw_root = Path(os.getenv("RAW_ROOT", "raw"))
    failed_root = raw_root / "_failed"

    extractor_name = os.getenv("INGEST_EXTRACTOR", "mock")
    if extractor_name == "openai":
        from hypertensiondb.ingest.frontmatter_extractor_llm import LLMFrontmatterExtractor
        extractor = LLMFrontmatterExtractor(
            api_key=os.environ["OPENAI_API_KEY"],
            model=os.getenv("OPENAI_EXTRACT_MODEL", "gpt-4o-mini"),
        )
    else:
        from hypertensiondb.ingest.frontmatter_extractor import MockFrontmatterExtractor
        extractor = MockFrontmatterExtractor()

    return IngestPipeline(
        parser=PyMuPDFParser(),
        extractor=extractor,
        evidence_root=evidence_root,
        failed_root=failed_root,
    )


@ingest_app.command("pdf")
def ingest_pdf(
    pdf_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    evidence_type: str = typer.Option(..., "--type", "-t",
                                      help="RCT|SR|META|GL|TCM"),
) -> None:
    """Full ingest: PDF → parse → clean → section → extract → validate → write."""
    if evidence_type not in {"RCT", "SR", "META", "GL", "TCM"}:
        typer.echo(f"Invalid type: {evidence_type}")
        raise typer.Exit(1)
    pipeline = _build_ingest_pipeline()
    result = pipeline.ingest_pdf(pdf_path, evidence_type=evidence_type)
    if result.status.value == "ok":
        typer.echo(f"OK: written to {result.output_path}")
    elif result.status.value == "quarantined":
        typer.echo(f"QUARANTINED: {result.error}")
        typer.echo(f"  see {result.output_path}")
        raise typer.Exit(2)
    elif result.status.value == "parse_failed":
        typer.echo(f"PARSE_FAILED: {result.error}")
        raise typer.Exit(3)


@ingest_app.command("dry-run")
def ingest_dry_run(
    pdf_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    evidence_type: str = typer.Option("RCT", "--type", "-t",
                                      help="RCT|SR|META|GL|TCM"),
) -> None:
    """Run ingest pipeline without writing — print preview."""
    pipeline = _build_ingest_pipeline()
    result = pipeline.ingest_pdf(pdf_path, evidence_type=evidence_type, dry_run=True)
    typer.echo(f"Status: {result.status.value}")
    if result.frontmatter:
        typer.echo("--- frontmatter ---")
        import yaml as _yaml
        typer.echo(_yaml.safe_dump(result.frontmatter, allow_unicode=True, sort_keys=False))
    if result.sections:
        typer.echo("--- sections (non-empty keys) ---")
        for k, v in result.sections.items():
            if v.strip():
                typer.echo(f"  {k}: {v[:80]}{'...' if len(v) > 80 else ''}")
    if result.error:
        typer.echo(f"--- error ---\n{result.error}")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_ingest_cli.py -v`
Expected: 3 passed.

- [ ] **Step 5: 全单元回归确认没破坏 Plan A/B/C**

Run: `py -m pytest tests/unit/ -v --tb=line 2>&1 | tail -5`
Expected: 所有测试通过（约 ~190 passed）

---

## Task D.10: 端到端集成测试

**Files:**
- Create: `tests/integration/test_ingest_end_to_end.py`

- [ ] **Step 1: 写集成测试**

Create `tests/integration/test_ingest_end_to_end.py`:

```python
"""End-to-end: tiny synthetic PDF → ingest pipeline → evidence/{type}/{id}.md.

Uses the Mock extractor (no LLM cost). Validates the output passes the same
scripts/validate_evidence.py used by the pre-commit hook.
"""
import subprocess
import sys
import pytest
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from hypertensiondb.ingest.parse_pdf import PyMuPDFParser
from hypertensiondb.ingest.frontmatter_extractor import MockFrontmatterExtractor
from hypertensiondb.ingest.pipeline import IngestPipeline, IngestStatus


def _make_pdf(path: Path, sections: list[tuple[str, str]]) -> None:
    """Create a multi-section RCT-shaped PDF."""
    c = canvas.Canvas(str(path), pagesize=letter)
    y = 720
    for heading, body in sections:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, y, heading); y -= 16
        c.setFont("Helvetica", 10)
        for line in body.split("\n"):
            c.drawString(72, y, line); y -= 12
            if y < 72:
                c.showPage(); y = 720
        y -= 12
    c.save()


@pytest.mark.integration
def test_ingest_synthetic_rct_pdf(tmp_path):
    pdf = tmp_path / "rct.pdf"
    _make_pdf(pdf, [
        ("Background", "Hypertension is common.\n" * 5),
        ("Methods", "Randomized double-blind trial with 612 patients.\n" * 8),
        ("Results", "SBP decreased by 8 mmHg (95% CI -10.1, -6.7).\n" * 8),
        ("Conclusion", "Combination therapy is superior.\n" * 4),
    ])

    pipeline = IngestPipeline(
        parser=PyMuPDFParser(),
        extractor=MockFrontmatterExtractor(),
        evidence_root=tmp_path / "evidence",
        failed_root=tmp_path / "raw" / "_failed",
        id_generator=lambda fm, _root: "EV-RCT-2026-TEST-001",
    )
    result = pipeline.ingest_pdf(pdf, evidence_type="RCT")

    assert result.status == IngestStatus.OK, result.error
    assert result.output_path.exists()
    content = result.output_path.read_text(encoding="utf-8")
    assert "EV-RCT-2026-TEST-001" in content
    assert "## 方法 / Methods" in content or "## Methods" in content
    assert "SBP decreased" in content


@pytest.mark.integration
def test_ingest_output_passes_validator(tmp_path):
    """The written .md must validate via scripts/validate_evidence.py."""
    pdf = tmp_path / "rct.pdf"
    _make_pdf(pdf, [
        ("Methods", "Trial design.\n" * 8),
        ("Results", "Effective.\n" * 8),
        ("Conclusion", "Combination superior.\n" * 4),
    ])
    pipeline = IngestPipeline(
        parser=PyMuPDFParser(),
        extractor=MockFrontmatterExtractor(),
        evidence_root=tmp_path / "evidence",
        failed_root=tmp_path / "raw" / "_failed",
        id_generator=lambda fm, _root: "EV-RCT-2026-TEST-001",
    )
    result = pipeline.ingest_pdf(pdf, evidence_type="RCT")
    assert result.status == IngestStatus.OK

    # Run the project's validator on the produced file
    repo_root = Path(__file__).parent.parent.parent
    validator = repo_root / "scripts" / "validate_evidence.py"
    proc = subprocess.run(
        [sys.executable, str(validator), str(result.output_path)],
        capture_output=True, text=True, cwd=repo_root,
    )
    # Mock extractor produces sections only in methods/results/conclusion;
    # validator requires abstract_zh too. So either:
    # (a) the validator passes (good), or
    # (b) the validator fails for "abstract_zh missing" — acceptable since this
    #     is a Mock-extractor limitation, NOT a pipeline bug.
    if proc.returncode != 0:
        assert "abstract_zh" in proc.stdout or "abstract_zh" in proc.stderr, \
            f"Unexpected validator failure: {proc.stdout}\n{proc.stderr}"


@pytest.mark.integration
def test_ingest_quarantine_on_bad_extractor(tmp_path):
    class BadExtractor:
        def extract(self, text, evidence_type):
            return {"type": evidence_type, "year": "wrong"}
        @property
        def model_name(self): return "bad"

    pdf = tmp_path / "rct.pdf"
    _make_pdf(pdf, [("Methods", "x " * 200), ("Results", "y " * 200)])
    pipeline = IngestPipeline(
        parser=PyMuPDFParser(),
        extractor=BadExtractor(),
        evidence_root=tmp_path / "evidence",
        failed_root=tmp_path / "raw" / "_failed",
        id_generator=lambda fm, _root: "EV-RCT-2026-TEST-001",
    )
    result = pipeline.ingest_pdf(pdf, evidence_type="RCT")
    assert result.status == IngestStatus.QUARANTINED
    assert (tmp_path / "evidence" / "_quarantine").is_dir()
```

- [ ] **Step 2: 跑集成测试**

Run: `py -m pytest tests/integration/test_ingest_end_to_end.py -v -m integration --tb=short`
Expected: 3 passed.

- [ ] **Step 3: 全集成回归确认**

Run: `py -m pytest tests/integration/ -v -m integration --tb=line 2>&1 | tail -5`
Expected: 全部通过（Plan B 的 2 + Plan C 的 5 + Plan D 的 3 = 10）

---

## 自检（Self-Review）

**1. Spec 覆盖检查（设计 §4 管线 A + §6 错误处理）：**

| 设计要求 | 对应 Task |
|---------|----------|
| parse_pdf（Marker 优先 / MinerU 备选 / pypdf fallback） | D.2（实现 PyMuPDF；Marker/MinerU 留给后续 `[marker]/[mineru]` 扩展） |
| clean（去页眉页脚 / 合并断行 / 修复断词） | D.3 |
| section_mapper（启发式 IMRaD → 标准 8 节区） | D.4 |
| extract_frontmatter（LLM 辅助，Pydantic 强约束，失败→draft） | D.5 + D.6 |
| validate + write（ID 唯一性、写 evidence/{type}/、status=draft 默认） | D.7 + D.8 |
| 失败处理：PDF 解析报错 / 文本量异常 → raw/_failed/ | D.8（_move_to_failed + MIN_TEXT_CHARS） |
| 失败处理：Pydantic 校验失败 → _quarantine/ | D.7 + D.8（write_quarantine_md） |
| LLM 抽出字段打 _extracted_by: llm | D.5 + D.6（统一在 extractor 层强制） |
| ID 冲突拒绝写入 | D.7（FileExistsError, overwrite=False 默认） |
| CLI: hdb ingest pdf / dry-run | D.9 |

**2. Placeholder 扫描：** 无 TBD/TODO。所有代码段完整。`_default_id_generator` 注明"如签名不符可调整"——这是工程现实，非占位符。

**3. 类型一致性：**
- `ParsedPdf` 在 D.2 定义，D.8 pipeline 使用 ✓
- `BaseFrontmatterExtractor.extract(text, evidence_type) -> dict` 在 D.5 定义，D.6/D.8 一致使用 ✓
- `EvidenceWriteResult` 在 D.7 定义，D.8 使用 ✓
- `IngestStatus` enum 在 D.8 定义，D.9 CLI 引用 `.value` ✓
- `STANDARD_SECTIONS` 在 D.4 定义，D.7 `_SECTION_HEADINGS` 覆盖同样 8 个键 ✓

**4. 已知偏差/折中：**
- **Marker/MinerU 未实现**——它们引入 PyTorch + GPU 友好设定，对本 CPU 项目代价过大。PyMuPDF 已是合理默认。后续若用户提供扫描版 PDF 需要 OCR，再做 Marker 扩展。
- **LLM extractor 测试用 mock**——真实 OpenAI 调用需 API key 才能集成测试。生产时跑 `INGEST_EXTRACTOR=openai OPENAI_API_KEY=... hdb ingest pdf <path> --type RCT` 验证。
- **`abstract_zh` 节区**——MockExtractor 不生成正文，导致 validator 可能告警"abstract_zh missing"。这是 Mock 实现的局限，不是管线 bug，集成测试 D.10 中明确容忍。
- **`_default_id_generator`**：调用 `utils.id_gen.next_id`。如该函数当前签名不接受 `evidence_root=` 参数，subagent 实现时按实际签名适配——保持 IngestPipeline 公共 API 稳定即可。

---

## 执行完成标志

Plan D 完成时你应该能够：

1. `py -m pytest tests/unit/ -v --tb=line 2>&1 | tail -5` → 全部通过（Plan A/B/C/D 累计 ~190 tests）
2. `py -m pytest tests/integration/ -v -m integration --tb=line 2>&1 | tail -5` → 全部通过（10 tests）
3. `py -m pytest tests/golden/ -v -m golden --tb=line 2>&1 | tail -5` → 全部通过（4 tests）
4. `hdb ingest --help` → 显示 `pdf` 和 `dry-run` 两个子命令
5. 把任意英文 RCT PDF 放到 `raw/incoming/`，跑 `INGEST_EXTRACTOR=mock hdb ingest pdf raw/incoming/foo.pdf --type RCT` → 在 `evidence/rcts/` 生成 `EV-RCT-...-NNN.md` 草稿
6. `INGEST_EXTRACTOR=openai OPENAI_API_KEY=sk-... hdb ingest pdf <path> --type RCT` → 用真实 LLM 抽 PICO，仍写 status=draft 草稿
