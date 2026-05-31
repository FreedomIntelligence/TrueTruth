# 高血压证据库 RAG 系统设计

- **创建日期**: 2026-05-19
- **范围**: 本期仅做证据库 + 检索层，不含 LLM 问答 Demo
- **下游消费方**: 未来的"医疗循证系统"（临床问答 / 决策支持 / 文献综述辅助）

---

## 0. 目标与边界

### 目标

构建一个面向高血压病症的本地化 RAG 证据库。系统持有结构化的高血压相关循证医学文献全文，对下游"医疗循证系统"提供混合检索 API。

- 文献类型：随机对照试验 (RCT) / 系统评价 / Meta 分析 / 临床指南/专家共识 / 中医药与中西医结合文献
- 语言：中英文并重
- 规模：100-1000 篇
- 检索质量优先于检索速度（CPU 机器，单查询 1.5-3.5s 可接受）

### 明确不做的事

- 不做 LLM 问答 / 摘要生成 / Prompt 拼装 —— 由下游"医疗循证系统"负责
- 不做用户管理、权限、审计 —— 本地工具，假定可信网络
- 不做自动爬取付费数据库（CNKI/万方/维普）—— 法律/合规风险
- 不做自动版本管理与自动字段修复 —— LLM 自动修复医学事实会引入静默错误

### 数据采集现实

| 来源 | 自动获取率 | 方式 |
|------|-----------|------|
| PubMed / PMC OA / Europe PMC / Semantic Scholar / ClinicalTrials.gov（英文） | 元数据100% / 全文OA子集25-30% | 合规 API |
| 国际指南 (ESC/ESH, AHA/ACC, JNC) | 半自动，需注册下载 | 手工脚本辅助 |
| Cochrane SR 全文 | 0% | 机构订阅 + 手工下载 |
| CNKI / 万方 / 维普（中文核心库） | 0%（违反 ToS） | 机构订阅 + Zotero 半手动 |
| 中文指南 | ~50% | 学会官网手工下载 |
| 中医药文献 | 少量 OA | 主要手工 |

实际比例预估：完全自动约 25-35%（英文为主），半自动 10-15%（指南类），手工 50-60%（中文核心 + Cochrane + 中医药）。

---

## 1. 架构总览

三层 + 一个胶水，每层职责单一、可独立测试。

```
L3  检索层 (Retrieval Layer)
    FastAPI 服务 /search?q=...&filter=...
    Hybrid: 稠密向量召回 + 稀疏(BM25)召回 → RRF 融合 → reranker
    元数据过滤(PICO/年份/证据类型/GRADE 等级)
        ▲ 读取
L2  索引层 (Index Layer)
    Qdrant (Docker 本地) — 单 collection, dense+sparse 双索引
    Embedding 适配器 (interface)  ← 默认云API, 可换 BGE-m3 本地
    Reranker (本地 bge-reranker-v2-m3, ONNX Runtime CPU 优化)
        ▲ 全量重建 / 增量更新
L1  数据层 (Source of Truth)
    Markdown + YAML frontmatter (人类可读, Git 管理)
    原始 PDF/HTML 快照 (raw/)
    文献 ID 约定: EV-{类型}-{年份}-{首作者拼音}-{序号}
        ▲
胶水: 入库管线 (Ingestion Pipeline)
    ingest 子命令: parse → extract structured fields → write Markdown
    index 子命令: read Markdown → chunk by section → embed → upsert
    半自动: 英文走 API 批量, 中文走"手工放 PDF + 脚本辅助提取"
```

### 关键边界

1. **L1 = 权威数据源；L2 = 派生索引**。Markdown 是唯一真理；向量库随时可重建。
2. **数据格式选 Markdown 而非数据库**：人类可读、Git diff/review 友好、YAML frontmatter 提供结构化字段。
3. **L3 只暴露检索 API，不调 LLM**。下游自行拼 prompt。
4. **Embedding 与 Reranker 均为可插拔接口**。

---

## 2. 文档格式（Markdown + YAML frontmatter）

每篇文献 = 一个 `.md` 文件 = YAML frontmatter（结构化字段）+ 正文（节区化全文）。

