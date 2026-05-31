# HypertensionDB 证据库详细描述

---

## 一、整体架构

HypertensionDB 是一个独立部署的 FastAPI 服务，与主 ebm5a 项目通过 HTTP 解耦运行。它由三个物理层组成：

```
PDF / PubMed 原始文献
        ↓  (ingest pipeline + LLM frontmatter 抽取)
evidence/*.md  —— 463 篇结构化 Markdown 文件（长期存储层）
        ↓  (chunker → embedder + sparse vectorizer → Qdrant upsert)
Qdrant 向量数据库（本地 Docker，端口 6333）—— 检索层
        ↓  (hybrid search → reranker → aggregation)
GET /search API（FastAPI，端口 8000）—— 服务层
        ↓  (HTTP)
hypertension_rag_client.py → AcquireAgent
```

**部署**：Qdrant 以 Docker Compose 运行（镜像 qdrant/qdrant:v1.12.5，数据持久化到 `./data/qdrant`）；hypertensiondb FastAPI 服务通过 `hdb serve run` 启动。两个进程独立，FastAPI 通过 Python qdrant-client 与 Qdrant 通信。

---

## 二、文献存储层：Markdown 文件结构

每篇文献对应 `evidence/` 目录下一个 Markdown 文件，文件名即为 evidence_id。文件由两部分组成：YAML frontmatter（结构化元数据）+ 正文章节（原文内容）。

### 2.1 evidence_id 命名规则

格式：`EV-{TYPE}-{YEAR}-{AUTHOR_PINYIN}-{NNN}`

示例：`EV-RCT-2025-PENG-001`（2025 年 Peng 等人发表的 RCT，序号 001）。AUTHOR_PINYIN 由第一作者姓氏的拼音转换生成，NNN 为同类型同年同作者的序号，防止碰撞。

### 2.2 YAML Frontmatter 字段（所有类型共有）

```yaml
id: EV-RCT-2025-PENG-001
type: RCT                          # RCT / SR / META / GL / TCM
title:
  zh: "..."                        # 中文标题
  en: "..."                        # 英文标题
authors: [...]
year: 2025
language: en                       # en / zh / bilingual
journal: "NEJM"
doi: "..."
pmid: "..."
status: reviewed                   # draft / reviewed / published / retracted / quarantined
full_text_status: complete         # complete / abstract_only / section_partial
tags: [hypertension, drug-class:ACE-inhibitor, ...]
mesh_terms: [...]
clinical_questions: [...]
quality_score: 0.85                # 0.0–1.0
extracted_by: llm                  # api / llm / manual
study_type: RCT                    # 由 backfill_grade.py 从全文 Methods 章节提取
```

### 2.3 类型专属字段

**RCT / SR / META / TCM** 额外包含：
```yaml
pico:
  population: {condition: "原发性高血压", sample_size: 9361}
  intervention: {name: "强化降压 SBP<120", details: "..."}
  comparison: {name: "标准降压 SBP<140"}
  outcomes:
    - {name: "心血管事件", effect_size: {hr: 0.75, ci: "0.64-0.89", p: "<0.001"}}
risk_of_bias:
  tool: RoB2                       # RoB2 / ROBINS-I / AMSTAR2 / AGREE-II
  overall: low                     # low / some_concerns / high
  domains: {...}
grade:
  level: high                      # high / moderate / low / very_low
  reasons: [...]
# SR/META 额外字段：
included_studies: [EV-RCT-2023-LI-001, ...]
heterogeneity: {i_squared: 23.4, p: 0.18}
```

**GL（指南）额外包含：**
```yaml
recommendations:
  - text: "..."
    strength: Strong
    grade: Moderate
    note: "..."
target_population: "成人高血压患者"
scope: "高血压初始用药"
```

### 2.4 正文章节（8 个标准章节）

