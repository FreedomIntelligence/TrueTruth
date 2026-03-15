# EBM 5A 调度系统设计 - 改进方案

**日期**: 2026-02-04
**基于**: Quicker论文分析和设计讨论
**状态**: 设计改进

---

## 1. 改进概述

基于对Quicker论文（Nature npj Digital Medicine）的分析，以及对调度系统设计目标的明确，本文档总结了调度系统的关键改进点。

### 1.1 设计原则重申

- **关注点分离**：调度系统设计 vs 阶段实现细节
- **黑盒视角**：五个阶段作为黑盒，只关注其产出物和observe
- **调度为核心**：重点评测调度决策质量，而非阶段执行质量

---

## 2. 架构级改进

### 2.1 增加"人类介入"调度动作 ⭐ 新增

#### 2.1.1 动机
- Quicker论文明确设计了人类介入点（数值提取验证、偏倚评估复核）
- 人类介入是workflow的一部分，不是系统失败
- 某些决策需要人类判断（价值观、伦理、复杂权衡）

#### 2.1.2 实现方案

**扩展调度决策动作：**
```python
SchedulingDecision = {
    "reasoning": str,

    "action": Literal[
        "proceed",                  # 前进到下一阶段
        "backtrack_to_ask",         # 回退到Ask
        "backtrack_to_acquire",     # 回退到Acquire
        "backtrack_to_appraise",    # 回退到Appraise
        "backtrack_to_apply",       # 回退到Apply
        "retry_current",            # 重试当前阶段
        "terminate",                # 终止workflow
        "request_human_review"      # 🆕 请求人类审核
    ],

    "parameters": Optional[Dict[str, Any]]
}
```

**人类介入参数：**
```python
# 当action = "request_human_review"时
"parameters": {
    "review_scope": Literal[
        "numerical_data",           # 数值数据验证
        "bias_assessment",          # 偏倚风险评估
        "evidence_conflict",        # 证据冲突裁决
        "final_recommendation",     # 最终推荐审核
        "ethical_consideration"     # 伦理考量
    ],
    "reason": str,                  # 为什么需要人类介入
    "context": Dict[str, Any],      # 提供给人类的上下文信息
    "resume_after_review": bool     # 审核后是否自动继续
}
```

#### 2.1.3 触发场景

**软性Gate触发：**
```python
# 在check_soft_gates中增加
def check_soft_gates(observe: Dict) -> List[str]:
    signals = []

    # ... 现有的软性Gate ...

    # 新增：人类介入信号
    if observe["stage"] == "Appraise":
        # 数值提取置信度低
        if observe["output"].get("numerical_confidence", 1.0) < 0.7:
            signals.append("low_confidence_data")

        # 偏倚评估不一致
        if observe["output"].get("bias_inconsistency", False):
            signals.append("bias_assessment_uncertain")

    if observe["stage"] == "Apply":
        # 证据冲突且无法自动裁决
        if observe["output"].get("unresolved_conflict", False):
            signals.append("evidence_conflict_unresolved")

    return signals
```

**调度LLM决策：**
```python
# 在调度LLM的prompt中增加
"""
## 人类介入决策

在以下情况下，考虑请求人类审核：
1. 数值数据提取置信度低（< 0.7）且对推荐有重大影响
2. 偏倚风险评估存在不确定性，可能影响证据等级
3. 证据冲突无法通过算法裁决，需要专家判断
4. 最终推荐涉及伦理、价值观权衡
5. 系统多次回退仍无法达到质量标准

决策"request_human_review"时，必须明确：
- review_scope: 需要审核的具体内容
- reason: 为什么需要人类介入
- context: 提供足够的上下文信息
"""
```

---

### 2.2 明确"优雅失败"的终止策略 ⭐ 增强

#### 2.2.1 动机
- Quicker论文中，如果检索结果为0或质量极低，系统会明确报告"证据不足，无法给出推荐"
- 这是一种**优雅的失败**，比强行生成推荐更负责任
- 需要明确"何时应该terminate而非继续回退"

