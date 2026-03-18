# EBM 5A 系统代码改进分析报告

**日期**: 2026-02-07
**基于**: logs/test_run_20260207_161025.log
**状态**: 分析完成

---

## 1. 运行日志关键问题总结

### 1.1 核心问题：死循环终止

```
WORKFLOW TERMINATED: dead_loop_detected
Message: 系统陷入死循环，连续3次回退到 Ask 阶段。
```

**执行路径分析**：
1. Ask (通过, 0.91) → proceed
2. Acquire (失败, 0.00) → backtrack_to_ask
3. Ask (通过, 0.90) → proceed
4. Acquire (失败, 0.65) → backtrack_to_ask
5. Ask (通过, 0.93) → proceed
6. Acquire (通过, 0.83) → proceed
7. Appraise (通过, 0.72) → retry_current (2次)
8. Appraise (通过, 0.72) → proceed
9. Apply (通过, 0.80) → proceed
10. Assess (通过, 0.73) → backtrack_to_ask (第3次！)
11. **死循环检测触发，终止**

### 1.2 问题根源分析

#### 问题1: 调度LLM过度保守
- **现象**: 即使整体评分通过(0.73)，仅有Minor问题，仍然选择回退
- **原因**: Assess阶段发现"未完整回答原始问题"（answer_completeness问题）
- **影响**: 导致不必要的回退，浪费预算

#### 问题2: Acquire阶段不稳定
- **第1次**: 0结果 (Critical问题)
- **第2次**: 4篇文章 (Major问题：数量不足)
- **第3次**: 12篇文章 (通过)
- **原因**: 搜索策略调整不够智能，前两次查询过于严格

#### 问题3: Appraise阶段重复retry
- **现象**: 连续2次retry_current，但评分没有变化(0.72)
- **原因**: 重试策略没有实质性改进，只是重复执行

#### 问题4: 决策矩阵未被严格遵守
- **Prompt中明确规定**: "如果所有问题都是Minor且整体评分通过，则必须选择proceed"
- **实际行为**: Assess阶段有2个Major问题 + 1个Minor问题，但整体通过(0.73)，仍然回退
- **问题**: LLM没有严格遵守决策矩阵，过度关注"完整性"而忽略效率

---

## 2. 符合设计文档的改进方案

### 2.1 改进1: 增强死循环检测逻辑 ⭐⭐⭐

**当前问题**:
```python
# gate_engine.py:36-60
# 只检测连续3次回退到同一阶段
if len(set(to_stages)) == 1:
    return GateTrigger(...)
```

**改进方案**:
```python
def check_dead_loop_gate(state: WorkflowState) -> Optional[GateTrigger]:
    """检测多种死循环模式"""
    backtrack_history = state.get("backtrack_history", [])

    if len(backtrack_history) < 3:
        return None

    recent_backtracks = backtrack_history[-3:]
    to_stages = [bt["to_stage"] for bt in recent_backtracks]

    # Pattern 1: 连续3次回退到同一阶段
    if len(set(to_stages)) == 1:
        return GateTrigger(
            gate_name="dead_loop",
            reason=f"连续3次回退到 {to_stages[0]} 阶段",
            suggested_action="terminate",
            output_message={
                "status": "dead_loop_detected",
                "message": f"系统陷入死循环，连续3次回退到 {to_stages[0]} 阶段。",
                "pattern": "consecutive_backtrack"
            }
        )

    # Pattern 2: 检测循环模式 (A→B→A→B)
    if len(backtrack_history) >= 4:
        last_4 = backtrack_history[-4:]
        stages = [bt["to_stage"] for bt in last_4]
        if stages[0] == stages[2] and stages[1] == stages[3]:
            return GateTrigger(
                gate_name="dead_loop",
                reason=f"检测到循环模式: {stages[0]}↔{stages[1]}",
                suggested_action="terminate",
                output_message={
                    "status": "dead_loop_detected",
                    "message": f"系统陷入循环，在 {stages[0]} 和 {stages[1]} 之间反复回退。",
                    "pattern": "alternating_backtrack"
                }
            )

    # Pattern 3: 回退后评分没有改善
    if len(backtrack_history) >= 2:
        last_2_backtracks = backtrack_history[-2:]
        # 检查是否回退到相同阶段
        if last_2_backtracks[0]["to_stage"] == last_2_backtracks[1]["to_stage"]:
            # 检查评分是否改善
            observe_history = state.get("observe_history", [])
            if len(observe_history) >= 2:
                # 找到回退前后的observe
                target_stage = last_2_backtracks[0]["to_stage"]
                stage_observes = [obs for obs in observe_history if obs.stage == target_stage]

                if len(stage_observes) >= 2:
                    prev_score = stage_observes[-2].evaluation.overall_score
                    curr_score = stage_observes[-1].evaluation.overall_score

                    # 如果评分改善小于0.05，认为没有实质性改善
                    if curr_score - prev_score < 0.05:
                        return GateTrigger(
                            gate_name="dead_loop",
                            reason=f"回退到 {target_stage} 后评分无改善 ({prev_score:.2f} → {curr_score:.2f})",
                            suggested_action="terminate",
                            output_message={
                                "status": "dead_loop_detected",
                                "message": f"多次回退到 {target_stage} 阶段，但质量无实质性改善。",
                                "pattern": "no_improvement"
                            }
                        )

    return None
```

