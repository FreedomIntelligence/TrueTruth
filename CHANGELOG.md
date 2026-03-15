# EBM 5A 系统改进记录

本文档记录系统在原始 MVP 基础上所做的两类主要改进：**运行时间优化**和**问题类型适配**。

---

## 一、运行时间优化

### 背景：为什么运行慢？

单次完整运行（Ask → Acquire → Appraise → Apply → Assess）涉及约 **10-15 次串行 LLM API 调用**，每次调用延迟约 15-45 秒。理论最小时间约 5 分钟，典型运行时间 6-10 分钟。主要瓶颈：

| 瓶颈 | 典型耗时 | 原因 |
|------|---------|------|
| Acquire 查询生成 | 25-35s | 单次 LLM 调用 |
| Appraise（×2 批） | 40-50s/次 | 10 篇文献分批并行 |
| Apply | 40-65s/次 | 长上下文生成 |
| Judge × 每阶段 | 7-13s/次 | 分类标签推理 |
| Scheduling LLM（有问题时） | 25-40s/次 | 树状决策分析 |

### 已实施的优化措施

#### 1. Scheduling 快速跳过（FAST-PATH）
**文件**：`src/coordinator/coordinator.py`

当 Judge 评分通过阈值且无 critical/major 问题时，直接 `proceed`，不调用 Scheduling LLM。

```python
# 条件：pass_threshold=True 且 issues 全为 minor 级别
if current_observe.evaluation.pass_threshold and not has_critical_or_major:
    decision = SchedulingDecision(action="proceed", ...)
    print("[FAST-PATH] ...")
```

**节省**：每触发一次节省约 25-40 秒。典型运行中 Ask/Acquire 阶段几乎总能触发。

#### 2. 循环 Major 问题自动前进（FAST-PATH-2）
**文件**：`src/coordinator/coordinator.py`

若当前 Major 问题维度组合在本阶段**任意历史尝试**中出现过，且分数已通过阈值 → 自动 `proceed`（避免 Scheduling LLM 重复分析同一循环问题）。

```python
dims_seen_before = any(
    current_major_dims == frozenset(...)
    for obs in prev_same_stage_obs  # 所有历史尝试，非仅最近一次
)
if dims_seen_before:
    decision = SchedulingDecision(action="proceed", ...)
    print("[FAST-PATH-2] ...")
```

**节省**：每触发一次节省约 25-40 秒。Appraise 阶段因 GRADE 分类反复出现 `grade_reasonableness` 问题时频繁触发。

#### 3. PubMed 并行 Fetch
**文件**：`src/tools/pubmed_api.py`

`fetch_summaries` 和 `fetch_abstracts` 用 `ThreadPoolExecutor` 并行执行。

**节省**：PubMed 检索总耗时从约 15s 降至约 6-8s（节省约 40%）。

#### 4. Appraise 并行批次
**文件**：`src/agents/appraise_agent.py`

10 篇文献分 2 批（每批 5 篇），用 `ThreadPoolExecutor` 并行调用 LLM。

**节省**：Appraise 耗时从约 80s 降至约 40-50s（节省约 50%）。

#### 5. PubMed 磁盘缓存
**文件**：`src/tools/pubmed_api.py`

相同查询结果缓存 24 小时到 `data/cache/`，避免重复 API 调用。

**收益**：重复测试同一问题时 Acquire 阶段从约 45s 降至约 8s。

#### 6. Scheduling 提示词截断
**文件**：`src/scheduling/scheduling_llm.py`

`stage_output` 截断到 3000 字符；Appraise 阶段额外剔除 `abstract` 字段，让 3000 字符额度用于关键分类信息。

**节省**：Scheduling 调用耗时从约 35s 降至约 25s（减少输入 token）。

#### 7. Judge Appraise 输入瘦身
**文件**：`src/judge/judge_llm.py`

