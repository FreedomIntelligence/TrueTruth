# Plan A: 项目骨架 + Schema 层 + 手工数据流

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 Python 项目骨架、定义所有文献类型的 Pydantic schema、建立"手工 md → 校验 → 入库"的最小可工作数据流。完成后用户可以手写 evidence markdown 文件并通过 schema 自动校验。

**Architecture:** 三层结构的 L1（数据层）+ schema 校验。Markdown + YAML frontmatter 作为权威数据源，Pydantic 模型作为运行时类型契约。本计划不涉及 Qdrant、检索 API 或 PDF 解析（留给 Plan B-D）。

**Tech Stack:** Python 3.11+, Pydantic v2, PyYAML, Typer (CLI), pytest, pre-commit, pypinyin

---

## 参考资料

- 设计文档: `docs/superpowers/specs/2026-05-19-hypertension-rag-design.md`
- 重点参考 §2（文档格式）、§3（目录布局 + ID 约定）、§6（数据质量）

## File Structure

完成本计划后会创建的文件清单。每个文件单一职责，便于独立测试。

```
pyproject.toml                              # 项目元数据 + 依赖 + CLI入口
.env.example                                # 占位的API key
.gitignore                                  # 忽略 data/、raw/、.env
.pre-commit-config.yaml                     # pre-commit hook 配置
README.md                                   # 项目说明骨架

evidence/                                   # 数据目录（带.gitkeep）
  rcts/.gitkeep
  systematic_reviews/.gitkeep
  meta_analyses/.gitkeep
  guidelines/.gitkeep
  tcm/.gitkeep
  _quarantine/.gitkeep

src/hypertensiondb/
  __init__.py                               # 导出 __version__
  cli.py                                    # `hdb` 命令入口（typer）

  schema/
    __init__.py                             # 导出所有模型类 + load_evidence
    base.py                                 # BaseFrontmatter, Title, EnumType, EnumLanguage, EnumStatus
    pico.py                                 # Pico, Population, Intervention, Comparison, Outcome, EffectSize
    bias_grade.py                           # RiskOfBias, Grade, ExtractedBy
    rct.py                                  # RctFrontmatter (BaseFrontmatter + Pico + RoB + Grade)
    sr_meta.py                              # SrFrontmatter, MetaFrontmatter (加 included_studies、meta_analysis)
    guideline.py                            # GuidelineFrontmatter (加 recommendations)
    tcm.py                                  # TcmFrontmatter, TcmSyndrome (证型/方剂)
    loader.py                               # load_evidence(path) → 解析 md → 返回正确类型的 Pydantic 实例
    sections.py                             # split_sections(markdown_body) → 标准 8 节 dict

  utils/
    __init__.py
    pinyin.py                               # to_first_author_pinyin(name) → "PENG"
    id_gen.py                               # next_id(type, year, author) → "EV-RCT-2026-PENG-001"

scripts/
  new_evidence.py                           # 交互式生成 md 骨架
  validate_evidence.py                      # 给 pre-commit hook 调用

tests/
  conftest.py                               # 共享 fixtures
  fixtures/
    schema/                                 # 合法+边界+非法 frontmatter 样本
      valid_rct.md
      valid_sr.md
      valid_meta.md
      valid_guideline.md
      valid_tcm.md
      invalid_missing_id.md
      invalid_bad_grade.md
      invalid_effect_size_string.md
  unit/
    test_pinyin.py
    test_id_gen.py
    test_schema_base.py
    test_schema_pico.py
    test_schema_rct.py
    test_schema_sr_meta.py
    test_schema_guideline.py
    test_schema_tcm.py
    test_loader.py
    test_sections.py
  integration/
    test_pre_commit_hook.py                 # 跑 scripts/validate_evidence.py
```

---

## M0: 项目骨架

### Task 0.1: 初始化 Python 项目

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "hypertensiondb"
version = "0.1.0"
description = "Hypertension Evidence RAG Database"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.7",
    "pyyaml>=6.0",
    "typer>=0.12",
    "pypinyin>=0.51",
    "python-frontmatter>=1.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "pre-commit>=3.7",
    "ruff>=0.4",
]

[project.scripts]
hdb = "hypertensiondb.cli:app"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "unit: fast unit tests",
    "integration: integration tests (may use docker)",
    "golden: golden set regression",
]

[tool.ruff]
line-length = 100
target-version = "py311"
```

- [ ] **Step 2: 安装依赖验证**

Run: `pip install -e .[dev]`
Expected: 安装成功，无报错

- [ ] **Step 3: Commit**

```bash
git init
git add pyproject.toml
git commit -m "chore: init python project with pydantic + typer"
```

### Task 0.2: 创建目录结构与 .gitkeep

**Files:**
- Create: `evidence/{rcts,systematic_reviews,meta_analyses,guidelines,tcm,_quarantine}/.gitkeep`
- Create: `src/hypertensiondb/{schema,utils}/__init__.py`
- Create: `tests/{unit,integration,fixtures/schema}/__init__.py`

- [ ] **Step 1: 创建所有目录与占位文件**

PowerShell 命令：
```powershell
New-Item -ItemType Directory -Path evidence/rcts, evidence/systematic_reviews, evidence/meta_analyses, evidence/guidelines, evidence/tcm, evidence/_quarantine -Force
New-Item -ItemType Directory -Path src/hypertensiondb/schema, src/hypertensiondb/utils -Force
New-Item -ItemType Directory -Path tests/unit, tests/integration, tests/fixtures/schema -Force
New-Item -ItemType Directory -Path scripts -Force
"" | Out-File -Encoding utf8 evidence/rcts/.gitkeep
"" | Out-File -Encoding utf8 evidence/systematic_reviews/.gitkeep
"" | Out-File -Encoding utf8 evidence/meta_analyses/.gitkeep
"" | Out-File -Encoding utf8 evidence/guidelines/.gitkeep
"" | Out-File -Encoding utf8 evidence/tcm/.gitkeep
"" | Out-File -Encoding utf8 evidence/_quarantine/.gitkeep
```

- [ ] **Step 2: 创建包初始化文件**

Create `src/hypertensiondb/__init__.py`:
```python
__version__ = "0.1.0"
```

Create `src/hypertensiondb/schema/__init__.py`, `src/hypertensiondb/utils/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py` 全部为空文件。

- [ ] **Step 3: Commit**

```bash
git add evidence/ src/ tests/ scripts/
git commit -m "chore: create directory layout for evidence + src + tests"
```

### Task 0.3: .gitignore 与 .env.example

**Files:**
- Create: `.gitignore`
- Create: `.env.example`

- [ ] **Step 1: 创建 .gitignore**

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
dist/
build/
.venv/

# Data (派生 + 敏感)
data/
raw/
.env

# Editor
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 2: 创建 .env.example**

```
# Embedding API（任选其一）
OPENAI_API_KEY=
ZHIPU_API_KEY=
VOYAGE_API_KEY=

# Reranker（本地不需要 key；走 Cohere 时填）
COHERE_API_KEY=