**符合设计文档**: ✅ 2026-02-02-scheduling-system-design-part2-decision-mechanism.md 第3.3节

---

### 2.2 改进2: 优化Acquire阶段的内部重试逻辑 ⭐⭐⭐

**当前问题**:
- 第1次查询过于严格，返回0结果
- 需要外部调度系统回退到Ask才能调整

**改进方案**:
在Acquire Agent内部实现简单的查询调整循环：

```python
# src/agents/acquire_agent.py

def execute(self, state: WorkflowState) -> Dict[str, Any]:
    """Execute acquire with internal retry logic"""
    pico = state.get("pico_query")

    max_internal_attempts = 3
    search_strategies = [
        "strict",      # 第1次：严格匹配
        "moderate",    # 第2次：中等宽松
        "relaxed"      # 第3次：宽松匹配
    ]

    for attempt, strategy in enumerate(search_strategies, 1):
        # 构建查询
        query = self._build_query(pico, strategy)

        # 调用PubMed
        results = self.pubmed_api.search(query, max_results=50)

        # 筛选相关文献
        filtered = self._filter_relevant(results, pico)

        # 检查结果质量
        if len(filtered) == 0 and attempt < max_internal_attempts:
            # 0结果，尝试放宽条件
            print(f"[Acquire] Attempt {attempt}: 0 results, relaxing query...")
            continue
        elif len(filtered) > 100 and attempt < max_internal_attempts:
            # 结果过多，尝试收紧条件
            print(f"[Acquire] Attempt {attempt}: {len(filtered)} results (too many), tightening query...")
            continue
        elif 5 <= len(filtered) <= 50:
            # 结果数量合适
            print(f"[Acquire] Attempt {attempt}: {len(filtered)} results (good)")
            break
        else:
            # 最后一次尝试，接受结果
            print(f"[Acquire] Attempt {attempt}: {len(filtered)} results (final)")
            break

    return {
        "evidence_list": filtered[:20],
        "search_query": query,
        "total_results": len(results),
        "selected_count": len(filtered[:20]),
        "internal_attempts": attempt
    }

def _build_query(self, pico: PICOQuery, strategy: str) -> str:
    """Build PubMed query with different strategies"""
    if strategy == "strict":
        # 使用所有关键词 + MeSH terms + 布尔逻辑
        return self._build_strict_query(pico)
    elif strategy == "moderate":
        # 减少必需关键词，放宽日期限制
        return self._build_moderate_query(pico)
    else:  # relaxed
        # 只使用核心关键词，不限制日期
        return self._build_relaxed_query(pico)
```

**符合设计文档**: ✅ mvp-implementation-strategy.md 第2.2节 "内部简单循环（可选）"

---

### 2.3 改进3: 增强调度LLM的决策质量 ⭐⭐⭐

**问题**: 调度LLM没有严格遵守决策矩阵

