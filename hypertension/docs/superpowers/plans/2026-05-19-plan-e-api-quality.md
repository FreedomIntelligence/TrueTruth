# Plan E: API 采集 + 数据质量工具

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 PubMed/PMC OA 英文文献接入入库管线（`hdb ingest pubmed`），并提供 corpus-wide 质量工具（`hdb lint` / `hdb publish` / `hdb stats`）。`hdb publish` 强制人工复核才能把 LLM 抽出的 draft 提到 reviewed，落实设计文档 §6 "绝对不能错"字段。

**Architecture:** 三段 — `NCBIClient` 调 E-utilities（esearch 拿 PMID、efetch 拿 metadata 与 JATS XML）→ `jats_to_evidence` 把 JATS XML 转 frontmatter + 节区 dict → 复用 Plan D 的 `EvidenceWriter` 落盘。质量工具直接遍历 `evidence/**/*.md`，结合 Pydantic 校验 + 状态机检查。

**Tech Stack:** Python 3.11+, httpx>=0.27（已装，PubMed HTTP）, lxml>=5.0（JATS XML 解析）, pytest>=8.0。NCBI E-utilities 不需 API key，但带 key 速率 10/s（无 key 3/s），通过 env var `NCBI_API_KEY` 可选注入。

---

## 参考资料

- 设计文档 §4 管线 A、§6 错误处理、§8 实施分期 M7-M8：`docs/superpowers/specs/2026-05-19-hypertension-rag-design.md`
- E-utilities API: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
- JATS XML schema: https://jats.nlm.nih.gov/publishing/tag-library/
- Plan D 已实现：`EvidenceWriter.write_evidence_md`, `IngestPipeline`, `MockFrontmatterExtractor`, `BaseFrontmatterExtractor`

## 注意事项

- **不需要 git 操作**
- 所有 NCBI HTTP 调用必须通过 `unittest.mock.patch` 屏蔽 — 测试不依赖真实网络
- JATS 转出的 frontmatter 也走 `extracted_by="api"` 标记（区别于 LLM/Human），但首次入库依然 `status="draft"`
- `hdb publish` 拒绝把 `extracted_by="llm"` 的 draft 提升到 reviewed/published —— 必须先手工把字段改成 `extracted_by="human"` 或填 `reviewed_by`

## File Structure

```
pyproject.toml                                # 修改：加 lxml

src/hypertensiondb/
  ingest/
    ncbi_client.py                            # 新建：PubMed esearch/efetch + PMC OA efetch
    jats_converter.py                         # 新建：JATS XML → (frontmatter, sections)
  quality/
    __init__.py                               # 新建
    lint.py                                   # 新建：corpus-wide validation
    publish.py                                # 新建：draft → reviewed 升级器
    stats.py                                  # 新建：corpus health snapshot
  cli.py                                      # 修改：hdb ingest pubmed / hdb lint / hdb publish / hdb stats

tests/
  unit/
    test_ncbi_client.py                       # 新建
    test_jats_converter.py                    # 新建
    test_quality_lint.py                      # 新建
    test_quality_publish.py                   # 新建
    test_quality_stats.py                     # 新建
    test_cli_pubmed.py                        # 新建
  fixtures/
    jats/                                     # 新建：2 个 JATS XML fixture
      sample_oa_rct.xml
      sample_minimal.xml
```

---

## Task E.1: 依赖 + lxml 安装

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: 加 lxml 依赖**

在 `[project] dependencies` 末尾追加 `"lxml>=5.0"`：

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
    "lxml>=5.0",
]
```

- [ ] **Step 2: 安装**

Run: `py -m pip install -e ".[dev]" -q`
Expected: 安装成功，无 ERROR。

- [ ] **Step 3: 验证 lxml 可用**

Run: `py -c "from lxml import etree; print('lxml OK', etree.LXML_VERSION)"`
Expected: 输出 `lxml OK` + 版本号元组。

- [ ] **Step 4: 不破坏现有测试**

Run: `py -m pytest tests/unit/ --tb=line 2>&1 | tail -3`
Expected: 185 passed。

---

## Task E.2: NCBIClient — PubMed/PMC E-utilities 客户端

**Files:**
- Create: `src/hypertensiondb/ingest/ncbi_client.py`
- Test: `tests/unit/test_ncbi_client.py`

- [ ] **Step 1: 写测试**

Create `tests/unit/test_ncbi_client.py`:

```python
import pytest
from unittest.mock import MagicMock, patch

from hypertensiondb.ingest.ncbi_client import NCBIClient


_ESEARCH_XML = """<?xml version="1.0" encoding="UTF-8"?>
<eSearchResult>
  <Count>3</Count>
  <RetMax>3</RetMax>
  <IdList>
    <Id>39111111</Id>
    <Id>39222222</Id>
    <Id>39333333</Id>
  </IdList>
</eSearchResult>"""