# Qdrant（默认本地 docker）
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore .env.example
git commit -m "chore: add gitignore and env example"
```

### Task 0.4: CLI 入口骨架

**Files:**
- Create: `src/hypertensiondb/cli.py`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: 写失败测试**

Create `tests/unit/test_cli.py`:
```python
import pytest
from typer.testing import CliRunner
from hypertensiondb.cli import app


runner = CliRunner()


@pytest.mark.unit
def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


@pytest.mark.unit
def test_cli_help_lists_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ingest" in result.stdout
    assert "index" in result.stdout
    assert "lint" in result.stdout
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/unit/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError` 或 `AttributeError`

- [ ] **Step 3: 实现最小 CLI**

Create `src/hypertensiondb/cli.py`:
```python
import typer
from hypertensiondb import __version__

app = typer.Typer(help="Hypertension Evidence DB CLI")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", callback=_version_callback, is_eager=True, help="Show version"
    ),
) -> None:
    """hdb: Hypertension Evidence DB command line."""


ingest_app = typer.Typer(help="Ingest evidence from PDF / API / manual")
index_app = typer.Typer(help="Manage Qdrant index")
lint_app = typer.Typer(help="Data quality checks")

app.add_typer(ingest_app, name="ingest")
app.add_typer(index_app, name="index")
app.add_typer(lint_app, name="lint")


@ingest_app.command("dry-run")
def ingest_dry_run() -> None:
    """Placeholder — implemented in Plan D."""
    typer.echo("Not yet implemented (Plan D)")


@index_app.command("update")
def index_update() -> None:
    """Placeholder — implemented in Plan B."""
    typer.echo("Not yet implemented (Plan B)")


@lint_app.command("run")
def lint_run() -> None:
    """Placeholder — implemented in Plan E."""
    typer.echo("Not yet implemented (Plan E)")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/unit/test_cli.py -v`
Expected: 2 passed

- [ ] **Step 5: 手动验证 CLI**

Run: `hdb --help`
Expected: 显示 ingest / index / lint 三个子命令

Run: `hdb --version`
Expected: `0.1.0`

- [ ] **Step 6: Commit**

```bash
git add src/hypertensiondb/cli.py tests/unit/test_cli.py
git commit -m "feat(cli): scaffold hdb command with ingest/index/lint subcommands"
```

### Task 0.5: README 骨架

**Files:**
- Create: `README.md`

- [ ] **Step 1: 写 README**

```markdown
# 高血压证据库 (Hypertension Evidence DB)

本地化的高血压循证医学证据 RAG 数据库，为下游临床决策支持系统提供混合检索 API。

## 设计文档

`docs/superpowers/specs/2026-05-19-hypertension-rag-design.md`

## 快速开始

```bash
pip install -e .[dev]
hdb --help
```

## 项目状态

- [x] Plan A: 项目骨架 + Schema + 手工数据流
- [ ] Plan B: 索引管线 + Qdrant
- [ ] Plan C: 检索 API + 黄金集
- [ ] Plan D: PDF 入库管线
- [ ] Plan E: 英文 API 采集 + 质量工具
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README skeleton with project status"
```

---

## M1: Schema 层

### Task 1.1: 工具类 — pinyin 与 id_gen

**Files:**
- Create: `src/hypertensiondb/utils/pinyin.py`
- Create: `src/hypertensiondb/utils/id_gen.py`
- Test: `tests/unit/test_pinyin.py`
- Test: `tests/unit/test_id_gen.py`

- [ ] **Step 1: 写 pinyin 失败测试**

Create `tests/unit/test_pinyin.py`:
```python
import pytest
from hypertensiondb.utils.pinyin import to_first_author_pinyin


@pytest.mark.unit
@pytest.mark.parametrize("name, expected", [
    ("彭勇",       "PENG"),
    ("张伟",       "ZHANG"),
    ("欧阳明",     "OUYANG"),  # 复姓：取完整姓
    ("Williams B", "WILLIAMS"),  # 英文：取第一个 token
    ("de Luca M",  "DE"),        # 英文复姓：取第一个 token
    ("Wang X",     "WANG"),
    ("CHS",        "CHS"),       # 机构缩写原样返回
    ("ESC",        "ESC"),
])
def test_to_first_author_pinyin(name, expected):
    assert to_first_author_pinyin(name) == expected
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/unit/test_pinyin.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 实现 pinyin.py**

Create `src/hypertensiondb/utils/pinyin.py`:
```python
from pypinyin import pinyin, Style

# 常见复姓列表（扩展可补充）
_COMPOUND_SURNAMES = {
    "欧阳", "司马", "诸葛", "上官", "东方", "夏侯",
    "独孤", "长孙", "宇文", "公孙", "慕容", "皇甫",
}

# 全大写英文 token 视为机构缩写，原样返回
_INSTITUTION_PATTERN_LEN = 3  # ≥3 个字符且全大写视为缩写


def to_first_author_pinyin(name: str) -> str:
    """Return UPPER-CASE pinyin of the first author's surname.

    For Chinese names, handles compound surnames.
    For English names, returns the first whitespace-delimited token uppercased.
    For institution abbreviations (all-caps ≥3 chars), returns as-is.
    """
    name = name.strip()
    if not name:
        raise ValueError("name must not be empty")

    # 机构缩写检测：全大写 + 无空格
    if name.isupper() and " " not in name:
        return name

    # 英文名检测：首字符是ASCII字母
    if name[0].isascii() and name[0].isalpha():
        return name.split()[0].upper()

    # 中文名：检查复姓
    if len(name) >= 2 and name[:2] in _COMPOUND_SURNAMES:
        surname = name[:2]
    else:
        surname = name[0]

    py = pinyin(surname, style=Style.NORMAL)
    return "".join(part[0] for part in py).upper()
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/unit/test_pinyin.py -v`
Expected: 8 passed

- [ ] **Step 5: 写 id_gen 失败测试**

Create `tests/unit/test_id_gen.py`:
```python
import pytest
from pathlib import Path
from unittest.mock import patch
from hypertensiondb.utils.id_gen import next_id


@pytest.mark.unit
def test_next_id_first_entry(tmp_path):
    """When no existing files, returns 001."""
    with patch("hypertensiondb.utils.id_gen.EVIDENCE_ROOT", tmp_path):
        (tmp_path / "rcts").mkdir()
        result = next_id("RCT", 2026, "PENG")
    assert result == "EV-RCT-2026-PENG-001"


@pytest.mark.unit
def test_next_id_increments(tmp_path):
    """Finds highest existing serial and returns next."""
    rcts = tmp_path / "rcts"
    rcts.mkdir()
    (rcts / "EV-RCT-2026-PENG-001.md").touch()
    (rcts / "EV-RCT-2026-PENG-002.md").touch()
    with patch("hypertensiondb.utils.id_gen.EVIDENCE_ROOT", tmp_path):
        result = next_id("RCT", 2026, "PENG")
    assert result == "EV-RCT-2026-PENG-003"


@pytest.mark.unit
def test_next_id_different_type_no_collision(tmp_path):
    """SR files don't affect RCT serial counter."""
    srs = tmp_path / "systematic_reviews"
    srs.mkdir()
    (tmp_path / "rcts").mkdir()
    (srs / "EV-SR-2026-PENG-001.md").touch()
    with patch("hypertensiondb.utils.id_gen.EVIDENCE_ROOT", tmp_path):
        result = next_id("RCT", 2026, "PENG")
    assert result == "EV-RCT-2026-PENG-001"
```