Appraise 阶段的 `stage_output` 剔除 `abstract` 字段，减少约 1000 tokens。

#### 8. GRADE 11 种研究类型
**文件**：`src/agents/appraise_agent.py`，`src/config/prompts/appraise_agent.txt`

从原始 4 种（RCT/Cohort/CaseControl/CaseReport）扩展到 11 种，新增：
- `SYSTEMATIC_REVIEW` / `META_ANALYSIS` / `NMA`（高质量，initial_grade=4）
- `GUIDELINE`（中等，initial_grade=3）
- `CROSS_SECTIONAL`（低，initial_grade=2）
- `NARRATIVE_REVIEW` / `EXPERT_OPINION`（极低，initial_grade=1）

**效果**：对于含大量系统综述/Meta分析的问题（如 T2DM、ACS 等），Appraise 通过率显著提升，减少重试次数约 50%。

#### 9. get_fast_llm() 基础设施
**文件**：`src/config/llm_config.py`，`src/main.py`

Judge 和 Scheduling 使用 `get_fast_llm()`，可通过 `.env` 中的 `FAST_LLM_MODEL` 环境变量配置更快的轻量模型（如 Sonnet）替代 Opus，进一步加速。

```bash
# .env 中添加：
FAST_LLM_MODEL=claude-sonnet-4-6
```

### 进一步缩短时间的可能性分析

| 优化方向 | 预计节省 | 实施难度 | 备注 |
|---------|---------|---------|------|
| **配置 FAST_LLM_MODEL=sonnet**（最推荐） | 每次 Judge/Scheduling 调用节省 60-70%，总计约 2-3 分钟 | 极低（改 `.env`） | 仅需添加一行配置，对结果质量影响小 |
| Ask agent 并行化（PICO + question_type 一次调用） | 目前已合并，无额外节省 | — | 已实现 |
| Acquire + Appraise 流水线并行 | 理论节省约 40s | 高 | 需重构工作流调度，架构改动大 |
| Apply 输入压缩（只传 title+质量+关键结论） | 约 10-20s | 中 | 可能降低推荐质量，需 A/B 测试 |
| 缓存 Appraise 结果（同 PMID 复用） | 仅对重复问题有效 | 低 | 适合批量评测场景 |
| 降低 _TOP_K（从 10 减至 7） | 约 10-20s | 低 | 可能降低 Acquire 质量 |

**结论**：在不改算法参数的前提下，**配置轻量 Scheduling/Judge 模型是性价比最高的优化手段**，可节省总时间约 30-40%。

---

## 二、问题类型适配

### 背景：哪些问题类型原来回答不了？

原系统针对**治疗型（Therapy）问题**设计：
1. **搜索过滤器**固定为 Cochrane HSSS（偏向 RCT/SR），对诊断型问题几乎找不到 DTA 研究
2. **推荐强度**仅有 Strong/Weak/Insufficient Evidence/No Recommendation，面对间接证据或专家共识无法给出有意义的推荐

典型失败案例：
- 诊断型问题（"该患者的诊断与鉴别诊断是什么？"）→ "无法基于检索证据提供循证诊断推荐"
- 证据不足但有间接支持的治疗问题（活动性 GI 出血 ACS 氯吡格雷单药 vs DAPT）→ "Insufficient Evidence"

### 已实施的适配措施

#### A. Ask Agent 增加 question_type 识别

**文件**：`src/config/prompts/ask_agent.txt`，`src/agents/ask_agent.py`，`src/state/schema.py`

Ask agent 在输出 PICO JSON 时同时识别并输出 `question_type` 字段，写入 `WorkflowState`：

| 类型 | 说明 | 适用场景 |
|------|------|---------|
| `Therapy` | 治疗干预效果（默认） | 药物/手术/疗程比较 |
| `Diagnosis` | 诊断测试准确性 | 诊断标准、检查准确度 |
| `Prognosis` | 疾病预后/转归 | 生存率、复发风险 |
| `Harm` | 不良反应/风险暴露 | 药物毒性、职业暴露 |
| `Prevention` | 预防干预 | 疫苗、筛查、预防性药物 |