```markdown
## clinical_bottom_line
临床要点摘要（检索时 1.2x 权重加成）

## abstract_zh
中文摘要

## abstract_en
English abstract

## background
研究背景

## methods
方法学（study_type 的权威来源）

## results
主要结果数据

## discussion
讨论

## conclusion
结论

## references
参考文献
```

---

## 三、索引管道

将 Markdown 文件转化为 Qdrant 向量点的完整流程。

### 3.1 分块（Chunker）

`src/hypertensiondb/index/chunker.py` 按章节切分，规则如下：

1. 解析 frontmatter + 正文，按 `##` 标题识别章节边界
2. 每个章节的文本长度 ≤ 1500 字符：直接作为一个 chunk 输出
3. 超过 1500 字符：依次尝试按 `###` 子标题切分 → 按段落切分 → 最后按句子切分
4. 每个 chunk 生成 `EvidenceChunk`，`point_id` 为 `SHA1(evidence_id:section_name)` 的 UUID 形式，`section_name` 在同章节多 chunk 时追加 `_0`、`_1` 等后缀

每篇文献产生约 50–200 个 chunk。`is_clinical_bottom_line` 字段标记 `clinical_bottom_line` 章节，检索时触发分数加成。

### 3.2 嵌入（Embedder）

`src/hypertensiondb/index/embedder_openai.py`：

- **模型**：实际部署使用 **ZhipuAI 嵌入模型**（由 `.env` 中 `EMBEDDER=zhipu`、`EMBED_DIM=2048` 指定），**向量维度：2048**
- 备选：`text-embedding-3-large`（OpenAI，3072 维）、Voyage 等，通过环境变量切换
- 批量调用 API，返回 `list[list[float]]`

### 3.3 稀疏向量化（Sparse Vectorizer）

`src/hypertensiondb/index/sparse.py`：

1. 使用 jieba 对文本分词（中英文混合）
2. 过滤中文停用词（的、了、是等）
3. 计算 TF 权重：`count / sqrt(doc_length)`（词频归一化）
4. 哈希映射：`hash(term) % 2^16` 得到词索引（词表大小 65536）
5. 同索引处权重相加（碰撞处理）
6. 输出：`(indices: list[int], values: list[float])`，即稀疏向量

### 3.4 Qdrant 存储结构

Collection 名称：`"hypertension_evidence"`

**每个 Point 的完整结构：**

```
id:     UUID (SHA1 of evidence_id:section_name)
vector: {
    "dense":  [float × 2048]          # ZhipuAI embedding
    "sparse": SparseVector {
                  indices: [int, ...],    # 词索引（65536 空间）
                  values:  [float, ...]   # TF 权重
              }
}
payload: {
    # 来自 frontmatter 的文章级元数据
    "evidence_id":             "EV-RCT-2025-PENG-001"
    "type":                    "RCT"
    "year":                    2025
    "language":                "en"
    "status":                  "reviewed"
    "title_zh":                "..."
    "title_en":                "..."
    "tags":                    ["hypertension", ...]
    "grade_level":             "high"          # 由 backfill_grade.py 填充
    "rob_overall":             "low"           # 由 backfill_grade.py 填充
    "study_type":              "RCT"           # 由 backfill_grade.py 填充（全文 Methods 来源）

    # chunk 级字段
    "section_name":            "results_2"
    "text":                    "SBP<120 组的心血管事件率为..."
    "is_clinical_bottom_line": false
    "indexed_at":              "2026-05-22T10:30:00Z"
}
```

批量 upsert，每批 64 个点。增量索引通过比较文件修改时间与 `indexed_at` 时间戳实现（`hdb index update`），未变更文件跳过重嵌入。

---

## 四、检索系统

### 4.1 混合检索（Hybrid Search + RRF 融合）

`src/hypertensiondb/retrieval/hybrid.py`：