### Frontmatter Schema（以 RCT 为例）

```yaml
---
# 1. 标识与溯源（所有类型共用）
id: EV-RCT-2026-PENG-001
type: RCT                          # RCT | SR | META | GUIDELINE | TCM
title:
  zh: 缬沙坦联合氨氯地平治疗中重度原发性高血压的多中心随机对照试验
  en: Valsartan plus amlodipine in moderate-to-severe primary hypertension...
authors: [Peng Y, Liu J, Wang X]
first_author_pinyin: peng
journal: Chinese Journal of Hypertension
year: 2026
language: zh                        # zh | en | bilingual
doi: 10.xxxx/xxxxx
pmid: 39xxxxxx
url: https://...
full_text_status: complete          # complete | abstract_only | section_partial
source: manual_cnki                 # pubmed_api | pmc_oa | manual_pdf | manual_cnki | ...
ingested_at: 2026-05-19
reviewed_by: null

# 2. PICO（RCT / SR / META 共用）
pico:
  population:
    condition: 原发性高血压
    severity: 中重度 (140-179/90-109 mmHg)
    age_range: 35-75
    sample_size: 612
    inclusion: [...]
    exclusion: [...]
  intervention:
    name: 缬沙坦 80mg/d + 氨氯地平 5mg/d
    drug_class: [ARB, CCB]
    dosage: ...
    duration_weeks: 12
  comparison:
    name: 缬沙坦 80mg/d 单药
  outcomes:
    primary:
      - name: 收缩压下降幅度 (mmHg)
        effect_size: {metric: MD, value: -8.4, ci_low: -10.1, ci_high: -6.7, p: 0.001}
      - name: 血压达标率
        effect_size: {metric: RR, value: 1.42, ci_low: 1.21, ci_high: 1.66}
    secondary:
      - name: 不良反应发生率
        effect_size: {metric: RR, value: 0.91, ci_low: 0.73, ci_high: 1.14, p: 0.42}

# 3. 偏倚与证据等级
risk_of_bias:
  tool: RoB2                        # RoB2 | ROBINS-I | AMSTAR2 | AGREE-II
  overall: low                      # low | some_concerns | high
  domains: {randomization: low, deviation: low, missing: some_concerns, ...}
grade:
  level: moderate                   # high | moderate | low | very_low
  reasons: [imprecision]

# 4. 检索标签
tags: [valsartan, amlodipine, ARB, CCB, combination_therapy, primary_hypertension]
mesh_terms: [Hypertension, Valsartan, Amlodipine]
clinical_questions:
  - ARB+CCB 联合 vs ARB 单药 在中重度高血压中的降压幅度
  - 联合治疗的不良反应风险

# 5. 状态管理
status: published                   # draft | reviewed | published | retracted | quarantined
quality_score: 0.85
---
```

### 正文节区（统一 8 节）

每个 `##` 标题下方放该节区的清洗后全文：

```
## 临床要点 / Clinical Bottom Line     ← 1-3 句中文要点，索引时高权重
## 中文摘要
## English Abstract
## 背景 / Background
## 方法 / Methods
  ### 研究设计 / 受试者 / 干预措施 / 结局指标 / 统计方法
## 结果 / Results
  ### 基线特征 / 主要结局 / 次要结局 / 不良事件
## 讨论 / Discussion
## 结论 / Conclusion
## 参考文献 / References
```

正文是真实的论文原文经解析清洗后逐节落盘，**不是占位符**。这就是被 chunk 进向量库的内容。

### 不同类型的 frontmatter 差异

| 字段 | RCT | SR/Meta | Guideline | TCM |
|------|-----|---------|-----------|-----|
| `pico` | ✓ | ✓（汇总） | ✗ | ✓+`tcm_syndrome` |
| `risk_of_bias.tool` | RoB2 | AMSTAR2 | AGREE-II | RoB2 (改良) |
| `meta_analysis` | — | I²/Q/亚组 | — | — |
| `recommendations` | — | — | 推荐条目+证据等级 | — |
| `tcm_syndrome` | — | — | — | 证型/方剂/君臣佐使 |
| `included_studies` | — | DOI列表 | 引用指南列表 | — |