**改进方案1: 增强Prompt约束**

```python
# src/config/prompts/scheduling_llm.txt (在决策矩阵后添加)

#### 3.4 强制规则（必须遵守）

**规则1: Minor问题且通过评估 → 必须proceed**
- 条件: 所有问题都是Minor级别 AND overall_score >= 0.7 AND pass_threshold = True
- 动作: 必须选择 "proceed"
- 例外: 无例外

**规则2: 连续回退限制**
- 如果已经回退到某阶段2次以上，且评分改善 < 0.1，则不应再次回退
- 应该选择: proceed 或 request_human_review

**规则3: 预算保护**
- 如果 remaining_budget < 5 且问题不是Critical，则优先选择 proceed
- Critical问题可以选择 request_human_review

**规则4: Assess阶段特殊处理**
- Assess阶段是最后评估阶段，如果通过评估，应该优先选择完成workflow
- 只有在发现Critical问题或逻辑矛盾时才考虑回退
- "未完整回答原始问题"如果是Minor问题，应该在推荐的caveats中说明，而非回退
```

**改进方案2: 添加决策验证逻辑**

```python
# src/scheduling/scheduling_llm.py

def make_decision(self, observe: Observe, state: WorkflowState, soft_gate_signals: List[str]) -> SchedulingDecision:
    """Make scheduling decision with validation"""

    # 调用LLM
    decision = self._call_llm(observe, state, soft_gate_signals)

    # 验证决策合理性
    validation_result = self._validate_decision(decision, observe, state)

    if not validation_result["valid"]:
        print(f"[Scheduling] Decision validation failed: {validation_result['reason']}")
        print(f"[Scheduling] Original decision: {decision.action}")

        # 使用规则引擎覆盖不合理的决策
        decision = self._apply_fallback_rules(observe, state)
        print(f"[Scheduling] Fallback decision: {decision.action}")

    return decision

def _validate_decision(self, decision: SchedulingDecision, observe: Observe, state: WorkflowState) -> Dict[str, Any]:
    """Validate scheduling decision against rules"""

    # Rule 1: Minor问题且通过 → 必须proceed
    all_minor = all(issue.severity == "minor" for issue in observe.evaluation.issues)
    passed = observe.evaluation.pass_threshold
    score_good = observe.evaluation.overall_score >= 0.7

    if all_minor and passed and score_good:
        if decision.action not in ["proceed", "request_human_review"]:
            return {
                "valid": False,
                "reason": "所有问题都是Minor且通过评估，不应回退",
                "rule": "Rule 1"
            }

    # Rule 2: 连续回退限制
    backtrack_history = state.get("backtrack_history", [])
    if decision.action.startswith("backtrack_to_"):
        target_stage = decision.action.replace("backtrack_to_", "").capitalize()

        # 统计回退到该阶段的次数
        backtrack_count = sum(1 for bt in backtrack_history if bt["to_stage"] == target_stage)

        if backtrack_count >= 2:
            # 检查评分改善
            stage_observes = [obs for obs in state["observe_history"] if obs.stage == target_stage]
            if len(stage_observes) >= 2:
                score_improvement = stage_observes[-1].evaluation.overall_score - stage_observes[-2].evaluation.overall_score

                if score_improvement < 0.1:
                    return {
                        "valid": False,
                        "reason": f"已回退到{target_stage}阶段{backtrack_count}次，评分改善不明显",
                        "rule": "Rule 2"
                    }

    # Rule 3: 预算保护
    remaining_budget = state.get("remaining_budget", 0)
    has_critical = any(issue.severity == "critical" for issue in observe.evaluation.issues)

    if remaining_budget < 5 and not has_critical:
        if decision.action in ["backtrack_to_ask", "backtrack_to_acquire", "retry_current"]:
            return {
                "valid": False,
                "reason": f"剩余预算不足({remaining_budget}步)且无Critical问题，不应回退",
                "rule": "Rule 3"
            }

    # Rule 4: Assess阶段特殊处理
    if observe.stage == "Assess" and passed:
        if decision.action.startswith("backtrack_") and not has_critical:
            return {
                "valid": False,
                "reason": "Assess阶段通过评估且无Critical问题，不应回退",
                "rule": "Rule 4"
            }

    return {"valid": True}

def _apply_fallback_rules(self, observe: Observe, state: WorkflowState) -> SchedulingDecision:
    """Apply rule-based fallback decision"""

    # 检查是否有Critical问题
    has_critical = any(issue.severity == "critical" for issue in observe.evaluation.issues)

    if has_critical:
        # Critical问题：回退或人类介入
        if state.get("remaining_budget", 0) < 5:
            return SchedulingDecision(
                reasoning="存在Critical问题但预算不足，请求人类介入",
                action="request_human_review",
                parameters={"review_scope": "critical_issue", "reason": "Critical问题需要人类判断"}
            )
        else:
            # 回退到前一阶段
            current_idx = self.agent_sequence.index(observe.stage)
            if current_idx > 0:
                target = self.agent_sequence[current_idx - 1].lower()
                return SchedulingDecision(
                    reasoning="存在Critical问题，回退到前一阶段",
                    action=f"backtrack_to_{target}",
                    parameters=None
                )

    # 默认：继续
    return SchedulingDecision(
        reasoning="应用降级策略：质量通过，继续前进",
        action="proceed",
        parameters=None
    )
```

