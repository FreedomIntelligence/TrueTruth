# 内容轴修复 + grounded 药品安全源 — 实施计划

> 状态：进行中。不 commit（设计/实施阶段用户手动提交）。

## 背景与诊断结论

18-run（6题×3次）网格证明 EBM 5A 评分**系统性波动**（每题分差 14–20，A4/B10/NONE2/FAIL2，均分 55.9），非单题特例。根因分两类：

1. **渲染器引入的回归（我方）**：① `_type_label` 用 evidence_id 类型段，与实际研究类型矛盾（POPAT id=RCT 实为 Meta/SR）→ Judge 判"错误/编造引用"→ A 类；② LLM 格式漂移时 EV 编号泄漏（中文相邻正则失效）→ Judge 判"编造编号"→ A 类。
2. **固有内容问题（改造前就有）**：OVERREACH(11/16) 过度外推/过强；SAFETY_CAVEAT(9/16) 安全提示不全/作用域错。证据：B01 三次检索证据**完全相同**却 40/55/60 → 变异在**生成端**，是 prompt/控制不足而非证据库不足；但 NONE 可达说明证据足够产出正确答案。

Judge 对**固定输入是确定的**（同文本5/5一致），故波动非 Judge 噪声。

## 关键设计决策（已与用户确认）

- 安全维度**结构**用 **SmPC 标准字段**（禁忌/警告/相互作用/妊娠哺乳·特殊人群/不良反应）——权威、药物无关，回答"其他药怎么办"。
- 安全**内容来源**：**grounded 进检索**（option A），不靠 LLM 自由回忆。文献证实 LLM 裸知识对禁忌不可靠（准确率 0.49–0.57→RAG 0.87–0.94），OpenEvidence 一律 grounded+可溯源。
- 数据源：**openFDA**（已实测主机连通，amlodipine SmPC 字段齐全：contraindications/warnings_and_cautions/drug_interactions/pregnancy/use_in_specific_populations/adverse_reactions）。

## 阶段计划

### P0 — 渲染器/健壮性修复（确定性，A/B 前提，两臂共享）
- `src/render/recommendation.py`：
  - **去掉参考文献的 `(类型)` 后缀** → 彻底消除"类型标注与标题矛盾"的 A 类（OpenEvidence 引用本就不标类型；类型从标题/正文自明）。
  - **修 EV 正则**：锚定到结尾 `-\d{3}`、非贪婪，使中文紧邻时也能正确截取 id。
  - **最终残留 EV 兜底清除**：渲染输出里任何残留 `EV-...` 一律 strip，保证无论 LLM 格式怎么飘，EV 编号永不泄漏给 Judge/用户。
- 查 Apply JSON 解析失败根因（2/18，"line 19 column 3"），判断是否新 prose prompt 引起，必要时加 JSON 修复/转义提示。