Schema 用 Pydantic 模型强约束。

---

## 3. 目录布局 + ID 约定

### 目录结构

```
高血压证据库/
├── README.md
├── pyproject.toml
├── .env.example
├── docker-compose.yml
├── docs/
│   ├── superpowers/specs/
│   └── schema.md
├── evidence/                          # L1 权威数据源 (Git)
│   ├── rcts/                          # EV-RCT-*.md
│   ├── systematic_reviews/            # EV-SR-*.md
│   ├── meta_analyses/                 # EV-META-*.md
│   ├── guidelines/                    # EV-GL-*.md
│   ├── tcm/                           # EV-TCM-*.md
│   └── _quarantine/                   # 入库失败/未通过 validate
├── raw/                               # 原始 PDF/HTML (Git LFS 或 .gitignore)
├── data/                              # 派生 (.gitignore)
│   ├── qdrant/
│   ├── cache/
│   └── logs/
├── src/hypertensiondb/
│   ├── cli.py                         # `hdb` CLI 入口
│   ├── schema/                        # Pydantic models
│   ├── ingest/                        # PDF → Markdown
│   │   ├── parse_pdf.py
│   │   ├── clean.py
│   │   ├── section_mapper.py
│   │   └── frontmatter_extractor.py
│   ├── index/                         # Markdown → Qdrant
│   │   ├── chunker.py
│   │   ├── embedder.py                # 抽象接口
│   │   ├── embedder_openai.py
│   │   ├── embedder_zhipu.py
│   │   ├── embedder_bge_local.py
│   │   ├── sparse.py                  # BM25 sparse vector
│   │   └── qdrant_writer.py
│   ├── retrieval/
│   │   ├── hybrid.py                  # dense+sparse RRF
│   │   ├── reranker.py                # 抽象接口
│   │   ├── reranker_bge.py
│   │   ├── reranker_cohere.py
│   │   └── filters.py
│   ├── api/                           # FastAPI
│   │   ├── server.py
│   │   ├── routes_search.py
│   │   └── routes_evidence.py
│   └── utils/
│       ├── pinyin.py
│       └── id_gen.py
├── scripts/
│   ├── fetch_pubmed.py
│   ├── fetch_pmc_oa.py
│   ├── new_evidence.py
│   └── reindex_all.py
└── tests/
    ├── fixtures/
    ├── unit/
    ├── integration/
    └── golden/
```

### ID 约定

格式：`EV-{TYPE}-{YEAR}-{FIRST_AUTHOR_PINYIN_UPPER}-{NNN}`

- `EV`：固定前缀
- `TYPE` ∈ {`RCT`, `SR`, `META`, `GL`, `TCM`}
- `YEAR`：4 位发表年（非入库年）
- `FIRST_AUTHOR_PINYIN_UPPER`：首作者姓的大写拼音（中文用 pypinyin，英文用姓本身）；组织/学会用缩写（CHS, ESC, AHA, WHO）
- `NNN`：3 位序号，同 `{TYPE+YEAR+AUTHOR}` 下递增

示例：`EV-RCT-2026-PENG-001`, `EV-GL-2024-CHS-001`, `EV-GL-2023-ESC-001`

### 文件 vs ID 一致性

- 文件名 = `{ID}.md`，与 frontmatter.id 必须一致（pre-commit hook 校验）
- 新建走 `scripts/new_evidence.py` 自动算序号
- 退稿：不复用 ID，新 ID + 原 ID `status=retracted` + `superseded_by: 新ID`

### Git 追踪策略

| 目录 | Git? | 理由 |
|------|------|------|
| `evidence/**/*.md` | ✓ | 权威数据源 |
| `docs/`, `src/`, `scripts/`, `tests/` | ✓ | — |
| `raw/*.pdf` | ✗（Git LFS 可选） | 体积+版权 |
| `data/qdrant/` | ✗ | 派生 |
| `.env` | ✗ | secrets |

---

## 4. 数据流

### 管线 A：入库（raw → Markdown）

