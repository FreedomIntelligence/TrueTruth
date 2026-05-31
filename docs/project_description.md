# EBM 5A 项目完整描述

> 生成日期：2026-05-26  
> 用途：报告写作参考素材

---

## 一、项目基础与来源

### 1.1 学术框架来源

本项目基于**循证医学（Evidence-Based Medicine, EBM）的 5A 工作流程**，该框架由 Sackett 等人于 1990 年代提出，现已成为国际临床实践指南制定的标准方法论。5A 代表五个有序步骤：

| 步骤 | 英文 | 含义 |
|------|------|------|
| 1 | Ask | 将临床问题结构化为可检索的 PICO 格式 |
| 2 | Acquire | 系统检索相关文献证据 |
| 3 | Appraise | 评价证据质量（使用 GRADE 方法） |
| 4 | Apply | 将证据转化为临床推荐意见 |
| 5 | Assess | 评估推荐意见的质量与可靠性 |

证据分级采用 **GRADE（Grading of Recommendations Assessment, Development and Evaluation）**方法，由 Guyatt 等人（2011 年，PMID 26845745）开发，现为 WHO、Cochrane 协作组等国际权威机构采用的金标准。PICO 查询框架（Patient/Population、Intervention、Comparison、Outcome）及其变体（PIRD 诊断框架、PEO 流行病学框架）均为 EBM 教学中的标准工具。

### 1.2 项目定位

**项目名称**：TrueTruth（工程目录名 ebm5a）

**本质**：一个自动化临床决策支持系统（CDSS），将 EBM 5A 工作流程转化为可运行的多智能体 AI pipeline，能自动接收临床问题并输出附有证据等级、引用来源和推荐强度的临床推荐意见。

**当前领域**：系统当前专注于**高血压**领域，配套建有包含约 461 篇文献的高血压循证数据库（hypertensiondb）。

**技术本质**：多智能体 ReAct（Reasoning + Acting）控制循环，配合专业化 Judge 和 Scheduling 模块实现自动质控与流程管控。

---

## 二、系统架构与逻辑

### 2.1 整体架构图

```
用户输入临床问题
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Coordinator（协调器）                       │
│  WorkflowState（全局状态）  ←→  ExecutionHistory（执行审计链）     │
└────────────┬────────────────────────────────────────────────────┘
             │  控制循环（最多 20 次迭代）
             ▼
    ┌──────────────────────────────────────────────────────────────┐
    │  Ask Agent → Acquire Agent → Appraise Agent → Apply → Assess │
    │       ↑                                                       │
    │       └──── Judge LLM ──→ Scheduling LLM ──→ 前进/回退/终止  │
    └──────────────────────────────────────────────────────────────┘
             │
             ▼
    结构化推荐意见（强度 + GRADE 等级 + 引用 + 免责声明）
```

### 2.2 五大核心 Agent

#### Ask Agent（问题结构化）

**职责**：接收用户的自然语言临床问题，进行领域判断、路由分类、查询框架构建。

**三步处理逻辑**：

1. **Step 0 — 领域过滤**：判断问题是否与高血压相关（宽松模式：合并症、边界案例默认放行；明确的糖尿病/肿瘤/骨科问题拒绝）。非高血压问题在此阶段终止，返回友好提示。

2. **Step 1 — 统一路由器（V2，2026-05-18 起）**：单次 LLM 调用，同时完成路由决策和框架选择。
   - 路由类型：`direct_answer`（简单事实题）、`sub_questions`（需拆分的复合题）、`full_pipeline`（需完整 EBM 分析的题目）
   - 问题类型：Therapy（治疗）、Diagnosis（诊断）、Prognosis（预后）、Harm（危害）、Prevention（预防）
   - 注：诊断类问题保留两步处理（diag_step1 → diag_step2）以保证质量

3. **Step 2 — EBM 查询构建**：根据问题类型选择对应查询框架：
   - PICO（治疗/危害/预防）：Patient + Intervention + Comparison + Outcome
   - PIRD（诊断）：Population + Index test + Reference standard + Diagnosis
   - PEO（流行病学）：Population + Exposure + Outcome
   - Prognosis（预后）：Population + Prognostic factor + Outcome

**输出**：`EBMQuery` dataclass（含 query_type、patient、primary_focus、outcome、keywords、comparator 等字段）

**关键设计决策**：V2 路由器将原来的两次 LLM 调用（路由 + 框架构建）合并为一次，节省约 10-15 秒，A/B 验证显示质量持平。

#### Acquire Agent（证据检索）

