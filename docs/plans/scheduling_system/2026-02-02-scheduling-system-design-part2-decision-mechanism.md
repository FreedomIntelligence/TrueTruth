# EBM 5A 调度系统设计文档 - Part 2: 调度决策机制

**日期**: 2026-02-02
**项目**: 基于ReAct模式的调度系统设计
**状态**: 设计阶段

---

## 3. 调度决策机制

### 3.1 设计思路

采用**分层混合决策机制**，结合规则引擎和LLM推理的优势：
- **第一层：硬性Gate** - 处理不容商量的情况，强制执行预定义动作
- **第二层：软性Gate** - 识别需要特别关注的情况，触发LLM决策
- **第三层：正常流程** - LLM基于observe做完整推理决策

### 3.2 为什么选择分层混合方式？

#### 3.2.1 纯Gate方式的问题
- ❌ 规则僵化，难以处理复杂边界情况
- ❌ 需要预先定义所有可能的触发条件和动作
- ❌ 缺乏灵活性，无法体现ReAct的推理过程

#### 3.2.2 纯LLM方式的问题
- ❌ 通用LLM在医学推理上可能不稳定
- ❌ 成本高，每次都需要LLM推理
- ❌ 可能出现明显错误（如死循环），缺乏安全保障

#### 3.2.3 分层混合方式的优势
- ✅ **可靠性保底**：硬性Gate保证底线，不会出现明显错误
- ✅ **灵活决策**：LLM处理复杂权衡，体现推理过程
- ✅ **成本可控**：只有通过Gate的才需要LLM推理
- ✅ **可解释性强**：Gate触发有明确规则，LLM决策有reasoning
- ✅ **适合当前阶段**：通用LLM不够可靠时，规则提供安全网
- ✅ **未来升级路径**：专门训练的调度LLM后，可逐步将软性Gate判断交给LLM

### 3.3 第一层：硬性Gate（强制动作）

**目的**：处理不容商量的情况，直接执行预定义动作，无需LLM推理。

#### 3.3.1 硬性Gate列表

**1. 最大迭代Gate**
```python
触发条件：
  - 总步骤数 > 20，或
  - 同一agent调用次数 > 5

动作：强制终止
理由：防止无限循环，保护系统资源
```

**2. 死循环检测Gate**
```python
触发条件：
  - 检测到相同路径重复 > 3次
  - 例如：Ask→Acquire→Appraise→Acquire→Appraise→Acquire

动作：强制终止
理由：系统陷入循环，无法自行跳出
输出：向用户报告循环原因和已收集的信息
```

**3. Critical问题Gate**
```python
触发条件：
  - observe中存在severity="critical"的issue，且
  - pass = false

动作：强制回退到相关阶段
映射规则：
  - 如果critical issue在Ask阶段 → 终止（问题本身有问题）
  - 如果critical issue在Acquire阶段 → 回退到Ask
  - 如果critical issue在Appraise阶段 → 回退到Acquire
  - 如果critical issue在Apply阶段 → 回退到Appraise
  - 如果critical issue在Assess阶段 → 回退到Apply
```

#### 3.3.2 硬性Gate实现

```python
def check_hard_gates(state: WorkflowState) -> Optional[HardGateTrigger]:
    """检查硬性Gate，返回触发信息"""

    # Gate 1: 最大迭代
    if state["iteration_count"] > 20:
        return HardGateTrigger(
            gate_name="max_iterations",
            reason=f"总步骤数超过20次（当前{state['iteration_count']}）",
            action="terminate"
        )

    for agent, count in state["agent_call_counts"].items():
        if count > 5:
            return HardGateTrigger(
                gate_name="max_iterations",
                reason=f"Agent {agent} 调用次数超过5次（当前{count}）",
                action="terminate"
            )

    # Gate 2: 死循环检测
    loop_detected = detect_loop(state["execution_history"])
    if loop_detected:
        return HardGateTrigger(
            gate_name="dead_loop",
            reason=f"检测到循环路径：{loop_detected['pattern']}",
            action="terminate"
        )

    # Gate 3: Critical问题
    current_observe = get_current_observe(state)
    if current_observe:
        critical_issues = [
            issue for issue in current_observe["evaluation"]["issues"]
            if issue["severity"] == "critical"
        ]
        if critical_issues and not current_observe["evaluation"]["pass"]:
            backtrack_target = determine_backtrack_target(
                state["current_step"],
                critical_issues
            )
            return HardGateTrigger(
                gate_name="critical_issue",
                reason=f"存在critical问题：{critical_issues[0]['description']}",
                action=f"backtrack_to_{backtrack_target}"
            )

    return None
```

