# 各阶段 Agent、Judge、Scheduling 迭代历史

---

## Ask Agent

### 第一阶段：单一 PICO 提取（2026-01 至 2026-02）

Ask Agent 最初的职责极为简单：接收用户输入的自然语言临床问题，调用一次 LLM，将其转化为结构化的 PICO 格式（Patient/Intervention/Comparison/Outcome），再附上若干检索关键词。整个实现只有一个 prompt 文件（`ask_agent.txt`）和对应的一次 LLM 调用，输出为 `PICOQuery` dataclass。

这一版本在运行中暴露了几个根本性问题：

**问题一：无问题类型路由，所有问题一律套 PICO。** PICO 框架是为治疗类问题设计的，但诊断准确性问题的正确框架是 PIRD（待评估诊断测试 + 金标准），病因/危险因素问题是 PEO，预后问题有其专属框架。将一个"哪种影像学检查对早期肺癌的诊断敏感性更高"的问题套入 PICO，会把"CT 检查"错误地映射为"干预措施"，生成语义错误的检索词。

**问题二：无紧急操作类问题识别。** 对于"心肺复苏时胸外按压深度是多少"这类有公认操作规范的急救问题，系统会照常走完整 5A 流程，花费数分钟检索文献、评价证据，最终得出一个与标准指南相同的答案。这一行为浪费资源，且对真实临床场景完全不实用。

**问题三：question_type 字段没有 Judge 覆盖。** 分类错误无法被下游捕获，会传导至 Acquire 阶段的检索过滤器选择，影响整条 pipeline 的质量。

### 第二阶段：路由架构引入（2026-04-20）

2026 年 4 月的全面重设计中，Ask Agent 被重构为两步架构：

**第一步：路由调用（`router.txt`）。** 单独一次 LLM 调用，判断问题性质，输出 route_type 字段：
- `direct_answer`：同时满足三个条件的急救/操作规范题（需立即操作指导 + 延迟危及生命 + 有公认操作标准）
- `diagnostic_reasoning`：核心是鉴别诊断推理的临床问题，走两步诊断推理流程
- `ebm_pico`/`ebm_pird`/`ebm_peo`/`ebm_prognosis`：各类 EBM 框架

**第二步：框架结构化调用（对应 `ebm_pico.txt`、`ebm_pird.txt`、`ebm_peo.txt`、`ebm_prognosis.txt`）。** 路由完成后，根据 route_type 选择对应的框架 prompt，进行第二次 LLM 调用，生成 `EBMQuery` dataclass（比 `PICOQuery` 更通用，引入 query_type、primary_focus 等泛化字段，适配四种框架）。

`diagnostic_reasoning` 路由另外走两步诊断推理：diag_step1 生成最多 3 个鉴别诊断（按"危重需排除 > 最可能 > 常见鉴别"优先排序），diag_step2 将每个诊断转化为独立的 EBMQuery，存入 `sub_pico_queries` 字段，为后续多子问题并行 5A 流程预留接口。

这一版本的核心缺陷是**两次 LLM 调用串行执行**，加上网络往返时间，Ask 阶段耗时增加至 15–30 秒，成为新的延迟瓶颈。

### 第三阶段：V2 统一路由器 + 领域过滤（2026-05-18 至 05-22）

2026 年 5 月做了两个独立改进：

**V2 统一路由器（2026-05-18）：** 将原来的两次串行 LLM 调用合并为一次，创建 `router_unified.txt`，在单次调用中同时输出 route_type 和完整 EBMQuery。经过 A/B 验证，合并后质量持平，Ask 阶段延迟减少约 10–15 秒。为了不损失诊断类问题的质量，`diagnostic_reasoning` 保留了独立的两步处理（diag_step1 + diag_step2），不参与合并。

**高血压领域过滤（2026-05-22）：** 向 `router_unified.txt` 新增 Step 0——在所有处理之前判断问题是否与高血压相关，输出 `hypertension_related: bool` 字段。若为 `false`，Ask Agent 直接返回友好拒绝说明，设置 `should_terminate=true`，整条 pipeline 终止。判定策略为宽松模式：高血压合并症、边界案例默认放行；只有与高血压完全无关的问题才被拒绝。这个改动消除了因领域不匹配导致的无效检索循环。

---

## Acquire Agent

### 第一阶段：基础 PubMed 检索（2026-01 至 2026-02）