**符合设计文档**: ✅ 2026-02-02-scheduling-system-design-part2-decision-mechanism.md 第3.5.4节

---

### 2.4 改进4: 优化retry_current的执行策略 ⭐⭐

**问题**: Appraise阶段连续2次retry但评分无变化

**改进方案**: 在retry时传递调整策略

```python
# src/coordinator/coordinator.py

def handle_scheduling_decision(self, state: WorkflowState, decision) -> WorkflowState:
    """Handle scheduling decision with strategy adjustment"""
    action = decision.action

    if action == "retry_current":
        # 记录retry原因和调整策略
        state["backtrack_reason"] = decision.reasoning

        # 如果有调整策略，记录到state中供agent使用
        if decision.parameters and "adjust_strategy" in decision.parameters:
            state["retry_strategy"] = decision.parameters["adjust_strategy"]
            state["retry_focus"] = decision.parameters.get("focus_on")

        # 检查是否已经retry过
        retry_count = state.get("retry_count", {}).get(state["current_step"], 0)
        state.setdefault("retry_count", {})[state["current_step"]] = retry_count + 1

        # 如果retry次数过多，强制proceed
        if retry_count >= 2:
            print(f"[Coordinator] {state['current_step']} 已retry {retry_count}次，强制继续")
            next_step = self.route_next(state)
            state["current_step"] = next_step
            state["retry_count"][state["current_step"]] = 0  # 重置

    # ... 其他action处理 ...
```

**符合设计文档**: ✅ 2026-02-04-scheduling-system-improvements.md 第2.2节

---

### 2.5 改进5: 增加"优雅完成"逻辑 ⭐⭐

**问题**: Assess阶段即使通过也可能回退，导致无法完成workflow

**改进方案**: 在Assess阶段增加完成条件检查

```python
# src/coordinator/coordinator.py

def execute_workflow(self, question: str) -> WorkflowState:
    """Execute workflow with graceful completion"""
    state = self.initialize_state(question)

    while not state.get("should_terminate"):
        current_step = state["current_step"]

        if current_step is None:
            break

        # 执行agent
        state = self.execute_agent(current_step, state)

        # 检查硬性Gate
        gate_trigger = check_hard_gates(state)
        if gate_trigger:
            # ... 处理gate触发 ...
            break

        # 特殊处理：Assess阶段完成检查
        if current_step == "Assess":
            assess_observe = state["observe_history"][-1]

            # 如果Assess通过且无Critical问题，应该完成workflow
            has_critical = any(issue.severity == "critical" for issue in assess_observe.evaluation.issues)

            if assess_observe.evaluation.pass_threshold and not has_critical:
                print(f"\n[Coordinator] Assess阶段通过评估且无Critical问题，完成workflow")
                state["should_terminate"] = True
                state["termination_reason"] = "workflow_completed_successfully"
                break

        # 收集软性Gate信号
        soft_gate_signals = collect_soft_gate_signals(state)
        state["soft_gate_signals"] = soft_gate_signals

        # 调度决策
        current_observe = state["observe_history"][-1]
        decision = self.scheduling_llm.make_decision(current_observe, state, soft_gate_signals)

        # 记录决策
        state["decision_history"].append(decision)

        # 处理决策
        state = self.handle_scheduling_decision(state, decision)

        if state["current_step"] is None:
            break

    return state
```