1. **稠密向量查询**：将用户查询字符串嵌入为 2048 维向量
2. **稀疏向量查询**：同一查询字符串经 jieba 分词后生成稀疏向量
3. **Qdrant Prefetch + RRF Fusion**：
   ```
   Prefetch[
     { query: dense_vector,  using: "dense",  limit: 50 },
     { query: sparse_vector, using: "sparse", limit: 50 }
   ]
   FusionQuery(fusion: RRF)  →  top_k_rerank=30
   ```
   RRF 公式：`score(d) = Σ 1/(k + rank_i(d))`（k=60 为常数），综合稠密排名和稀疏排名，无需手动调权重
4. 返回 30 个候选 chunk，附 RRF 融合分数

**为什么用混合检索**：纯稠密检索在中英文混合查询时跨语言语义匹配有噪声；纯稀疏（BM25）在医学同义词（如"心肌梗死"vs"AMI"）面前词汇不匹配严重。RRF 融合取两者之长，且无需标注数据调参。

### 4.2 Reranker

`src/hypertensiondb/retrieval/reranker_api.py`（API 模式）：

- **模型**：`BAAI/bge-reranker-v2-m3`，通过 HuatuoGPT gateway `/rerank` 端点调用
- **输入**：(query, [chunk_text₁, chunk_text₂, ...]) 的 cross-encoder 评分对
- **输出**：每个 chunk 的相关性浮点分数（0–1）
- **超时处理**：reranker 失败时 fallback 到 RRF 分数，`degraded=["rerank"]` 标志写入响应

Reranker 是从 mock 版本（直接返回 score=0）升级到 API 调用的关键改进（2026-05-22）。引入 API reranker 后，Q2（ARB+CCB）等原本因语义相关性判断失准导致死循环的问题全部消除。

### 4.3 临床要点加权

检索结果中，`is_clinical_bottom_line=True` 的 chunk 得分乘以 **1.2 倍**加成。临床要点章节是作者对研究结论最精炼的总结，对 Acquire 阶段最有直接参考价值。

### 4.4 /search API 的完整响应结构

```json
{
  "query": "ARB联合CCB治疗中重度原发性高血压的疗效",
  "took_ms": 320,
  "results": [
    {
      "evidence_id":   "EV-META-2023-CHO-001",
      "section":       "results_3",
      "score":         0.762,
      "rerank_score":  0.912,
      "snippet":       "ARB联合CCB在降低SBP方面较单药显著...",
      "is_clinical_bottom_line": false,
      "evidence_meta": {
        "title": {"zh": "...", "en": "..."},
        "type": "META",
        "year": 2023,
        "language": "en",
        "study_type":   "META_ANALYSIS",
        "grade_level":  "moderate",
        "rob_overall":  "some_concerns",
        "tags": ["hypertension", "drug-combination", "ARB", "CCB"]
      }
    }
  ],
  "facets": {
    "type":     {"RCT": 8, "META": 4, "SR": 3},
    "year":     {"2022": 3, "2023": 5, "2024": 7},
    "grade":    {"high": 4, "moderate": 9, "low": 2},
    "language": {"en": 12, "zh": 3}
  },
  "degraded": []
}
```

---

## 五、Pipeline 侧的聚合：Chunk → Paper+Passages

`hypertension_rag_client.py` 中的 `_aggregate()` 函数负责将 chunk 级结果转化为 pipeline 可用的 Evidence 对象：

**聚合逻辑（4 步）：**

1. **按 evidence_id 分组**：将 15 个 chunk（top_k=15）按所属文章归组
2. **组内按 rerank_score 排序**：每篇文章内部，chunk 按相关性分数降序
3. **截取前 N 个 Passage**（`max_passages_per_paper=3`）：每篇文章保留最相关的 3 个段落，构造 `Passage(section, snippet, score)` 对象
4. **按组最高分排序文章**（`max_papers=6`）：每篇文章的代表分数 = 组内最高 rerank_score；6 篇文章按此分数降序排列，超出截断

**输出的 Evidence 对象结构：**

