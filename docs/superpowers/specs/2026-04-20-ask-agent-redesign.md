# Ask Agent 重设计规范

**日期**: 2026-04-20
**范围**: Ask 阶段（`ask_agent.py` + `ask_agent.txt` + `schema.py` + `coordinator.py` 小改）
**不在本次范围内**: Acquire/Appraise/Apply/Assess 阶段的格式适配；PICo（质性研究）格式支持；多子问题并行执行架构

---

## 背景与目标

当前 Ask 阶段直接将用户问题结构化为 PICO，存在以下问题：

1. **无路由**：所有问题一律走 PICO，导致诊断准确性、预后、病因等类型的问题被错误结构化
2. **`question_type` 无 Judge 覆盖**：分类错误无法被捕获，会传导到 Acquire 的搜索过滤器选择
3. **单一格式**：PICO 不适用于诊断准确性（应用 PIRD）、病因（PEO）、预后等问题类型
4. **无问题性质判断**：急救操作类问题不适合走完整 5A 流程

目标：在 Ask 阶段引入路由机制，先判断问题性质再选择对应处理路径，并让 Judge 覆盖路由正确性验证。

---

## 整体流程

```
用户输入
    │
    ▼
[路由 LLM 调用]  ← router.txt
    │
    ├─ direct_answer ──────────────────────→ [直接输出 + 免责声明] → coordinator 终止流程
    │   （满足全部3条触发条件的急救/操作规范）
    │
    ├─ diagnostic_reasoning ───────────────→ [Step1: 鉴别诊断 LLM] → [Step2: 串行×≤3个子PICO LLM]
    │                                          子PICO写入 sub_pico_queries，等待后续迭代实现并行5A流程
    │
    └─ ebm_pico / ebm_pird / ebm_peo / ebm_prognosis
                │
                ▼
        [EBM结构化 LLM 调用]  ← ebm_*.txt
                │
                ▼
        [EBMQuery 输出] → 写入 WorkflowState → 后续 Acquire 等阶段

路由验证与结构化质量验证由 Ask Judge 在独立的 judge_llm.py 中实现（不在本次范围内）。
```

---

## 路由分类

### 路由输出结构

```json
{
  "route_type": "direct_answer | diagnostic_reasoning | ebm_pico | ebm_pird | ebm_peo | ebm_prognosis",
  "reasoning": "一句话路由依据"
}
```

### 各路由触发规则

| 路由类型 | 触发条件 |
|---|---|
| `direct_answer` | 同时满足3条（见下） |
| `diagnostic_reasoning` | 问题核心是"这是什么病/鉴别诊断是什么"，需要从临床特征推断诊断 |
| `ebm_pico` | 治疗/干预效果比较（RCT 适用） |
| `ebm_pird` | 诊断测试的准确性/灵敏度/特异性 |
| `ebm_peo` | 病因、危险因素、有害暴露 |
| `ebm_prognosis` | 疾病自然病程、预后因素、生存率 |

### `direct_answer` 触发的3条条件（须全部满足）

1. 问题要求立即操作性指导（动词如：如何处理、立即给、紧急处置）
2. 延迟回答会直接危及患者生命安全
3. 答案来自已有公认标准流程（BLS/ACLS/指南操作章节）

**边界示例：**
- "心肺复苏按压深度" → 满足全部3条 → `direct_answer` ✓
- "脓毒症抗生素初始选择" → 不满足条件3（无单一公认操作标准）→ `ebm_pico`
- "急性心梗用阿司匹林" → 不满足条件3 → `ebm_pico`

---

## 各路由处理细节

### A. `direct_answer`

单次 LLM 调用，输出急救/操作规范步骤，强制附加：
- 免责声明："本答案来自公认操作规范，未经循证检索，仅供参考"
- 知识截止日期标注

输出写入 `WorkflowState.direct_answer_output`，coordinator 检测到后直接终止，跳过 Acquire 等阶段。

### B. `diagnostic_reasoning`

**Step1 LLM 调用**（diag_step1.txt）：

输入：原始问题
输出：
```json
{
  "clinical_features": ["症状/体征/检查结果"],
  "differential_diagnoses": [
    { "diagnosis": "xxx", "priority": 1, "rationale": "危重，需优先排除" },
    { "diagnosis": "yyy", "priority": 2, "rationale": "最可能" },
    { "diagnosis": "zzz", "priority": 3, "rationale": "常见鉴别" }
  ]
}
```

Prompt 硬约束：输出上限3个诊断，优先排序规则：需立即排除的危重疾病 > 最可能的诊断 > 常见鉴别。