最初的 Acquire Agent 直接调用 PubMed Entrez API，以 PICO 关键词构建布尔查询，获取最多 20 篇摘要，再调用 LLM 对每篇摘要进行相关性评分（0–1），筛选 relevance_score > 0.6 的文章，最终保留前 10 篇。研究类型通过基于规则的关键词匹配推断（标题含"randomized"→RCT，含"systematic review"→SR，依此类推）。

主要问题：**只使用摘要，没有全文内容。** 摘要通常不包含完整的方法学信息，导致 Appraise 阶段的 GRADE 评价缺少关键依据。此外，LLM 逐篇打分相关性的方式（每篇一次 LLM 调用）极其低效，20 篇文章需要 20 次调用，延迟无法接受。

### 第二阶段：两段式检索 + 混合 RAG（2026-04-20）

2026 年 4 月重设计引入了完整的两阶段检索架构：

**Stage 1（PubMed 检索）：** 适配新的 EBMQuery 格式，按 query_type 选择对应的 PubMed 过滤器（`ebm_pico` → HSSS 过滤器选 RCT+SR；`ebm_pird` → DTA 过滤器；`ebm_peo`/`ebm_prognosis` → 观察性研究过滤器），调用 LLM 构建布尔查询，检索最多 20 篇候选。

**Stage 2（PMC 全文并行拉取）：** 对有 pmcid 的文章，使用 `ThreadPoolExecutor + as_completed` 并发拉取 PMC 全文 XML，每篇设置 10 秒超时，单篇失败不影响其余文章。

**混合 RAG 预处理（BM25 → Embedding 两级）：** 对每篇候选文章的全文（或摘要降级），先用 BM25 初筛 Top-8 段落，再用 `sentence-transformers/all-MiniLM-L6-v2` 嵌入模型精排 Top-3 段落，写入 `key_sentences` 字段。20 篇文章按 embedding 相关性分数缩减到 Top-10，再送入 Listwise LLM 排序，最终保留 Top-K。

这一版本在运行中遇到了新问题：BM25 对医学领域存在严重的同义词盲区（"myocardial infarction"和"acute coronary syndrome"在词汇层面完全不匹配），全文拉取也因 PMC 网络延迟和付费文章访问限制频繁失败。embedding 模型（all-MiniLM-L6-v2）对中文和专业医学术语效果较差，整个 RAG 管道的实际召回质量不稳定。

### 第三阶段：全面 RAG 化，移除 PubMed（2026-05-22）

这是 Acquire Agent 历史上最大规模的改造。上述所有代码——PubMed API 调用、PMC 全文拉取、BM25、embedding 精排、Listwise ranking、过滤器常量——全部删除，由新建的 `src/tools/hypertension_rag_client.py` 一个文件替代。

新流程极为简洁：LLM 读取 EBMQuery，生成一段中英文混合的自然语言检索词，HTTP GET 发送到本地 hypertensiondb FastAPI 服务（`/search?q=<query>&top_k=15`）。服务端完成稠密检索 + BM25 + RRF 融合 + BAAI/bge-reranker-v2-m3 重排序，返回最相关的 15 个 chunk。客户端将 chunk 按 evidence_id 聚合为 paper + passages 结构，每篇保留最多 3 个最相关段落，按分数排序后返回最多 6 篇文章。

Evidence 数据模型同步重构：删除 `pmid`、`pmcid`、`abstract`、`full_text`、`has_full_text`、`pub_types`、`key_sentences` 等所有 PubMed 时代字段，新增 `evidence_id`、`supporting_passages`（Passage 列表）、`language`、`tags`、`grade_level`、`rob_overall`。

**直接改善：** Q2（ARB+CCB 联合治疗问题）在旧版本中由于语义检索质量差和 mock reranker 频繁死循环，改造后正常完成；消除了因 PubMed API 不稳定导致的随机失败。

---

## Appraise Agent

### 第一阶段：纯 LLM 推断 GRADE（2026-01 至 2026-04）

最初的 Appraise Agent 完全依赖 LLM：一次调用，输入证据摘要，输出 study_type、risk_of_bias、grade_level 等标签，再由简单 Python 代码将这些标签转换为 GRADE 等级。

这一版本存在多处与 GRADE 学术标准不符的实现错误：