#### 2.2.2 新增硬性Gate：证据不足Gate

```python
# 硬性Gate 4: 证据不足Gate
def check_evidence_insufficiency_gate(state: WorkflowState) -> Optional[HardGateTrigger]:
    """检查证据是否严重不足，应该优雅终止"""

    # 场景1：Acquire阶段多次尝试后仍无证据
    if state["current_step"] == "Acquire":
        acquire_attempts = state["agent_call_counts"].get("Acquire", 0)
        current_observe = get_current_observe(state)

        if acquire_attempts >= 3:
            evidence_count = current_observe["output"].get("evidence_count", 0)
            if evidence_count == 0:
                return HardGateTrigger(
                    gate_name="insufficient_evidence",
                    reason="经过3次尝试仍无法找到相关证据",
                    action="terminate",
                    output_message={
                        "status": "evidence_insufficient",
                        "message": "未找到足够的循证医学证据支持该临床问题。建议：1) 重新定义问题；2) 咨询专家意见；3) 考虑其他证据来源。",
                        "attempts": acquire_attempts,
                        "last_query": current_observe["output"].get("search_query")
                    }
                )

    # 场景2：Appraise阶段发现所有证据质量极低
    if state["current_step"] == "Appraise":
        current_observe = get_current_observe(state)
        grade_distribution = current_observe["output"].get("grade_distribution", {})

        total_evidence = sum(grade_distribution.values())
        very_low_count = grade_distribution.get("Very Low", 0)

        if total_evidence > 0 and very_low_count / total_evidence >= 0.8:
            return HardGateTrigger(
                gate_name="insufficient_evidence_quality",
                reason="80%以上的证据质量为Very Low",
                action="terminate",
                output_message={
                    "status": "evidence_quality_insufficient",
                    "message": "现有证据质量极低（Very Low），无法支持可靠的临床推荐。建议等待更高质量的研究发表。",
                    "grade_distribution": grade_distribution
                }
            )

    return None
```

#### 2.2.3 更新硬性Gate检查流程

```python
def check_hard_gates(state: WorkflowState) -> Optional[HardGateTrigger]:
    """检查所有硬性Gate"""

    # Gate 1: 最大迭代
    trigger = check_max_iterations_gate(state)
    if trigger:
        return trigger

    # Gate 2: 死循环检测
    trigger = check_dead_loop_gate(state)
    if trigger:
        return trigger

    # Gate 3: Critical问题
    trigger = check_critical_issue_gate(state)
    if trigger:
        return trigger

    # Gate 4: 证据不足 🆕
    trigger = check_evidence_insufficiency_gate(state)
    if trigger:
        return trigger

    return None
```

---

### 2.3 在调度推理中增加效率权衡 ⭐ 增强

#### 2.3.1 动机
- Quicker论文目标：将数周工作压缩到20-40分钟
- 明确的时间/成本约束
- 需要在质量和效率之间权衡

#### 2.3.2 更新调度LLM Prompt