**职责**：将结构化 PICO 查询转化为自然语言检索词，在高血压文献数据库中进行语义检索，返回相关文献及支撑段落。

**处理流程**：
1. LLM 读取 EBMQuery，生成中英文混合的自然语言检索词（面向 RAG 优化的短语式查询）
2. HTTP GET 请求发送至 hypertensiondb FastAPI 服务（`/search?q=<query>&top_k=15`）
3. 将返回的 chunk 级结果按 evidence_id 聚合为 paper + passages 格式
4. 按相关性分数排序，限制至最多 6 篇文章 × 3 段 passages

**错误处理**：RAG 服务不可用时抛出 RAGUnavailable 异常，重试 2 次（指数退避）；支持 backtrack 反馈（接收上一次检索的失败说明，引导生成更宽/更窄的检索词）。

**历史演变**：2026-05-22 前使用实时 PubMed/PMC API 检索，改造后切换为本地 RAG 服务，消除网络延迟不稳定性，引入语义重排序提升召回质量。

#### Appraise Agent（证据评价）

**职责**：对每篇检索到的文献进行 GRADE 证据质量评估，生成结构化的证据质量等级。

**双路径架构**：

- **路径 A（有预计算字段）**：若文献有 hypertensiondb 预计算的 `grade_level` + `rob_overall`，直接使用，跳过 LLM 推断。
- **路径 B（无预计算字段）**：LLM 从文献内容推断 GRADE 因子标签，Python 确定性计算最终等级。

**GRADE 计算规则（确定性 Python 实现）**：

| 研究类型 | 初始分数 |
|---------|---------|
| RCT / 系统评价 / Meta 分析 / 网络 Meta 分析 | 4 分（High） |
| 队列研究 / 病例对照研究 | 2 分（Low） |
| 指南 | 3 分（Moderate） |
| 病例报告 / 专家意见 / 叙述性综述 | 1 分（Very Low） |

降级因子（每个 SERIOUS -1 分，VERY_SERIOUS -2 分）：
- 偏倚风险（risk_of_bias）
- 不一致性（inconsistency）
- 间接性（indirectness）
- 不精确性（imprecision）
- 发表偏倚（publication_bias，-1 分）

升级因子（仅观察性研究可用，上限 Moderate）：
- 大效应量（large_effect，+1）
- 剂量-反应关系（dose_response，+1）
- 混杂因素减弱（confounding_mitigates，+1）

最终分数 → 等级：4=High，3=Moderate，2=Low，1=Very Low

**特殊规则**：`rob_overall=some_concerns` 映射为 NOT_SERIOUS（不自动降级），仅 `high` 映射为 SERIOUS，符合 GRADE 方法论（some_concerns 表示不确定性，不是确定偏倚）。

**并行处理**：使用 ThreadPoolExecutor 并发评价多篇文献，减少串行等待时间。

#### Apply Agent（推荐生成）

**职责**：综合证据评价结果，生成结构化的临床推荐意见。

**输入上下文**：
- 原始问题 + 结构化 EBMQuery
- 所有已评价文献（带 GRADE 等级和支撑段落）
- 降级因子摘要（限制推荐信心的关键问题）
- 矛盾性标志（is_conflicting_evidence）

**推荐强度映射（GRADE 标准，2026-05-22 修正）**：

| 证据情况 | 推荐强度 |
|---------|---------|
| Very Low + 结果一致 | Conditional（而非 Weak） |
| Low + 结果一致 | Conditional |
| Moderate + 一致 + 效益明显 | Strong |
| 存在间接性（indirectness） | 写入 caveats，不降低强度 |
| Low/Very Low + 结果不一致 | Weak |
| 无相关证据 | Insufficient Evidence |

**引用格式**：强制使用 `[evidence_id / section]` 格式，例如 `[EV-META-2023-CHO-001 / results_3]`，确保每条事实陈述可追溯至具体文献的具体章节。

**输出**：`Recommendation` dataclass（text、strength、rationale、caveats[]、evidence_quality）

#### Assess Agent（质量审计）

**职责**：对最终推荐意见进行质量评分，决定是否需要回退重新生成。

**评分维度（加权）**：
- 完整性（50%）：推荐是否覆盖了问题的各个方面
- 强度一致性（25%）：推荐强度是否与证据质量相符
- 推理链（15%）：从证据到推荐的逻辑是否清晰
- 免责声明（10%）：是否恰当说明了证据局限性

**评分等级映射**：YES=1.0, PARTIAL=0.55~0.70, NO=0.1~0.3, NA=1.0