```
来源分流
  英文 API: PubMed / PMC OA / Europe PMC / Semantic Scholar
  手工: 用户把 PDF/Word 丢到 raw/incoming/
        ↓
Step 1: parse_pdf
  PDF/HTML → 文本 + 表格
  工具: Marker (优先) / MinerU (备选) / pypdf (fallback)
  输出: data/cache/parsed/{ID}.json
        ↓
Step 2: clean + section_map
  去页眉页脚 / 合并断行 / 修复断词
  启发式 IMRaD 结构 → 我们的 8 个标准 ## 节区
  启发式失败时 → LLM 辅助识别（仅这一步）
  输出: 草稿 Markdown（仅正文）
        ↓
Step 3: extract_frontmatter (LLM 辅助)
  抽 PICO / sample_size / effect_size / RoB / GRADE
  Pydantic 强约束
  失败 → 字段留空，status=draft
        ↓
Step 4: validate + write
  Pydantic validate
  ID 唯一性
  写入 evidence/{type}/{ID}.md
  默认 status=draft, 人工 review 后升 reviewed/published
```

CLI：

```
hdb ingest pdf raw/incoming/PENG_2026.pdf --type RCT
hdb ingest pubmed --query "hypertension AND combination therapy" --since 2024 --limit 50
hdb ingest dry-run raw/incoming/PENG_2026.pdf
```

### 管线 B：索引（Markdown → Qdrant）

```
扫描 evidence/**/*.md
  只索引 status ∈ {reviewed, published}（draft 不入索引）
        ↓
chunk by ## 节区
  1 节区 = 1 chunk；超长 (>1500 token) 按 ### 切
  metadata = frontmatter + {section_name, char_range}
  "临床要点" 节区打 boost 标志
        ↓
并行两路
  dense: Embedder 接口生成稠密向量
  sparse: BM25 sparse vector (jieba 中文 + 英文混合)
        ↓
Qdrant upsert
  collection: hypertension_evidence
  vector: {dense, sparse}
  payload: 全部 frontmatter + chunk 元数据
  point_id = sha1(evidence_id + section_name)  ← 幂等
```

CLI：

- `hdb index update` 增量（对比 mtime + Qdrant 已有 ID 集合）
- `hdb index rebuild --confirm` 删 collection 重建（换 embedder 或 chunk 策略时用）

### 读取流：检索

```
GET /search?q=...&type=RCT&grade_min=high
        ↓
filter 组装 (type/grade/year/language/tags)
query embed (dense + sparse)
        ↓
Qdrant hybrid: dense top50 + sparse top50 → RRF → top30
        ↓
Reranker (bge-reranker-v2-m3, 本地) 30 → top_k=10
"临床要点" 节区 score × 1.2 加权
        ↓
组装响应 + facets
```

### 三条管线的关系

- 管线 A 与 B **完全解耦**：可分别独立运行
- A 半自动，B 全自动
- 检索层只读 Qdrant，不直接读 Markdown；响应带 `evidence_id`，下游可二次 `/evidence/{id}` 取详情

---

## 5. 检索 API

FastAPI，4 个端点，UTF-8 JSON，错误用 RFC 7807。

### `GET /search`（核心端点）

**Query 参数**：

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `q` | str (必填) | — | 自然语言 query |
| `top_k` | int | 10 | rerank 后返回数 |
| `type` | csv | 全部 | RCT,SR,META,GL,TCM |
| `language` | csv | 全部 | zh,en |
| `year_min` / `year_max` | int | — | 发表年范围 |
| `grade_min` | enum | — | very_low/low/moderate/high |
| `tags` | csv | — | 命中其一 |
| `section` | csv | 全部 | 限定节区 |
| `include_draft` | bool | false | — |
| `expand_evidence` | bool | false | 响应内嵌完整 frontmatter |

**响应**：

```json
{
  "query": "...",
  "took_ms": 412,
  "results": [
    {
      "evidence_id": "EV-RCT-2026-PENG-001",
      "section": "结果/主要结局",
      "score": 0.87,
      "rerank_score": 0.91,
      "snippet": "...（最长 800 字符）",
      "evidence_meta": {
        "title": {"zh": "...", "en": "..."},
        "type": "RCT", "year": 2026, "language": "zh",
        "grade": {"level": "moderate"},
        "risk_of_bias": {"tool": "RoB2", "overall": "low"},
        "pico": { ... }
      }
    }
  ],
  "facets": {
    "type": {"RCT": 6, "META": 3, "GL": 1},
    "year": {"2026": 2, "2025": 5},
    "grade": {"high": 4, "moderate": 5, "low": 1}
  },
  "degraded": []
}
```