### 3.4 第二层：软性Gate（触发LLM决策）

**目的**：识别需要特别关注的情况，但不强制执行动作，而是标记后交给LLM决策。

#### 3.4.1 软性Gate列表

**1. 质量不通过Gate**
```python
触发条件：
  - observe中 pass = false（但没有critical issue）

信号：needs_attention = "quality_failed"
作用：提示LLM该阶段质量不达标，需要考虑是否回退
```

**2. 重大问题Gate**
```python
触发条件：
  - observe中存在severity="major"的issue

信号：needs_attention = "major_issues"
作用：提示LLM存在重大问题，需要权衡是否继续
```

**3. 低分Gate**
```python
触发条件：
  - observe中 overall_score < 0.6

信号：needs_attention = "low_score"
作用：提示LLM整体质量较低，需要评估
```

**4. 证据冲突Gate**
```python
触发条件：
  - Appraise阶段检测到证据冲突（has_conflict = true）

信号：needs_attention = "evidence_conflict"
作用：提示LLM存在证据冲突，可能需要特殊处理
```

#### 3.4.2 软性Gate实现

```python
def check_soft_gates(observe: Dict) -> List[str]:
    """检查软性Gate，返回信号列表"""
    signals = []

    evaluation = observe["evaluation"]

    # Gate 1: 质量不通过
    if not evaluation["pass"]:
        # 排除已被硬性Gate处理的critical情况
        has_critical = any(
            issue["severity"] == "critical"
            for issue in evaluation["issues"]
        )
        if not has_critical:
            signals.append("quality_failed")

    # Gate 2: 重大问题
    major_issues = [
        issue for issue in evaluation["issues"]
        if issue["severity"] == "major"
    ]
    if major_issues:
        signals.append("major_issues")

    # Gate 3: 低分
    if evaluation["overall_score"] < 0.6:
        signals.append("low_score")

    # Gate 4: 证据冲突（仅Appraise阶段）
    if observe["stage"] == "Appraise":
        if observe["output"].get("appraisal_results", {}).get("has_conflict"):
            signals.append("evidence_conflict")

    return signals
```

### 3.5 第三层：LLM决策

**目的**：基于observe和软性Gate信号，进行完整的推理和决策。

#### 3.5.1 调度LLM的输入格式（标准化）

```python
SchedulingInput = {
    "observe": {
        "stage": str,                    # 当前阶段
        "output": Dict[str, Any],        # 阶段输出
        "evaluation": {
            "overall_score": float,
            "dimension_scores": Dict[str, float],
            "pass": bool,
            "issues": List[Issue],
            "summary": str
        }
    },
    "soft_gate_signals": List[str],      # 触发的软性Gate信号
    "execution_history": List[ExecutionNode],  # 完整执行历史
    "original_question": str,            # 原始临床问题
    "current_iteration": int             # 当前迭代次数
}
```

#### 3.5.2 调度LLM的输出格式（标准化）

```python
SchedulingDecision = {
    "reasoning": str,  # 推理过程，必须包含：
                       # - 识别的关键问题
                       # - 考虑的因素（证据质量、效率、风险等）
                       # - 决策依据

    "action": Literal[
        "proceed",              # 前进到下一阶段
        "backtrack_to_ask",     # 回退到Ask
        "backtrack_to_acquire", # 回退到Acquire
        "backtrack_to_appraise",# 回退到Appraise
        "backtrack_to_apply",   # 回退到Apply
        "retry_current",        # 重试当前阶段
        "terminate"             # 终止workflow
    ],

    "parameters": Optional[Dict[str, Any]]  # 可选参数
    # 例如：
    # - adjust_strategy: "增加系统评价类型的检索"
    # - focus_on: "bias_assessment"
    # - reason_for_termination: "证据严重不足，无法给出推荐"
}
```

#### 3.5.3 调度LLM的Prompt设计

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

1. **识别关键问题**：observe中指出了哪些问题？这些问题的严重程度如何？
2. **评估影响**：这些问题是否会影响最终推荐的质量？
3. **权衡选项**：
   - 继续前进：如果问题不严重，可以继续
   - 回退：如果问题需要在前面阶段解决，应该回退到哪里？
   - 重试：如果当前阶段可以改进，是否值得重试？
   - 终止：如果无法得出有效结论，应该终止
4. **考虑效率**：已经执行了{current_iteration}步，是否还有改进空间？
5. **考虑历史**：之前是否已经尝试过类似的回退？效果如何？

## 输出格式

请以JSON格式输出你的决策：

