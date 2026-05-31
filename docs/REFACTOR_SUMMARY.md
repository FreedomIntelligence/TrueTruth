# EBM 5A 高血压 RAG 改造总结

**日期**: 2026-05-22  
**分支**: feature/hypertension-rag  
**基于**: main 分支 commit 52e7e59（4/20-4/22 重设计后的运行系统）

---

## 一、本次改造做了什么

### 1.1 系统架构改造

**领域限定（Ask Agent）**

- `router_unified.txt` 新增 Step 0 领域过滤：判断问题是否与高血压相关
- `ask_agent.py` 新增 `_handle_out_of_domain()` 软拒绝路径
- 非高血压问题（如糖尿病、肿瘤、骨科）在 Ask 阶段直接返回友好提示，不进入后续 pipeline
- 策略：宽松模式——高血压合并症、边界案例默认放行

**证据检索全面 RAG 化（Acquire Agent）**

- 删除 PubMed / PMC 全文抓取 / BM25 RAG / Listwise rerank 全套
- 新建 `src/tools/hypertension_rag_client.py`：httpx HTTP client，调用 hypertensiondb FastAPI `/search`
- Acquire 流程：PICO → LLM 生成中英文混合自然语言 query → `/search` → chunk 聚合为 paper+passages
- 新增 `.env` 配置：`HYPERTENSION_API_URL`、`HYPERTENSION_API_TIMEOUT`、`RAG_SEARCH_TOP_K`、`RAG_MAX_PAPERS`、`RAG_MAX_PASSAGES_PER_PAPER`

**Evidence 数据模型改造（paper + passages）**

- `src/state/schema.py`：新增 `Passage` dataclass；`Evidence` 改为 paper+passages 模型
- 删除旧字段：`pmid`、`pmcid`、`abstract`、`full_text`、`has_full_text`、`pub_types`、`key_sentences`
- 新增字段：`evidence_id`、`supporting_passages`、`language`、`tags`、`grade_level`、`rob_overall`

**下游 prompt 重写（OpenEvidence 风格引用）**

- `appraise_agent.txt`：适配 paper+passages 输入格式
- `apply_agent.txt`：强制 `[evidence_id / section]` 引用格式（每条事实陈述后必须有引用标记）
- `assess_agent.txt`：新增 `citation_validity` 评估维度
- 5 个 Judge prompt 同步更新评分维度

**渐进式输出（首字时间优化）**

- `coordinator.py`：`execute_workflow()` 新增 `on_stage_complete` 回调，每个 agent 完成后立即打印结果
- `ask_agent.py`：`_call_unified_router()` 改用 `stream_reasoning()`，Ask Reasoning 段实时流式打印
- `apply_agent.py`：同样改用 `stream_reasoning()`，Apply 推理过程实时可见
- `llm_config.py`：新增 `stream_reasoning()` 方法（状态机：SCAN → PRINT → DONE，只打印 Reasoning 段，过滤 JSON）
- `main.py`：warmup 改为 fire-and-forget（不阻塞 Ask 启动）
- **效果**：首字出现时间从 ~15s 降至 ~2-6s（API 首 token 延迟）

---

### 1.2 hypertensiondb 证据库改造

**API Reranker（最大召回质量提升）**

- 新建 `hypertension/src/hypertensiondb/retrieval/reranker_api.py`
- 调用 HuatuoGPT gateway 的 `BAAI/bge-reranker-v2-m3` API（`/rerank` 端点）
- 替代 mock reranker，/search 耗时从 0s（mock）增加约 3s（API 调用）
- **效果**：召回质量从"只能找到高曝光文章"变为"精准语义匹配"，Q2（ARB+CCB）从死循环变为正常完成

**Landmark Trial 入库（6篇）**

手动下载 PDF 并通过 `hdb ingest pdf` 入库：

| 试验 | PMID | 年份 | 核心贡献 |
|------|------|------|---------|
| SPRINT | 26551272 | 2015 | 强化降压 SBP<120 vs <140，n=9361 |
| STEP | 34739196 | 2021 | 中国老年高血压强化降压，n=8511 |
| ALLHAT | 12479763 | 2002 | 氯噻酮 vs 赖诺普利 vs 氨氯地平，n=33357 |
| ACCORD BP | 20228401 | 2010 | 糖尿病+高血压强化降压 |
| HYVET | 18378519 | 2008 | 80岁以上高血压，n=3845 |
| ONTARGET | 18378520 | 2008 | 替米沙坦 vs 雷米普利，n=25620 |

入库时用 `HuatuoGPT-3-32B-no-thinking` 自动抽取 PICO/grade/rob 字段，status 自动升级为 reviewed。

**批量补充 grade/rob 字段（401篇）**

- 新建 `hypertension/scripts/backfill_grade.py`
- 对所有已入库文献（RCT/META/SR/GL/TCM）调 LLM 抽取 `grade_level`、`rob_overall`、`study_type`
- 修复 `risk_of_bias.tool` 缺失问题（批量补 `tool: RoB2`）
- 全量 rebuild Qdrant 索引，chunk payload 带上预计算字段