**强制降级门槛**：若 quality_score < 0.70 但推荐强度为 Strong，则自动降级为 Weak 并附说明，防止证据质量不足的情况下给出过强推荐。

### 2.3 Judge LLM（质量裁判）

**职责**：在每个 Agent 执行后，对输出结果进行多维度打分，生成 Observe 对象（观察报告）。

**工作模式**：
- 每个阶段有独立的评分维度 JSON 文件（ask_dimensions.json 等）
- 每个维度有权重（1-3）和通过/失败/部分通过判断标准
- 输出 overall_score（0-1）、各维度得分、issues 列表
- 合格门槛：0.70（70分）
- 硬性门槛（hard gate）：特定条件直接触发特殊处理，不经打分

**各阶段关键评分维度**：

| 阶段 | 核心维度（权重） |
|------|----------------|
| Ask | core_dimensions_present(3), secondary_dimensions_present(2), statement_unambiguous(1) |
| Acquire | keywords_cover_pico(3), primary_focus_match(3), p_match(3), o_match(3) |
| Appraise | included_study_type_correct(3), conflicts_identified(2), downgrade_factors(1，2026-05-25 从 3 降低) |
| Apply | strength_matches_evidence(3), effect_size_correct(3), population_applicability(2) |
| Assess | answer_completeness(35%), reasoning_chain(35%), logical_consistency(30%) |

**2026-05-25 重要调整**：将 `downgrade_factors_appropriate` 从 CRITICAL（权重 3）降为 Minor（权重 1），原因是 GRADE 降级因子的判断属于主观 judgment call，两名专家之间的一致性 kappa 仅约 0.39-0.41，系统不应将主观判断设为 retry 触发条件。

### 2.4 Scheduling LLM（流程调度）

**职责**：综合 Judge 评估结果和历史状态，决定工作流程如何继续。

**四种决策动作**：
1. `proceed`：进入下一阶段
2. `retry_current`：当前阶段重试（通常因写作问题，非证据问题）
3. `backtrack_to_X`：回退到之前某阶段重新执行
4. `terminate`：终止（证据不足或已达质量要求）
5. `request_human_review`：请求人工干预

**快速通道（FAST-PATH）优化**：
- 无 Major/Critical 问题 → 自动 proceed（减少不必要的等待）
- 所有 PARTIAL 且总分通过 → proceed（GRADE 接受部分合规）
- 同一维度已循环多次 → 强制 proceed（防止无限重试）
- 达到 20 次迭代上限 → 强制 terminate

**2026-05-25 学术规范对齐**：
- Acquire PARTIAL 匹配必须 proceed（PICO 部分匹配是正当的学术发现，由 Appraise 的 GRADE indirectness 降级处理）
- 已 backtrack 一次仍无相关证据 → 识别为数据库内容空白，直接输出 Insufficient Evidence
- `downgrade_factors` 单独不触发 retry，必须伴随 `computed_grade_reasonable=NO`（数学计算错误）才触发

### 2.5 Coordinator（协调器）

**职责**：中央调度引擎，维护全局状态，按顺序调度五个 Agent，处理 Judge/Scheduling 反馈。

**关键特性**：
- 迭代预算：remaining_budget = 20 - iteration_count（硬上限保证终止）
- backtrack 保护：记录 backtrack 历史，防止同一问题无限循环
- 回调机制：每个 Agent 完成后触发 on_stage_complete，支持实时流式输出
- 守护规则：backtrack_to_acquire 仅在 0 结果或已 backtrack 一次后仍不满意时合法

---

## 三、数据库架构、字段与部署

### 3.1 hypertensiondb 整体架构

hypertensiondb 是一个运行于本地的 FastAPI 服务，专为高血压文献检索设计，当前存储约 461 篇文献。

```
PDF/PubMed 原始文献
        ↓
LLM 结构化抽取（HuatuoGPT-3-32B-no-thinking）
        ↓
Markdown 格式的结构化文献文件（evidence/ 目录）
        ↓
分章节 Chunking + ZhipuAI 嵌入（2048维）
        ↓
Qdrant 向量数据库（本地 Docker，端口 6333）
        ↓
/search API（FastAPI，端口 8000）
        ↓
hypertension_rag_client.py → Acquire Agent
```

### 3.2 Qdrant 向量数据库

**向量维度**：2048（ZhipuAI 嵌入模型）