```python
Evidence(
    evidence_id     = "EV-META-2023-CHO-001",
    title           = "ARB联合CCB治疗高血压的Meta分析",
    source          = "hypertensiondb",
    year            = 2023,
    language        = "en",
    tags            = ["hypertension", "ARB", "CCB"],
    relevance_score = 0.912,
    supporting_passages = [
        Passage(section="results_3",           snippet="...", score=0.912),
        Passage(section="clinical_bottom_line", snippet="...", score=0.887),
        Passage(section="discussion_1",        snippet="...", score=0.821),
    ],
    study_type   = "META_ANALYSIS",
    grade_level  = "moderate",
    rob_overall  = "some_concerns",
)
```

`study_type` 优先读取 payload 中的专属字段（GRADE 学术标准值），fallback 到文件分类 `type` 字段；`grade_level` 和 `rob_overall` 直接透传，None 时 Appraise Agent 从 passage 文本推断。

---

## 六、字段抽取：backfill_grade.py

`scripts/backfill_grade.py` 是一个离线批处理脚本，解决了文献入库时自动抽取结果精度不足的问题。

**问题背景**：文献入库时，LLM 基于摘要和部分文本抽取字段，而 Cochrane Handbook 明确规定研究设计类型应从全文 **Methods** 章节判断，而非从标题、摘要或文件分类标签推断。依赖入库时的自动抽取会导致：以观察性研究为主的 Meta 分析被误判为 High GRADE；文件标签"META"和 GRADE study_type"META_ANALYSIS（含RCT）"混用。

**执行流程：**

1. 遍历所有 `evidence/*.md` 文件（可按类型过滤）
2. 加载 frontmatter + 正文，提取 `methods` + `results` + `conclusion` 三章节（总长度上限 6000 字符）
3. 调用 LLM（`HuatuoGPT-3-32B-no-thinking`），prompt 要求从全文内容判断：
   - `study_type`：RCT / SYSTEMATIC_REVIEW / META_ANALYSIS / COHORT / CASE_CONTROL / GUIDELINE / NARRATIVE_REVIEW / CASE_REPORT
   - `rob_overall`：low / some_concerns / high
   - `grade_level`：high / moderate / low / very_low
4. 解析 JSON 响应，就地更新 YAML frontmatter
5. `--force-study-type` 参数可强制对已有值的文章重新提取（用于修正早期错误值）

**执行结果**：460/461 篇文章成功完成 backfill（1 篇因无 Methods 内容跳过）。完成后全量重建 Qdrant 索引（`hdb index rebuild --confirm`），使新字段写入 Qdrant payload。

---

## 七、文献入库流程

### 7.1 PDF 入库

```bash
hdb ingest pdf path/to/trial.pdf
```

1. **PDF 解析**（PyMuPDF/fitz）：逐页提取文本 + 元数据（页数、PDF metadata）
2. **文本清洗**：
   - 去除重复行（页眉页脚噪声，出现频率 >66% 的行）
   - 修复连字符断行（`Hyper-\nten` → `Hyperten`）
   - 合并断行（CJK 无空格合并，拉丁语加空格）
   - 归一化空白
3. **章节检测**（heuristic regex）：识别双语标题（"临床要点|Clinical Bottom Line"、"方法|Methods"等），无标题时全文归入 `results` 章节
4. **LLM 结构化抽取**：将清洗后文本 + 章节内容传给 LLM，提取完整 frontmatter（title、authors、year、PICO、risk_of_bias、grade 等），`status=draft`、`extracted_by=llm`
5. **ID 生成**：`next_id(type, year, pinyin)` 根据类型 + 年份 + 作者拼音自动递增序号
6. **Pydantic 验证**：字段格式、范围检查；失败则写入 `evidence/_quarantine/` 隔离目录
7. **写入 Markdown**：生成标准格式 evidence 文件，自动升级为 `reviewed` 状态以供立即索引

### 7.2 PubMed 批量入库

```bash
hdb ingest pubmed --pmid-list sprint.txt
hdb ingest pubmed --query "hypertension CCB RCT" --type RCT
```