**错误一：升级因素缺失第三条。** GRADE 规定三个升级因素，实现只处理了前两个，漏掉了"confounding_bias_mitigates"（所有残余混杂因素都偏向低估真实效应时可升级）。

**错误二：SR/MA/NMA 初始分固定为 High。** 系统评价和 Meta 分析的初始 GRADE 等级应取决于其纳入研究的类型：纳入 RCT 为主的 SR→High，纳入观察性研究为主的 SR→Low，混合型→Moderate。早期实现对所有 SR/MA/NMA 一律给 High，导致以观察性研究为主的 Meta 分析被严重高估。

**错误三：横断面研究可以使用升级因素。** GRADE 的升级因素只适用于评价因果效应的观察性研究（队列、病例对照）。横断面研究不评价因果效应，升级因素在概念上不适用。

**错误四：升级因素的使用没有偏倚风险前置条件。** 如果一篇研究存在严重偏倚风险（risk_of_bias = SERIOUS 或 VERY_SERIOUS），其升级因素不应被考虑。

**错误五：观察性研究升级上限缺失。** 即使所有三个升级因素都触发，观察性研究的 GRADE 等级上限也只能升至 Moderate（3分），不能达到 High（4分）。

### 第二阶段：GRADE 计算规则全面修正（2026-04-20）

基于以上发现，`_compute_grade()` 函数被完整重写：SR/MA/NMA 的初始分改为按 `included_study_type` 动态查表；新增 `confounding_bias_mitigates` 升级因素；`_UPGRADE_STUDY_TYPES` 集合只包含 COHORT 和 CASE_CONTROL；升级前加入偏倚风险前置检查；升级后用 `min(points, 3)` 强制上限。

### 第三阶段：预计算字段 + study_type 权威来源（2026-05-22 至 05-25）

随着 hypertensiondb 的引入，Appraise Agent 获得了"快速路径"：如果文献的 hypertensiondb payload 中已有预计算的 `grade_level` 和 `rob_overall` 字段，则直接使用，完全跳过 LLM 推断。

2026 年 5 月 25 日解决了更深层的学术合规问题：**study_type 的权威来源**。早期系统使用文献的文件分类标签（RCT/META/TCM 等）作为 study_type hint，但 Cochrane Handbook 5.1.1 明确规定研究设计应从全文 Methods 章节判断。

修复方案：通过 `backfill_grade.py --force-study-type` 对所有 461 篇文章重新从 Methods 章节全文提取 study_type（460/461 成功），并将 study_type 字段完整透传进 Qdrant payload → 检索 API → Evidence 对象 → appraise_agent.py。有预计算 study_type 时，直接用于 GRADE 初始分计算，LLM 输出仅作参考。

---

## Apply Agent

### 第一阶段：基础推荐生成，硬编码 PICO 框架（2026-01 至 2026-04）

Apply Agent 的初始版本读取 Appraise 输出的 overall_grade 和证据列表（只有 title/quality/source，无实际内容），调用 LLM 生成推荐文本。Python 侧有一条简单的强度限制规则：evidence_quality 为 Very Low 或 Low 时，LLM 输出的 Strong 推荐会被强制降为 Weak。

主要问题：Step 1 一致性检查硬编码了"Population / Intervention / Outcome"三个标签，对 PIRD 问题中的"Index Test"被错误地称为"Intervention"；`appraisal_summary` 是自由文本，LLM 无法区分"GRADE=Moderate 但存在 inconsistency=SERIOUS"与"GRADE=Moderate 且各因素均良好"；evidence_summary 只包含 title/quality/source，没有 Acquire 阶段 RAG 提取的 key_sentences；"inconsistency=SERIOUS → 强制 Weak"的规则未实现。

### 第二阶段：结构化输入 + GRADE enforcement 补全（2026-04-20）

针对四个问题的集中修复：prompt 中的 Step 1 按 route_type 动态展示对应框架的维度标签；appraisal_summary 拆分为四个结构化字段（`overall_grade`、`downgrade_factors` 摘要、`consistency_flag`、`appraisal_narrative`）；evidence_summary 开始注入 key_sentences 实际段落内容；Python 侧补充 inconsistency Rule 2（`has_serious_inconsistency and llm_strength == "Strong"` → 强制降为 Weak）。

### 第三阶段：GRADE 推荐强度规则纠偏 + 引用格式强制（2026-05-22）