**每个 Chunk 的 Payload 字段**（Qdrant 的文档元数据）：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `evidence_id` | str | 唯一标识符，格式：`EV-{类型}-{年份}-{作者}-{序号}`，如 `EV-RCT-2025-PENG-001` |
| `title_en` | str | 英文标题 |
| `title_zh` | str | 中文标题 |
| `authors` | list | 作者列表 |
| `year` | int | 发表年份 |
| `language` | str | `en`/`zh`/`bilingual` |
| `type` | str | 文献类型标签：`RCT`/`META`/`SR`/`GL`（指南）/`TCM`（中医） |
| `study_type` | str | GRADE 学术标准研究设计：`RCT`/`SYSTEMATIC_REVIEW`/`META_ANALYSIS`/`COHORT`/... |
| `grade_level` | str | `high`/`moderate`/`low`/`very_low` |
| `rob_overall` | str | `low`/`some_concerns`/`high` |
| `section` | str | 章节：`background`/`methods`/`results`/`discussion`/`clinical_bottom_line` |
| `content` | str | 章节原文内容 |
| `pico` | object | 结构化 PICO（population、intervention、comparison、outcomes） |
| `tags` | list | 关键词标签 |

**检索方式**：混合检索（RRF 融合）
- 稠密检索：ZhipuAI 向量 + Qdrant 近似最近邻
- 稀疏检索：jieba 分词 + BM25 关键词匹配
- Reranker：BAAI/bge-reranker-v2-m3（通过 HuatuoGPT API 调用）

### 3.3 文献结构化抽取字段

入库时 LLM 从原始文献抽取的 JSON 结构：

```json
{
  "type": "RCT | META | SR | GL | TCM",
  "title": {"en": "...", "zh": "..."},
  "authors": ["...", "..."],
  "year": 2024,
  "language": "en | zh | bilingual",
  "pico": {
    "population": {"condition": "原发性高血压", "sample_size": 9361},
    "intervention": {"name": "强化降压（SBP<120）", "details": "..."},
    "comparison": {"name": "标准降压（SBP<140）"},
    "outcomes": [{"name": "心血管事件", "effect_size": {"hr": 0.75, "ci": "0.64-0.89"}}]
  },
  "risk_of_bias": {"tool": "RoB2", "overall": "low | some_concerns | high"},
  "grade": {"level": "high | moderate | low | very_low"},
  "study_type": "RCT | SYSTEMATIC_REVIEW | META_ANALYSIS | COHORT | ...",
  "rob_overall": "low | some_concerns | high"
}
```

### 3.4 backfill_grade.py — GRADE 字段批量补充

**目的**：对所有已入库文献，从全文 Methods + Results + Conclusion 重新提取 study_type、rob_overall、grade_level，覆盖早期基于摘要的推断值。

**学术依据**：Cochrane Handbook 5.1.1 明确规定研究设计应从全文 Methods 章节判断，而非从文章标题或分类标签推断。

**执行结果**：460/461 篇文章完成 backfill，1 篇因无 Methods 内容跳过。

**`--force-study-type` 参数**：可强制对已有值的文章重新提取，确保最权威来源（全文 Methods）覆盖早期错误值。

### 3.5 Evidence 数据模型（pipeline 侧）

pipeline 侧的 Evidence dataclass（非 Qdrant 内部格式）：

```python
@dataclass
class Passage:
    section: str        # "results_3", "discussion_2" 等
    snippet: str        # 原文段落内容
    score: float        # 相关性分数（来自 reranker）

@dataclass
class Evidence:
    evidence_id: str                      # 唯一标识符
    title: str                            # 文章标题
    source: str                           # 来源说明
    relevance_score: float                # 最高 passage 分数
    supporting_passages: List[Passage]    # 最多 3 个相关段落
    study_type: Optional[str]             # 研究类型（来自 backfill）
    grade_level: Optional[str]            # 预计算 GRADE 等级
    rob_overall: Optional[str]            # 预计算偏倚风险
    language: Optional[str]
    tags: Optional[List[str]]
    year: Optional[int]
```

### 3.6 hypertensiondb 部署架构

**启动顺序**：
1. Qdrant Docker 容器（`docker compose up -d`，在 hypertension/ 目录）
2. hypertensiondb FastAPI 服务（`hdb serve run`，监听 localhost:8000）
3. EBM pipeline（`py src/main.py "问题"`）