_EFETCH_PUBMED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>39111111</PMID>
      <Article>
        <Journal>
          <Title>J Hypertens</Title>
        </Journal>
        <ArticleTitle>Test RCT on hypertension</ArticleTitle>
        <Abstract>
          <AbstractText>We studied combination therapy.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author>
            <LastName>Smith</LastName>
            <ForeName>John</ForeName>
          </Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">39111111</ArticleId>
        <ArticleId IdType="doi">10.1234/test</ArticleId>
        <ArticleId IdType="pmc">PMC9999999</ArticleId>
      </ArticleIdList>
      <History>
        <PubMedPubDate PubStatus="pubmed">
          <Year>2026</Year><Month>1</Month><Day>15</Day>
        </PubMedPubDate>
      </History>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>"""


@pytest.fixture
def mock_http():
    with patch("hypertensiondb.ingest.ncbi_client.httpx.Client") as MockClient:
        instance = MagicMock()
        MockClient.return_value.__enter__.return_value = instance
        yield instance


@pytest.mark.unit
def test_esearch_returns_id_list(mock_http):
    mock_resp = MagicMock(status_code=200)
    mock_resp.text = _ESEARCH_XML
    mock_http.get.return_value = mock_resp

    client = NCBIClient()
    ids = client.esearch(query="hypertension", db="pubmed", retmax=10)
    assert ids == ["39111111", "39222222", "39333333"]
    args, kwargs = mock_http.get.call_args
    assert "esearch" in args[0]
    assert kwargs["params"]["term"] == "hypertension"
    assert kwargs["params"]["db"] == "pubmed"
    assert kwargs["params"]["retmax"] == 10


@pytest.mark.unit
def test_esearch_passes_api_key_when_set(mock_http, monkeypatch):
    monkeypatch.setenv("NCBI_API_KEY", "test-key-abc")
    mock_resp = MagicMock(status_code=200)
    mock_resp.text = _ESEARCH_XML
    mock_http.get.return_value = mock_resp

    NCBIClient().esearch(query="x")
    _, kwargs = mock_http.get.call_args
    assert kwargs["params"]["api_key"] == "test-key-abc"


@pytest.mark.unit
def test_esearch_omits_api_key_when_unset(mock_http, monkeypatch):
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    mock_resp = MagicMock(status_code=200, text=_ESEARCH_XML)
    mock_http.get.return_value = mock_resp
    NCBIClient().esearch(query="x")
    _, kwargs = mock_http.get.call_args
    assert "api_key" not in kwargs["params"]


@pytest.mark.unit
def test_efetch_pubmed_parses_metadata(mock_http):
    mock_resp = MagicMock(status_code=200, text=_EFETCH_PUBMED_XML)
    mock_http.get.return_value = mock_resp

    records = NCBIClient().efetch_pubmed(["39111111"])
    assert len(records) == 1
    r = records[0]
    assert r["pmid"] == "39111111"
    assert r["doi"] == "10.1234/test"
    assert r["pmc_id"] == "PMC9999999"
    assert r["title"] == "Test RCT on hypertension"
    assert r["abstract"].startswith("We studied")
    assert r["authors"] == ["Smith J"]
    assert r["year"] == 2026
    assert r["journal"] == "J Hypertens"


@pytest.mark.unit
def test_efetch_pmc_xml_returns_raw(mock_http):
    fake_jats = "<?xml version='1.0'?><article><body/></article>"
    mock_resp = MagicMock(status_code=200, text=fake_jats)
    mock_http.get.return_value = mock_resp

    xml = NCBIClient().efetch_pmc_xml("PMC9999999")
    assert xml == fake_jats
    _, kwargs = mock_http.get.call_args
    assert kwargs["params"]["db"] == "pmc"
    assert kwargs["params"]["id"] == "9999999"  # PMC prefix stripped
    assert kwargs["params"]["rettype"] == "xml"


@pytest.mark.unit
def test_http_error_raises(mock_http):
    mock_resp = MagicMock(status_code=503)
    mock_resp.raise_for_status.side_effect = Exception("503 Server Error")
    mock_http.get.return_value = mock_resp
    with pytest.raises(Exception):
        NCBIClient().esearch(query="x")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_ncbi_client.py -v`
Expected: ModuleNotFoundError。

- [ ] **Step 3: 实现 ncbi_client.py**

Create `src/hypertensiondb/ingest/ncbi_client.py`:

```python
import os
from typing import Optional

import httpx
from lxml import etree


_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_ESEARCH_URL = f"{_EUTILS_BASE}/esearch.fcgi"
_EFETCH_URL = f"{_EUTILS_BASE}/efetch.fcgi"


class NCBIClient:
    """Thin client over NCBI E-utilities.

    Pass NCBI_API_KEY env var to get 10 req/s (vs 3 req/s without).
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def _params(self, **kwargs) -> dict:
        api_key = os.environ.get("NCBI_API_KEY")
        if api_key:
            kwargs["api_key"] = api_key
        return kwargs

    def esearch(self, query: str, db: str = "pubmed", retmax: int = 50) -> list[str]:
        """Search and return list of IDs (PMIDs or PMCIDs)."""
        with httpx.Client(timeout=self._timeout) as c:
            resp = c.get(_ESEARCH_URL, params=self._params(
                db=db, term=query, retmax=retmax, retmode="xml",
            ))
            resp.raise_for_status()
        root = etree.fromstring(resp.text.encode("utf-8"))
        return [el.text for el in root.findall(".//IdList/Id") if el.text]

    def efetch_pubmed(self, pmids: list[str]) -> list[dict]:
        """Fetch PubMed metadata for given PMIDs, return list of parsed dicts."""
        if not pmids:
            return []
        with httpx.Client(timeout=self._timeout) as c:
            resp = c.get(_EFETCH_URL, params=self._params(
                db="pubmed", id=",".join(pmids), rettype="xml", retmode="xml",
            ))
            resp.raise_for_status()
        return _parse_pubmed_xml(resp.text)

    def efetch_pmc_xml(self, pmc_id: str) -> str:
        """Fetch JATS XML for a PMC OA article. Returns raw XML string.

        Accepts 'PMC9999999' or '9999999' — strips the PMC prefix.
        """
        clean_id = pmc_id.removeprefix("PMC")
        with httpx.Client(timeout=self._timeout) as c:
            resp = c.get(_EFETCH_URL, params=self._params(
                db="pmc", id=clean_id, rettype="xml", retmode="xml",
            ))
            resp.raise_for_status()
        return resp.text


def _parse_pubmed_xml(xml_text: str) -> list[dict]:
    """Parse the PubMed efetch XML into a list of dicts."""
    root = etree.fromstring(xml_text.encode("utf-8"))
    records: list[dict] = []
    for art in root.findall(".//PubmedArticle"):
        rec: dict = {}
        rec["pmid"] = _text(art, ".//MedlineCitation/PMID")
        rec["title"] = _text(art, ".//ArticleTitle")
        rec["abstract"] = " ".join(
            t.text or "" for t in art.findall(".//Abstract/AbstractText")
        ).strip()
        rec["journal"] = _text(art, ".//Journal/Title")
        rec["doi"] = _id_by_type(art, "doi")
        rec["pmc_id"] = _id_by_type(art, "pmc")

        # Authors → "LastName F" format
        authors: list[str] = []
        for a in art.findall(".//AuthorList/Author"):
            last = _text(a, "LastName")
            fore = _text(a, "ForeName")
            initials = "".join(p[0] for p in (fore or "").split() if p)
            if last:
                authors.append(f"{last} {initials}".strip())
        rec["authors"] = authors

        # Year — prefer PubMedPubDate/pubmed, fall back to anything we can find
        year_str = _text(art, ".//PubMedPubDate[@PubStatus='pubmed']/Year") \
                   or _text(art, ".//PubDate/Year")
        rec["year"] = int(year_str) if year_str and year_str.isdigit() else None

        records.append(rec)
    return records


def _text(node, xpath: str) -> Optional[str]:
    el = node.find(xpath)
    return el.text.strip() if (el is not None and el.text) else None


def _id_by_type(art, id_type: str) -> Optional[str]:
    for el in art.findall(".//ArticleIdList/ArticleId"):
        if el.get("IdType") == id_type:
            return el.text
    return None
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_ncbi_client.py -v`
Expected: 6 passed。

---

## Task E.3: JATS XML → (frontmatter, sections) 转换器

**Files:**
- Create: `src/hypertensiondb/ingest/jats_converter.py`
- Test: `tests/unit/test_jats_converter.py`
- Test fixture: `tests/fixtures/jats/sample_oa_rct.xml`

- [ ] **Step 1: 创建 fixture JATS XML**

Create `tests/fixtures/jats/sample_oa_rct.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96)//EN" "JATS-archivearticle1.dtd">
<article article-type="research-article" xml:lang="en">
  <front>
    <journal-meta>
      <journal-title-group>
        <journal-title>Journal of Hypertension</journal-title>
      </journal-title-group>
    </journal-meta>
    <article-meta>
      <article-id pub-id-type="pmid">39111111</article-id>
      <article-id pub-id-type="pmc">PMC9999999</article-id>
      <article-id pub-id-type="doi">10.1234/jh.2026.001</article-id>
      <title-group>
        <article-title>Combination therapy for moderate hypertension: a randomized trial</article-title>
      </title-group>
      <contrib-group>
        <contrib contrib-type="author">
          <name><surname>Smith</surname><given-names>John</given-names></name>
        </contrib>
        <contrib contrib-type="author">
          <name><surname>Doe</surname><given-names>Jane M</given-names></name>
        </contrib>
      </contrib-group>
      <pub-date pub-type="epub">
        <year>2026</year><month>2</month><day>10</day>
      </pub-date>
      <abstract>
        <p>We evaluated ARB plus CCB versus ARB monotherapy in 612 patients with moderate hypertension. SBP fell by 8 mmHg more in the combination arm.</p>
      </abstract>
    </article-meta>
  </front>
  <body>
    <sec sec-type="intro">
      <title>Introduction</title>
      <p>Hypertension affects over 1 billion adults worldwide.</p>
    </sec>
    <sec sec-type="methods">
      <title>Methods</title>
      <p>Double-blind RCT. 612 patients randomized 1:1 to valsartan 80mg+amlodipine 5mg vs valsartan 80mg monotherapy.</p>
    </sec>
    <sec sec-type="results">
      <title>Results</title>
      <p>Mean SBP fell by 8.4 mmHg more in the combination arm (95% CI -10.1, -6.7, P&lt;0.001).</p>
    </sec>
    <sec sec-type="discussion">
      <title>Discussion</title>
      <p>Findings consistent with prior trials.</p>
    </sec>
    <sec sec-type="conclusions">
      <title>Conclusion</title>
      <p>Combination therapy outperforms ARB monotherapy in moderate hypertension.</p>
    </sec>
  </body>