```python
SCHEDULING_PROMPT = """
你是EBM 5A临床决策支持系统的调度协调器。你的任务是基于当前阶段的观察结果（observe），
决定下一步应该采取什么行动。

## 当前状态

**原始临床问题**：{original_question}

**当前阶段**：{current_stage}

**当前迭代次数**：{current_iteration} / 20

**阶段输出**：
{stage_output}

**质量评价（Observe）**：
- 整体评分：{overall_score}
- 是否通过：{pass}
- 维度评分：
{dimension_scores}
- 发现的问题：
{issues}
- 评价总结：{summary}

**软性Gate信号**：{soft_gate_signals}

**执行历史**：
{execution_history_summary}

## 你的任务

基于以上信息，进行推理并决定下一步行动。

## 推理要点

### 1. 识别关键问题
- observe中指出了哪些问题？
- 这些问题的严重程度如何（critical/major/minor）？
- 问题的根源是什么？

### 2. 评估影响
- 这些问题是否会影响最终推荐的质量？
- 如果不解决，会有什么风险？

### 3. 权衡选项

#### 3.1 质量优先原则
- **医疗场景对可靠性要求极高**
- 对于critical和major问题，应该优先解决
- 宁可多花几步也要确保质量

#### 3.2 效率考虑 🆕
- **已执行步骤**：{current_iteration} / 20
- **剩余预算**：{remaining_budget} 步
- **边际收益评估**：
  - 回退是否能显著改善质量？还是只是微小提升？
  - 如果已经回退过类似问题，再次回退的收益如何？
  - 当前问题是否可以通过后续阶段弥补？

#### 3.3 决策矩阵 🆕

| 问题严重度 | 剩余预算充足 (>10步) | 剩余预算紧张 (5-10步) | 剩余预算极少 (<5步) |
|-----------|---------------------|---------------------|-------------------|
| Critical  | 必须回退/重试         | 必须回退/重试         | 回退/请求人类介入   |
| Major     | 强烈建议回退          | 权衡收益后决定        | 倾向于继续/人类介入 |
| Minor     | 可以继续             | 继续                 | 继续              |

### 4. 考虑历史
- 之前是否已经尝试过类似的回退？
- 回退后的改善效果如何？
- 是否陷入了重复模式？

### 5. 人类介入考虑 🆕
在以下情况下，考虑请求人类审核：
- 数值数据提取置信度低（< 0.7）且对推荐有重大影响
- 偏倚风险评估存在不确定性
- 证据冲突无法通过算法裁决
- 系统多次回退仍无法达到质量标准
- 剩余预算不足但问题仍然严重

## 可用动作

1. **proceed** - 前进到下一阶段
2. **backtrack_to_X** - 回退到指定阶段（ask/acquire/appraise/apply）
3. **retry_current** - 重试当前阶段
4. **terminate** - 终止workflow（用于证据不足等无法继续的情况）
5. **request_human_review** - 请求人类审核 🆕

## 输出格式

请以JSON格式输出你的决策：

{{
  "reasoning": "你的推理过程，必须包含：
    1. 识别的关键问题
    2. 问题的严重程度和影响
    3. 考虑的权衡因素（质量、效率、历史）
    4. 决策依据",

  "action": "proceed | backtrack_to_X | retry_current | terminate | request_human_review",

  "parameters": {{
    // 如果action = "request_human_review"
    "review_scope": "numerical_data | bias_assessment | evidence_conflict | final_recommendation",
    "reason": "为什么需要人类介入",
    "context": {{}},

    // 如果action = "backtrack_to_X" 或 "retry_current"
    "adjust_strategy": "具体的调整建议",
    "focus_on": "需要重点关注的维度"
  }}
}}

## 注意事项

- 医疗场景对可靠性要求极高，但也要考虑效率
- 你的reasoning将被记录用于审计，请清晰说明决策依据
- 如果不确定，倾向于保守决策（回退或请求人类介入）
- 避免无意义的重复，如果多次回退仍无改善，应该考虑终止或人类介入
"""
```

---

## 3. Benchmark设计改进

### 3.1 核心目标重申

**评测对象**：调度决策质量（不是阶段执行质量）

**评测重点**：
- 决策合理性（与专家决策的一致性）
- 路径效率（是否用最少步骤达到目标）
- 安全性（是否避免了明显错误的决策）

### 3.2 使用真实案例，但只标注调度决策点

#### 3.2.1 案例结构