{{
  "reasoning": "你的推理过程...",
  "action": "proceed | backtrack_to_X | retry_current | terminate",
  "parameters": {{"key": "value"}}  // 可选
}}

## 注意事项

- 医疗场景对可靠性要求极高，宁可多花几步也要确保质量
- 但也要避免无意义的重复，如果多次回退仍无改善，应该考虑终止
- 你的reasoning将被记录用于审计，请清晰说明决策依据
"""
```

#### 3.5.4 调度流程实现

```python
def coordinate_next_step(observe: Dict, state: WorkflowState) -> SchedulingDecision:
    """协调下一步行动"""

    # 第一层：硬性Gate检查
    hard_gate_trigger = check_hard_gates(state)
    if hard_gate_trigger:
        return execute_forced_action(hard_gate_trigger)

    # 第二层：软性Gate检查
    soft_gate_signals = check_soft_gates(observe)

    # 第三层：LLM决策
    llm_input = prepare_scheduling_input(
        observe=observe,
        soft_gate_signals=soft_gate_signals,
        state=state
    )

    decision = scheduling_llm.reason_and_decide(llm_input)

    # 验证LLM决策的合理性（简单检查）
    if is_decision_valid(decision, state):
        return decision
    else:
        # 降级策略：如果LLM决策不合理，使用保守策略
        return fallback_decision(observe, state)

def is_decision_valid(decision: SchedulingDecision, state: WorkflowState) -> bool:
    """验证LLM决策的基本合理性"""

    # 检查1：action是否合法
    valid_actions = [
        "proceed", "backtrack_to_ask", "backtrack_to_acquire",
        "backtrack_to_appraise", "backtrack_to_apply",
        "retry_current", "terminate"
    ]
    if decision["action"] not in valid_actions:
        return False

    # 检查2：回退目标是否合理（不能回退到未来）
    if decision["action"].startswith("backtrack_to_"):
        target = decision["action"].replace("backtrack_to_", "")
        current_idx = AGENT_SEQUENCE.index(state["current_step"])
        target_idx = AGENT_SEQUENCE.index(target.capitalize())
        if target_idx >= current_idx:
            return False

    # 检查3：reasoning是否存在
    if not decision.get("reasoning") or len(decision["reasoning"]) < 20:
        return False

    return True

def fallback_decision(observe: Dict, state: WorkflowState) -> SchedulingDecision:
    """降级策略：当LLM决策不合理时使用"""

    # 保守策略：如果pass=false，回退；否则前进
    if not observe["evaluation"]["pass"]:
        # 回退到前一个阶段
        current_idx = AGENT_SEQUENCE.index(state["current_step"])
        if current_idx > 0:
            target = AGENT_SEQUENCE[current_idx - 1]
            return SchedulingDecision(
                reasoning="LLM决策无效，使用降级策略：质量不通过，回退到前一阶段",
                action=f"backtrack_to_{target.lower()}",
                parameters=None
            )

    # 默认：前进
    return SchedulingDecision(
        reasoning="LLM决策无效，使用降级策略：质量通过，继续前进",
        action="proceed",
        parameters=None
    )
```

### 3.6 完整决策流程图

```
用户提问
    ↓
初始化状态 → current_step = "Ask"
    ↓
┌─────────────────────────────────────┐
│  执行当前阶段Agent                    │
│  state = execute_agent(current_step) │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Judge LLM生成Observe                │
│  observe = judge_llm.evaluate(output)│
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  第一层：检查硬性Gate                 │
│  hard_trigger = check_hard_gates()   │
└─────────────────────────────────────┘
    ↓
  触发？ ──Yes→ 执行强制动作 → 终止或回退
    │
   No
    ↓
┌─────────────────────────────────────┐
│  第二层：检查软性Gate                 │
│  signals = check_soft_gates(observe) │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  第三层：调度LLM决策                  │
│  decision = scheduling_llm.decide()  │
│  输入：observe + signals + history   │
│  输出：reasoning + action + params   │
└─────────────────────────────────────┘
    ↓
  验证决策合理性
    ↓
  合理？ ──No→ 使用降级策略
    │
   Yes
    ↓
  执行决策
    ↓
  action = "proceed" ──→ current_step = next_stage
  action = "backtrack_to_X" ──→ current_step = X
  action = "retry_current" ──→ 保持current_step
  action = "terminate" ──→ 结束workflow
    ↓
  是否结束？ ──No→ 回到"执行当前阶段Agent"
    │
   Yes
    ↓
  输出最终结果
```

---

**续：Part 3 - Benchmark设计**