</article>
```

- [ ] **Step 2: 创建 minimal fixture**

Create `tests/fixtures/jats/sample_minimal.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<article>
  <front>
    <article-meta>
      <title-group>
        <article-title>Tiny paper</article-title>
      </title-group>
      <contrib-group>
        <contrib contrib-type="author">
          <name><surname>Williams</surname><given-names>A</given-names></name>
        </contrib>
      </contrib-group>
      <pub-date><year>2024</year></pub-date>
    </article-meta>
  </front>
  <body/>
</article>
```

- [ ] **Step 3: 写测试**

Create `tests/unit/test_jats_converter.py`:

```python
import pytest
from pathlib import Path

from hypertensiondb.ingest.jats_converter import jats_to_evidence


FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "jats"


@pytest.fixture
def oa_rct_xml():
    return (FIXTURE_DIR / "sample_oa_rct.xml").read_text(encoding="utf-8")


@pytest.fixture
def minimal_xml():
    return (FIXTURE_DIR / "sample_minimal.xml").read_text(encoding="utf-8")


@pytest.mark.unit
def test_jats_extracts_title(oa_rct_xml):
    fm, _ = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    assert "Combination therapy" in fm["title"]["en"]


@pytest.mark.unit
def test_jats_extracts_authors(oa_rct_xml):
    fm, _ = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    # Surname + initials format
    assert "Smith J" in fm["authors"]
    assert any("Doe J" in a for a in fm["authors"])  # "Doe JM" or "Doe J"


@pytest.mark.unit
def test_jats_extracts_year(oa_rct_xml):
    fm, _ = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    assert fm["year"] == 2026


@pytest.mark.unit
def test_jats_extracts_ids(oa_rct_xml):
    fm, _ = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    assert fm["doi"] == "10.1234/jh.2026.001"
    assert fm["pmid"] == "39111111"


@pytest.mark.unit
def test_jats_extracts_journal(oa_rct_xml):
    fm, _ = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    assert fm["journal"] == "Journal of Hypertension"


@pytest.mark.unit
def test_jats_sets_language_en(oa_rct_xml):
    fm, _ = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    assert fm["language"] == "en"


@pytest.mark.unit
def test_jats_sets_status_draft_extracted_by_api(oa_rct_xml):
    fm, _ = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    assert fm["status"] == "draft"
    assert fm["extracted_by"] == "api"


@pytest.mark.unit
def test_jats_extracts_abstract_to_abstract_en(oa_rct_xml):
    _, sections = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    assert "612 patients" in sections["abstract_en"]


@pytest.mark.unit
def test_jats_maps_imrad_sections(oa_rct_xml):
    _, sections = jats_to_evidence(oa_rct_xml, evidence_type="RCT")
    assert "1 billion" in sections["background"]
    assert "valsartan 80mg" in sections["methods"]
    assert "8.4 mmHg" in sections["results"]
    assert "Findings consistent" in sections["discussion"]
    assert "outperforms" in sections["conclusion"]


@pytest.mark.unit
def test_jats_minimal_xml_returns_skeleton(minimal_xml):
    fm, sections = jats_to_evidence(minimal_xml, evidence_type="RCT")
    assert fm["title"]["en"] == "Tiny paper"
    assert fm["authors"] == ["Williams A"]
    assert fm["year"] == 2024
    assert fm["status"] == "draft"
    # No body → empty sections OK
    assert sections["methods"] == ""
    assert sections["results"] == ""
```

- [ ] **Step 4: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_jats_converter.py -v`
Expected: ModuleNotFoundError。

- [ ] **Step 5: 实现 jats_converter.py**

Create `src/hypertensiondb/ingest/jats_converter.py`:

```python
from typing import Optional

from lxml import etree


_SEC_TYPE_TO_KEY = {
    "intro": "background",
    "introduction": "background",
    "background": "background",
    "methods": "methods",
    "materials|methods": "methods",
    "results": "results",
    "discussion": "discussion",
    "conclusions": "conclusion",
    "conclusion": "conclusion",
}

_STANDARD_KEYS = [
    "clinical_bottom_line", "abstract_zh", "abstract_en",
    "background", "methods", "results", "discussion", "conclusion",
]


def jats_to_evidence(xml_text: str, evidence_type: str) -> tuple[dict, dict]:
    """Parse JATS XML into (frontmatter dict, sections dict).

    The frontmatter always carries status='draft' and extracted_by='api'.
    """
    root = etree.fromstring(xml_text.encode("utf-8"))

    fm: dict = {
        "type": evidence_type,
        "language": "en",
        "status": "draft",
        "extracted_by": "api",
        "authors": [],
        "tags": [],
    }

    # Title
    title_el = root.find(".//article-meta/title-group/article-title")
    title_en = _flatten_text(title_el) if title_el is not None else None
    fm["title"] = {"zh": None, "en": title_en or "Untitled"}

    # Authors
    for contrib in root.findall(".//article-meta/contrib-group/contrib[@contrib-type='author']"):
        surname = _text(contrib, ".//surname")
        given = _text(contrib, ".//given-names")
        if surname:
            initials = "".join(p[0] for p in (given or "").split() if p)
            fm["authors"].append(f"{surname} {initials}".strip())

    # Year — prefer epub, then ppub, then any pub-date
    year_str = (
        _text(root, ".//article-meta/pub-date[@pub-type='epub']/year")
        or _text(root, ".//article-meta/pub-date[@pub-type='ppub']/year")
        or _text(root, ".//article-meta/pub-date/year")
    )
    if year_str and year_str.isdigit():
        fm["year"] = int(year_str)

    # Journal
    journal = _text(root, ".//journal-meta//journal-title")
    if journal:
        fm["journal"] = journal

    # IDs
    for art_id in root.findall(".//article-meta/article-id"):
        id_type = art_id.get("pub-id-type")
        value = (art_id.text or "").strip()
        if not value:
            continue
        if id_type == "doi":
            fm["doi"] = value
        elif id_type == "pmid":
            fm["pmid"] = value
        elif id_type == "pmc":
            fm["url"] = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{value}/"

    # Sections
    sections: dict[str, str] = {k: "" for k in _STANDARD_KEYS}

    # Abstract → abstract_en
    abstract_paragraphs = root.findall(".//article-meta/abstract//p")
    if abstract_paragraphs:
        sections["abstract_en"] = "\n\n".join(
            _flatten_text(p) for p in abstract_paragraphs if _flatten_text(p)
        )

    # Body sections
    for sec in root.findall(".//body/sec"):
        sec_type = (sec.get("sec-type") or "").lower().strip()
        key = _SEC_TYPE_TO_KEY.get(sec_type)
        if not key:
            # Try to infer from <title>
            title = _text(sec, "title")
            if title:
                key = _infer_section_from_title(title)
        if not key:
            continue
        # Collect <p> children
        paras = [
            _flatten_text(p) for p in sec.findall(".//p")
            if _flatten_text(p)
        ]
        if paras:
            new_text = "\n\n".join(paras)
            if sections[key]:
                sections[key] = sections[key] + "\n\n" + new_text
            else:
                sections[key] = new_text

    return fm, sections


def _flatten_text(el) -> str:
    """Recursively extract all text content from an element."""
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def _text(node, xpath: str) -> Optional[str]:
    el = node.find(xpath)
    if el is not None and el.text:
        return el.text.strip()
    return None


def _infer_section_from_title(title: str) -> Optional[str]:
    """Map a section <title> string to a standard key."""
    t = title.lower().strip()
    if "method" in t or "材料" in t:
        return "methods"
    if "result" in t or "finding" in t:
        return "results"
    if "conclusion" in t or "summary" in t:
        return "conclusion"
    if "discussion" in t:
        return "discussion"
    if "introduction" in t or "background" in t:
        return "background"
    return None
```

- [ ] **Step 6: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_jats_converter.py -v`
Expected: 10 passed。

---

## Task E.4: `hdb ingest pubmed` CLI

**Files:**
- Modify: `src/hypertensiondb/cli.py`
- Test: `tests/unit/test_cli_pubmed.py`

- [ ] **Step 1: 写测试**

Create `tests/unit/test_cli_pubmed.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from hypertensiondb.cli import app