1. NCBI ESearch API → PMID 列表
2. efetch API 获取摘要级元数据（title、authors、year、journal、DOI、PMID）
3. 识别有 PMC ID 的开放获取文章
4. PMC efetch API 下载 JATS XML 全文
5. `jats_to_evidence()` 转换：解析 `<article-meta>` + `<body>`，将 JATS section type 映射到标准 8 个章节
6. 写入 evidence 文件，`status=draft`，`extracted_by=api`

### 7.3 索引重建

修改 evidence 文件后需重建索引：

```bash
hdb index rebuild --confirm   # 全量重建
hdb index update              # 增量（对比 indexed_at 时间戳）
```

---

## 八、各阶段 Agent 对证据库的调用方式

### AcquireAgent（直接调用方）

```
EBMQuery（来自 Ask）
    ↓
LLM 调用（acquire_agent.txt prompt）
    → 输出：中英文混合自然语言 query
    ↓
hypertension_rag_client.search(query)
    → GET /search?q=<query>&top_k=15
    ↓
_aggregate()
    → 15 chunks → 6 篇 Evidence（每篇 ≤3 个 Passage）
    ↓
写入 WorkflowState["evidence_list"]
```

backtrack 时（`state["backtrack_reason"]` 有值），prompt 携带上一次失败说明，引导 LLM 生成更宽或更窄的检索词。

### AppraiseAgent（消费 evidence_list）

读取每个 Evidence 对象的：
- `supporting_passages`（section + snippet + score）：作为 LLM 评价证据质量的原始内容
- `study_type`（来自 payload backfill 值）：直接用于 GRADE 初始分计算，跳过 LLM 推断
- `grade_level`（来自 payload 预计算）：若有值，直接作为 GRADE 等级，绕过 `_compute_grade()` 函数
- `rob_overall`（来自 payload 预计算）：`some_concerns` → NOT_SERIOUS（不降级）；`high` → SERIOUS（降级 1 分）

### ApplyAgent（消费 evidence_list 和 grade_rationales）

读取每个 Evidence 的 `supporting_passages` 作为实际引用来源，生成 `[evidence_id / section]` 格式的内联引用。例如 Apply 输出中的 `[EV-META-2023-CHO-001 / results_3]` 即对应 hypertensiondb 中该文献 `results_3` chunk 的原文段落。

### AssessAgent（间接核查引用格式）

Assess 评价 Apply 输出的 `citation_validity` 维度：检查 `[evidence_id / section]` 引用的格式合法性，以及 evidence_id 是否出现在已知的 evidence_list 中，间接与 hypertensiondb 的 ID 体系对齐。

---

## 九、关键设计决策总结

| 决策 | 实现方式 | 原因 |
|------|---------|------|
| 按章节分块（非固定 token） | 最大 1500 字符，章节边界切分 | 保留文档语义结构；Methods 和 Results 不被截断混合 |
| 双路混合检索（dense + sparse） | Qdrant Prefetch + RRF 融合 | 覆盖语义检索（稠密）和关键词精确匹配（稀疏）两种需求 |
| BGE 交叉编码 reranker | API 调用 BAAI/bge-reranker-v2-m3 | 交叉编码器对 (query, passage) 联合建模，相关性判断比双编码器更准 |
| clinical_bottom_line 1.2x 加成 | Python 侧乘法修正 | 临床要点章节是结论精华，对生成推荐最直接有用 |
| Qdrant payload 存全量 frontmatter | 每个 chunk payload 带完整元数据 | 检索时直接获取文章元数据，无需二次查表 |
| study_type 从 Methods 全文提取 | backfill_grade.py + --force-study-type | Cochrane Handbook 学术标准；摘要层面无法可靠判断研究设计 |
| 预计算字段透传 pipeline | Qdrant payload → /search → Evidence 对象 | 避免 Appraise LLM 重复推断，保证全文级权威值优先 |
| Markdown 作为长期存储 | evidence/*.md 文件 | 人可读、可 git 版本管理、Qdrant 索引可随时从文件重建 |