发现 Apply prompt 中推荐强度映射规则与 GRADE 学术标准不符：

| 情况 | 旧规则（错误） | 新规则（GRADE 标准） |
|------|--------------|-------------------|
| Low + 结果一致 | Weak | **Conditional** |
| Very Low + 结果一致 | Weak | **Conditional** |
| Moderate + 一致 + 效益明显 | Conditional | **Strong** |
| 存在间接性（indirectness） | 降低推荐强度 | 写入 caveats，不降强度 |

同时引入强制引用格式规范：每条事实陈述后必须附 `[evidence_id / section]` 格式的内联引用（如 `[EV-META-2023-CHO-001 / results_3]`），使每条推荐内容都可追溯至 hypertensiondb 中具体文献的具体章节。

---

## Assess Agent

### 第一阶段：基础质量审计（2026-01 至 2026-04）

Assess Agent 从一开始就是 5A 流程中最后一道质量关卡，但早期实现相对简单：LLM 对推荐意见进行整体评价，输出 quality_score（0–1）和 gaps 列表，Coordinator 根据 needs_backtrack 标志决定是否回退。早期版本的 quality_score 计算缺乏明确的维度权重定义，也没有强制降级机制——即使 LLM 生成了一个基于 Very Low 证据的 Strong 推荐，Assess 也只是记录问题，不会主动触发降级。

### 第二阶段：加权评分 + 强制降级门槛（2026-04 至今）

重设计引入了四个显式评分维度的加权合并：
- 完整性（50%）：推荐是否覆盖了问题的各个方面
- 强度一致性（25%）：推荐强度是否与证据质量相符
- 推理链（15%）：从证据到推荐的逻辑是否清晰
- 免责声明（10%）：是否恰当说明了证据局限性

以及推荐强度的强制降级机制：quality_score < 0.70 但推荐为 Strong 时，自动降级为 Weak 并附说明文字。这一机制作为最后一道安全门，防止证据质量不足的情况下仍输出 Strong 推荐。

---

## Judge LLM

### 第一阶段：维度评分架构（2026-02）

Judge LLM 的设计灵感来自 ReAct 模式的"Observe"环节。早期设计（2026-02-02 调度系统设计文档）已确立了核心结构：Judge 对每个阶段输出进行多维度评分，产出 overall_score、dimension_scores、issues 列表和 summary。各阶段各有独立的评价维度（Ask 的 pico_completeness、searchability；Acquire 的 quantity_sufficiency、relevance、diversity 等）。

但这一版本的维度权重完全平等，所有维度一视同仁，没有"这个维度判断错误是灾难性的"与"这个维度稍有偏差是可接受的"之间的区分，导致系统对本质上是主观判断的 GRADE 因素和客观可验证的数学计算错误同等严苛，产生大量不必要的 retry 循环。

### 第二阶段：Gate + Rubrics 架构（2026-04-22）

2026 年 4 月的 judge_llm.py 重写引入了两层结构：

**Hard Gates（硬性门控）：** 一旦触发，直接影响流程，不经过打分加权。包括：
- `intent_not_distorted`：PICO 方向是否被扭曲
- `route_correct`：路由是否正确
- `recommendation_grounded_in_evidence`：推荐是否有证据支撑
- `strength_not_grossly_inflated`：Very Low 给 Strong 是明确错误
- `computed_grade_reasonable`：GRADE 数学计算路径可验算

**Rubrics（加权评分项）：** 每个维度有明确权重（1 = Minor，2 = Major，3 = Critical），`RUBRIC_WEIGHTS` 字典集中定义，`_score_rubrics()` 方法按权重计算加权得分，`_check_gates()` 方法独立检查硬门控。

各阶段核心评分维度：

| 阶段 | 核心维度（权重） |
|------|----------------|
| Ask | core_dimensions_present(3), secondary_dimensions_present(2), statement_unambiguous(1) |
| Acquire | keywords_cover_pico(3), primary_focus_match(3), p_match(3), o_match(3) |
| Appraise | included_study_type_correct(3), conflicts_identified(2), downgrade_factors(3→1) |
| Apply | strength_matches_evidence(3), effect_size_correct(3), population_applicability(2) |
| Assess | answer_completeness(35%), reasoning_chain(35%), logical_consistency(30%) |

### 第三阶段：学术规范对齐（2026-05-25）

