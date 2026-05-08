# Acquire Agent 重设计规范

**日期**: 2026-04-20
**范围**: Acquire 阶段（`acquire_agent.py` + `acquire_agent.txt` + `acquire_ranking.txt` + `pubmed_api.py` + `schema.py` 小改）
**不在本次范围内**: Acquire Judge 的格式适配；diagnostic_reasoning 子问题的多路检索

---

## 背景与目标

当前 Acquire 阶段存在以下问题：

1. **硬编码 PICO 格式**：从 `pico_query` 读取字段，无法处理 Ask 新架构输出的 `EBMQuery`（PIRD/PEO/Prognosis 格式）
2. **仅使用摘要**：PubMed 摘要信息有限，无法支撑 Appraise 阶段的完整 GRADE 评级
3. **无全文检索**：缺乏从 PMC 获取全文的能力，证据本体无法被利用
4. **过滤器映射依赖旧 `question_type`**：需适配新的 `route_type` 字段

目标：引入两段式检索（PubMed 发现 + PMC 全文获取）和混合 RAG（BM25 + Embedding），在 Listwise 排序前为每篇文章提取最相关段落，提升后续 Appraise 的证据质量。

---

## 新流程

```
EBMQuery（来自 Ask 阶段）
    ↓
[LLM 构建 Boolean 查询]  ← acquire_agent.txt（按 query_type 注入对应字段）
    ↓
PubMed 检索（max 20 篇，按 route_type 选过滤器）
    ↓
并行拉取 PMC 全文（有 pmcid 的文章，as_completed + timeout=10s/篇）
    无全文 → has_full_text=False，使用摘要作为 RAG 源
    有全文 → has_full_text=True，使用全文作为 RAG 源
    ↓
[混合 RAG 预处理]（所有 20 篇，每篇独立执行）
    query_string = " ".join(keywords)（拼接为单一查询串）
    BM25 初筛：Top-min(8, len(chunks)) 段落
    Embedding 精排：Top-min(3, len(bm25_top)) 段落 → 写入 key_sentences
    ↓
[候选集缩减]：按 RAG 相关性分数保留 Top-10
    ↓
[后处理分层]：has_full_text=True 的文章整体排在 has_full_text=False 之前
    ↓
[Listwise 排序]（≤10 篇，使用 key_sentences）
    ↓
Top-K 输出（key_sentences 随 Evidence 传给 Appraise）
```

---

## 一、EBMQuery 适配

### 过滤器映射更新

旧 `_FILTER_BY_QUESTION_TYPE` 替换为 `_FILTER_BY_ROUTE_TYPE`，同时保留旧映射作为兼容回退：

| route_type | 过滤器 | 说明 |
|---|---|---|
| `ebm_pico` | `_HSSS_FILTER` | RCT + SR，治疗/干预 |
| `ebm_pird` | `_DTA_FILTER` | 诊断准确性 |
| `ebm_peo` | `_OBSERVATIONAL_FILTER` | 观察性研究，病因/危险因素 |
| `ebm_prognosis` | `_OBSERVATIONAL_FILTER` | 观察性研究，预后 |
| 旧 `question_type` 字符串 | 原有映射 | 过渡期兼容 |

### 查询构建 prompt 字段注入（acquire_agent.txt）

按 `query_type` 注入不同字段标签：

| query_type | patient | primary_focus | comparator | outcome | 额外字段 |
|---|---|---|---|---|---|
| `pico` | Patient | Intervention | Comparison | Outcome | — |
| `pird` | Patient | Index Test | Reference Standard | Diagnostic Accuracy | — |
| `peo` | Patient | Exposure | —（不注入） | Outcome | — |
| `prognosis` | Patient | Prognostic Factor | —（不注入） | Outcome | time_horizon |

### Listwise ranking prompt（acquire_ranking.txt）

字段标签按 `query_type` 动态替换，不再硬编码"Intervention/Comparison"字样。

---

## 二、两段式检索

### Stage 1：PubMed 检索

现有逻辑保持不变。读取来源优先 `ebm_query`，回退 `pico_query`（兼容过渡期）。

### Stage 2：PMC 全文并行拉取

使用 `as_completed` 模式，每篇设置 10 秒超时，单篇失败不影响其余文章：

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def _fetch_full_texts(self, candidates: List[Evidence]) -> None:
    futures = {
        executor.submit(fetch_pmc_full_text, e.pmcid): e
        for e in candidates if e.pmcid
    }
    try:
        for future in as_completed(futures, timeout=30):
            evidence = futures[future]
            try:
                text = future.result(timeout=10)
                if text:
                    evidence.full_text = text
                    evidence.has_full_text = True
            except Exception:
                pass  # 单篇失败：保持 has_full_text=False，继续用摘要
    except TimeoutError:
        pass  # 整批30秒超时：已完成的文章保留结果，未完成的保持 has_full_text=False