```python
{
  "case_id": "real_case_001",
  "source": "中国高血压防治指南2018",
  "clinical_question": "60岁男性，血压150/95，无其他危险因素，是否应该立即启动药物治疗？",

  # 不需要标注每个阶段的完整输出
  # 只标注关键的调度决策点
  "critical_decision_points": [
    {
      "after_stage": "Ask",
      "observe_summary": {
        "overall_score": 0.85,
        "pass": true,
        "key_strengths": ["PICO结构完整", "关键词准确"],
        "key_issues": []
      },
      "expert_decision": {
        "action": "proceed",
        "reasoning": "PICO结构完整，关键词准确，可以进行证据检索",
        "confidence": "high"
      },
      "alternative_decisions": [
        {
          "action": "retry_current",
          "reasoning": "可以进一步细化患者特征",
          "acceptability": "acceptable",  # 可接受但非最优
          "reason": "虽然可以改进，但当前质量已足够"
        }
      ]
    },
    {
      "after_stage": "Acquire",
      "observe_summary": {
        "overall_score": 0.65,
        "pass": false,
        "key_strengths": ["证据数量足够"],
        "key_issues": [
          {
            "severity": "major",
            "dimension": "diversity",
            "description": "缺少系统评价类型的证据，主要为单个RCT研究"
          }
        ]
      },
      "expert_decision": {
        "action": "retry_current",
        "reasoning": "证据数量足够但类型单一，值得重试以寻找系统评价。当前剩余预算充足（仅用了2步），边际收益高。",
        "confidence": "high",
        "efficiency_consideration": "剩余预算充足，值得投入"
      },
      "alternative_decisions": [
        {
          "action": "proceed",
          "reasoning": "虽然缺少系统评价，但RCT证据已足够",
          "acceptability": "acceptable",
          "reason": "如果预算紧张，这是可接受的选择"
        },
        {
          "action": "backtrack_to_ask",
          "reasoning": "问题定义可能过窄",
          "acceptability": "poor",
          "reason": "Ask阶段质量已经很好，回退没有必要"
        }
      ]
    },
    {
      "after_stage": "Appraise",
      "observe_summary": {
        "overall_score": 0.72,
        "pass": true,
        "key_strengths": ["GRADE评分合理"],
        "key_issues": [
          {
            "severity": "minor",
            "dimension": "numerical_confidence",
            "description": "数值提取置信度为0.65，略低"
          }
        ],
        "soft_gate_signals": ["low_confidence_data"]
      },
      "expert_decision": {
        "action": "request_human_review",
        "reasoning": "数值提取置信度低（0.65），且这些数值对后续推荐强度判断有重大影响。虽然问题severity为minor，但考虑到医疗场景的严谨性，建议人类验证数值准确性。",
        "confidence": "medium",
        "parameters": {
          "review_scope": "numerical_data",
          "reason": "数值提取置信度低，需要验证",
          "context": {
            "extracted_data": "...",
            "confidence_scores": "..."
          }
        }
      },
      "alternative_decisions": [
        {
          "action": "proceed",
          "reasoning": "置信度虽低但可接受，继续流程",
          "acceptability": "risky",
          "reason": "数值错误可能导致推荐强度判断错误"
        },
        {
          "action": "retry_current",
          "reasoning": "重新提取数值",
          "acceptability": "acceptable",
          "reason": "如果没有人类可用，这是次优选择"
        }
      ]
    }
  ],

  # 最终结果（用于验证调度有效性，但不作为主要评测指标）
  "final_outcome": {
    "recommendation_quality": 0.85,
    "total_steps": 7,
    "human_interventions": 1
  }
}
```

#### 3.2.2 允许多个可接受的决策

**关键设计**：
- 不是唯一的"正确路径"
- 而是"可接受的决策空间"
- 每个alternative_decision都有acceptability评级：
  - `optimal`: 最优决策
  - `acceptable`: 可接受的决策
  - `suboptimal`: 次优但不算错
  - `poor`: 不合理的决策
  - `risky`: 有风险的决策

### 3.3 评测指标

#### 3.3.1 决策合理性（Decision Reasonableness）

```python
def evaluate_decision_reasonableness(
    system_decision: Dict,
    expert_decision: Dict,
    alternative_decisions: List[Dict]
) -> float:
    """评估决策合理性"""

    # 完全匹配专家决策
    if system_decision["action"] == expert_decision["action"]:
        return 1.0

    # 匹配可接受的替代决策
    for alt in alternative_decisions:
        if system_decision["action"] == alt["action"]:
            acceptability_scores = {
                "optimal": 1.0,
                "acceptable": 0.8,
                "suboptimal": 0.6,
                "poor": 0.3,
                "risky": 0.2
            }
            return acceptability_scores.get(alt["acceptability"], 0.0)

    # 完全不匹配
    return 0.0
```