### 关键设计点

- **chunk 级返回，不在服务端合并文献** —— 下游决定
- snippet 最长 800 字符
- facets 总返回
- filter 语义：字段间 AND，字段内 OR
- PICO **只做过滤，不做语义检索**

### 其他端点

- `GET /evidence/{id}` —— 单篇完整 frontmatter + 切好的 sections + 原始 markdown URL
- `GET /evidence?type=RCT&tags=ARB&year_min=2024&sort=year_desc` —— 纯元数据过滤列表查询
- `GET /health` —— Qdrant / Embedder / Reranker 状态 + collection 大小

### 性能预期（CPU 机器，1000 篇）

| 步骤 | 耗时 |
|------|------|
| embed query (云 API) | 300-600ms |
| Qdrant hybrid search | 30-80ms |
| Reranker (30 chunks) | 800-2500ms |
| 总体 | 1.5-3.5s |

优化旋钮：`top_k_rerank` 可调小；reranker 可后期换 ONNX int8 或上 GPU。

---

## 6. 错误处理 & 数据质量

### L1 数据层：写入失败 → 隔离不污染

| 失败 | 处理 |
|------|------|
| PDF 解析报错 / 文本量异常 (<500 字符) | PDF 移到 `raw/_failed/`，附 error.log |
| Pydantic 校验失败 | 写到 `evidence/_quarantine/`，status=`quarantined`，不索引 |
| LLM 抽 PICO 结构不合规 | 字段留空，status=draft，不索引 |
| ID 冲突 | 拒绝写入 |
| 必填字段缺失 | 拒绝写入 |

原则：**宁缺毋滥**。

### L2 索引层：失败可重试、永远幂等

| 失败 | 处理 |
|------|------|
| Embedder API 超时/429 | 指数退避 3 次 (1s/4s/16s)；仍失败 → 写 `data/logs/index_failed.jsonl`，下次 update 自动补 |
| Embedder 维度变化（换模型未重建） | 启动时检查 collection 配置；不一致拒绝写入，提示 rebuild |
| Qdrant 不可用 | 快速失败，提示检查 docker compose |
| chunk 内容空 / 全脚注 | 跳过 |
| 同节区重复索引 | sha1 point_id 保证 upsert 幂等 |

### L3 检索层：永不返回 500，能降级就降级

| 失败 | 处理 |
|------|------|
| Embedder 超时 | 跳过 dense 路，纯 sparse 检索，`degraded: ["dense"]` |
| Reranker 失败 | 按 RRF 分数返回，`degraded: ["rerank"]` |
| Qdrant 不可用 | 503 + 明确 message |
| query 空 / 过长 (>500 字符) | 400 |
| 0 结果 | 200 + `results: []` |

### 数据质量保障

**入库前**：

1. Pydantic 强约束（effect_size 数字、grade 枚举、年份 1900-当前）
2. DOI/PMID 唯一性检查
3. LLM 抽出字段打 `_extracted_by: llm`；人工复核改 `human`

**入库后**：

4. pre-commit hook：文件名 vs id、frontmatter YAML、节区完整性、必填字段
5. `hdb lint`：crossref DOI 验证（可选）、PICO 与正文一致性抽样、draft 积压提醒
6. **黄金集回归测试**：`tests/golden/queries.jsonl` 维护 30-50 条临床问题，每次改 chunk/embedder/reranker 必跑

**运行时**：

7. 结构化日志 `data/logs/{ingest,index,search}.jsonl`
8. `/metrics` Prometheus 端点（可选）

### "绝对不能错"字段清单

机器抽出的这些字段只允许 status=draft；`hdb publish {id}` 强制要求这些字段被人工复核（`_extracted_by: human` 或 `reviewed_by` 非空）：