**关键配置环境变量**（hypertension/.env）：
```
EMBEDDER=zhipu                         # ZhipuAI 嵌入模型
EMBED_DIM=2048
RERANKER=api                           # API 模式 reranker
LLM_BASE_URL=https://api.huatuogpt.cn/v1
LLM_API_KEY=<HuatuoGPT 密钥>
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
QDRANT_HOST=localhost
QDRANT_PORT=6333
EVIDENCE_ROOT=evidence                 # Markdown 文献存储目录
OPENAI_EXTRACT_MODEL=HuatuoGPT-3-32B-no-thinking
```

**关键配置环境变量**（ebm5a/.env）：
```
HYPERTENSION_API_URL=http://localhost:8000
HYPERTENSION_API_TIMEOUT=60
RAG_SEARCH_TOP_K=15        # 每次检索返回的 chunk 数量
RAG_MAX_PAPERS=6           # 聚合后最多保留的文章数
RAG_MAX_PASSAGES_PER_PAPER=3   # 每篇文章最多保留的段落数

LLM_BASE_URL=https://api.huatuogpt.cn/v1
LLM_API_KEY=<密钥>
LLM_MODEL=HuatuoGPT-3-32B
FAST_LLM_MODEL=<可选，给 Judge/Scheduling 用的快速模型>
```

---

## 四、历史改动记录

### 4.1 v0（初始版本，2025 年底 ~ 2026-04 之前）

- 5A 框架基本骨架搭建
- 使用实时 PubMed/PMC API 进行证据检索
- Judge 和 Scheduling 基础实现
- 本地 BM25 RAG + 模拟 reranker

### 4.2 2026-04-20 至 04-22（主要重设计，commit ae78a60）

- Agent 架构基本稳定，确立了 Judge + Scheduling 控制循环
- GRADE 计算从纯 LLM 推断改为"LLM 分类标签 + Python 确定性计算"的混合架构，使 GRADE 等级具有可复现性
- WorkflowState TypedDict 设计确立，成为贯穿全流程的状态总线
- 所有测试通过，系统进入可运行状态

### 4.3 2026-05-18（性能优化批次）

**Ask Agent V2 统一路由器**：
- 将路由决策和框架选择合并为单次 LLM 调用
- 创建 `router_unified.txt` 替代原来的 `router.txt` + 独立框架提示词
- Diagnosis 问题保留两步处理（diag_step1/diag_step2）
- A/B 验证：V2 质量持平，延迟减少 10-15 秒

**冷启动优化**：
- `llm_config.py` 引入模块级 OpenAI 客户端单例（模块加载时初始化）
- `main.py` warmup 改为 fire-and-forget（并发预热 agent/judge/scheduling 三路连接）
- 首字出现时间从 ~15 秒降至 ~2-6 秒

### 4.4 2026-05-22（最大规模改造——PubMed→RAG 迁移，commit 09423a6）

**Acquire Agent 全面 RAG 化**：
- 删除 PubMed API、PMC 全文抓取、BM25、Listwise rerank 全套代码
- 新建 `src/tools/hypertension_rag_client.py`，调用本地 hypertensiondb FastAPI
- 检索流程：PICO → LLM 生成中英文混合 NL query → `/search` → chunk 聚合为 paper+passages
- 效果：消除实时 PubMed 网络延迟（原 10-30 秒/次），引入语义 reranker 提升召回质量
- Q2（ARB+CCB 问题）从死循环变为正常完成

**Ask Agent 领域过滤**：
- `router_unified.txt` 新增 Step 0 领域过滤规则
- `ask_agent.py` 新增 `_handle_out_of_domain()` 路径
- 非高血压问题友好拒绝，不进入后续 pipeline 浪费资源

**Evidence 数据模型重构**：
- `state/schema.py`：新增 `Passage` dataclass
- `Evidence` 从"单一文本"改为"paper + passages 聚合"模型
- 删除旧字段：pmid、pmcid、abstract、full_text、has_full_text、pub_types、key_sentences
- 新增字段：evidence_id、supporting_passages、language、tags、grade_level、rob_overall

**Apply 引用格式新规范**：
- `apply_agent.txt` 强制 `[evidence_id / section]` 格式引用
- 每条事实陈述后必须有引用标记，实现证据可溯源

**流式输出优化**：
- Ask、Apply agent 改用 `stream_reasoning()` 流式输出推理过程
- `coordinator.py` 新增 `on_stage_complete` 回调，每个阶段完成后立即打印
- `llm_config.py` 新增状态机式流式处理（SCAN→PRINT→DONE，只打印 Reasoning 段，过滤 JSON）

**hypertensiondb 新增 API Reranker**：
- `reranker_api.py`：调用 HuatuoGPT gateway 的 BAAI/bge-reranker-v2-m3 API
- 替代 mock reranker，/search 耗时增加约 3 秒但召回质量大幅提升