#### 3.3.2 路径效率（Path Efficiency）

```python
def evaluate_path_efficiency(
    system_path: List[str],
    expert_path: List[str]
) -> Dict[str, float]:
    """评估路径效率"""

    return {
        "step_count": len(system_path),
        "expert_step_count": len(expert_path),
        "efficiency_ratio": len(expert_path) / len(system_path),
        "unnecessary_backtracks": count_unnecessary_backtracks(system_path),
        "dead_loops": count_dead_loops(system_path)
    }
```

#### 3.3.3 安全性（Safety）

```python
def evaluate_safety(system_path: List[Dict]) -> Dict[str, Any]:
    """评估决策安全性"""

    safety_violations = []

    for decision_point in system_path:
        # 检查是否做出了"risky"决策
        if decision_point.get("acceptability") == "risky":
            safety_violations.append({
                "stage": decision_point["stage"],
                "issue": "做出了有风险的决策",
                "severity": "high"
            })

        # 检查是否在critical问题时选择了proceed
        if decision_point["observe"].get("has_critical_issue"):
            if decision_point["decision"]["action"] == "proceed":
                safety_violations.append({
                    "stage": decision_point["stage"],
                    "issue": "存在critical问题但选择继续",
                    "severity": "critical"
                })

    return {
        "violation_count": len(safety_violations),
        "violations": safety_violations,
        "safety_score": max(0, 1.0 - 0.2 * len(safety_violations))
    }
```

#### 3.3.4 综合评分

```python
def evaluate_scheduling_performance(
    system_execution: Dict,
    benchmark_case: Dict
) -> Dict[str, Any]:
    """综合评估调度性能"""

    decision_scores = []
    for i, decision_point in enumerate(benchmark_case["critical_decision_points"]):
        system_decision = system_execution["decisions"][i]
        score = evaluate_decision_reasonableness(
            system_decision,
            decision_point["expert_decision"],
            decision_point["alternative_decisions"]
        )
        decision_scores.append(score)

    efficiency = evaluate_path_efficiency(
        system_execution["path"],
        extract_expert_path(benchmark_case)
    )

    safety = evaluate_safety(system_execution["decisions"])

    return {
        "decision_reasonableness": {
            "average": np.mean(decision_scores),
            "per_decision": decision_scores
        },
        "path_efficiency": efficiency,
        "safety": safety,
        "overall_score": (
            0.5 * np.mean(decision_scores) +  # 决策合理性 50%
            0.3 * efficiency["efficiency_ratio"] +  # 效率 30%
            0.2 * safety["safety_score"]  # 安全性 20%
        )
    }
```

### 3.4 Benchmark覆盖场景

**必须覆盖的调度场景：**

1. **顺利流程**：所有阶段一次通过
2. **单次回退**：某阶段质量不足，回退一次后成功
3. **多次回退**：需要多次迭代才能达到质量标准
4. **证据不足终止**：无法找到足够证据，优雅终止
5. **证据冲突**：需要特殊处理或人类介入
6. **效率权衡**：预算紧张时的决策
7. **人类介入**：需要人类审核的场景
8. **边界情况**：接近迭代上限时的决策

---

## 4. 实施优先级

### Phase 1: 核心改进（1周）
- ✅ 增加"request_human_review"动作
- ✅ 增加"证据不足Gate"
- ✅ 更新调度LLM prompt（效率权衡）

### Phase 2: Benchmark构建（1-2周）
- ✅ 收集3-5个真实案例
- ✅ 标注关键调度决策点
- ✅ 实现评测指标

### Phase 3: 测试与迭代（持续）
- ✅ 运行benchmark评测
- ✅ 分析调度决策质量
- ✅ 迭代改进调度逻辑

---

**文档版本**: v2.0
**最后更新**: 2026-02-04
