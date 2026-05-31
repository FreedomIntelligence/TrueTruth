# EBM 5A — 会话记忆导出
> 生成时间：2026-05-25  
> 来源：Claude Code memory（`~/.claude/projects/C--Users-Winda-Desktop-ebm5a/memory/`）

---

## 一、项目状态（Project Memory）

### 系统架构（2026-05-22 大改造完成）

分支：`feature/hypertension-rag`，基于 main commit 52e7e59  
完整文档：`docs/REFACTOR_SUMMARY.md`

**架构改动**：
- Ask agent 加领域过滤（非高血压软拒绝）
- Acquire 从 PubMed 全面切换为 hypertensiondb RAG（HTTP `/search`）
- Evidence 改为 paper+passages 模型
- Apply prompt 强制 `[evidence_id / section]` 引用格式
- 首字时间优化：流式输出 + warmup，首字 ~2-6s

**证据库**：
- 461 篇文章（含 6 篇 landmark trial：SPRINT/STEP/ALLHAT/ACCORD/HYVET/ONTARGET）
- API reranker：BAAI/bge-reranker-v2-m3 via HuatuoGPT gateway
- 所有文章已补 `grade_level` / `rob_overall` / `study_type` 字段

**GRADE 规则修正**（符合 Guyatt et al. 2011）：
- Low + consistent → Conditional（原来错误地给 Weak）
- Moderate + consistent + 效益明显 → Strong
- rob_overall=some_concerns → NOT_SERIOUS（不自动降级）

---

### 性能基准（2026-05-25 最新）

| 指标 | 数值 |
|------|------|
| 30题平均耗时 | **149.3s**（历史最低，目标 <4min ✅） |
| max | 197.6s（全面消除 300s+ outlier） |
| 改善幅度 | 216.6s → 149.3s，提升 31% |

---

### study_type 架构改动（2026-05-25）

**根本问题**：judge 的 G1 用 passage 片段验证 study_type，但 passage 不如全文 Methods 权威，导致误判循环。学术标准（Cochrane Handbook）明确要求从全文 Methods 章节判断研究设计，而非片段推断。

**改动清单**：

1. `hypertension/scripts/backfill_grade.py`：新增 `--force-study-type` 参数，对全部 461 篇文章从 Methods 全文章节重新提取 study_type（460/461 成功）
2. `hypertension/src/hypertensiondb/schema/base.py`：`BaseFrontmatter` 新增 `study_type: Optional[str] = None`
3. `hypertension/src/hypertensiondb/index/chunker.py`：`study_type` 写入 Qdrant payload
4. `hypertension/src/hypertensiondb/retrieval/models.py`：`EvidenceMeta` 新增 `study_type` 字段
5. `hypertension/src/hypertensiondb/retrieval/search.py`：从 payload 读取 `study_type` 并返回
6. `src/tools/hypertension_rag_client.py`：优先读 `study_type`，fallback 到 `type`
7. `src/agents/appraise_agent.py`：预计算 study_type 直接覆盖 LLM 输出用于 GRADE 计算；hint 标记为"来自全文 Methods 提取，权威值"
8. `src/config/prompts/judge/appraise_judge.txt`：G1 规则改为有预计算值时直接使用（不再用 passage 验证）
9. `src/judge/judge_llm.py`：G1=NO 从 MAJOR gate 降为 MINOR（不触发 retry）

---

### Judge/Scheduling 学术规范对齐（2026-05-25）

**背景**：对比 EBM 学术标准（GRADE Guyatt et al. 2011 + Cochrane Handbook）发现多处 judge 标准与学术不符，导致无效 retry 循环。

**改动**：

| 文件 | 改动内容 |
|------|---------|
| `src/judge/judge_llm.py` | `downgrade_factors_appropriate` 权重 3 → 1（GRADE 降级因素是 judgment call） |
| `src/config/prompts/scheduling_llm.txt` | 新增 `acquire_partial_pico_match` 规则：Acquire PARTIAL 必须 proceed |
| 同上 | 新增 `database_content_gap` 规则：backtrack 后仍无关 → 识别为内容缺口，proceed |
| 同上 | 新增 `downgrade_factors_judgment` 规则：此项单独不触发 retry |

**FAST-PATH 合理性评估**：整体与学术标准一致，仅 FAST-PATH-3 Acquire 空结果分支有隐含"数据库有内容"假设，已用 scheduling 规则补充。

---

### 一致性测试结果（2026-05-25）

两轮 30 题 batch test 对比（Run 1: 203534 / Run 2: 214656）：

**机器精确匹配**：
| 维度 | 一致率 | 说明 |
|------|-------|------|
| 推荐强度 | 83%（20/24） | 其中 3 道为 API 错误，排除后真实率 **95%** |
| 证据质量 | 83% | 同上 |

**gpt-5.5 方向 Rubric**（依据 GRADE IRR 标准，已移除"适用人群"维度）：
| 维度 | 一致率 |
|------|-------|
| 推荐对象 | 76% (16/21) |
| 推荐倾向 | 81% (17/21) |
| **综合方向** | **67%** 一致 / 29% 部分一致 / 5% 不一致 |

**说明**："适用人群描述"不作为独立一致性指标——依据 GRADE IRR 研究（PMID 26845745），推荐方向（for/against）的 kappa≈0.74，适用人群描述差异属于 GRADE indirectness 范畴。