### P1 — grounded 药品安全源（openFDA）= T1
- ✅ **schema**（worktree）：`EvidenceType.DRUG_SAFETY = "DRUGSAFETY"`（值无下划线，保渲染器 `EV-[A-Z]+` 兼容）+ id 正则扩；新建 `schema/label.py::LabelFrontmatter`(drug_name/drug_class/brand_names/spl_set_id…)；注册 loader `_TYPE_MODEL`+`AnyFrontmatter`+`__init__`；id_gen `_VALID_TYPES`；`sections.py` 加 6 个 SmPC 维度（黑框警告 before 警告）。round-trip 验证 PASS（6 段各成 chunk、type=DRUGSAFETY、id 过正则、渲染器识别并转 [n]）。
- ✅ **fetcher**：`hypertension/scripts/fetch_drug_safety.py`，53 种降压药（13 类）拉 openFDA label → SmPC 维度 md，写入 worktree `hypertension/evidence/`。**关键修正**：openFDA `generic_name` 搜索会命中复方制剂（如 amlodipine+benazepril），其 benazepril 的 FETAL-TOXICITY 黑框警告会被错挂到 amlodipine（纯 CCB）→ 用 `openfda.substance_name` 强制单成分过滤（`bases=={generic}`），ARNI 等真复方走 `allow_combo`+components 校验。结果 written=52 / failed=1（eprosartan 美国无 label）。审计：18 个 RAS 类（ACEI/ARB/ARNI/肾素抑制剂）有 fetal 黑框（正确），其余黑框均为各药自身真实黑框（β-阻滞剂停药、保钾利尿剂高钾、袢利尿剂、螺内酯、米诺地尔心包积液），**0 复方污染**。
- ✅ **索引**（增量，不 rebuild）：live Qdrant 是 named volume（不踩 [[project_qdrant_zero_vector_bug]]），EMBEDDER=zhipu/2048 与现有 collection 一致。写精准驱动 `_index_drugsafety.py` 只嵌入 52 个新文件（`hdb index update` 会因 worktree checkout mtime 误判全量重嵌，故不用）。`ensure_collection` 对已存在 collection 是 no-op、upsert 按新 point_id 纯插入 → 现有 11762 点不动。结果：605 chunk，collection 11762→12367，type=DRUGSAFETY=605。跨语种检索冒烟通过（中文 query→对药英文 label chunk：氨氯地平→AMLODIPINE 妊娠段、螺内酯→EPLERENONE/SPIRONOLACTONE、ACEI 妊娠→perindopril/ramipril/quinapril）。
- ✅ **安全子检索**：`hypertension_rag_client.search_safety()`（新增 `SafetyRAGConfig`，min_score=0.0 放宽、type=DRUGSAFETY 过滤、`_request_with_retries` 加 extra_params）；Acquire.execute 主检索后追加一次安全子检索（query 附"安全性 禁忌 警告 不良反应 相互作用 妊娠"线索），结果存 `state["safety_evidence"]`、标 `evidence_role="safety_only"`，**不进 evidence_list（不被 GRADE）**。`/search` API 本就支持 `type` 过滤，无需改 API。live 验证：ARB/ACEI 问题→RAS 类药安全段；螺内酯问题→螺内酯+保钾相关。无 LLM 调用（仅多一次 HTTP）。
- ✅ **Apply prompt**：`apply_agent.py` 构建 `safety_evidence_summary`（带 `[evidence_id/section]` 标签，缺省时给出"标缺口、勿凭记忆"占位）并传入；`apply_agent.txt` 加 Grounded Drug-Safety Labels 输入块 + **Step 3.5 强制 grounded 安全段**（SmPC 维度、逐条 `[evidence_id/section]` 引用、禁止编造未在 label 中的禁忌/警告、缺药显式标缺口、安全性不改推荐强度）。编译通过、prompt .format 占位校验通过。**改 LLM 调用结构 → 待 P3 A/B 验证 + e2e 冒烟**。

### P2 — 反外推 T2（prompt）
- ✅ Apply：每条人群相关推荐前**显式声明证据人群 vs 问题人群匹配**；不匹配强制 hedge。针对 overstatement gate（仅词法）抓不住的隐性外推。
- 实现（prompt-only，无新代码门）：`apply_agent.txt` 新增 **Step 1.6 - Population-Match Declaration (Anti-Overreach, MANDATORY)**，置于 Step 1.5（方向语言门）与 Step 1.7（结局覆盖）之间。三步：①从 Structured Query Patient + 问题点名亚组（儿童/孕妇/老年/肾肝功能不全/合并症/单药未控者）识别目标人群；②用 `Evidence Role`+`Indirectness` 注释判定该人群是否被采纳证据代表（`core_direct`=代表；`core_direct_limited` 及人群来源 indirectness=不代表）；③prose 必含一句显式人群作用域声明。**HARD RULE — Forced Hedge**：目标人群/点名亚组未被代表时，禁止"对[亚组]推荐X/[孕妇/儿童]应用X/可安全使用X"等直接适用措辞（**即使不含优越性词**），强制 hedge + 个体化/转诊指引，并写进 caveats；**不改 GRADE 强度**（与 Step 3 一致），仅禁直接适用措辞。
- 与既有边界关系：词法 overstatement gate（`assess_agent.py`，正则 `首选|优于…`+无 core_direct→硬回溯）只抓**词**；Step 1.6 抓**隐性外推**（无触发词却把结论说成直接适用于未研究亚组），独立且更严。同时强化 Recommendation Writing Style（加一条人群声明 bullet）与 Reasoning item 1（要求显式判定是否需 hedge），使声明真正落进 prose（Judge R3 population_applicability 看输出）。
- 校验：prompt `.format()` 占位完整（18290 chars），Step 1.6/Forced Hedge/写作 bullet/reasoning 项全部就位。**改 LLM 调用内容（非结构）→ 行为效果待 P3 A/B + e2e 冒烟**。