**符合设计文档**: ✅ 2026-02-04-scheduling-system-improvements.md 第2.2节 "优雅失败"

---

## 3. 改进优先级和实施计划

### Phase 1: 紧急修复（1-2天）⭐⭐⭐

**目标**: 解决死循环问题，让系统能够正常完成workflow

1. **改进2.3**: 增强调度LLM决策验证（半天）
   - 实现 `_validate_decision()` 方法
   - 实现 `_apply_fallback_rules()` 方法
   - 测试验证逻辑

2. **改进2.5**: 增加优雅完成逻辑（半天）
   - 在Assess阶段增加完成条件检查
   - 测试完成流程

3. **改进2.1**: 增强死循环检测（半天）
   - 实现3种死循环模式检测
   - 测试检测逻辑

### Phase 2: 质量提升（2-3天）⭐⭐

**目标**: 提升各阶段执行质量，减少不必要的回退

4. **改进2.2**: 优化Acquire内部重试（1天）
   - 实现3级查询策略
   - 测试不同策略效果

5. **改进2.4**: 优化retry策略（1天）
   - 实现retry计数和强制继续
   - 传递调整策略给agent

### Phase 3: 系统优化（持续）⭐

6. 收集更多测试案例
7. 调优各阶段的评价标准
8. 优化LLM prompt

---

## 4. 预期效果

### 4.1 解决当前问题

- ✅ 死循环问题：通过增强检测和决策验证，避免不必要的回退
- ✅ Acquire不稳定：通过内部重试，减少外部回退次数
- ✅ 过度保守：通过决策验证，强制执行合理的proceed决策
- ✅ 无法完成：通过优雅完成逻辑，确保Assess阶段能够正常结束

### 4.2 性能提升预期

**当前运行**:
- 总迭代次数: 12
- 回退次数: 3
- 完成状态: 死循环终止

**改进后预期**:
- 总迭代次数: 7-9
- 回退次数: 0-1
- 完成状态: 正常完成

**效率提升**: ~30-40%

---

## 5. 风险和注意事项

### 5.1 风险

1. **过度约束**: 决策验证规则可能过于严格，限制LLM的灵活性
   - **缓解**: 保留人类介入选项，允许在特殊情况下请求审核

2. **质量下降**: 减少回退可能导致最终推荐质量下降
   - **缓解**: 只在Minor问题时强制proceed，Critical/Major问题仍然回退

3. **边界情况**: 新的逻辑可能在某些边界情况下失效
   - **缓解**: 增加更多测试案例，覆盖各种场景

### 5.2 注意事项

1. **保持设计原则**: 所有改进必须符合docs/plans中的设计思想
2. **渐进式改进**: 先实现Phase 1，验证效果后再进行Phase 2
3. **充分测试**: 每个改进都需要单元测试和集成测试
4. **文档更新**: 改进后更新相关设计文档

---

## 6. 测试验证计划

### 6.1 单元测试

- `test_dead_loop_detection()`: 测试3种死循环模式
- `test_decision_validation()`: 测试4条验证规则
- `test_acquire_retry()`: 测试内部重试逻辑
- `test_graceful_completion()`: 测试优雅完成

### 6.2 集成测试

使用当前失败的案例重新测试：
```python
question = "阿司匹林能预防心血管疾病吗？"
```

**预期结果**:
- 不应该出现死循环
- 应该在7-9步内完成
- 最终应该生成推荐

### 6.3 回归测试

使用其他临床问题测试，确保改进没有破坏现有功能。

---

**文档版本**: v1.0
**作者**: Claude (EBM 5A Analysis)
**最后更新**: 2026-02-07