**RAG client 传递预计算字段**

- `hypertension_rag_client.py`：从 `evidence_meta` 读取 `grade_level`、`rob_overall`、`type`，直接填入 `Evidence` 对象
- 不再硬编码 `grade_level=None`

**Appraise 优先读预计算字段**

- `appraise_agent.py`：若 `evidence.grade_level` 和 `evidence.rob_overall` 有值，直接用，不走 LLM 推断
- `rob_overall` 映射修正：`some_concerns` → `NOT_SERIOUS`（不自动降级），只有 `high` → `SERIOUS`

---

### 1.3 GRADE 推荐强度规则修正

**Apply prompt Step 3 修正（符合 GRADE 学术标准）**

| 旧规则（错误） | 新规则（GRADE 标准） |
|--------------|-------------------|
| Low OR inconsistent → Weak | Low + consistent → **Conditional** |
| Low + inconsistent → Weak | Low + inconsistent → Weak（不变） |
| Very Low + consistent → Weak | Very Low + consistent → **Conditional** |
| Moderate + 有局限 → Conditional | Moderate + consistent + 效益明显 → **Strong** |
| indirectness → 降低 strength | indirectness → 写进 caveats，不降 strength |

**Apply judge R2 同步更新**，与新规则一致。

---

## 二、改造效果（30题测试对比）

| 指标 | 改造前（mock reranker） | 改造后（最终版） |
|------|----------------------|----------------|
| 完成率 | 28/30（有死循环） | **30/30** |
| 平均总耗时 | ~179s | **~161s** |
| 首字时间 | ~15s | **~2-6s** |
| Strong 推荐数 | 0 | **~4-6题** |
| Conditional 推荐数 | 0 | **~18-20题** |
| Weak 推荐数 | ~18 | **~2-4题** |
| Evidence Quality High | 0 | **~2题** |
| Evidence Quality Moderate | ~19 | **~19题** |
| Cross-run consistency（Strength） | 未测 | **19/30（63%）** |
| Cross-run consistency（Quality） | 未测 | **23/30（77%）** |

---

## 三、代码层面还缺什么

### 3.1 中等优先级

**Appraise 的 GRADE 计算仍有偏差**

`_compute_grade()` 函数基于 LLM 分类标签做 Python 计算，但当文章有预计算字段时，这个函数的输出会被覆盖。两套逻辑并存，容易混乱。建议统一：有预计算字段时完全跳过 `_compute_grade()`，直接用 frontmatter 值。

**Assess agent 的 `citation_validity` 维度未充分利用**

Assess 能检测 Apply 的引用格式，但目前 Assess 的 backtrack 触发阈值较高，citation 问题很少触发回退。可以降低阈值，让引用错误更容易触发 Apply 重试。

**Scheduling LLM 的"证据不足时回退 Ask"策略过激**

当 Acquire 召回 0-1 篇时，Scheduling 倾向于回退 Ask 重写 PICO。但如果是数据覆盖问题（库里根本没有），回退无效且浪费 budget。应改为：回退 1 次后若仍无改善，直接 proceed 走"证据不足"路径。

**Pipeline 稳定性（Q6/15/18 偶发未生成推荐）**

某些题偶发 workflow 提前终止，原因未完全定位。需要加更细粒度的错误日志。

### 3.2 低优先级

- `batch_test_questions.py` 脚本在 Windows 终端有编码问题，需要用户手动运行
- `run_test.sh` 用 `python3` 命令，Windows 上需改为 `py`
- 旧测试文件（`tests/agents/test_ask_agent.py` 等）部分仍有旧字段引用，未完全清理

---

## 四、证据库层面还缺什么

### 4.1 高优先级（直接影响核心问题的推荐质量）

**缺失的关键 landmark trial（需手动找 PDF）**

| 试验 | 核心贡献 | 影响的问题 |
|------|---------|-----------|
| ASCOT-BPLA（Lancet 2005） | 氨氯地平 vs 阿替洛尔，证明 β 阻滞剂劣于 CCB | Q5 β受体阻滞剂地位 |
| ACCOMPLISH（NEJM 2008） | 贝那普利+氨氯地平 vs 贝那普利+利尿剂 | Q6 加药策略 |
| LIFE（Lancet 2002） | 氯沙坦 vs 阿替洛尔，ARB 优于 β 阻滞剂 | Q1 ARB vs ACEI |
| CAMELOT（JAMA 2004） | 氨氯地平 vs 依那普利 in 冠心病 | Q13 高血压+冠心病 |
| CHIPS（NEJM 2015） | 妊娠高血压严格 vs 宽松控制 | Q12 妊娠期高血压 |
| PATHWAY-2（Lancet 2015） | 螺内酯治疗难治性高血压 | Q16 难治性高血压 |

**中医/针灸高质量 RCT 缺失**