- `effect_size.value` / `ci_low` / `ci_high` / `p`
- `grade.level`
- `risk_of_bias.overall`
- `pico.population.sample_size`
- `pico.intervention.dosage`
- `pico.population.exclusion`

### 不做过度防御

- 不自动重新抓取/版本管理
- 不后台跑 LLM 修复数据
- 不自动猜补缺失字段

---

## 7. 测试策略

四层 pytest 金字塔。

### L1 Schema 单元测试（秒级）

`tests/unit/test_schema.py`：合法/边界/非法 frontmatter；不同 type 的 schema 差异；DOI/PMID 格式；`_extracted_by` 枚举。

### L2 管线单元测试（秒级，无外部依赖）

| 模块 | 测试 |
|------|------|
| `chunker` | 8 节区→8 chunk；超长按 ### 切；空节区跳过 |
| `section_mapper` | Methods/研究方法 → 标准节区 |
| `clean` | 页眉页脚、断行、连字符 |
| `embedder_*` | mock HTTP，接口契约、维度、重试 |
| `sparse` | jieba 分词 + 英文混合 |
| `pinyin` | 彭→PENG，复姓 |
| `id_gen` | 序号递增 |
| `filters` | Qdrant filter 结构 |

### L3 集成测试（分钟级，起容器）

用 `testcontainers-python` 起 Qdrant：

- `test_ingest_pdf_end_to_end`（用 PMC OA 开源 PDF fixture）
- `test_index_update_incremental` —— 增量正确
- `test_index_rebuild_idempotent` —— 两次 rebuild 结果一致
- `test_quarantine_flow`
- `test_search_hybrid` / `test_search_filter` / `test_search_degraded_dense`
- `test_evidence_get_by_id`

LLM 调用全 mock（vcr.py 或 fixture）。

### L4 黄金集回归（关键）

```
tests/golden/
├── queries.jsonl
├── corpus/          # 10-20 篇 fixture md
└── test_recall.py
```

每条 query：

```json
{
  "id": "Q-001",
  "query": "...",
  "expected_top": ["EV-RCT-2026-PENG-001", "EV-META-2024-LIU-001"],
  "required_section": ["结果", "结论"],
  "min_grade": "moderate",
  "language": "zh"
}
```

断言：

- `recall@10` —— expected_top 必出现
- `MRR > 0.6`
- `filter_correctness` —— min_grade=high 时低质量文献被排除

改 chunk/embedder/reranker 必跑，退化超阈值 → CI 红。

### L5 性能 smoke test

1000 chunk 索引耗时阈值；`/search` p95 < 5s。防回归用，不是基准。

### CI / 本地测试矩阵

| 阶段 | 跑 |
|------|---|
| pre-commit | schema validate, lint, format |
| `pytest -m unit` | L1+L2 |
| `pytest -m integration` | L3，需 docker |
| `pytest -m golden` | L4，需 docker + 1 次 embedder API |
| 改 embedder/reranker | 必跑 L4 |

### 不测什么

- 不测 Qdrant 自身正确性
- 不测 Marker/MinerU PDF 解析准确率（只测能跑通）
- 不测 LLM 抽 PICO 准确率（靠人工复核）
- 不追求 100% 覆盖率

---

## 8. 实施分期建议（供后续计划参考）

虽然本设计文档不规定实施顺序，但下面是一个合理的分期，供下一步 `writing-plans` 阶段参考：

1. **M0 项目骨架**：pyproject.toml、目录结构、docker-compose、CLI 框架
2. **M1 Schema 层**：所有 Pydantic models + 单测
3. **M2 数据层手工流**：手工写 5-10 篇 fixture md + 校验 + pre-commit hook
4. **M3 索引管线**：chunker + embedder 抽象 + sparse + qdrant_writer + 增量 update
5. **M4 检索层**：hybrid + reranker + filters + FastAPI 4 端点
6. **M5 黄金集**：维护 30-50 条 query + recall@10 / MRR 基线
7. **M6 入库管线 (PDF→md)**：parse_pdf + clean + section_map + extract_frontmatter（半自动）
8. **M7 英文 API 采集脚本**：PubMed / PMC OA / Europe PMC
9. **M8 数据质量工具**：`hdb lint`, `hdb publish`, draft 积压提醒