**入库 6 篇 Landmark Trial**（手动下载 PDF）：

| 试验 | 年份 | 核心贡献 | 样本量 |
|------|------|---------|--------|
| SPRINT | 2015 | 强化降压 SBP<120 vs <140 | n=9361 |
| STEP | 2021 | 中国老年高血压强化降压 | n=8511 |
| ALLHAT | 2002 | 氯噻酮 vs 赖诺普利 vs 氨氯地平 | n=33357 |
| ACCORD BP | 2010 | 糖尿病+高血压强化降压 | — |
| HYVET | 2008 | 80岁以上老年高血压 | n=3845 |
| ONTARGET | 2008 | 替米沙坦 vs 雷米普利 | n=25620 |

**GRADE 推荐强度规则修正**（Apply prompt）：

| 旧规则（错误） | 新规则（GRADE 标准） |
|--------------|-------------------|
| Low OR inconsistent → Weak | Low + consistent → Conditional |
| Very Low + consistent → Weak | Very Low + consistent → Conditional |
| Moderate + 有局限 → Conditional | Moderate + consistent + 效益明显 → Strong |
| indirectness → 降低 strength | indirectness → 写进 caveats，不降 strength |
| rob=some_concerns → 自动降级 | some_concerns → NOT_SERIOUS（不自动降级） |

**批量补充 grade/rob 字段**：
- 新建 `hypertension/scripts/backfill_grade.py`
- 对 401 篇文献批量抽取 grade_level、rob_overall、study_type（从全文 Methods 章节）
- 全量重建 Qdrant 索引

**30 题测试结果对比**：

| 指标 | 改造前 | 改造后 |
|------|--------|--------|
| 完成率 | 28/30（有死循环） | 30/30 |
| 平均总耗时 | ~179 秒 | ~161 秒 |
| 首字时间 | ~15 秒 | ~2-6 秒 |
| Strong 推荐数 | 0 | ~4-6 题 |
| Conditional 推荐数 | 0 | ~18-20 题 |
| Weak 推荐数 | ~18 | ~2-4 题 |

### 4.5 2026-05-22 下午（RAG 检索稳定性研究与方法论对齐）

**现象**：同一问题不同措辞（`ARB+CCB 联合治疗` vs `ARB 联合 CCB 治疗的疗效如何？`）导致不同推荐强度。

**调查结论**：这是 EBM 方法论的正确行为，不是 bug——不同 PICO 是不同研究问题，检索到不同证据集在学术上是正当的。尝试过 keyword anchor 双路检索（取并集）方案，后回滚，因为这会引入与当前 PICO comparator/outcome 无关的文献，违反 GRADE 的间接性降级原则。

**正确解法**：在 Ask 阶段展示并由用户确认 PICO（真实临床指南制定的做法），而非技术层面强行消除措辞变体。

### 4.6 2026-05-25（学术规范全面对齐）

**Judge G1（study_type 验证）规则修正**：
- 原规则：用 passage 片段验证 study_type（用质量低的信息推翻质量高的信息，学术上倒置）
- 新规则：有预计算 study_type（来自全文 Methods）→ G1 按预计算值判断；无预计算值 → 才用 passage 验证
- G1=NO 从 MAJOR gate（触发 retry）降为 MINOR（仅记录，不影响流程）

**Appraise Judge downgrade_factors 权重调整**：
- `downgrade_factors_appropriate` 权重从 3（Critical）降至 1（Minor）
- 原因：GRADE 降级因子是主观 judgment call，专家间 kappa≈0.39，系统不应将其设为强 retry 触发条件

**Scheduling 规则学术对齐**：
- 规则1：Acquire PARTIAL 匹配必须 proceed（不是检索失败，是有意义的间接证据）
- 规则2：已 backtrack 一次仍无相关证据 → content gap → 直接 proceed 输出 Insufficient Evidence
- 规则3：downgrade_factors 单独不触发 retry，需伴随 computed_grade_reasonable=NO

**2026-05-25 一致性测试（首次）**：

| 维度 | 一致率 | 说明 |
|------|-------|------|
| 推荐强度（精确匹配） | 95%（20/21 有效题） | 排除 3 道 API 错误后 |
| 证据质量（精确匹配） | 95% | 同上 |
| 推荐对象（gpt-5.5 判断） | 76% | |
| 推荐倾向（gpt-5.5 判断） | 81% | |
| 综合方向 | 67% 一致 / 29% 部分一致 / 5% 不一致 | |