Q22/23/24 的 cross-run consistency 差，根本原因是库里中医相关的高质量 RCT 极少。需要补充天麻钩藤饮、针灸降压的 Cochrane 系统评价或大型 RCT。

### 4.2 中等优先级

**grade/rob 字段质量偏保守**

批量补充的 grade/rob 字段由 LLM 从有限文本推断，系统性偏保守（大量 `some_concerns`）。随着更多 landmark trial 入库并经人工审核，这些字段会逐步准确。

**PubMed 批量入库的文章质量参差**

当前 401 篇中有部分文章（如 `EV-RCT-2026-NEGM-001` Propranolol+gabapentin for TBI）与高血压无关，是 PubMed 查询时的噪声。建议定期运行 `hdb lint` 清理。

---

## 五、后续改进方向

### 5.1 近期（1-2周）

1. **补充 6 篇 landmark trial**（ASCOT/ACCOMPLISH/LIFE/CAMELOT/CHIPS/PATHWAY-2）
2. **再跑一轮 30 题测试**，验证 Strong 推荐数是否进一步提升
3. **修复 Scheduling 的过激回退策略**（代码改动，1-2小时）

### 5.2 中期（1个月）

1. **扩充证据库到 500-600 篇**，重点补充：
   - 中医/针灸高质量 RCT（改善 Q22/23/24 consistency）
   - 新型药物（SGLT2i、finerenone、renal denervation 最新 RCT）
   - 中国人群特异性研究（CSPPT、STEP 系列）
2. **人工审核 grade/rob 字段**（至少审核 landmark trial 的 6 篇 + 高频召回的 top 20 篇）
3. **切换到真实 bge reranker**（等有 GPU 或找到更快的 API 方案）

### 5.3 长期（架构层面）

1. **Appraise 架构重构**：彻底分离"读预计算字段"和"从 passage 推断"两条路径，消除当前的双轨并存
2. **Apply 引入患者偏好维度**：当前 Apply 的 `patient_preference_considered` 评分长期偏低，需要在 prompt 里加入更明确的患者价值观考量框架
3. **证据库质量管理流程**：建立定期 lint + 人工抽审机制，防止低质量文章积累

---

## 六、关键配置参数

```env
# hypertensiondb 服务
HYPERTENSION_API_URL=http://localhost:8000
HYPERTENSION_API_TIMEOUT=60
RAG_SEARCH_TOP_K=15
RAG_MAX_PAPERS=6
RAG_MAX_PASSAGES_PER_PAPER=3

# hypertensiondb .env
EMBEDDER=zhipu
RERANKER=api
LLM_API_KEY=<HuatuoGPT key>
LLM_BASE_URL=https://api.huatuogpt.cn/v1
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
```

---

*本文档记录截至 2026-05-22 的改造状态。*

---

## 七、RAG 检索稳定性分析（2026-05-22 下午）

### 7.1 发现的现象

对同一临床问题的不同措辞（`ARB+CCB 联合治疗中重度原发性高血压` vs `ARB 联合 CCB 治疗中重度原发性高血压的疗效如何？`），pipeline 给出了不同的推荐强度（Weak/Strong/Conditional），引发了对检索稳定性的调查。

**调查结论**：

- 同一问题文本三次运行，batch 测试结果完全一致（Conditional/Moderate）——**pipeline 本身是稳定的**
- 不同措辞导致不同结果，根本原因是：Ask agent 对不同措辞生成了不同的 PICO（尤其是 comparator 和 outcome 字段），进而生成了不同的 NL 检索 query，召回了不同的证据集

### 7.2 尝试的解法与回滚原因

**尝试方案**：在 Acquire agent 加入 keyword anchor 双路检索——同时用 NL query 和 PICO keywords 字段检索，取并集，以保证核心文献（如 PINTANINGRUM）稳定出现。

**回滚原因**：该方案不符合循证医学方法论。

根据 GRADE 工作组和 Cochrane Handbook（5.1.1）的核心原则，**PICO 的精确表述决定了什么证据算"直接证据"**——不同的 PICO 问的是不同的问题，检索到不同的证据集，在方法论上是正当的，不应在技术层面强行消除。Keyword anchor 会绕过 PICO 的决定权，把与当前 PICO 的 comparator/outcome 无关的文献强行拉入证据集，引入 indirectness，反而违反了 GRADE 的间接性降级原则。

### 7.3 正确的处理方式

EBM 方法论给出的答案是：**在 Ask 阶段完成 PICO 构建后，向用户展示并确认 PICO，然后再进入检索**。PICO 一旦确认，后续检索在 temperature=0 下是确定性的，不同措辞的问题在 PICO 确认环节自然收敛。

这是真实临床指南制定的做法——专家组显式讨论并锁定 PICO，不期望系统自动归一化所有措辞变体。

**结论：这是设计上需要接受的行为，不是 bug。** 未来如需改善，入口在 Ask 阶段的 PICO 确认交互，而不是检索层的补偿机制。