runner = CliRunner()


_PMC_JATS = """<?xml version="1.0"?>
<article xml:lang="en">
  <front>
    <article-meta>
      <article-id pub-id-type="pmid">39111111</article-id>
      <article-id pub-id-type="pmc">PMC9999999</article-id>
      <article-id pub-id-type="doi">10.1234/x</article-id>
      <title-group><article-title>API ingest test</article-title></title-group>
      <contrib-group><contrib contrib-type="author">
        <name><surname>Smith</surname><given-names>John</given-names></name>
      </contrib></contrib-group>
      <pub-date><year>2026</year></pub-date>
      <abstract><p>Test abstract content here.</p></abstract>
    </article-meta>
  </front>
  <body>
    <sec sec-type="methods"><title>Methods</title><p>Trial design here.</p></sec>
    <sec sec-type="results"><title>Results</title><p>SBP fell 8 mmHg.</p></sec>
    <sec sec-type="conclusions"><title>Conclusion</title><p>Effective.</p></sec>
  </body>
</article>"""


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_ROOT", str(tmp_path / "evidence"))
    return tmp_path


@pytest.mark.unit
def test_ingest_pubmed_writes_drafts(env):
    """pubmed search → 1 PMID with PMC OA → JATS → draft written."""
    mock_client = MagicMock()
    mock_client.esearch.return_value = ["39111111"]
    mock_client.efetch_pubmed.return_value = [{
        "pmid": "39111111", "doi": "10.1234/x", "pmc_id": "PMC9999999",
        "title": "API ingest test",
        "abstract": "Test abstract content here.",
        "authors": ["Smith J"], "year": 2026, "journal": "J Hyp",
    }]
    mock_client.efetch_pmc_xml.return_value = _PMC_JATS

    with patch("hypertensiondb.cli.NCBIClient", return_value=mock_client):
        result = runner.invoke(app, [
            "ingest", "pubmed", "--query", "hypertension", "--limit", "5",
            "--type", "RCT",
        ])

    assert result.exit_code == 0, result.output
    assert "1" in result.output  # 1 record ingested
    # File written under evidence/rcts/
    written = list((env / "evidence" / "rcts").rglob("EV-RCT-2026-*.md"))
    assert len(written) == 1


@pytest.mark.unit
def test_ingest_pubmed_skips_non_oa(env):
    """A PMID without pmc_id is skipped (no full-text source)."""
    mock_client = MagicMock()
    mock_client.esearch.return_value = ["39111111"]
    mock_client.efetch_pubmed.return_value = [{
        "pmid": "39111111", "doi": "10.1234/x", "pmc_id": None,
        "title": "Abstract only", "abstract": "x", "authors": ["A"],
        "year": 2026, "journal": "J",
    }]

    with patch("hypertensiondb.cli.NCBIClient", return_value=mock_client):
        result = runner.invoke(app, [
            "ingest", "pubmed", "--query", "x", "--limit", "5", "--type", "RCT",
        ])

    assert result.exit_code == 0, result.output
    assert "skipped" in result.output.lower() or "0 ingested" in result.output.lower()
    written = list((env / "evidence" / "rcts").rglob("EV-RCT-2026-*.md"))
    assert len(written) == 0


@pytest.mark.unit
def test_ingest_pubmed_no_results(env):
    mock_client = MagicMock()
    mock_client.esearch.return_value = []
    with patch("hypertensiondb.cli.NCBIClient", return_value=mock_client):
        result = runner.invoke(app, [
            "ingest", "pubmed", "--query", "nothing", "--type", "RCT",
        ])
    assert result.exit_code == 0
    assert "no results" in result.output.lower() or "0" in result.output
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_cli_pubmed.py -v`
Expected: 失败（命令未实现）。

- [ ] **Step 3: 修改 cli.py — 加 NCBIClient 顶层导入与 pubmed 子命令**

在 `src/hypertensiondb/cli.py` 顶部 `from hypertensiondb import __version__` 下方添加：

```python
from hypertensiondb.ingest.ncbi_client import NCBIClient
```

然后在 `@ingest_app.command("pdf")` 函数 **之后**（且在 `_build_ingest_pipeline` 之后）追加：

```python
@ingest_app.command("pubmed")
def ingest_pubmed(
    query: str = typer.Option(..., "--query", "-q", help="PubMed query"),
    since: int = typer.Option(None, "--since", help="Only papers since year YYYY"),
    limit: int = typer.Option(20, "--limit", help="Max records to fetch"),
    evidence_type: str = typer.Option("RCT", "--type", "-t",
                                      help="RCT|SR|META|GL|TCM"),
) -> None:
    """Search PubMed; for PMC OA hits, convert JATS → draft markdown."""
    from hypertensiondb.ingest.jats_converter import jats_to_evidence
    from hypertensiondb.ingest.writer import write_evidence_md
    from hypertensiondb.utils.id_gen import next_id
    from hypertensiondb.utils.pinyin import to_first_author_pinyin

    if evidence_type not in {"RCT", "SR", "META", "GL", "TCM"}:
        typer.echo(f"Invalid type: {evidence_type}")
        raise typer.Exit(1)

    full_query = query
    if since:
        full_query = f"({query}) AND {since}:3000[pdat]"

    client = NCBIClient()
    pmids = client.esearch(query=full_query, db="pubmed", retmax=limit)
    if not pmids:
        typer.echo("No results.")
        return

    records = client.efetch_pubmed(pmids)
    ev_root = Path(os.getenv("EVIDENCE_ROOT", "evidence"))

    ingested = 0
    skipped = 0
    for rec in records:
        if not rec.get("pmc_id"):
            typer.echo(f"  PMID {rec.get('pmid')}: no PMC OA — skipped")
            skipped += 1
            continue
        try:
            jats = client.efetch_pmc_xml(rec["pmc_id"])
            fm, sections = jats_to_evidence(jats, evidence_type=evidence_type)
            # Override frontmatter with PubMed metadata if present
            if rec.get("doi"): fm["doi"] = rec["doi"]
            if rec.get("pmid"): fm["pmid"] = rec["pmid"]
            if rec.get("journal"): fm["journal"] = rec["journal"]
            first_author = fm["authors"][0] if fm["authors"] else "Unknown"
            pinyin = to_first_author_pinyin(first_author)
            fm["id"] = next_id(evidence_type, fm.get("year", 2026), pinyin)
            write_evidence_md(frontmatter=fm, sections=sections, evidence_root=ev_root)
            typer.echo(f"  PMID {rec['pmid']}: ingested as {fm['id']}")
            ingested += 1
        except Exception as e:
            typer.echo(f"  PMID {rec.get('pmid')}: FAILED — {e}")
            skipped += 1

    typer.echo(f"Done. {ingested} ingested, {skipped} skipped.")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_cli_pubmed.py -v`
Expected: 3 passed。

---

## Task E.5: `hdb lint` — corpus-wide validation

**Files:**
- Create: `src/hypertensiondb/quality/__init__.py`
- Create: `src/hypertensiondb/quality/lint.py`
- Test: `tests/unit/test_quality_lint.py`

- [ ] **Step 1: 写测试**

Create `tests/unit/test_quality_lint.py`:

```python
import pytest
from pathlib import Path

from hypertensiondb.quality.lint import run_lint, LintReport, LintIssue


_VALID_FM = """---
id: EV-RCT-2026-VALID-001
type: RCT
title:
  zh: 测试
authors: [Test A]
year: 2026
language: zh
status: reviewed
pico:
  population: {condition: 高血压}
  intervention: {name: 测试}
  outcomes: {}
risk_of_bias: {tool: RoB2, overall: low}
grade: {level: moderate}
---

## 方法 / Methods

x x x

## 结果 / Results

y y y

## 结论 / Conclusion

z z z

## 中文摘要

abstract.
"""