**学术参考**：GRADE IRR 研究（PMID 26845745）显示推荐强度（strong/weak）的人工评审者间 kappa≈0.39，系统 95% 的一致率显著优于人类专家水平。

**最终性能**：
- 平均耗时：149.3 秒（从基准 161 秒降低 7.4%）
- max 耗时：197.6 秒
- 消除所有 300 秒以上的长尾异常（原有 3 道题超过 300 秒）
- 完成率：30/30（100%）

---

## 五、Web 界面

### 5.1 后端（FastAPI + SSE）

`web/backend/app.py` 提供三个核心端点：
- `POST /api/sessions`：注册问题，返回 session_id
- `GET /api/run?session_id=X`：Server-Sent Events（SSE）实时流推送工作流进度
- `GET /api/health`：健康检查

事件类型：WORKFLOW_START、STAGE_COMPLETE、JUDGMENT、SCHEDULING_DECISION、WORKFLOW_END、ERROR、HEARTBEAT

`InstrumentedCoordinator` 包装 Coordinator，在每个阶段完成后发射 SSE 事件，允许前端实时展示进度。

### 5.2 前端（React + Vite）

**技术栈**：React 18 + Vite + TailwindCSS + Recharts + Zustand（状态管理）

**核心组件**：
- `WorkflowPipeline`：可视化 5A 阶段进度
- `EvidenceTable`：已评价文献列表，显示 GRADE 等级和支撑段落
- `RecommendationPanel`：推荐强度、质量评分、推理说明、免责声明
- `ExecutionTimeline`：回退事件和调度决策时间线

`useWorkflowSSE` Hook 管理 EventSource 连接，解析 SSE 事件，更新全局 Zustand 状态。

### 5.3 容器化部署

Docker Compose 三服务架构：
- `backend`：Uvicorn + FastAPI（生产端口 8000）
- `frontend`：Nginx 服务 React 构建产物（端口 8080）
- `hypertensiondb`：独立在 hypertension/ 目录管理（localhost:8000）

开发模式命令（Makefile）：

```bash
make dev              # 同时启动前后端（热重载）
make dev-backend      # 仅后端
make dev-frontend     # 仅前端
make docker-up        # 生产容器构建并启动
make cli QUERY="..."  # CLI 模式单条查询
```

---

## 六、其他重要方面

### 6.1 提示词缓存（Prompt Caching）

**机制**：所有提示词模板包含 `%%USER_INPUT_BELOW%%` 标记，将不变的系统前缀（GRADE 规则定义、输出格式说明）与可变的用户输入分离。

**实现**：`split_prompt_for_caching()` 函数将提示词拆分为 `{system, user}` 字典，供支持前缀缓存的 LLM 网关（如 huatuogpt.cn）使用。

**效果**：在同一会话的多文献评价中，prompt_tokens 减少约 98%（网关侧验证），显著降低 token 消耗。

### 6.2 双模型架构

系统支持两套 LLM 实例：
- **全功能模型**（LLM_MODEL）：用于 Ask/Acquire/Appraise/Apply/Assess 五个核心 Agent
- **快速模型**（FAST_LLM_MODEL，可选）：用于 Judge 和 Scheduling 这两个分类性任务

理由：Judge 和 Scheduling 本质上是分类任务（打分 + 决策），不需要完整的推理能力；使用较小模型可降低 30-40% 的 pipeline 延迟，A/B 验证显示质量持平。

### 6.3 状态管理（WorkflowState）

`WorkflowState` TypedDict 是整个 pipeline 的"中枢神经系统"，贯穿所有阶段。关键字段分组：

**控制字段**：original_question、current_step、iteration_count、remaining_budget、should_terminate、route_type、out_of_domain

**EBM 查询字段**：ebm_query、sub_pico_queries、sub_question_index、question_type

**历史字段**：execution_history（完整 ExecutionNode 列表）、observe_history（Judge 报告）、decision_history（Scheduling 决策）、backtrack_history（回退记录）

**质量控制字段**：agent_call_counts（各 Agent 调用次数）、soft_gate_signals（软门触发记录）、rag_degraded（RAG 服务降级标志）

### 6.4 错误处理与容错

- LLM 调用：指数退避重试（5xx）、长间隔重试（429 限速）、立即失败（4xx）
- RAG 服务：2 次重试（5xx），立即失败（4xx），失败后进入 rag_degraded 模式
- JSON 解析：`robust_parse_json()` 多策略容错（正则提取、标记清理、宽松解析）
- 迭代预算：硬上限 20 次，防止无限循环