无效值自动回退到 `Therapy`。

#### B. Acquire Agent 根据 question_type 切换搜索过滤器

**文件**：`src/agents/acquire_agent.py`

新增两种专用过滤器，替代原有统一 HSSS 过滤器：

```
Therapy / Prevention → HSSS 过滤器（RCT + 系统综述）[原有]
Diagnosis           → DTA 过滤器（sensitivity/specificity/ROC/QUADAS/诊断准确性）
Prognosis / Harm    → 观察性研究过滤器（cohort/prospective/retrospective，去掉 RCT 限制）
```

当过滤后结果为 0 时，自动回退到无过滤的基础查询。

#### C. Apply Agent 增加 Conditional 和 Consensus-based 推荐强度

**文件**：`src/config/prompts/apply_agent.txt`，`src/config/prompts/judge/apply_judge.txt`，`src/config/prompts/assess_agent.txt`

新增两种推荐强度：

**Conditional（条件性推荐）**
- 适用条件：有间接证据（不同人群、替代终点、相似干预），但无直接适用研究证据
- 要求：必须说明"什么间接证据支持"以及"为何缺乏直接证据"
- 典型案例：活动性 GI 出血 ACS 患者的抗血小板治疗（所有 RCT 排除活动性出血，但有高出血风险 ACS 的间接证据）

**Consensus-based（共识性推荐）**
- 适用条件：无相关研究证据，但有权威临床指南/专家共识支持
- 特殊权限：**唯一允许引用外部指南知识**的强度（其他强度严格依赖检索证据）
- 要求：必须注明"基于指南共识非研究证据，建议独立验证"
- 典型案例：临床诊断与鉴别诊断（引用 ESC/ACC/AHA 诊断标准）

对应的 Judge 评分规则（`apply_judge.txt`）和 Assess 评分说明（`assess_agent.txt`）均已同步更新。

#### D. Apply Agent JSON 解析重试

**文件**：`src/agents/apply_agent.py`

对于包含长患者档案的复合问题，LLM 可能在 Apply 阶段生成超长 Reasoning 导致响应被截断、JSON 部分丢失，引发程序崩溃。

修复：JSON 解析失败时自动追加一次精简 prompt 重试（仅要求输出 JSON），防止 crash。

### 适配效果

| 问题类型 | 改动前输出 | 改动后输出 |
|---------|---------|---------|
| NSTEMI+GI出血 氯吡格雷 vs DAPT（无直接 RCT） | `Insufficient Evidence`，quality 0.52 | `Conditional`，quality **0.88** |
| 复合问题：诊断+治疗（诊断部分无文献证据） | 诊断部分："无法提供推荐"；可能 crash | 诊断 `Consensus-based`（引用 ESC 2020）+ 治疗 `Conditional`，quality **0.88** |

---

## 三、推荐强度完整参考

改动后系统支持的推荐强度（`strength` 字段）：

| 强度 | 适用证据 | EBM 含义 |
|------|---------|---------|
| `Strong` | High/Moderate 直接证据，结果一致 | 推荐执行，效益明确超过风险 |
| `Weak` | Low 证据，或结果不一致 | 推荐考虑，效益不确定 |
| `Conditional` | 仅间接证据（不同人群/替代终点/相似干预）| 在特定条件下可参考，需说明间接性 |
| `Consensus-based` | 无研究证据，仅专家共识/权威指南 | 基于临床实践经验，证据等级最低 |
| `Insufficient Evidence` | Very Low 且不一致，无法外推 | 现有证据不足以形成推荐 |
| `No Recommendation` | 检索无任何相关文献 | 无法就该问题给出任何意见 |

---

*最后更新：2026-03-15*