_DUPLICATE_FM = _VALID_FM.replace("EV-RCT-2026-VALID-001", "EV-RCT-2026-DUP-001")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.mark.unit
def test_lint_clean_corpus_returns_no_issues(tmp_path):
    _write(tmp_path / "rcts" / "EV-RCT-2026-VALID-001.md", _VALID_FM)
    report = run_lint(evidence_root=tmp_path)
    assert isinstance(report, LintReport)
    assert report.total_files == 1
    assert report.issues == []


@pytest.mark.unit
def test_lint_detects_filename_id_mismatch(tmp_path):
    _write(tmp_path / "rcts" / "WRONG-NAME.md", _VALID_FM)
    report = run_lint(evidence_root=tmp_path)
    assert any(i.code == "filename_mismatch" for i in report.issues)


@pytest.mark.unit
def test_lint_detects_duplicate_doi(tmp_path):
    fm_with_doi = _VALID_FM.replace(
        "language: zh",
        "language: zh\ndoi: 10.1234/dup",
    )
    second = fm_with_doi.replace("EV-RCT-2026-VALID-001", "EV-RCT-2026-VALID-002")
    _write(tmp_path / "rcts" / "EV-RCT-2026-VALID-001.md", fm_with_doi)
    _write(tmp_path / "rcts" / "EV-RCT-2026-VALID-002.md", second)
    report = run_lint(evidence_root=tmp_path)
    assert any(i.code == "duplicate_doi" for i in report.issues)


@pytest.mark.unit
def test_lint_detects_pydantic_failure(tmp_path):
    """A file whose frontmatter is invalid (e.g. year out of range) is flagged."""
    bad = _VALID_FM.replace("year: 2026", "year: 1850")
    _write(tmp_path / "rcts" / "EV-RCT-2026-VALID-001.md", bad)
    report = run_lint(evidence_root=tmp_path)
    assert any(i.code == "schema_error" for i in report.issues)


@pytest.mark.unit
def test_lint_counts_drafts_in_summary(tmp_path):
    draft_fm = _VALID_FM.replace("status: reviewed", "status: draft")
    _write(tmp_path / "rcts" / "EV-RCT-2026-VALID-001.md", draft_fm)
    _write(tmp_path / "rcts" / "EV-RCT-2026-VALID-002.md",
           draft_fm.replace("VALID-001", "VALID-002"))
    report = run_lint(evidence_root=tmp_path)
    assert report.draft_count == 2


@pytest.mark.unit
def test_lint_skips_quarantine_directory(tmp_path):
    """Files under _quarantine/ are excluded from corpus lint."""
    _write(tmp_path / "_quarantine" / "bad.md", "garbage content not valid")
    _write(tmp_path / "rcts" / "EV-RCT-2026-VALID-001.md", _VALID_FM)
    report = run_lint(evidence_root=tmp_path)
    assert report.total_files == 1
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_quality_lint.py -v`
Expected: ModuleNotFoundError。

- [ ] **Step 3: 创建 quality/__init__.py**

Create `src/hypertensiondb/quality/__init__.py`:

```python
from hypertensiondb.quality.lint import run_lint, LintReport, LintIssue

__all__ = ["run_lint", "LintReport", "LintIssue"]
```

- [ ] **Step 4: 实现 lint.py**

Create `src/hypertensiondb/quality/lint.py`:

```python
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter
from pydantic import ValidationError

from hypertensiondb.schema.loader import load_evidence


@dataclass
class LintIssue:
    path: Path
    code: str
    detail: str


@dataclass
class LintReport:
    total_files: int = 0
    draft_count: int = 0
    reviewed_count: int = 0
    published_count: int = 0
    quarantined_count: int = 0
    issues: list[LintIssue] = field(default_factory=list)


def run_lint(evidence_root: Path) -> LintReport:
    """Walk evidence_root, validate every .md, return a summary report."""
    evidence_root = Path(evidence_root)
    report = LintReport()

    doi_seen: dict[str, list[Path]] = defaultdict(list)
    pmid_seen: dict[str, list[Path]] = defaultdict(list)
    id_seen: dict[str, list[Path]] = defaultdict(list)

    if not evidence_root.exists():
        return report

    for md in sorted(evidence_root.rglob("*.md")):
        if "_quarantine" in md.parts:
            continue
        report.total_files += 1

        # Parse frontmatter loosely first to spot non-schema issues
        try:
            raw = frontmatter.load(str(md))
        except Exception as e:
            report.issues.append(LintIssue(
                path=md, code="parse_error", detail=str(e),
            ))
            continue

        meta = dict(raw.metadata)
        fm_id = meta.get("id", "")

        # Filename vs id
        if fm_id and md.name != f"{fm_id}.md":
            report.issues.append(LintIssue(
                path=md, code="filename_mismatch",
                detail=f"file is '{md.name}' but frontmatter id is '{fm_id}'",
            ))

        # Pydantic full validate
        try:
            fm, _ = load_evidence(md)
            status = str(fm.status)
            if status == "draft":
                report.draft_count += 1
            elif status == "reviewed":
                report.reviewed_count += 1
            elif status == "published":
                report.published_count += 1
            elif status == "quarantined":
                report.quarantined_count += 1
        except (ValidationError, ValueError) as e:
            report.issues.append(LintIssue(
                path=md, code="schema_error", detail=str(e)[:300],
            ))
            continue

        # Cross-file duplicate trackers
        if fm_id:
            id_seen[fm_id].append(md)
        doi = meta.get("doi")
        if doi:
            doi_seen[doi].append(md)
        pmid = meta.get("pmid")
        if pmid:
            pmid_seen[pmid].append(md)

    # Emit duplicate issues
    for did, paths in id_seen.items():
        if len(paths) > 1:
            for p in paths:
                report.issues.append(LintIssue(
                    path=p, code="duplicate_id",
                    detail=f"id '{did}' also at: {[str(x) for x in paths if x != p]}",
                ))
    for doi, paths in doi_seen.items():
        if len(paths) > 1:
            for p in paths:
                report.issues.append(LintIssue(
                    path=p, code="duplicate_doi",
                    detail=f"doi '{doi}' also at: {[str(x) for x in paths if x != p]}",
                ))
    for pmid, paths in pmid_seen.items():
        if len(paths) > 1:
            for p in paths:
                report.issues.append(LintIssue(
                    path=p, code="duplicate_pmid",
                    detail=f"pmid '{pmid}' also at: {[str(x) for x in paths if x != p]}",
                ))

    return report
```

- [ ] **Step 5: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_quality_lint.py -v`
Expected: 6 passed。

---

## Task E.6: `hdb publish <id>` — 草稿提升器

**Files:**
- Create: `src/hypertensiondb/quality/publish.py`
- Test: `tests/unit/test_quality_publish.py`

- [ ] **Step 1: 写测试**

Create `tests/unit/test_quality_publish.py`:

```python
import pytest
from pathlib import Path

from hypertensiondb.quality.publish import publish_evidence, PublishError


_DRAFT_LLM = """---
id: EV-RCT-2026-PUB-001
type: RCT
title:
  zh: 测试
authors: [Test A]
year: 2026
language: zh
status: draft
extracted_by: llm
pico:
  population: {condition: 高血压}
  intervention: {name: 测试}
  outcomes: {}
risk_of_bias: {tool: RoB2, overall: low}
grade: {level: moderate}
---

## 方法 / Methods

x

## 结果 / Results

y

## 结论 / Conclusion

z

## 中文摘要

a
"""

_DRAFT_HUMAN_REVIEWED = _DRAFT_LLM.replace(
    "extracted_by: llm",
    "extracted_by: human",
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.mark.unit
def test_publish_rejects_llm_draft_without_review(tmp_path):
    _write(tmp_path / "rcts" / "EV-RCT-2026-PUB-001.md", _DRAFT_LLM)
    with pytest.raises(PublishError) as ei:
        publish_evidence("EV-RCT-2026-PUB-001", evidence_root=tmp_path,
                         target_status="reviewed")
    assert "human review" in str(ei.value).lower()


@pytest.mark.unit
def test_publish_accepts_human_extracted_to_reviewed(tmp_path):
    _write(tmp_path / "rcts" / "EV-RCT-2026-PUB-001.md", _DRAFT_HUMAN_REVIEWED)
    publish_evidence("EV-RCT-2026-PUB-001", evidence_root=tmp_path,
                     target_status="reviewed")
    content = (tmp_path / "rcts" / "EV-RCT-2026-PUB-001.md").read_text(encoding="utf-8")
    assert "status: reviewed" in content
    assert "status: draft" not in content


@pytest.mark.unit
def test_publish_accepts_llm_draft_with_reviewer_set(tmp_path):
    content = _DRAFT_LLM.replace(
        "extracted_by: llm",
        "extracted_by: llm\nreviewed_by: alice@example.com",
    )
    _write(tmp_path / "rcts" / "EV-RCT-2026-PUB-001.md", content)
    publish_evidence("EV-RCT-2026-PUB-001", evidence_root=tmp_path,
                     target_status="reviewed")
    new = (tmp_path / "rcts" / "EV-RCT-2026-PUB-001.md").read_text(encoding="utf-8")
    assert "status: reviewed" in new


@pytest.mark.unit
def test_publish_reviewed_to_published(tmp_path):
    reviewed = _DRAFT_HUMAN_REVIEWED.replace("status: draft", "status: reviewed")
    _write(tmp_path / "rcts" / "EV-RCT-2026-PUB-001.md", reviewed)
    publish_evidence("EV-RCT-2026-PUB-001", evidence_root=tmp_path,
                     target_status="published")
    content = (tmp_path / "rcts" / "EV-RCT-2026-PUB-001.md").read_text(encoding="utf-8")
    assert "status: published" in content


@pytest.mark.unit
def test_publish_not_found(tmp_path):
    with pytest.raises(PublishError) as ei:
        publish_evidence("EV-RCT-2099-NOSUCH-001", evidence_root=tmp_path,
                         target_status="reviewed")
    assert "not found" in str(ei.value).lower()


@pytest.mark.unit
def test_publish_invalid_target_status(tmp_path):
    _write(tmp_path / "rcts" / "EV-RCT-2026-PUB-001.md", _DRAFT_HUMAN_REVIEWED)
    with pytest.raises(PublishError):
        publish_evidence("EV-RCT-2026-PUB-001", evidence_root=tmp_path,
                         target_status="draft")  # can only go up the ladder
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_quality_publish.py -v`
Expected: ModuleNotFoundError。

- [ ] **Step 3: 实现 publish.py**

Create `src/hypertensiondb/quality/publish.py`:

```python
from pathlib import Path
from typing import Literal

import frontmatter


class PublishError(Exception):
    """Raised when a publish attempt fails."""


_VALID_TARGETS = {"reviewed", "published"}
_ALLOWED_TRANSITIONS = {
    ("draft", "reviewed"),
    ("reviewed", "published"),
    ("draft", "published"),  # skip review only if reviewed_by set
}


def _find_by_id(evidence_id: str, evidence_root: Path) -> Path | None:
    if not evidence_root.exists():
        return None
    matches = list(evidence_root.rglob(f"{evidence_id}.md"))
    return matches[0] if matches else None


def publish_evidence(
    evidence_id: str,
    evidence_root: Path,
    target_status: Literal["reviewed", "published"],
) -> Path:
    """Promote a draft/reviewed file to a higher status.

    Raises PublishError on any safety violation.
    """
    if target_status not in _VALID_TARGETS:
        raise PublishError(
            f"target_status must be one of {_VALID_TARGETS}, got {target_status!r}"
        )

    path = _find_by_id(evidence_id, evidence_root)
    if path is None:
        raise PublishError(f"Evidence not found: {evidence_id}")

    post = frontmatter.load(str(path))
    meta = dict(post.metadata)
    current = str(meta.get("status", "draft"))

    if (current, target_status) not in _ALLOWED_TRANSITIONS:
        raise PublishError(
            f"Cannot transition status {current!r} → {target_status!r}"
        )

    # The critical safety check from spec §6: LLM-extracted drafts MUST have
    # a human reviewer recorded before promotion.
    extracted_by = meta.get("extracted_by")
    reviewed_by = meta.get("reviewed_by")
    if extracted_by == "llm" and not reviewed_by:
        raise PublishError(
            f"Refusing to promote LLM-extracted draft without human review. "
            f"Set extracted_by='human' or reviewed_by=<name> before publishing."
        )

    meta["status"] = target_status
    post.metadata = meta
    path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return path
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_quality_publish.py -v`
Expected: 6 passed。

---

## Task E.7: `hdb stats` — corpus 健康快照

**Files:**
- Create: `src/hypertensiondb/quality/stats.py`
- Test: `tests/unit/test_quality_stats.py`

- [ ] **Step 1: 写测试**

Create `tests/unit/test_quality_stats.py`:

```python
import pytest
from pathlib import Path

from hypertensiondb.quality.stats import compute_stats, CorpusStats


_TEMPLATE = """---
id: {id}
type: {type}
title:
  zh: 测试
authors: [A]
year: {year}
language: {language}
status: {status}
pico:
  population: {{condition: 高血压}}
  intervention: {{name: 测试}}
  outcomes: {{}}
risk_of_bias: {{tool: RoB2, overall: low}}
grade: {{level: {grade}}}
---

## 方法 / Methods

x

## 结果 / Results

y

## 结论 / Conclusion

z

## 中文摘要

a
"""


def _write(tmp_path: Path, subdir: str, id_: str, **kwargs) -> None:
    defaults = {"type": "RCT", "year": 2026, "language": "zh",
                "status": "reviewed", "grade": "moderate"}
    defaults.update(kwargs)
    defaults["id"] = id_
    path = tmp_path / subdir / f"{id_}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_TEMPLATE.format(**defaults), encoding="utf-8")


@pytest.mark.unit
def test_stats_empty_corpus(tmp_path):
    stats = compute_stats(evidence_root=tmp_path)
    assert isinstance(stats, CorpusStats)
    assert stats.total == 0


@pytest.mark.unit
def test_stats_counts_by_type(tmp_path):
    _write(tmp_path, "rcts", "EV-RCT-2026-A-001", type="RCT")
    _write(tmp_path, "rcts", "EV-RCT-2026-A-002", type="RCT")
    _write(tmp_path, "meta_analyses", "EV-META-2026-A-001", type="META")
    stats = compute_stats(evidence_root=tmp_path)
    assert stats.total == 3
    assert stats.by_type == {"RCT": 2, "META": 1}


@pytest.mark.unit
def test_stats_counts_by_status(tmp_path):
    _write(tmp_path, "rcts", "EV-RCT-2026-A-001", status="draft")
    _write(tmp_path, "rcts", "EV-RCT-2026-A-002", status="reviewed")
    _write(tmp_path, "rcts", "EV-RCT-2026-A-003", status="published")
    stats = compute_stats(evidence_root=tmp_path)
    assert stats.by_status["draft"] == 1
    assert stats.by_status["reviewed"] == 1
    assert stats.by_status["published"] == 1


@pytest.mark.unit
def test_stats_counts_by_grade(tmp_path):
    _write(tmp_path, "rcts", "EV-RCT-2026-A-001", grade="high")
    _write(tmp_path, "rcts", "EV-RCT-2026-A-002", grade="moderate")
    _write(tmp_path, "rcts", "EV-RCT-2026-A-003", grade="moderate")
    stats = compute_stats(evidence_root=tmp_path)
    assert stats.by_grade == {"high": 1, "moderate": 2}


@pytest.mark.unit
def test_stats_counts_by_year(tmp_path):
    _write(tmp_path, "rcts", "EV-RCT-2026-A-001", year=2026)
    _write(tmp_path, "rcts", "EV-RCT-2025-A-001", year=2025)
    _write(tmp_path, "rcts", "EV-RCT-2024-A-001", year=2024)
    stats = compute_stats(evidence_root=tmp_path)
    assert stats.by_year[2026] == 1
    assert stats.by_year[2024] == 1


@pytest.mark.unit
def test_stats_skips_quarantine(tmp_path):
    _write(tmp_path, "rcts", "EV-RCT-2026-A-001")
    bad_dir = tmp_path / "_quarantine"
    bad_dir.mkdir()
    (bad_dir / "anything.md").write_text("garbage", encoding="utf-8")
    stats = compute_stats(evidence_root=tmp_path)
    assert stats.total == 1


@pytest.mark.unit
def test_stats_draft_pile_alert_threshold(tmp_path):
    """Pile-up alert triggers when drafts > 20% of corpus."""
    # 4 drafts, 1 reviewed = 80% drafts
    for i in range(4):
        _write(tmp_path, "rcts", f"EV-RCT-2026-A-{i:03d}",
               id=f"EV-RCT-2026-A-{i:03d}", status="draft")
    _write(tmp_path, "rcts", "EV-RCT-2026-X-001", status="reviewed")
    stats = compute_stats(evidence_root=tmp_path)
    assert stats.draft_pileup_alert is True
```