**"部分一致"的规律**：特殊人群/合并症题（老年、CKD、糖尿病、冠心病）和新兴干预（肾去神经术）一致性低于简单直接题，符合 GRADE IRR 文献预期。

---

### 待做事项

**代码 bug**：
- Q18 偶发 JSON 解析错误（`Extra data: line 1 column 7`）未定位根因
- `coordinator.py` FAST-PATH-3 Acquire 空结果分支未同步 `database_content_gap` 逻辑

**证据库内容缺口**（需入库）：
- 阿司匹林抗血小板二级预防 RCT/SR（Q26 content gap）
- ASCOT-BPLA（Lancet 2005）→ Q5 β受体阻滞剂
- ACCOMPLISH（NEJM 2008）→ Q6 加药策略
- LIFE（Lancet 2002）→ Q1 ARB vs ACEI
- CAMELOT（JAMA 2004）→ Q13 高血压+冠心病
- CHIPS（NEJM 2015）→ Q12 妊娠期高血压
- PATHWAY-2（Lancet 2015）→ Q16 难治性高血压
- 中医/针灸高质量 RCT（改善 Q22/23/24 consistency）

**准确性评估**（下一步）：
- 为 25 道领域内问题编制"指南参考答案表"（2023 ESC/ESH 或中国 2023 高血压指南）
- 以 Guideline Concordance 作为准确性客观标准

---

### 关键配置

```
# ebm5a/.env
HYPERTENSION_API_URL=http://localhost:8000
HYPERTENSION_API_TIMEOUT=60
RAG_SEARCH_TOP_K=15
RAG_MAX_PAPERS=6
RAG_MAX_PASSAGES_PER_PAPER=3

# hypertension/.env
EMBEDDER=zhipu  EMBED_DIM=2048
RERANKER=api
LLM_API_KEY=<HuatuoGPT key>
LLM_BASE_URL=https://api.huatuogpt.cn/v1
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
QDRANT_HOST=localhost  QDRANT_PORT=6333
EVIDENCE_ROOT=evidence
```

启动服务：`cd hypertension && hdb serve run --host 127.0.0.1 --port 8000`

---

## 二、操作规范（Feedback Memory）

### 准确性优先于延迟

性能优化（缩短 TTFT / 全流程耗时）是次要目标，**准确性永远第一**。

- 任何会改变 LLM 调用结构（合并调用、模型降级、prompt 大幅重写）的优化，必须先设计对比实验再采纳
- 不影响模型输入/输出的优化（连接复用、warm-up、prompt caching 前缀重排、无依赖调用并行化）可以直接做

### 测试规范

**不做**单元测试、集成测试、golden test。  
唯一有效的验证：全流程跑一遍 pipeline → 看 `[TIMING]` 数据 → 读输出质量。

### Git 操作规范

设计/规划/brainstorming 阶段**不做任何 `git commit` / `git add`**。用户手动提交。

### .env 文件操作规范

修改 `.env` 文件**只用 Edit 工具**，绝不用 Write 整体重写。  
历史教训：Write 重写 `hypertension/.env` 导致 `LLM_API_KEY` 被删除，reranker 静默回退到 score=0.0，整个会话的检索质量降级。

### Judge Rubric 设计原则

新增/修改 judge rubric 时，先问"这是客观可验证的，还是学术上允许分歧的判断？"

**可触发 retry（客观可验证）**：
- `computed_grade_reasonable`：数学计算路径可以验算
- `recommendation_grounded_in_evidence`：推荐方向与证据一致性
- `strength_not_grossly_inflated`：Very Low 给 Strong 是明确错误
- `effect_size_correctly_reported`：数字转述可以核对
- `intent_not_distorted`：PICO 方向性错误

**不应触发 retry（GRADE 主观 judgment call）**：
- `downgrade_factors_appropriate`：risk_of_bias / indirectness / imprecision 均为主观判断，权重已降为 1
- `study_type_correct`（G1）：边界情况是学术模糊地带，已改为 MINOR
- 适用人群描述差异：属于 GRADE indirectness 范畴，不是独立的一致性失败条件

---

## 三、技术参考（Reference Memory）

### HuatuoGPT 网关 Prompt Caching

网关支持自动前缀缓存，但报告方式非标准：

- 标准 OpenAI：`cached_tokens` 单独字段
- huatuogpt 实际：`prompt_tokens` 直接扣减（只算未缓存部分），`cached_tokens` 始终为 0

衡量缓存效果应看 **prompt_tokens 总量随调用次数的增长曲线**，而非 hit_rate。  
缓存范围约有 ~3000 token 上限。重排 prompt 模板可提高缓存命中率，但属于改变模型输入顺序的优化，需 A/B 验证。

**可用模型（HuatuoGPT 网关，2026-05-25 验证）**：
- `gpt-5.5`（最新）、`gpt-5.4`、`gpt-5.4-xhigh`、`gpt-5.4-high`
- `gpt-5.3-codex`、`gpt-5.2`
- `gemini-3.1-pro-preview-thinking`、`deepseek-r1-250528`
- `HuatuoGPT-3-32B-no-thinking`（主力 LLM）、`BAAI/bge-reranker-v2-m3`（reranker）