### P3 — A/B 验证
- 对照 A=仅 P0；实验 B=P0+P1+P2。同 N 题×M 次×2 臂。两臂经 `EBM_AB_ARM` 切换（control 跳 DRUG_SAFETY 子检索 + 用 P0 baseline apply prompt；treatment=当前 P0+P1+P2）。harness：`scripts/run_ab_safety.py`，评委 `JUDGE_MODEL=gpt-5.5`（网关）。
- 指标：mean_score（封顶后）、**mean_raw_score（安全 A/B 封顶前的维度原始和——封顶会压平 total，维度级效应只在此可见）**、同题波动、safety 触发(A+B)分布、JSON 失败率、clarity/relevance（防 T1 啰嗦反噬）。
- **预设采纳/回退规则（跑前定死，不得看完数据再挪门槛）——加进来的复杂度必须挣到位置，平局算回退（简单优先）：**
  - **保留 P1+P2** 仅当**全部**成立：① mean_score(B) ≥ mean_score(A)；② mean_raw_score(B) ≥ mean_raw_score(A) − 1.0（封顶前不更差）；③ safety 触发(A+B)数 B ≤ A（P1/P2 本意就是降安全触发，不得增加）；④ JSON-fail/crash B 不高于 A；⑤ clarity 与 relevance 维度均分 B ≥ A − 0.5（防啰嗦反噬）。
  - **回退到 P0-only**：若上述任一不满足，或结果整体持平/混合 → 回退。`git restore` P1/P2 改动（apply_agent.txt/py、acquire_agent.py、schema/client/state 的 P1 部分），保留 P0（渲染器/JSON）+ 已修的 DRUGSAFETY 渲染。
  - 两种结果都**终结循环**：不再按单点瑕疵追加 prompt 规则。
- **不按 n=1 改 prompt**：B01 单点（control raw 64 / treatment raw 61，均被 B 封顶到 60）暴露了"P1 诱发未 grounded 的数值（干咳20%/卒中3.5%）""P2 未拦住方向语言"，但有 B 封顶压平 + 两臂检索证据不同两重混淆，只够作事实信号、不够支撑改法 → 进网格用分布判定。
- 基线参照：18-run（55.9 / A4 B10 NONE2 / FAIL2）。

#### P3 裁决（2026-06-03，6题×3次×2臂=36run，评委 gpt-5.5，完整无失败）
**结论：回退 P1+P2（5 条规则 4 条不过，完败）。**

| 指标 | control(P0) | treatment(P0+P1+P2) | 规则 |
|---|---|---|---|
| mean_score(capped) | 61.9 | 51.9 | ❌ −10.0 |
| mean_raw_score | 64.3 | 52.8 | ❌ −11.6 |
| safety 触发(A+B)/18 | 13 | 15 | ❌ +2 |
| JSON-fail | 0 | 0 | ✅ |
| clarity / relevance | 7.6 / 8.5 | 6.6 / 8.2 | ❌ clarity |
| safety_category | A=1 B=12 NONE=5 | **A=9** B=6 NONE=3 | — |
| within-Q 波动 | 6.53 | 7.95（更差） | — |

**根因（n=18 坐实 B01 单点的怀疑）**：P1 的 grounded 安全段诱导模型写"未 grounded 的具体安全声明（发生率/禁忌/相互作用）"→ Judge 判 **A 类（编造/危险误用，封顶40）**，A 类从 1→9。`safety_risk_control` 维度反而从 12.5 掉到 9.3。逐题 treatment 输 5/6（仅 B09 噪声内险胜）。
**副发现**：P2 反外推 violation 7→5（小幅起效）但被 P1 淹没；overreach **不是**基线瓶颈，基线天花板在**安全完整性(B类12/18)+个体化**。
**方法学定论**："grounded 安全经 prompt 让 LLM 自撰"是死路（适得其反）；若要 grounded 安全只能走**结构化(D4：确定性渲染标签原文、LLM 不撰写安全事实)**。
**回退执行**：`git checkout HEAD` 还原 apply_agent.txt/py、acquire_agent.py（本会话起为干净=HEAD，P0 未碰）；删 apply_agent.baseline.txt。**保留**：P0（渲染器/JSON）、DRUGSAFETY 渲染修复（safety_evidence 恒空→无害死码）、schema DRUGSAFETY 类型、Qdrant 语料、rag_client.search_safety、harness（均可复用于将来 D4/比较）。实验数据存 `ab_grid_6x3.json`。
- 渲染缺陷修复（属 P1 正确性，render-only，非 prompt）：DRUGSAFETY 引用原渲染为伪造作者 "Captopril 等."（Judge 易判编造引用→压分）；现两处 render 调用并入 `safety_evidence`，`_format_authors`/`_format_reference` 对 DRUGSAFETY id 抑制 id-author 回退 → 渲染为正规药品标签 title（B01 treatment 已确认：`[4] Captopril 药品安全信息（FDA 说明书）. 2022.`）。

## 约束（来自用户记忆）
- 不加单元/集成测试，只跑全流程 e2e 读 timing+质量。
- 设计/计划阶段不 commit；用户手动提交。
- 碰 LLM 调用结构的改动（P1 prompt/P2）需 A/B（即 P3）。
- .env 只用 Edit 不用 Write。