- [ ] **Step 6: 实现 id_gen.py**

Create `src/hypertensiondb/utils/id_gen.py`:
```python
import re
from pathlib import Path

EVIDENCE_ROOT = Path(__file__).parent.parent.parent.parent / "evidence"

_TYPE_DIR = {
    "RCT": "rcts",
    "SR": "systematic_reviews",
    "META": "meta_analyses",
    "GL": "guidelines",
    "TCM": "tcm",
}


def next_id(ev_type: str, year: int, author_pinyin: str) -> str:
    """Return the next available evidence ID for the given type/year/author."""
    ev_type = ev_type.upper()
    author_pinyin = author_pinyin.upper()
    if ev_type not in _TYPE_DIR:
        raise ValueError(f"Unknown evidence type: {ev_type}")

    prefix = f"EV-{ev_type}-{year}-{author_pinyin}-"
    folder = EVIDENCE_ROOT / _TYPE_DIR[ev_type]
    folder.mkdir(parents=True, exist_ok=True)

    existing = sorted(folder.glob(f"{prefix}*.md"))
    if not existing:
        serial = 1
    else:
        pattern = re.compile(rf"{re.escape(prefix)}(\d+)\.md$")
        serials = [
            int(m.group(1))
            for f in existing
            if (m := pattern.search(f.name))
        ]
        serial = max(serials) + 1 if serials else 1

    return f"{prefix}{serial:03d}"
```

- [ ] **Step 7: 跑所有 id_gen 测试**

Run: `pytest tests/unit/test_id_gen.py -v`
Expected: 3 passed

- [ ] **Step 8: Commit**

```bash
git add src/hypertensiondb/utils/ tests/unit/test_pinyin.py tests/unit/test_id_gen.py
git commit -m "feat(utils): add pinyin converter and evidence id generator"
```

---

### Task 1.2: Schema 基础层 — base + pico + bias_grade

**Files:**
- Create: `src/hypertensiondb/schema/base.py`
- Create: `src/hypertensiondb/schema/pico.py`
- Create: `src/hypertensiondb/schema/bias_grade.py`
- Test: `tests/unit/test_schema_base.py`
- Test: `tests/unit/test_schema_pico.py`

- [ ] **Step 1: 写 base schema 失败测试**

Create `tests/unit/test_schema_base.py`:
```python
import pytest
from hypertensiondb.schema.base import BaseFrontmatter, EvidenceType, Language, Status


@pytest.mark.unit
def test_valid_base_minimal():
    fm = BaseFrontmatter(
        id="EV-RCT-2026-PENG-001",
        type=EvidenceType.RCT,
        title={"zh": "测试标题", "en": "Test title"},
        authors=["Peng Y"],
        year=2026,
        language=Language.ZH,
    )
    assert fm.id == "EV-RCT-2026-PENG-001"
    assert fm.status == Status.DRAFT  # default


@pytest.mark.unit
def test_id_must_match_pattern():
    with pytest.raises(Exception):
        BaseFrontmatter(
            id="bad-id",
            type=EvidenceType.RCT,
            title={"zh": "标题"},
            authors=["Peng Y"],
            year=2026,
            language=Language.ZH,
        )


@pytest.mark.unit
def test_year_range():
    with pytest.raises(Exception):
        BaseFrontmatter(
            id="EV-RCT-2026-PENG-001",
            type=EvidenceType.RCT,
            title={"zh": "标题"},
            authors=["Peng Y"],
            year=1800,  # 太早
            language=Language.ZH,
        )
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/unit/test_schema_base.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 实现 base.py**

Create `src/hypertensiondb/schema/base.py`:
```python
import re
from datetime import date
from enum import StrEnum
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator


class EvidenceType(StrEnum):
    RCT = "RCT"
    SR = "SR"
    META = "META"
    GL = "GL"
    TCM = "TCM"


class Language(StrEnum):
    ZH = "zh"
    EN = "en"
    BILINGUAL = "bilingual"