```

`fetch_pmc_full_text(pmcid)` 新增于 `pubmed_api.py`，通过 PMC OA API 获取全文 XML 并解析为纯文本。

---

## 三、混合 RAG（BM25 Top-8 → Embedding Top-3）

### BM25-first 缺陷与缓解

BM25-first pipeline 在医学领域存在已知缺陷：同义词和缩写丰富（如 "myocardial infarction" vs "acute coronary syndrome"），词汇不匹配会导致语义相关段落被 BM25 过滤。

缓解措施（双管齐下）：
1. **BM25 阈值放宽**：初筛取 Top-8，给 embedding 更大候选池
2. **依赖 Ask 阶段 keywords 质量**：`EBMQuery.keywords` 要求包含 MeSH 词 + 同义词（Ask Judge 的 `has_synonyms_or_mesh` 已覆盖），BM25 查询串展开全部 keywords

### `_rag_extract` 实现（含完整边界处理）

```python
def _rag_extract(self, evidence: Evidence, query_terms: List[str]) -> Tuple[str, float]:
    """返回 (key_sentences, relevance_score)。
    relevance_score = 最高 embedding cosine similarity 分数（0.0 表示降级路径）。
    """
    source = evidence.full_text if evidence.has_full_text else (evidence.abstract or "")

    # 防御性检查
    if not source or not source.strip():
        return "", 0.0
    if not query_terms:
        return source[:1000], 0.0  # 降级：直接返回前段内容，分数为0

    chunks = self._chunk_text(source, chunk_size=512)

    # chunks 数量可能少于 top_n（如摘要只产生1个 chunk）
    bm25_top_n = min(8, len(chunks))
    bm25_top = bm25_retrieve(chunks, query_terms, top_n=bm25_top_n)

    # embedding 接收单一查询字符串，而非关键词列表
    query_string = " ".join(query_terms)
    rerank_top_n = min(3, len(bm25_top))
    reranked, top_score = self._embedding_rerank(bm25_top, query=query_string, top_n=rerank_top_n)
    # _embedding_rerank 返回 (List[str], float)，top_score 为最高 cosine similarity

    key_sentences = "\n---\n".join(reranked) if reranked else source[:1000]
    score = top_score if reranked else 0.0
    return key_sentences, score
```

**注意**：`_embedding_rerank` 需同时返回排序后的段落列表和最高相关性分数，供候选集缩减使用。

### Embedding 模型单例（线程安全）

```python
import threading
_model_lock = threading.Lock()
_embedding_model = None

def _get_embedding_model():
    global _embedding_model
    with _model_lock:
        if _embedding_model is None:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model
```

模块级单例 + 锁保护，多线程场景下安全。首次加载约 5-10 秒，模型文件约 80MB，从 HuggingFace Hub 下载（首次运行需网络）。离线部署时需提前下载并通过 `SENTENCE_TRANSFORMERS_HOME` 环境变量指定本地路径。

---

## 四、候选集缩减与后处理分层

### 候选集缩减（RAG 后，Listwise 前）

RAG 预处理完成后，20 篇候选按 `_rag_extract` 返回的 `relevance_score`（最高 embedding cosine similarity）降序保留 Top-10，避免 Listwise prompt 超出 context window：

```
20篇 × 3段 × ~512 tokens ≈ 30,000 tokens（超出大多数模型上限）
→ 缩减到 10篇 × 3段 × ~512 tokens ≈ 15,000 tokens（可控）
```

降级路径（`relevance_score=0.0`）的文章排在有分数的文章之后，保证有实际相关内容的文章优先进入 Listwise。

### 后处理分层（Listwise 后）

Listwise 排序完成后，强制将 `has_full_text=True` 的文章整体排在 `has_full_text=False` 之前，不依赖 prompt 指令：

```python
def _post_sort_by_full_text(self, ranked: List[Evidence]) -> List[Evidence]:
    full_text = [e for e in ranked if e.has_full_text]
    abstract_only = [e for e in ranked if not e.has_full_text]
    return full_text + abstract_only
```

Listwise 排序只负责各组内部的相关性排序，后处理保证全文组整体优先。

---

## 五、数据类变更

`Evidence`（`schema.py`）新增字段：

```python
has_full_text: bool = False   # 是否成功获取 PMC 全文
```

（`full_text` 和 `key_sentences` 字段已存在，无需新增）

---

## 六、新增依赖

| 库 | 用途 | 安装 |
|---|---|---|
| `rank-bm25` | BM25 检索 | `pip install rank-bm25` |
| `sentence-transformers` | Embedding 精排 | `pip install sentence-transformers` |

---

## 七、文件改动清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `src/agents/acquire_agent.py` | 修改 | EBMQuery 适配；PMC 拉取 + RAG 流程；过滤器映射更新；embedding 线程安全单例 |
| `src/config/prompts/acquire_agent.txt` | 修改 | 支持多格式字段注入（PICO/PIRD/PEO/Prognosis） |
| `src/config/prompts/acquire_ranking.txt` | 修改 | 字段标签按 `query_type` 动态适配 |
| `src/tools/pubmed_api.py` | 修改 | 新增 `fetch_pmc_full_text(pmcid)` 函数 |
| `src/state/schema.py` | 小改 | `Evidence` 新增 `has_full_text: bool = False` |
| `requirements.txt` | 小改 | 新增 `rank-bm25`、`sentence-transformers` |

---

## 明确不在本次范围内

- Acquire Judge 对 PIRD/PEO/Prognosis 格式的专属评分维度
- `diagnostic_reasoning` 子问题的多路并行检索
- Embedding 模型的替换或微调（使用默认 `all-MiniLM-L6-v2`）
- PMC 全文解析的边缘情况处理（付费文章、格式异常等）
