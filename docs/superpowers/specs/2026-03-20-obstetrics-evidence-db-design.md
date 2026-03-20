# 产科本地证据库设计文档

**日期**: 2026-03-20
**状态**: 待实现

---

## 背景与目标

当前系统通过 PubMed E-utilities API 实时检索文献，受限于：
- 只能获取 title + abstract，无全文
- 网络延迟高，每次查询需 3 次 API 调用
- 产科专科问题的检索精度依赖通用 Boolean 查询

目标：构建一个本地产科专科证据库，**替代** Acquire agent 中的 PubMed 检索流程，支持全文混合检索。

---

## 范围

- Demo 规模：~10 篇产科相关全文文献
- 数据来源：PMC Open Access（合法、免费、有全文 XML）
- 检索方式：BM25 关键词 + 向量语义，RRF 融合
- 集成方式：替代 `search_pubmed()`，对外接口保持兼容

**不在范围内**：
- 付费文献爬取
- 与 PubMed 并行双路检索
- 非产科问题的本地库支持

---

## 架构

### 组件

```
scripts/build_obstetrics_db.py   # 一次性建库脚本（爬取 + 解析 + 索引）
src/tools/local_evidence_db.py   # 检索接口（供 AcquireAgent 调用）
data/obstetrics_db/              # 原始全文 XML + 解析后 JSON
data/obstetrics_chroma/          # ChromaDB 向量索引
```

### 数据流

```
build_obstetrics_db.py
  └─ 1. 从 PMC 爬取产科文献全文 XML（PMCID 列表硬编码）
  └─ 2. 解析 XML → 提取 title/abstract/full_text/pmid/pmcid/authors/date
  └─ 3. 分块（chunk_size=512 tokens，overlap=64）
  └─ 4. 生成 embedding（all-MiniLM-L6-v2）→ 存入 ChromaDB
  └─ 5. 建 BM25 索引（rank_bm25 库）→ 序列化到 data/obstetrics_db/bm25.pkl

local_evidence_db.py
  └─ search(query, top_k=20)
       ├─ BM25 检索 → top-N 候选 + BM25 分数
       ├─ 向量检索（ChromaDB）→ top-N 候选 + 余弦相似度
       └─ RRF 融合 → 返回 List[Evidence]（与现有 schema 兼容）
```

---

## 数据模型

复用现有 `Evidence` dataclass，新增两个可选字段：

```python
@dataclass
class Evidence:
    # 现有字段（不变）
    title: str
    source: str
    pmid: Optional[str]
    abstract: str
    relevance_score: float
    study_type: Optional[str]
    publication_date: Optional[str]
    grade_level: Optional[str]
    # 新增
    pmcid: Optional[str] = None       # PMC 文章 ID
    full_text: Optional[str] = None   # 全文（仅本地库有）
```

---

## 检索算法

### BM25
- 库：`rank_bm25`
- 索引粒度：文章级（title + abstract + full_text 拼接）
- 分词：简单空格分词（英文足够）

### 向量检索
- 模型：`sentence-transformers/all-MiniLM-L6-v2`（384 维，本地运行）
- 索引：ChromaDB persistent client
- 索引粒度：512-token 分块，检索后聚合回文章级

### RRF 融合
```
rrf_score(d) = Σ 1 / (k + rank_i(d))，k=60
```
两路各取 top-20，RRF 合并后返回 top_k 篇。

---

## AcquireAgent 集成

修改 `acquire_agent.py`：

```python
# 新增导入
from src.tools.local_evidence_db import search_local

# execute() 中替换检索调用
if self._use_local_db(question_type):
    raw_results = search_local(query=base_query, top_k=20)
else:
    raw_results = search_pubmed(query=filtered_query, max_results=20)
```

`_use_local_db()` 判断逻辑：当前 demo 阶段始终返回 `True`（后续可按 question_type 或配置开关控制）。

---

## 建库脚本设计

`scripts/build_obstetrics_db.py` 接受一个 PMCID 列表（硬编码 10 个产科相关文章），执行：

1. `GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={pmcid}&retmode=xml`
2. 解析 JATS XML，提取结构化字段
3. 全文分块 + embedding
4. 写入 ChromaDB 和 BM25 索引

幂等：重复运行不重复写入（按 pmcid 去重）。

---

## 依赖

新增 Python 包：
```
rank-bm25
chromadb
sentence-transformers
```

---

## Demo 文献列表（初始 10 篇）

选取产科高影响力开放获取文献，覆盖：
- 妊娠期高血压/子痫前期
- 妊娠期糖尿病
- 产后出血
- 早产
- 剖宫产 vs 阴道分娩

具体 PMCID 在实现时确认（需验证 PMC OA 可访问性）。

---

## 风险与限制

| 风险 | 缓解 |
|------|------|
| PMC XML 结构不统一 | 解析器做容错，缺字段时降级到 abstract |
| embedding 模型首次下载慢 | 脚本提示用户，模型缓存到 `~/.cache/` |
| 10 篇样本召回率低 | 明确标注为 demo，后续扩库不改接口 |
| full_text 字段增大 Appraise prompt | Appraise agent 继续只用 abstract；full_text 仅用于检索阶段 |