class Status(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    PUBLISHED = "published"
    RETRACTED = "retracted"
    QUARANTINED = "quarantined"


class FullTextStatus(StrEnum):
    COMPLETE = "complete"
    ABSTRACT_ONLY = "abstract_only"
    SECTION_PARTIAL = "section_partial"


_ID_PATTERN = re.compile(
    r"^EV-(RCT|SR|META|GL|TCM)-\d{4}-[A-Z]+(-[A-Z]+)*-\d{3}$"
)


class Title(BaseModel):
    zh: Optional[str] = None
    en: Optional[str] = None

    @model_validator(mode="after")
    def at_least_one(self) -> "Title":
        if not self.zh and not self.en:
            raise ValueError("Title must have at least one of zh or en")
        return self


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

    @field_validator("id")
    @classmethod
    def id_must_match_pattern(cls, v: str) -> str:
        if not _ID_PATTERN.match(v):
            raise ValueError(
                f"id '{v}' does not match pattern EV-{{TYPE}}-{{YEAR}}-{{AUTHOR}}-{{NNN}}"
            )
        return v

    @field_validator("year")
    @classmethod
    def year_in_range(cls, v: int) -> int:
        current_year = date.today().year
        if not (1900 <= v <= current_year + 1):
            raise ValueError(f"year {v} out of plausible range 1900-{current_year + 1}")
        return v

    @field_validator("quality_score")
    @classmethod
    def quality_score_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("quality_score must be between 0.0 and 1.0")
        return v
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/unit/test_schema_base.py -v`
Expected: 3 passed

- [ ] **Step 5: 写 PICO schema 失败测试**

Create `tests/unit/test_schema_pico.py`:
```python
import pytest
from hypertensiondb.schema.pico import EffectSize, Outcome, Pico


@pytest.mark.unit
def test_effect_size_requires_numeric_value():
    with pytest.raises(Exception):
        EffectSize(metric="MD", value="not-a-number", ci_low=-10.0, ci_high=-6.0)


@pytest.mark.unit
def test_valid_effect_size():
    es = EffectSize(metric="MD", value=-8.4, ci_low=-10.1, ci_high=-6.7, p=0.001)
    assert es.value == -8.4


@pytest.mark.unit
def test_ci_low_must_be_less_than_ci_high():
    with pytest.raises(Exception):
        EffectSize(metric="RR", value=1.2, ci_low=2.0, ci_high=1.0)


@pytest.mark.unit
def test_valid_pico_minimal():
    pico = Pico(
        population={"condition": "原发性高血压", "sample_size": 612},
        intervention={"name": "缬沙坦 80mg + 氨氯地平 5mg", "drug_class": ["ARB", "CCB"]},
        comparison={"name": "缬沙坦单药"},
        outcomes={"primary": [], "secondary": []},
    )
    assert pico.population.condition == "原发性高血压"
```

- [ ] **Step 6: 实现 pico.py**

Create `src/hypertensiondb/schema/pico.py`:
```python
from typing import Optional, Literal
from pydantic import BaseModel, field_validator, model_validator


class EffectSize(BaseModel):
    metric: Literal["MD", "SMD", "RR", "OR", "HR", "RD", "ARR", "NNT", "NNH"]
    value: float
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    p: Optional[float] = None
    _extracted_by: str = "llm"  # "llm" | "human"

    @model_validator(mode="after")
    def ci_low_lt_ci_high(self) -> "EffectSize":
        if self.ci_low is not None and self.ci_high is not None:
            if self.ci_low >= self.ci_high:
                raise ValueError("ci_low must be less than ci_high")
        return self


class Outcome(BaseModel):
    name: str
    effect_size: Optional[EffectSize] = None
    note: Optional[str] = None


class Outcomes(BaseModel):
    primary: list[Outcome] = []
    secondary: list[Outcome] = []


class Population(BaseModel):
    condition: str
    severity: Optional[str] = None
    age_range: Optional[str] = None
    sample_size: Optional[int] = None
    inclusion: list[str] = []
    exclusion: list[str] = []


class Intervention(BaseModel):
    name: str
    drug_class: list[str] = []
    dosage: Optional[str] = None
    duration_weeks: Optional[int] = None


class Comparison(BaseModel):
    name: str


class Pico(BaseModel):
    population: Population
    intervention: Intervention
    comparison: Optional[Comparison] = None
    outcomes: Outcomes = Outcomes()
```

- [ ] **Step 7: 跑 PICO 测试**

Run: `pytest tests/unit/test_schema_pico.py -v`
Expected: 4 passed

- [ ] **Step 8: 实现 bias_grade.py（无单独测试，通过 RCT schema 覆盖）**

Create `src/hypertensiondb/schema/bias_grade.py`:
```python
from enum import StrEnum
from typing import Optional, Any
from pydantic import BaseModel


class RobTool(StrEnum):
    ROB2 = "RoB2"
    ROBINS_I = "ROBINS-I"
    AMSTAR2 = "AMSTAR2"
    AGREE_II = "AGREE-II"


class RobOverall(StrEnum):
    LOW = "low"
    SOME_CONCERNS = "some_concerns"
    HIGH = "high"


class GradeLevel(StrEnum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    VERY_LOW = "very_low"


class RiskOfBias(BaseModel):
    tool: RobTool
    overall: RobOverall
    domains: dict[str, Any] = {}


class Grade(BaseModel):
    level: GradeLevel
    reasons: list[str] = []
```

- [ ] **Step 9: Commit**

```bash
git add src/hypertensiondb/schema/ tests/unit/test_schema_base.py tests/unit/test_schema_pico.py
git commit -m "feat(schema): add base, pico, bias_grade Pydantic models"
```

---

### Task 1.3: 具体文献类型 Schema — RCT / SR+META / Guideline / TCM

**Files:**
- Create: `src/hypertensiondb/schema/rct.py`
- Create: `src/hypertensiondb/schema/sr_meta.py`
- Create: `src/hypertensiondb/schema/guideline.py`
- Create: `src/hypertensiondb/schema/tcm.py`
- Test: `tests/unit/test_schema_rct.py`
- Test: `tests/unit/test_schema_sr_meta.py`
- Test: `tests/unit/test_schema_guideline.py`
- Test: `tests/unit/test_schema_tcm.py`

- [ ] **Step 1: 写 RCT schema 失败测试**

Create `tests/unit/test_schema_rct.py`:
```python
import pytest
from hypertensiondb.schema.rct import RctFrontmatter
from hypertensiondb.schema.base import EvidenceType, Language


def _base_rct_data() -> dict:
    return {
        "id": "EV-RCT-2026-PENG-001",
        "type": "RCT",
        "title": {"zh": "测试RCT"},
        "authors": ["Peng Y"],
        "year": 2026,
        "language": "zh",
        "pico": {
            "population": {"condition": "原发性高血压", "sample_size": 612},
            "intervention": {"name": "缬沙坦 + 氨氯地平"},
            "outcomes": {"primary": [], "secondary": []},
        },
        "risk_of_bias": {"tool": "RoB2", "overall": "low"},
        "grade": {"level": "moderate"},
    }


@pytest.mark.unit
def test_valid_rct():
    fm = RctFrontmatter(**_base_rct_data())
    assert fm.type == EvidenceType.RCT
    assert fm.pico.population.sample_size == 612


@pytest.mark.unit
def test_rct_type_must_be_rct():
    data = _base_rct_data()
    data["type"] = "SR"
    with pytest.raises(Exception):
        RctFrontmatter(**data)


@pytest.mark.unit
def test_rct_published_without_review_allowed_as_draft():
    """Draft status can exist without reviewed_by."""
    data = _base_rct_data()
    data["status"] = "draft"
    fm = RctFrontmatter(**data)
    assert fm.reviewed_by is None
```

- [ ] **Step 2: 实现 rct.py**

Create `src/hypertensiondb/schema/rct.py`:
```python
from typing import Literal
from pydantic import model_validator
from hypertensiondb.schema.base import BaseFrontmatter, EvidenceType
from hypertensiondb.schema.pico import Pico
from hypertensiondb.schema.bias_grade import RiskOfBias, Grade


class RctFrontmatter(BaseFrontmatter):
    type: Literal[EvidenceType.RCT] = EvidenceType.RCT
    pico: Pico
    risk_of_bias: RiskOfBias
    grade: Grade

    @model_validator(mode="after")
    def type_must_be_rct(self) -> "RctFrontmatter":
        if self.type != EvidenceType.RCT:
            raise ValueError("RctFrontmatter requires type=RCT")
        return self
```

- [ ] **Step 3: 跑 RCT 测试**

Run: `pytest tests/unit/test_schema_rct.py -v`
Expected: 3 passed

- [ ] **Step 4: 实现 sr_meta.py + 写测试**

Create `tests/unit/test_schema_sr_meta.py`:
```python
import pytest
from hypertensiondb.schema.sr_meta import SrFrontmatter, MetaFrontmatter


def _base_sr() -> dict:
    return {
        "id": "EV-SR-2024-ZHANG-001",
        "type": "SR",
        "title": {"zh": "系统评价示例"},
        "authors": ["Zhang W"],
        "year": 2024,
        "language": "zh",
        "pico": {
            "population": {"condition": "高血压"},
            "intervention": {"name": "ARB"},
            "outcomes": {},
        },
        "risk_of_bias": {"tool": "AMSTAR2", "overall": "low"},
        "grade": {"level": "high"},
        "included_studies": ["10.1000/xyz123"],
    }


@pytest.mark.unit
def test_valid_sr():
    fm = SrFrontmatter(**_base_sr())
    assert fm.included_studies == ["10.1000/xyz123"]


@pytest.mark.unit
def test_valid_meta():
    data = _base_sr()
    data["id"] = "EV-META-2024-ZHANG-001"
    data["type"] = "META"
    data["heterogeneity"] = {"i_squared": 45.2, "q_p": 0.03}
    fm = MetaFrontmatter(**data)
    assert fm.heterogeneity["i_squared"] == 45.2
```

Create `src/hypertensiondb/schema/sr_meta.py`:
```python
from typing import Literal, Optional, Any
from hypertensiondb.schema.base import BaseFrontmatter, EvidenceType
from hypertensiondb.schema.pico import Pico
from hypertensiondb.schema.bias_grade import RiskOfBias, Grade


class SrFrontmatter(BaseFrontmatter):
    type: Literal[EvidenceType.SR] = EvidenceType.SR
    pico: Pico
    risk_of_bias: RiskOfBias
    grade: Grade
    included_studies: list[str] = []


class MetaFrontmatter(BaseFrontmatter):
    type: Literal[EvidenceType.META] = EvidenceType.META
    pico: Pico
    risk_of_bias: RiskOfBias
    grade: Grade
    included_studies: list[str] = []
    heterogeneity: dict[str, Any] = {}
```

- [ ] **Step 5: 实现 guideline.py + 写测试**

Create `tests/unit/test_schema_guideline.py`:
```python
import pytest
from hypertensiondb.schema.guideline import GuidelineFrontmatter, Recommendation


@pytest.mark.unit
def test_valid_guideline():
    fm = GuidelineFrontmatter(
        id="EV-GL-2024-CHS-001",
        type="GL",
        title={"zh": "中国高血压防治指南2024"},
        authors=["CHS"],
        year=2024,
        language="zh",
        risk_of_bias={"tool": "AGREE-II", "overall": "low"},
        recommendations=[
            {"text": "初始治疗推荐CCB或ARB", "strength": "strong", "grade": "high"}
        ],
    )
    assert len(fm.recommendations) == 1
    assert fm.recommendations[0].strength == "strong"
```

Create `src/hypertensiondb/schema/guideline.py`:
```python
from typing import Literal, Optional
from pydantic import BaseModel
from hypertensiondb.schema.base import BaseFrontmatter, EvidenceType
from hypertensiondb.schema.bias_grade import RiskOfBias, GradeLevel


class Recommendation(BaseModel):
    text: str
    strength: Optional[str] = None     # "strong" | "weak" | "conditional"
    grade: Optional[GradeLevel] = None
    note: Optional[str] = None


class GuidelineFrontmatter(BaseFrontmatter):
    type: Literal[EvidenceType.GL] = EvidenceType.GL
    risk_of_bias: RiskOfBias
    recommendations: list[Recommendation] = []
    target_population: Optional[str] = None
    scope: Optional[str] = None
```

- [ ] **Step 6: 实现 tcm.py + 写测试**

Create `tests/unit/test_schema_tcm.py`:
```python
import pytest
from hypertensiondb.schema.tcm import TcmFrontmatter


@pytest.mark.unit
def test_valid_tcm():
    fm = TcmFrontmatter(
        id="EV-TCM-2023-CHEN-001",
        type="TCM",
        title={"zh": "半夏白术天麻汤治疗痰湿壅盛型高血压RCT"},
        authors=["Chen L"],
        year=2023,
        language="zh",
        pico={
            "population": {"condition": "痰湿壅盛型高血压", "sample_size": 80},
            "intervention": {"name": "半夏白术天麻汤"},
            "outcomes": {},
        },
        risk_of_bias={"tool": "RoB2", "overall": "some_concerns"},
        grade={"level": "low"},
        tcm_syndrome={
            "pattern": "痰湿壅盛",
            "formula": "半夏白术天麻汤",
        },
    )
    assert fm.tcm_syndrome["pattern"] == "痰湿壅盛"
```

Create `src/hypertensiondb/schema/tcm.py`:
```python
from typing import Literal, Optional, Any
from hypertensiondb.schema.base import BaseFrontmatter, EvidenceType
from hypertensiondb.schema.pico import Pico
from hypertensiondb.schema.bias_grade import RiskOfBias, Grade


class TcmFrontmatter(BaseFrontmatter):
    type: Literal[EvidenceType.TCM] = EvidenceType.TCM
    pico: Pico
    risk_of_bias: RiskOfBias
    grade: Grade
    tcm_syndrome: dict[str, Any] = {}
```

- [ ] **Step 7: 跑全部 schema 测试**

Run: `pytest tests/unit/test_schema_*.py -v`
Expected: 所有测试通过（约 13 tests）

- [ ] **Step 8: Commit**

```bash
git add src/hypertensiondb/schema/rct.py src/hypertensiondb/schema/sr_meta.py \
        src/hypertensiondb/schema/guideline.py src/hypertensiondb/schema/tcm.py \
        tests/unit/test_schema_rct.py tests/unit/test_schema_sr_meta.py \
        tests/unit/test_schema_guideline.py tests/unit/test_schema_tcm.py
git commit -m "feat(schema): add RCT, SR, META, Guideline, TCM frontmatter models"
```

---

### Task 1.4: Schema 包入口 + Loader + SectionSplitter

**Files:**
- Create: `src/hypertensiondb/schema/loader.py`
- Create: `src/hypertensiondb/schema/sections.py`
- Modify: `src/hypertensiondb/schema/__init__.py`
- Test: `tests/unit/test_loader.py`
- Test: `tests/unit/test_sections.py`
- Create: `tests/fixtures/schema/valid_rct.md`（以及其他 7 个 fixture）

- [ ] **Step 1: 创建 fixture md 文件**

Create `tests/fixtures/schema/valid_rct.md`:
```markdown
---
id: EV-RCT-2026-PENG-001
type: RCT
title:
  zh: 缬沙坦联合氨氯地平治疗中重度原发性高血压的多中心随机对照试验
  en: Valsartan plus amlodipine for moderate-to-severe hypertension
authors: [Peng Y, Liu J]
year: 2026
language: zh
doi: 10.1000/xyz001
full_text_status: complete
source: manual_cnki
ingested_at: 2026-05-19
status: draft
pico:
  population:
    condition: 原发性高血压
    sample_size: 612
  intervention:
    name: 缬沙坦 80mg + 氨氯地平 5mg
    drug_class: [ARB, CCB]
  comparison:
    name: 缬沙坦 80mg 单药
  outcomes:
    primary:
      - name: 收缩压下降幅度
        effect_size:
          metric: MD
          value: -8.4
          ci_low: -10.1
          ci_high: -6.7
          p: 0.001
    secondary: []
risk_of_bias:
  tool: RoB2
  overall: low
  domains: {}
grade:
  level: moderate
  reasons: [imprecision]
tags: [ARB, CCB, combination_therapy]
---

## 临床要点 / Clinical Bottom Line

缬沙坦联合氨氯地平较单药治疗可额外降低收缩压 8.4 mmHg（P<0.001），血压达标率提升42%。

## 中文摘要

本研究评价了缬沙坦联合氨氯地平治疗中重度原发性高血压的疗效与安全性。

## English Abstract

This study evaluated the efficacy and safety of valsartan combined with amlodipine.

## 背景 / Background

原发性高血压是心血管疾病的主要危险因素。

## 方法 / Methods

多中心、随机、双盲、平行对照设计，共纳入612例受试者。

## 结果 / Results

12周时联合组收缩压下降23.6±9.2 mmHg，单药组15.2±8.7 mmHg。

## 讨论 / Discussion

本研究在东亚人群中验证了ARB+CCB起始联合治疗的优效性。

## 结论 / Conclusion

缬沙坦联合氨氯地平较单药治疗可显著改善中重度高血压患者的血压控制。

## 参考文献 / References

1. Williams B, et al. 2018 ESC/ESH Guidelines. Eur Heart J. 2018;39:3021-3104.
```

Create `tests/fixtures/schema/invalid_bad_grade.md`:
```markdown
---
id: EV-RCT-2026-TEST-001
type: RCT
title:
  zh: 测试文献
authors: [Test A]
year: 2026
language: zh
pico:
  population:
    condition: 高血压
  intervention:
    name: 测试药物
  outcomes: {}
risk_of_bias:
  tool: RoB2
  overall: low
grade:
  level: super_high   # 非法枚举值
---
## 临床要点 / Clinical Bottom Line
无。
```

Create `tests/fixtures/schema/invalid_missing_id.md`:
```markdown
---
type: RCT
title:
  zh: 测试文献
authors: [Test A]
year: 2026
language: zh
pico:
  population:
    condition: 高血压
  intervention:
    name: 测试药物
  outcomes: {}
risk_of_bias:
  tool: RoB2
  overall: low
grade:
  level: moderate
---
## 临床要点 / Clinical Bottom Line
无。
```

- [ ] **Step 2: 写 sections 失败测试**

Create `tests/unit/test_sections.py`:
```python
import pytest
from pathlib import Path
from hypertensiondb.schema.sections import split_sections

FIXTURE = Path("tests/fixtures/schema/valid_rct.md")


@pytest.mark.unit
def test_split_returns_all_standard_sections():
    text = FIXTURE.read_text(encoding="utf-8")
    sections = split_sections(text)
    assert "clinical_bottom_line" in sections
    assert "background" in sections
    assert "methods" in sections
    assert "results" in sections
    assert "conclusion" in sections


@pytest.mark.unit
def test_section_content_is_not_empty():
    text = FIXTURE.read_text(encoding="utf-8")
    sections = split_sections(text)
    assert len(sections["results"].strip()) > 10


@pytest.mark.unit
def test_missing_section_returns_empty_string():
    sections = split_sections("## 结果 / Results\n内容")
    assert sections["abstract_zh"] == ""
```

- [ ] **Step 3: 实现 sections.py**

Create `src/hypertensiondb/schema/sections.py`:
```python
import re

# 从 Markdown ## 标题到标准 section key 的映射
_SECTION_MAP: list[tuple[re.Pattern, str]] = [
    (re.compile(r"临床要点|Clinical Bottom Line", re.I), "clinical_bottom_line"),
    (re.compile(r"中文摘要|摘要$", re.I),                 "abstract_zh"),
    (re.compile(r"English Abstract|Abstract$", re.I),    "abstract_en"),
    (re.compile(r"背景|Background", re.I),                "background"),
    (re.compile(r"方法|Methods?", re.I),                  "methods"),
    (re.compile(r"结果|Results?", re.I),                  "results"),
    (re.compile(r"讨论|Discussion", re.I),                "discussion"),
    (re.compile(r"结论|Conclusions?", re.I),              "conclusion"),
    (re.compile(r"参考文献|References?", re.I),           "references"),
]

_ALL_KEYS = {key for _, key in _SECTION_MAP}
_HEADING_RE = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)


def split_sections(markdown: str) -> dict[str, str]:
    """Split markdown body (after frontmatter) into standard section dict.

    Returns a dict with all standard section keys; missing sections → "".
    """
    result: dict[str, str] = {key: "" for _, key in _SECTION_MAP}

    # Strip YAML frontmatter if present
    if markdown.startswith("---"):
        end = markdown.find("\n---", 3)
        if end != -1:
            markdown = markdown[end + 4:]

    # Split on ## headings
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
```

- [ ] **Step 4: 跑 sections 测试**

Run: `pytest tests/unit/test_sections.py -v`
Expected: 3 passed

- [ ] **Step 5: 写 loader 失败测试**

Create `tests/unit/test_loader.py`:
```python
import pytest
from pathlib import Path
from hypertensiondb.schema.loader import load_evidence
from hypertensiondb.schema.rct import RctFrontmatter

VALID_RCT = Path("tests/fixtures/schema/valid_rct.md")
INVALID_GRADE = Path("tests/fixtures/schema/invalid_bad_grade.md")
INVALID_ID = Path("tests/fixtures/schema/invalid_missing_id.md")


@pytest.mark.unit
def test_load_valid_rct_returns_correct_type():
    fm, sections = load_evidence(VALID_RCT)
    assert isinstance(fm, RctFrontmatter)
    assert fm.id == "EV-RCT-2026-PENG-001"


@pytest.mark.unit
def test_load_valid_rct_sections_present():
    fm, sections = load_evidence(VALID_RCT)
    assert "clinical_bottom_line" in sections
    assert len(sections["results"]) > 0


@pytest.mark.unit
def test_load_invalid_grade_raises():
    with pytest.raises(Exception):
        load_evidence(INVALID_GRADE)


@pytest.mark.unit
def test_load_missing_id_raises():
    with pytest.raises(Exception):
        load_evidence(INVALID_ID)
```

- [ ] **Step 6: 实现 loader.py**

Create `src/hypertensiondb/schema/loader.py`:
```python
from pathlib import Path
from typing import Union
import frontmatter
from pydantic import ValidationError

from hypertensiondb.schema.base import EvidenceType
from hypertensiondb.schema.rct import RctFrontmatter
from hypertensiondb.schema.sr_meta import SrFrontmatter, MetaFrontmatter
from hypertensiondb.schema.guideline import GuidelineFrontmatter
from hypertensiondb.schema.tcm import TcmFrontmatter
from hypertensiondb.schema.sections import split_sections

AnyFrontmatter = Union[
    RctFrontmatter, SrFrontmatter, MetaFrontmatter, GuidelineFrontmatter, TcmFrontmatter
]

_TYPE_MODEL = {
    EvidenceType.RCT: RctFrontmatter,
    EvidenceType.SR: SrFrontmatter,
    EvidenceType.META: MetaFrontmatter,
    EvidenceType.GL: GuidelineFrontmatter,
    EvidenceType.TCM: TcmFrontmatter,
}


def load_evidence(path: Path) -> tuple[AnyFrontmatter, dict[str, str]]:
    """Parse an evidence .md file into (frontmatter model, sections dict).

    Raises ValidationError if frontmatter is invalid.
    Raises ValueError if evidence type is unknown.
    """
    raw = frontmatter.load(str(path))
    meta = dict(raw.metadata)
    body = raw.content

    ev_type_str = meta.get("type", "")
    try:
        ev_type = EvidenceType(ev_type_str)
    except ValueError:
        raise ValueError(f"Unknown evidence type '{ev_type_str}' in {path}")

    model_cls = _TYPE_MODEL[ev_type]
    fm = model_cls(**meta)
    sections = split_sections(body)
    return fm, sections
```

- [ ] **Step 7: 更新 schema __init__.py**

Edit `src/hypertensiondb/schema/__init__.py`:
```python
from hypertensiondb.schema.base import (
    BaseFrontmatter, EvidenceType, Language, Status, FullTextStatus
)
from hypertensiondb.schema.pico import EffectSize, Pico, Outcome
from hypertensiondb.schema.bias_grade import RiskOfBias, Grade, GradeLevel
from hypertensiondb.schema.rct import RctFrontmatter
from hypertensiondb.schema.sr_meta import SrFrontmatter, MetaFrontmatter
from hypertensiondb.schema.guideline import GuidelineFrontmatter, Recommendation
from hypertensiondb.schema.tcm import TcmFrontmatter
from hypertensiondb.schema.loader import load_evidence, AnyFrontmatter
from hypertensiondb.schema.sections import split_sections

__all__ = [
    "BaseFrontmatter", "EvidenceType", "Language", "Status", "FullTextStatus",
    "EffectSize", "Pico", "Outcome",
    "RiskOfBias", "Grade", "GradeLevel",
    "RctFrontmatter", "SrFrontmatter", "MetaFrontmatter",
    "GuidelineFrontmatter", "Recommendation",
    "TcmFrontmatter",
    "load_evidence", "AnyFrontmatter",
    "split_sections",
]
```

- [ ] **Step 8: 跑所有 schema + loader 测试**

Run: `pytest tests/unit/ -v`
Expected: 全部通过（约 20 tests）

- [ ] **Step 9: Commit**

```bash
git add src/hypertensiondb/schema/ tests/unit/test_loader.py tests/unit/test_sections.py \
        tests/fixtures/schema/
git commit -m "feat(schema): add loader, section splitter, and fixture md files"
```

---

## M2: 手工数据流 + Pre-commit Hook

### Task 2.1: new_evidence 交互式脚手架

**Files:**
- Create: `scripts/new_evidence.py`

- [ ] **Step 1: 实现 new_evidence.py**

Create `scripts/new_evidence.py`:
```python
#!/usr/bin/env python3
"""Interactive scaffold for new evidence entries."""
import sys
from pathlib import Path
from datetime import date

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import typer
from hypertensiondb.schema.base import EvidenceType
from hypertensiondb.utils.pinyin import to_first_author_pinyin
from hypertensiondb.utils.id_gen import next_id

_TYPE_DIR = {
    EvidenceType.RCT: "rcts",
    EvidenceType.SR: "systematic_reviews",
    EvidenceType.META: "meta_analyses",
    EvidenceType.GL: "guidelines",
    EvidenceType.TCM: "tcm",
}

TEMPLATE = """\
---
id: {ev_id}
type: {ev_type}
title:
  zh:
  en:
authors: []
year: {year}
language: zh
doi:
pmid:
full_text_status: complete
source: manual_pdf
ingested_at: {today}
status: draft
pico:
  population:
    condition:
    sample_size:
  intervention:
    name:
    drug_class: []
  comparison:
    name:
  outcomes:
    primary: []
    secondary: []
risk_of_bias:
  tool: RoB2
  overall:
  domains: {{}}
grade:
  level:
  reasons: []
tags: []
---

## 临床要点 / Clinical Bottom Line

（在此填写 1-3 句关键结论）

## 中文摘要

## English Abstract

## 背景 / Background

## 方法 / Methods

## 结果 / Results

## 讨论 / Discussion

## 结论 / Conclusion

## 参考文献 / References
"""

app = typer.Typer()


@app.command()
def main(
    ev_type: str = typer.Option(..., prompt="Evidence type (RCT/SR/META/GL/TCM)"),
    year: int = typer.Option(..., prompt="Publication year"),
    first_author: str = typer.Option(..., prompt="First author (Chinese name or English surname)"),
) -> None:
    ev_type_upper = ev_type.strip().upper()
    try:
        et = EvidenceType(ev_type_upper)
    except ValueError:
        typer.echo(f"Unknown type: {ev_type_upper}. Must be one of {list(EvidenceType)}")
        raise typer.Exit(1)

    pinyin = to_first_author_pinyin(first_author.strip())
    ev_id = next_id(ev_type_upper, year, pinyin)
    ev_dir = Path("evidence") / _TYPE_DIR[et]
    ev_dir.mkdir(parents=True, exist_ok=True)
    out_path = ev_dir / f"{ev_id}.md"

    content = TEMPLATE.format(
        ev_id=ev_id,
        ev_type=ev_type_upper,
        year=year,
        today=date.today().isoformat(),
    )
    out_path.write_text(content, encoding="utf-8")
    typer.echo(f"Created: {out_path}")
    typer.echo(f"ID: {ev_id}")


if __name__ == "__main__":
    app()
```

- [ ] **Step 2: 手动测试脚手架**

Run: `python scripts/new_evidence.py`
按提示输入 `RCT`, `2026`, `彭勇`
Expected: 生成 `evidence/rcts/EV-RCT-2026-PENG-001.md`（或下一个可用序号）

- [ ] **Step 3: Commit**

```bash
git add scripts/new_evidence.py
git commit -m "feat(scripts): add interactive new_evidence scaffold"
```

---

### Task 2.2: validate_evidence 脚本 + pre-commit 配置

**Files:**
- Create: `scripts/validate_evidence.py`
- Create: `.pre-commit-config.yaml`
- Test: `tests/integration/test_pre_commit_hook.py`

- [ ] **Step 1: 写 pre-commit 集成失败测试**

Create `tests/integration/test_pre_commit_hook.py`:
```python
import subprocess
import shutil
import pytest
from pathlib import Path

VALID_RCT = Path("tests/fixtures/schema/valid_rct.md")
INVALID_GRADE = Path("tests/fixtures/schema/invalid_bad_grade.md")


@pytest.mark.integration
def test_validate_valid_file_exits_0():
    result = subprocess.run(
        ["python", "scripts/validate_evidence.py", str(VALID_RCT)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.integration
def test_validate_invalid_file_exits_1():
    result = subprocess.run(
        ["python", "scripts/validate_evidence.py", str(INVALID_GRADE)],
        capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "grade" in result.stdout.lower() or "grade" in result.stderr.lower()


@pytest.mark.integration
def test_filename_id_mismatch_exits_1(tmp_path):
    """File named differently from its frontmatter id should fail."""
    content = Path("tests/fixtures/schema/valid_rct.md").read_text(encoding="utf-8")
    wrong_name = tmp_path / "EV-RCT-2099-WRONG-999.md"
    wrong_name.write_text(content, encoding="utf-8")
    result = subprocess.run(
        ["python", "scripts/validate_evidence.py", str(wrong_name)],
        capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "mismatch" in result.stdout.lower() or "mismatch" in result.stderr.lower()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/integration/test_pre_commit_hook.py -v -m integration`
Expected: FAIL with `FileNotFoundError` (脚本不存在)

- [ ] **Step 3: 实现 validate_evidence.py**

Create `scripts/validate_evidence.py`:
```python
#!/usr/bin/env python3
"""Validate evidence .md files — used by pre-commit and CI."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pydantic import ValidationError
from hypertensiondb.schema.loader import load_evidence

REQUIRED_SECTIONS = {"abstract_zh", "methods", "results", "conclusion"}


def validate_file(path: Path) -> list[str]:
    """Return list of error messages. Empty list = valid."""
    errors: list[str] = []

    # 1. Filename must match frontmatter id
    try:
        fm, sections = load_evidence(path)
    except ValidationError as e:
        return [f"Schema validation failed:\n{e}"]
    except Exception as e:
        return [f"Parse error: {e}"]

    expected_name = f"{fm.id}.md"
    if path.name != expected_name:
        errors.append(
            f"Filename mismatch: file is '{path.name}', frontmatter id is '{fm.id}' "
            f"(expected filename '{expected_name}')"
        )

    # 2. Required sections must be non-empty
    for section_key in REQUIRED_SECTIONS:
        if not sections.get(section_key, "").strip():
            errors.append(f"Required section '{section_key}' is empty or missing")

    return errors


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: validate_evidence.py <file.md> [file2.md ...]")
        sys.exit(1)

    any_failed = False
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.suffix == ".md":
            continue
        errors = validate_file(path)
        if errors:
            any_failed = True
            print(f"FAIL: {path}")
            for e in errors:
                print(f"  {e}")
        else:
            print(f"OK:   {path}")

    sys.exit(1 if any_failed else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑集成测试**

Run: `pytest tests/integration/test_pre_commit_hook.py -v -m integration`
Expected: 3 passed

- [ ] **Step 5: 配置 pre-commit**

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: validate-evidence
        name: Validate evidence markdown files
        entry: python scripts/validate_evidence.py
        language: system
        files: ^evidence/.*\.md$
        pass_filenames: true

      - id: evidence-id-uniqueness
        name: Check evidence ID uniqueness
        entry: python scripts/check_id_uniqueness.py
        language: system
        files: ^evidence/.*\.md$
        pass_filenames: false
```

- [ ] **Step 6: 实现 check_id_uniqueness.py**

Create `scripts/check_id_uniqueness.py`:
```python
#!/usr/bin/env python3
"""Check that all evidence IDs are unique across the evidence/ directory."""
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import frontmatter

EVIDENCE_ROOT = Path("evidence")


def main() -> None:
    ids: list[tuple[str, Path]] = []
    for md in EVIDENCE_ROOT.rglob("*.md"):
        if "_quarantine" in md.parts:
            continue
        try:
            raw = frontmatter.load(str(md))
            ev_id = raw.metadata.get("id", "")
            if ev_id:
                ids.append((ev_id, md))
        except Exception:
            pass

    counter = Counter(ev_id for ev_id, _ in ids)
    duplicates = [ev_id for ev_id, count in counter.items() if count > 1]

    if duplicates:
        print("Duplicate evidence IDs found:")
        for dup_id in duplicates:
            paths = [str(p) for ev_id, p in ids if ev_id == dup_id]
            print(f"  {dup_id}: {paths}")
        sys.exit(1)
    else:
        print(f"OK: {len(ids)} unique evidence IDs")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: 安装 pre-commit hook**

Run: `pre-commit install`
Expected: `pre-commit installed at .git/hooks/pre-commit`

- [ ] **Step 8: 验证 hook 生效**

用 `scripts/new_evidence.py` 生成一个测试 md，手动填写 title/methods/results/conclusion 后：
```bash
git add evidence/rcts/EV-RCT-2026-TEST-001.md
git commit -m "test: verify pre-commit hook"
```
Expected: pre-commit 运行 `validate-evidence` 和 `evidence-id-uniqueness`，commit 成功

- [ ] **Step 9: Commit**

```bash
git add scripts/validate_evidence.py scripts/check_id_uniqueness.py \
        .pre-commit-config.yaml tests/integration/test_pre_commit_hook.py
git commit -m "feat(quality): add validate_evidence script and pre-commit hooks"
```

---

### Task 2.3: 全部测试通过 + tests/conftest.py

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: 创建共享 conftest**

Create `tests/conftest.py`:
```python
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
```

- [ ] **Step 2: 跑全套单元测试**

Run: `pytest tests/unit/ -v --tb=short`
Expected: 全部通过（约 20 tests）

- [ ] **Step 3: 跑集成测试**

Run: `pytest tests/integration/ -v -m integration --tb=short`
Expected: 全部通过（3 tests）

- [ ] **Step 4: 最终整体测试**

Run: `pytest tests/ -v --tb=short -m "unit or integration"`
Expected: 全部通过，无 warnings

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add shared conftest with fixture paths"
```

---

## 自检（Self-Review）

**1. Spec 覆盖检查：**

| Spec 要求 | 对应 Task |
|-----------|----------|
| 目录结构（§3）| Task 0.2 |
| ID 约定 EV-{TYPE}-{YEAR}-{AUTHOR}-{NNN}（§3）| Task 1.1 (id_gen) |
| Pydantic 强约束 schema（§6）| Task 1.2-1.3 |
| PICO + effect_size + RoB + GRADE（§2）| Task 1.2-1.3 |
| 所有4种类型的 frontmatter（RCT/SR/META/GL/TCM）（§2）| Task 1.3 |
| `load_evidence()` 解析 md → 返回正确类型（§4）| Task 1.4 |
| Section splitter（§4 chunk pipeline 基础）| Task 1.4 |
| `new_evidence.py` 脚手架（§3）| Task 2.1 |
| filename vs id 一致性检查（§3, §6）| Task 2.2 |
| pre-commit hook（§6）| Task 2.2 |
| DOI/PMID 唯一性检查（§6）| Task 2.2 (check_id_uniqueness.py) |
| `_quarantine/` 隔离区（§6）| 目录已在 Task 0.2 创建；quarantine 写入逻辑在 Plan D（PDF ingest）中实现 |
| 必填节区非空校验（§6）| Task 2.2 (validate_evidence.py) |
| CLI `hdb` 框架（§5 隐含）| Task 0.4 |
| `status: draft 不入索引`（§4）| 在 Plan B 的 index pipeline 中实现（Task 2 无索引逻辑）|
| 黄金集（§7）| Plan C |
| `hdb publish` 强制人工复核（§6）| Plan E |

**2. Placeholder 扫描：** 无 TBD/TODO/类似表达。

**3. 类型一致性：**
- `to_first_author_pinyin(name: str) → str` 在 id_gen.py 中调用 ✓
- `next_id(ev_type, year, author_pinyin) → str` 在 new_evidence.py 中调用 ✓
- `load_evidence(path) → (AnyFrontmatter, dict[str, str])` 在 loader.py + test_loader.py + validate_evidence.py 中一致使用 ✓
- `split_sections(markdown: str) → dict[str, str]` 在 sections.py + test_sections.py + loader.py 一致 ✓

**4. 遗漏 gap：** `valid_sr.md`, `valid_meta.md`, `valid_guideline.md`, `valid_tcm.md` fixture 文件在 Task 1.4 Step 1 只创建了 `valid_rct.md`。补充：在同一步骤中创建其余 4 个类型的最小合法 fixture（只需要 frontmatter + 8 节区占位文字，格式与 `valid_rct.md` 平行）。这些文件在 Plan C 黄金集中会被用到。

---

## 执行完成标志

Plan A 完成时你应该能够：

1. `hdb --help` 显示 ingest / index / lint 三个子命令
2. `python scripts/new_evidence.py` → 交互式生成 md 骨架
3. `python scripts/validate_evidence.py evidence/rcts/EV-RCT-2026-PENG-001.md` → OK 或详细错误
4. `pytest tests/ -m "unit or integration"` → 全部通过
5. `git commit` 时 pre-commit 自动校验 evidence/ 下的 md 文件