**Step2 LLM 调用（串行，每次1个诊断）**（diag_step2.txt）：

输入模板（每次仅传入1个诊断）：
```
患者临床特征：{clinical_features}
当前鉴别诊断：{single_diagnosis}
任务：将该诊断转化为 EBM 可检索的子问题
```

输出：针对该诊断的 `EBMQuery`（通常为 `ebm_pico` 类型）

所有子问题写入 `WorkflowState.sub_pico_queries`。**本次迭代不实现并行5A执行**，子问题的后续处理留待下一迭代。

### C. EBM 格式结构化（4种）

每种格式对应独立 prompt 文件，输出统一为 `EBMQuery`。

---

## 数据类设计

### 新增 `EBMQuery`

```python
@dataclass
class EBMQuery:
    query_type: str          # "pico" | "pird" | "peo" | "prognosis"
    patient: str             # P（所有格式共用）
    primary_focus: str       # PICO→intervention；PIRD→index_test；PEO→exposure；Prognosis→prognostic_factor
    comparator: Optional[str]  # PICO→comparison；PIRD→reference_standard；PEO/Prognosis→None（不适用）
    outcome: str             # O/D（所有格式共用）
    keywords: List[str]      # 英文 MeSH 关键词
    reference_standard: Optional[str] = None   # PIRD 专用（R字段）
    time_horizon: Optional[str] = None         # Prognosis 专用
```

PIRD 字段映射（明确修正）：
- P = `patient`
- I = `primary_focus`（index test，待评估的诊断测试）
- R = `comparator` + `reference_standard`（参考标准/金标准，冗余存储以保持语义）
- D = `outcome`（诊断准确性结局）

`PICOQuery` 保持不变（向后兼容）。过渡期内 `WorkflowState` 同时保留 `pico_query` 和新的 `ebm_query`；非 PICO 路由使用 `ebm_query`，Acquire 等下游阶段读取 `query_type` 后当前迭代降级为 PICO 行为，后续迭代逐格式适配。

### `WorkflowState` 新增字段

```python
route_type: Optional[str]                    # 路由结果
route_confidence: Optional[str]             # "normal"（默认，路由首次通过）| "low"（重试超限后 fallback 标记）
                                             # 路由 LLM 调用成功后无论是否重试，均写入该字段；初始值 None 仅在 Ask 阶段未执行时存在
direct_answer_output: Optional[str]          # direct_answer 类的最终输出
ebm_query: Optional[EBMQuery]               # 非PICO格式的结构化输出
sub_pico_queries: Optional[List[EBMQuery]]   # 诊断推理的子问题列表
sub_question_index: Optional[int]            # 当前处理第几个子问题（0-based）
sub_question_total: Optional[int]            # 子问题总数
```

---

## Prompt 文件结构

```
src/config/prompts/ask/
├── router.txt           # 路由分类（含3条 direct_answer 触发条件）
├── direct_answer.txt    # 急救/操作规范直接回答
├── diag_step1.txt       # 鉴别诊断生成（MAX=3 硬约束 + 优先排序规则）
├── diag_step2.txt       # 单诊断→EBMQuery 转化（每次1个诊断）
├── ebm_pico.txt         # PICO 格式（从 ask_agent.txt 迁移改写）
├── ebm_pird.txt         # PIRD 格式（P/I/R/D 字段明确定义）
├── ebm_peo.txt          # PEO 格式
└── ebm_prognosis.txt    # 预后格式（含 time_horizon）
```

旧 `src/config/prompts/ask_agent.txt` 废弃，功能由 `ask/ebm_pico.txt` 替代。

---

## 文件改动清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `src/config/prompts/ask/` | 新建目录，8个文件 | 见上方 Prompt 文件结构 |
| `src/agents/ask_agent.py` | 重写 | 路由→Judge→分支调用→统一输出 |
| `src/state/schema.py` | 扩展 | 新增 `EBMQuery`，`WorkflowState` 新增6个字段 |
| `src/coordinator/coordinator.py` | 小改 | 检测 `route_type == "direct_answer"` 后提前终止 |
| `src/config/prompts/ask_agent.txt` | 废弃（保留文件，不删除） | 由 `ask/ebm_pico.txt` 替代 |

---

## 明确不在本次范围内

- Acquire/Appraise/Apply/Assess 对非PICO格式的完整适配（当前降级为PICO行为）
- `diagnostic_reasoning` 子问题的并行5A执行（子问题已结构化，执行逻辑留待下一迭代）
- PICo（质性研究）格式支持（需 CERQual 评价框架，单独迭代）
- `ebm_query` 完全替换 `pico_query`（本次过渡期并存）