- [ ] **Step 2: 跑测试确认失败**

Run: `py -m pytest tests/unit/test_quality_stats.py -v`
Expected: ModuleNotFoundError。

- [ ] **Step 3: 实现 stats.py**

Create `src/hypertensiondb/quality/stats.py`:

```python
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter


_DRAFT_PILEUP_RATIO = 0.20


@dataclass
class CorpusStats:
    total: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    by_status: dict[str, int] = field(default_factory=dict)
    by_grade: dict[str, int] = field(default_factory=dict)
    by_year: dict[int, int] = field(default_factory=dict)
    by_language: dict[str, int] = field(default_factory=dict)
    draft_pileup_alert: bool = False


def compute_stats(evidence_root: Path) -> CorpusStats:
    """Walk evidence_root, return aggregate stats."""
    evidence_root = Path(evidence_root)
    stats = CorpusStats()
    if not evidence_root.exists():
        return stats

    type_c: Counter[str] = Counter()
    status_c: Counter[str] = Counter()
    grade_c: Counter[str] = Counter()
    year_c: Counter[int] = Counter()
    lang_c: Counter[str] = Counter()

    for md in sorted(evidence_root.rglob("*.md")):
        if "_quarantine" in md.parts:
            continue
        try:
            raw = frontmatter.load(str(md))
        except Exception:
            continue
        m = raw.metadata
        stats.total += 1

        if m.get("type"):
            type_c[str(m["type"])] += 1
        if m.get("status"):
            status_c[str(m["status"])] += 1
        if m.get("language"):
            lang_c[str(m["language"])] += 1
        grade = (m.get("grade") or {}).get("level") if isinstance(m.get("grade"), dict) else None
        if grade:
            grade_c[str(grade)] += 1
        year = m.get("year")
        if isinstance(year, int):
            year_c[year] += 1

    stats.by_type = dict(type_c)
    stats.by_status = dict(status_c)
    stats.by_grade = dict(grade_c)
    stats.by_year = dict(year_c)
    stats.by_language = dict(lang_c)

    drafts = status_c.get("draft", 0)
    if stats.total > 0 and drafts / stats.total > _DRAFT_PILEUP_RATIO:
        stats.draft_pileup_alert = True

    return stats
```

- [ ] **Step 4: 跑测试确认通过**

Run: `py -m pytest tests/unit/test_quality_stats.py -v`
Expected: 7 passed。

---

## Task E.8: CLI wire-up — `hdb lint` / `hdb publish` / `hdb stats`

**Files:**
- Modify: `src/hypertensiondb/cli.py`

- [ ] **Step 1: 替换占位 `lint run` 并加 publish/stats 子命令**

在 `src/hypertensiondb/cli.py` 中：

(a) 删除原有的：

```python
@lint_app.command("run")
def lint_run() -> None:
    """Placeholder — implemented in Plan E."""
    typer.echo("Not yet implemented (Plan E)")
```

(b) 替换为：

```python
@lint_app.command("run")
def lint_run() -> None:
    """Run corpus-wide validation: schema, filename, duplicates, draft pileup."""
    from hypertensiondb.quality.lint import run_lint

    ev_root = Path(os.getenv("EVIDENCE_ROOT", "evidence"))
    report = run_lint(ev_root)
    typer.echo(f"Total files: {report.total_files}")
    typer.echo(f"  draft={report.draft_count} reviewed={report.reviewed_count} "
               f"published={report.published_count}")
    if report.issues:
        typer.echo(f"\n{len(report.issues)} issues:")
        for issue in report.issues:
            typer.echo(f"  [{issue.code}] {issue.path}: {issue.detail}")
        raise typer.Exit(1)
    typer.echo("OK: no issues.")


@app.command("publish")
def publish_cmd(
    evidence_id: str = typer.Argument(..., help="Evidence ID like EV-RCT-2026-X-001"),
    to: str = typer.Option("reviewed", "--to", help="reviewed|published"),
) -> None:
    """Promote a draft/reviewed file to the next status (with safety checks)."""
    from hypertensiondb.quality.publish import publish_evidence, PublishError

    ev_root = Path(os.getenv("EVIDENCE_ROOT", "evidence"))
    try:
        path = publish_evidence(evidence_id, evidence_root=ev_root, target_status=to)
        typer.echo(f"OK: {evidence_id} → {to}")
        typer.echo(f"  {path}")
    except PublishError as e:
        typer.echo(f"FAILED: {e}")
        raise typer.Exit(2)


@app.command("stats")
def stats_cmd() -> None:
    """Print corpus health summary."""
    from hypertensiondb.quality.stats import compute_stats

    ev_root = Path(os.getenv("EVIDENCE_ROOT", "evidence"))
    s = compute_stats(ev_root)
    typer.echo(f"Total: {s.total}")
    typer.echo(f"  by type:   {s.by_type}")
    typer.echo(f"  by status: {s.by_status}")
    typer.echo(f"  by grade:  {s.by_grade}")
    typer.echo(f"  by year:   {s.by_year}")
    typer.echo(f"  by language: {s.by_language}")
    if s.draft_pileup_alert:
        typer.echo("\n⚠ DRAFT PILE-UP: more than 20% of files are draft. Run 'hdb lint' "
                   "and review them.")
```

- [ ] **Step 2: 验证 CLI 注册**

Run: `py -c "from hypertensiondb.cli import app; cmds = [c.name for c in app.registered_commands]; print('commands:', cmds); groups = [g.name for g in app.registered_groups]; print('groups:', groups)"`
Expected: commands 含 `publish`, `stats`；groups 含 `ingest`, `index`, `lint`, `serve`。

- [ ] **Step 3: 烟测 lint 命令**

Run: `EVIDENCE_ROOT=tests/golden/corpus py -m hypertensiondb.cli lint run 2>&1 | head -5` （PowerShell: `$env:EVIDENCE_ROOT="tests/golden/corpus"; py -m hypertensiondb.cli lint run`）
Expected: 报告 10 个文件，无 issues（golden corpus 是干净的）。

- [ ] **Step 4: 全单元回归**

Run: `py -m pytest tests/unit/ --tb=line 2>&1 | tail -3`
Expected: ~220+ passed（Plan A/B/C/D/E 累计）。

---

## Task E.9: 集成测试 — PubMed → JATS → md 端到端

**Files:**
- Create: `tests/integration/test_pubmed_ingest_e2e.py`

- [ ] **Step 1: 写测试**

Create `tests/integration/test_pubmed_ingest_e2e.py`:

```python
"""End-to-end: mock NCBI HTTP → hdb ingest pubmed → evidence/rcts/*.md → lint."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from hypertensiondb.cli import app
from hypertensiondb.quality.lint import run_lint
from hypertensiondb.quality.stats import compute_stats


_FAKE_JATS = """<?xml version="1.0"?>
<article xml:lang="en">
  <front>
    <article-meta>
      <article-id pub-id-type="pmid">39111111</article-id>
      <article-id pub-id-type="pmc">PMC9999999</article-id>
      <article-id pub-id-type="doi">10.5555/integration</article-id>
      <title-group><article-title>Integration test paper on hypertension</article-title></title-group>
      <contrib-group><contrib contrib-type="author">
        <name><surname>Chen</surname><given-names>Wei</given-names></name>
      </contrib></contrib-group>
      <pub-date><year>2026</year></pub-date>
      <abstract><p>Integration test abstract. Combination therapy vs monotherapy.</p></abstract>
    </article-meta>
  </front>
  <body>
    <sec sec-type="methods"><title>Methods</title><p>Double-blind RCT with 612 patients.</p></sec>
    <sec sec-type="results"><title>Results</title><p>SBP fell 8 mmHg in combination arm.</p></sec>
    <sec sec-type="conclusions"><title>Conclusion</title><p>Combination superior.</p></sec>
  </body>
</article>"""


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_ROOT", str(tmp_path / "evidence"))
    return tmp_path


@pytest.mark.integration
def test_pubmed_to_markdown_to_lint(env):
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.esearch.return_value = ["39111111"]
    mock_client.efetch_pubmed.return_value = [{
        "pmid": "39111111", "doi": "10.5555/integration", "pmc_id": "PMC9999999",
        "title": "Integration test paper on hypertension",
        "abstract": "Integration test abstract.",
        "authors": ["Chen W"], "year": 2026, "journal": "J Hyp",
    }]
    mock_client.efetch_pmc_xml.return_value = _FAKE_JATS

    with patch("hypertensiondb.cli.NCBIClient", return_value=mock_client):
        result = runner.invoke(app, [
            "ingest", "pubmed", "--query", "hypertension", "--type", "RCT",
        ])

    assert result.exit_code == 0, result.output
    written = list((env / "evidence" / "rcts").rglob("EV-RCT-2026-*.md"))
    assert len(written) == 1, f"output: {result.output}"

    # Lint the corpus — schema errors here would indicate a JATS → frontmatter bug
    report = run_lint(env / "evidence")
    schema_errors = [i for i in report.issues if i.code == "schema_error"]
    assert not schema_errors, f"schema errors: {schema_errors}"

    # Stats reflect the new draft
    stats = compute_stats(env / "evidence")
    assert stats.total == 1
    assert stats.by_status.get("draft", 0) == 1


@pytest.mark.integration
def test_publish_cli_flow(env):
    """draft → reviewed → published end-to-end via CLI."""
    runner = CliRunner()

    # Seed a draft file
    content = """---
id: EV-RCT-2026-CHEN-001
type: RCT
title:
  zh: 测试
authors: [Chen W]
year: 2026
language: zh
status: draft
extracted_by: human
pico:
  population: {condition: 高血压}
  intervention: {name: 测试}
  outcomes: {}
risk_of_bias: {tool: RoB2, overall: low}
grade: {level: moderate}
---

## 方法 / Methods

x

## 结果 / Results

y

## 结论 / Conclusion

z

## 中文摘要

a
"""
    f = env / "evidence" / "rcts" / "EV-RCT-2026-CHEN-001.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")

    # draft → reviewed
    r1 = runner.invoke(app, ["publish", "EV-RCT-2026-CHEN-001", "--to", "reviewed"])
    assert r1.exit_code == 0, r1.output
    assert "status: reviewed" in f.read_text(encoding="utf-8")

    # reviewed → published
    r2 = runner.invoke(app, ["publish", "EV-RCT-2026-CHEN-001", "--to", "published"])
    assert r2.exit_code == 0, r2.output
    assert "status: published" in f.read_text(encoding="utf-8")
```

- [ ] **Step 2: 跑集成测试**

Run: `py -m pytest tests/integration/test_pubmed_ingest_e2e.py -v -m integration --tb=short`
Expected: 2 passed。

- [ ] **Step 3: 全集成回归确认**

Run: `py -m pytest tests/integration/ -m integration --tb=line 2>&1 | tail -3`
Expected: 全部通过（累计 ~15 passed）。

---

## 自检（Self-Review）

**1. Spec 覆盖检查（设计 §4 + §6 + §8 M7-M8）：**

| 设计要求 | 对应 Task |
|---------|----------|
| PubMed E-utilities 集成 | E.2 + E.4 |
| PMC OA 全文 XML 接入 | E.2 + E.3 + E.4 |
| JATS → 标准 8 节区映射 | E.3 |
| LLM/API 抽出字段必须 status=draft | E.3 (jats_to_evidence 强制) |
| extracted_by 区分 llm/api/human | E.3 (api) + Plan D D.6 (llm) |
| `hdb lint`：schema + 唯一性 + draft 统计 | E.5 + E.8 |
| `hdb publish`：拒绝 LLM-draft 无人工复核 | E.6 + E.8 |
| `hdb stats`：corpus 健康 + draft 积压告警 | E.7 + E.8 |
| 不自动重抓 / 不自动修复 | 通过：所有命令都需手工触发，无后台 job |

**2. Placeholder 扫描：** 无 TBD/TODO。所有代码段完整。

**3. 类型一致性：**
- `NCBIClient.efetch_pubmed` 返回 `list[dict]` —— E.2 定义、E.4 使用 ✓
- `jats_to_evidence(xml, evidence_type) -> tuple[dict, dict]` —— E.3 定义、E.4 调用 ✓
- `LintReport.issues: list[LintIssue]`、`LintIssue.code/detail/path` —— E.5 定义、E.8 CLI 使用 ✓
- `publish_evidence(id, evidence_root, target_status)` —— E.6 定义、E.8 调用 ✓
- `CorpusStats.draft_pileup_alert: bool` —— E.7 定义、E.8 检查 ✓

**4. 已知折中：**
- **NCBI 真实 HTTP 集成测试缺失** —— 所有测试 mock httpx.Client，不验证真实 PubMed 响应解析。生产前用 `INGEST_EXTRACTOR=api hdb ingest pubmed --query "hypertension" --limit 3 --type RCT` 手动验一次。
- **JATS 转换非完美** —— `_SEC_TYPE_TO_KEY` 只覆盖标准 sec-type。出版社自定义的 sec-type（如 "patients-and-methods"）落到 `_infer_section_from_title` 兜底；遇到完全非标准的 JATS 会丢节区，但 frontmatter 仍能写出。
- **`hdb lint` 不调 crossref/PubMed 验证 DOI 真实性** —— spec §6 说"可选"，本期暂不实现，留给后续 lint-strict 模式。
- **stale draft 检测（>30 天）未实现** —— 需要 `ingested_at` 字段时间比较，spec §6 提到"draft 积压提醒"，目前只做了比例告警（>20%）。

---

## 执行完成标志

Plan E 完成时你应该能够：

1. `py -m pytest tests/unit/ --tb=line 2>&1 | tail -3` → 全部通过（累计 ~220 passed）
2. `py -m pytest tests/integration/ -m integration` → 全部通过（累计 ~15 passed）
3. `py -m pytest tests/golden/ -m golden` → 4 passed
4. `hdb --help` → 显示 `ingest`/`index`/`lint`/`serve`/`publish`/`stats` 全部命令
5. `hdb stats` → 打印 corpus 摘要
6. `hdb lint run` → 报告 issues 或 OK
7. `INGEST_EXTRACTOR=mock hdb ingest pubmed --query "hypertension" --limit 5 --type RCT`（mock 模式跑通；真实模式需 NCBI 网络）
8. 编辑某个 draft 文件设 `extracted_by: human`，跑 `hdb publish <id> --to reviewed` → 升级成功

至此整套 RAG 证据库（数据层 + 索引 + 检索 + 入库 + 采集 + 质量工具）齐备。