运行 30 题测试并与 EBM 学术文献对照后，发现 Judge 的一个系统性问题：若干被设为高权重的 Rubric 维度，其判断标准在学术上属于"允许专家分歧的主观判断"，不应触发 retry。

具体修改：

**`downgrade_factors_appropriate` 权重从 3（Critical）降为 1（Minor）。** GRADE 降级因子本质上是 judgment call，两名专业评审者的 κ 约为 0.39，系统不应将主观分歧视为错误强制重试。

**G1（study_type 验证）从 MAJOR gate 降为 MINOR。** 原规则用 passage 片段验证 LLM 输出的 study_type（用质量低的信息推翻质量高的信息）。修改为：有预计算 study_type（来自全文 Methods）时直接按预计算值判断；无预计算值时才用 passage 验证。G1=NO 的触发后果改为仅记录，不触发 retry。

---

## Scheduling LLM

### 第一阶段：基础决策逻辑（2026-02 至 2026-04）

Scheduling LLM 从一开始就确立：一个独立的 LLM 实例，读取 Judge 的 Observe 输出 + 历史状态，决定工作流如何继续：

- `proceed`：进入下一阶段
- `retry_current`：当前阶段重试
- `backtrack_to_X`：回退到之前某阶段
- `terminate`：终止
- `request_human_review`：请求人工干预

早期版本的决策规则依赖 LLM 的通用推理能力，缺乏领域专属的 EBM 方法论约束，导致部分决策与学术预期不符。

### 第二阶段：FAST-PATH 优化 + 迭代预算（2026-04 至 2026-05）

为防止无限循环，加入若干程序性保障：

**FAST-PATH 规则（跳过 Scheduling LLM 直接 proceed）：**
- 无 Major/Critical 问题 → 自动 proceed
- 所有 PARTIAL 且总分通过 → proceed（GRADE 接受部分合规）
- 同一维度已循环多次 → 强制 proceed（防止无限重试）
- N 次重试上限 → 强制 terminate

**全局迭代预算：** remaining_budget = 20 - iteration_count（硬上限保证终止）

**上下文截断：** 阶段输出内容截断至 3000 字符，优先保留决策相关字段，压缩证据摘要，防止 Scheduling 的 context window 被证据内容淹没。

### 第三阶段：EBM 方法论对齐（2026-05-25）

与 Judge 的学术对齐同步进行，`scheduling_llm.txt` 新增三条基于 EBM/GRADE 学术标准的规则：

**规则一（acquire_partial_pico_match）：** Acquire 返回的证据如果只是 PICO 部分匹配（人群稍有差异、代理结局），必须 proceed 进入 Appraise，由 GRADE 的 indirectness 降级机制处理，而非视为检索失败回退到 Ask。这符合 GRADE 方法论核心原则——间接证据是有价值的，不是"搜索失败"。

**规则二（database_content_gap）：** 如果系统已 backtrack_to_ask 一次，重新构建 PICO 后 Acquire 仍然返回无关证据，则识别为数据库内容空白（不是 PICO 问题），直接 proceed 输出 Insufficient Evidence，不再继续循环改写 PICO。

**规则三（downgrade_factors_judgment）：** `downgrade_factors_appropriate` 单独失败不触发 retry，必须同时伴随 `computed_grade_reasonable=NO`（GRADE 数学计算路径有明确错误）才考虑 retry。

---

## 整体演进规律总结

纵观所有组件的迭代历史，可以看到一条清晰的主线——系统从"能跑通"到"跑得快"再到"符合学术规范"三个层次依次演进。

早期版本的主要错误集中在两类：
1. **GRADE 规则的具体计算细节与学术标准不符**：升级因素缺失、SR 初始分固定、推荐强度映射错误、rob_overall=some_concerns 被错误降级。
2. **将学术上允许主观分歧的判断标准错误地设置为强触发条件**：GRADE 降级因子（κ≈0.39）被设为 Critical 权重触发 retry；study_type 边界情况被设为 MAJOR gate；Acquire PARTIAL 匹配被视为检索失败触发回退。

2026 年 5 月的改造通过将主观与客观可验证的指标明确区分，最终将跨运行推荐强度一致率提升至 95%，平均耗时从基准 216.6 秒降至 149.3 秒，最大耗时从未统计降至 197.6 秒，消除了所有 300 秒以上的长尾异常。