### 6.5 当前已知问题（截至 2026-05-25）

1. **证据库内容缺口**：ASCOT-BPLA、ACCOMPLISH、LIFE、CAMELOT、CHIPS、PATHWAY-2 等关键 landmark trial 未入库，影响 Q1、Q5、Q6、Q12、Q13、Q16 等题目的推荐质量
2. **Q18 JSON 解析错误**：偶发 `Extra data: line 1 column 7`，原因未定位
3. **Appraise 双路径架构**：有预计算字段时两套逻辑并存，建议统一为单一路径
4. **Scheduling content_gap 规则**：代码层面仍未同步 prompt 层面的修复
5. **中医/针灸文献稀少**：影响 Q22/23/24 一致性（pediatric/TCM 领域文献极少）

### 6.6 性能基准（2026-05-25）

| 阶段 | 典型耗时 | 性能目标 |
|------|---------|---------|
| Ask | 8-30 秒 | < 30 秒 |
| Acquire | 20-30 秒 | < 60 秒 |
| Appraise | 30-60 秒 | < 60 秒 |
| Apply | 15-30 秒 | < 30 秒 |
| Assess | 10-20 秒 | < 20 秒 |
| Judge（每阶段） | 5-15 秒 | — |
| Scheduling（每阶段） | 5-10 秒 | — |
| **全流程平均** | **149.3 秒** | **< 240 秒（4 分钟）** |
| 最大耗时 | 197.6 秒 | — |
| 完成率 | 100%（30/30） | — |

### 6.7 目录结构

```
ebm5a/
├── src/                          # 核心多智能体引擎
│   ├── main.py                   # CLI 入口
│   ├── agents/
│   │   ├── base.py               # BaseAgent + robust_parse_json() + split_prompt_for_caching()
│   │   ├── ask_agent.py          # PICO + 路由 + 领域过滤
│   │   ├── acquire_agent.py      # RAG 查询生成 + /search
│   │   ├── appraise_agent.py     # GRADE + 矛盾检测（确定性规则）
│   │   ├── apply_agent.py        # 推荐生成
│   │   └── assess_agent.py       # 质量审计 + 强度限制
│   ├── coordinator/
│   │   ├── coordinator.py        # 工作流编排，回退处理
│   │   └── gate_engine.py        # 软/硬门检查
│   ├── judge/
│   │   └── judge_llm.py          # 阶段评估 + rubric 打分
│   ├── scheduling/
│   │   └── scheduling_llm.py     # 工作流进度决策 + 学术规则
│   ├── state/
│   │   └── schema.py             # 所有 dataclass + WorkflowState TypedDict
│   ├── tools/
│   │   └── hypertension_rag_client.py  # HTTP /search 客户端 + 聚合
│   └── config/
│       ├── llm_config.py         # OpenAI 客户端池、重试逻辑、缓存
│       ├── prompts/              # 20+ .txt 提示词模板
│       └── evaluation_dimensions/  # 各阶段 Judge rubric 权重 JSON
├── web/
│   ├── backend/
│   │   ├── app.py                # FastAPI 路由，SSE 流
│   │   ├── instrumented_coordinator.py  # 事件发射包装器
│   │   └── event_types.py        # SSE 事件 schema
│   └── frontend/
│       ├── src/components/       # React UI 组件
│       ├── src/hooks/useWorkflowSSE.js  # SSE 连接管理
│       └── src/store/workflowStore.js   # Zustand 全局状态
├── tests/                        # 测试套件
├── docs/                         # 文档（架构设计、改进总结、测试基准）
├── scripts/                      # 工具脚本（批量测试、一致性报告）
├── docker-compose.yml
├── Makefile
├── requirements.txt
└── .env.example
```

---

## 附录：报告写作时可补充的维度

1. **与现有 CDSS 系统的比较**：UpToDate、DynaMed、OpenEvidence 等商业系统的方法论差异（人工编辑 vs 自动化 AI）
2. **临床应用前景**：上市前监管路径（FDA/NMPA 医疗器械软件分类）、临床验证研究设计、数据监管合规
3. **局限性讨论**：当前仅覆盖高血压、数据库规模限制（461 篇）、LLM 幻觉风险、缺乏准确性（vs 指南一致性）验证
4. **伦理与安全**：AI 推荐的责任归属、错误推荐的后果管控、人机协作模式设计
5. **可扩展性**：扩展至其他专科（心血管、内分泌、感染）的技术路径和工作量评估
