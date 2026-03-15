# EBM 5A 调度系统设计文档 - Part 3: Benchmark设计

**日期**: 2026-02-02
**项目**: 基于ReAct模式的调度系统设计
**状态**: 设计阶段

---

## 4. Benchmark设计

### 4.1 设计目标

设计一个**Rubrics式评测集**来评价调度LLM的决策能力，采用"问题 + 理想路径 + 评分标准"的结构，类似HealthBench。

### 4.2 评价重点

**核心重点**：调度LLM的决策能力（决策正确性 + 效率）

**辅助指标**：最终结果质量（用于验证决策有效性，但不作为主要评价对象）

**原因**：
- Assess LLM（Stage 5）负责评价最终推荐的"自洽性"（无ground truth）
- Benchmark评价最终推荐与"专家推荐"的一致性（有ground truth）
- 但最终结果质量受所有5个阶段LLM影响，不能单独归因于调度LLM
- 因此重点放在调度LLM本身的决策质量和效率上

### 4.3 Benchmark结构

#### 4.3.1 单个测试案例结构

```python
{
  "case_id": "case_001",

  "clinical_question": "35岁初产妇，孕20周，血压140/90，是否应该使用阿司匹林预防子痫前期？",

  "reference_path": {
    # 理想执行路径（专家标注）
    "steps": [
      {
        "stage": "Ask",
        "output": {
          "pico_query": {
            "patient": "35岁初产妇，孕20周，血压140/90",
            "intervention": "低剂量阿司匹林",
            "comparison": "不使用或安慰剂",
            "outcome": "子痫前期发生率",
            "keywords": ["aspirin", "preeclampsia", "prevention", "pregnancy"]
          },
          "mesh_terms": ["D001241", "D011225"]
        },
        "observe": {
          "stage": "Ask",
          "evaluation": {
            "overall_score": 0.85,
            "dimension_scores": {
              "pico_completeness": 0.9,
              "searchability": 0.8,
              "terminology_accuracy": 0.9,
              "clarity": 0.85,
              "clinical_context": 0.8
            },
            "pass": true,
            "issues": [],
            "summary": "PICO结构完整，关键词合理"
          }
        },
        "decision": {
          "action": "proceed",
          "reasoning": "PICO结构完整，关键词合理，可以进行证据检索",
          "parameters": null
        }
      },
      {
        "stage": "Acquire",
        "output": {
          "evidence_list": [...],  # 10篇文献
          "total_results": 45,
          "selected_count": 10
        },
        "observe": {
          "stage": "Acquire",
          "evaluation": {
            "overall_score": 0.65,
            "dimension_scores": {
              "strategy_quality": 0.7,
              "quantity_sufficiency": 0.7,
              "relevance": 0.75,
              "diversity": 0.5,  # 低分
              "timeliness": 0.8
            },
            "pass": false,
            "issues": [
              {
                "severity": "major",
                "dimension": "diversity",
                "description": "缺少系统评价类型的证据，主要为单个RCT研究"
              }
            ],
            "summary": "证据数量足够但类型单一，建议补充系统评价"
          }
        },
        "decision": {
          "action": "backtrack_to_acquire",
          "reasoning": "证据类型单一是重大问题，缺少高质量的系统评价可能影响推荐可靠性。应该调整检索策略，增加meta-analysis和systematic review的检索",
          "parameters": {
            "adjust_strategy": "增加检索词：meta-analysis OR systematic review",
            "focus_on": "diversity"
          }
        }
      },
      {
        "stage": "Acquire",  # 第二次
        "output": {
          "evidence_list": [...],  # 12篇文献，包含3篇系统评价
          "total_results": 58,
          "selected_count": 12
        },
        "observe": {
          "stage": "Acquire",
          "evaluation": {
            "overall_score": 0.82,
            "dimension_scores": {
              "strategy_quality": 0.85,
              "quantity_sufficiency": 0.8,
              "relevance": 0.8,
              "diversity": 0.85,
              "timeliness": 0.8
            },
            "pass": true,
            "issues": [],
            "summary": "检索策略改进后，证据类型多样，质量良好"
          }
        },
        "decision": {
          "action": "proceed",
          "reasoning": "证据类型已经改善，包含了系统评价，可以进行质量评价",
          "parameters": null
        }
      },
      {
        "stage": "Appraise",
        "output": {
          "appraisal_results": {...},
          "grade_distribution": {"High": 3, "Moderate": 7, "Low": 2}
        },
        "observe": {
          "stage": "Appraise",
          "evaluation": {
            "overall_score": 0.88,
            "dimension_scores": {
              "grade_reasonableness": 0.9,
              "consistency": 0.85,
              "conflict_identification": 0.9,
              "bias_assessment": 0.85,
              "synthesis_logic": 0.9
            },
            "pass": true,
            "issues": [],
            "summary": "证据质量评价合理，综合逻辑清晰"
          }
        },
        "decision": {
          "action": "proceed",
          "reasoning": "证据质量评价完成，大部分为中高质量证据，可以生成推荐",
          "parameters": null
        }
      },
      {
        "stage": "Apply",
        "output": {
          "recommendation": {
            "text": "建议使用低剂量阿司匹林（75-150mg/日）预防子痫前期...",
            "strength": "strong",
            "rationale": "基于多项高质量RCT和系统评价...",
            "caveats": ["禁忌症：阿司匹林过敏", "监测：定期产检"]
          }
        },
        "observe": {
          "stage": "Apply",
          "evaluation": {
            "overall_score": 0.85,
            "dimension_scores": {
              "evidence_alignment": 0.9,
              "strength_appropriateness": 0.9,
              "calculation_accuracy": 1.0,
              "caveat_completeness": 0.75,
              "actionability": 0.85
            },
            "pass": true,
            "issues": [
              {
                "severity": "minor",
                "dimension": "caveat_completeness",
                "description": "可以补充更多特殊人群的考虑"
              }
            ],
            "summary": "推荐合理，强度适当，但注意事项可以更全面"
          }
        },
        "decision": {
          "action": "proceed",
          "reasoning": "推荐质量良好，虽然有minor问题但不影响整体质量，可以进行最终评估",
          "parameters": null
        }
      },
      {
        "stage": "Assess",
        "output": {
          "assessment": {
            "quality_score": 0.85,
            "gaps": [],
            "needs_backtrack": false
          }
        },
        "observe": {
          "stage": "Assess",
          "evaluation": {
            "overall_score": 0.88,
            "dimension_scores": {
              "answer_completeness": 0.9,
              "reasoning_chain": 0.85,
              "logical_consistency": 0.9,
              "factor_coverage": 0.85,
              "gap_identification": 0.9
            },
            "pass": true,
            "issues": [],
            "summary": "整体质量良好，推理链完整，可以输出"
          }
        },
        "decision": {
          "action": "terminate",
          "reasoning": "workflow完成，质量达标，可以输出最终推荐",
          "parameters": {
            "reason_for_termination": "success"
          }
        }
      }
    ],

    "final_recommendation": {
      "text": "建议使用低剂量阿司匹林（75-150mg/日）预防子痫前期...",
      "strength": "strong",
      "evidence_quality": "High to Moderate"
    },

    "path_summary": {
      "total_steps": 7,
      "backtrack_count": 1,
      "backtrack_points": ["Acquire(1) -> Acquire(2)"],
      "final_stage_reached": "Assess"
    }
  },

  "rubrics": {
    # 评分标准
    "decision_quality": {
      "weight": 0.4,
      "sub_metrics": [
        {
          "name": "routing_accuracy",
          "description": "每个决策点的action是否与参考路径一致",
          "scoring": "automatic",
          "formula": "correct_decisions / total_decisions",
          "weight": 0.4
        },
        {
          "name": "backtrack_appropriateness",
          "description": "回溯决策是否合理（时机、目标阶段）",
          "scoring": "automatic",
          "weight": 0.3,
          "criteria": {
            "full_credit": "回溯时机和目标与参考路径完全一致",
            "partial_credit_0.7": "回溯时机正确但目标阶段相差1步",
            "partial_credit_0.5": "识别需要回溯但时机或目标不准确",
            "no_credit": "不必要的回溯或遗漏必要的回溯"
          }
        },
        {
          "name": "reasoning_quality",
          "description": "调度LLM的reasoning是否识别了关键问题",
          "scoring": "manual",
          "weight": 0.3,
          "scale": "1-5",
          "criteria": {
            "5": "完全识别关键问题，逻辑清晰，与专家reasoning高度一致",
            "4": "识别了主要问题，逻辑基本清晰",
            "3": "识别了部分问题，但有遗漏或逻辑不够严密",
            "2": "问题识别不充分，逻辑有明显缺陷",
            "1": "未能识别关键问题"
          }
        }
      ]
    },

    "efficiency": {
      "weight": 0.3,
      "sub_metrics": [
        {
          "name": "path_length_ratio",
          "description": "实际路径长度与参考路径的比值",
          "scoring": "automatic",
          "weight": 0.4,
          "formula": "min(1.0, reference_length / actual_length)",
          "note": "越接近1越好，超过参考路径会扣分"
        },
        {
          "name": "redundancy",
          "description": "不必要的重复调用次数",
          "scoring": "automatic",
          "weight": 0.3,
          "formula": "1 - (redundant_calls / total_calls)",
          "definition": "redundant_calls = 相同阶段连续调用且输入高度相似的次数"
        },
        {
          "name": "convergence_speed",
          "description": "从发现问题到解决问题的步骤数",
          "scoring": "automatic",
          "weight": 0.3,
          "criteria": {
            "full_credit": "与参考路径步骤数相同",
            "partial_credit_0.8": "多1步",
            "partial_credit_0.6": "多2步",
            "no_credit": "多3步以上"
          }
        }
      ]
    },

    "final_quality": {
      "weight": 0.3,
      "sub_metrics": [
        {
          "name": "recommendation_alignment",
          "description": "最终推荐与参考推荐的一致性",
          "scoring": "mixed",
          "weight": 0.5,
          "automatic_part": {
            "method": "semantic_similarity",
            "weight": 0.5
          },
          "manual_part": {
            "description": "专家判断临床等价性",
            "scale": "1-5",
            "weight": 0.5
          }
        },
        {
          "name": "evidence_quality",
          "description": "使用的证据质量分布",
          "scoring": "automatic",
          "weight": 0.3,
          "formula": "compare_grade_distribution(actual, reference)",
          "method": "计算High/Moderate/Low比例的相似度"
        },
        {
          "name": "completeness",
          "description": "是否覆盖了参考答案中的关键要素",
          "scoring": "automatic",
          "weight": 0.2,
          "checklist": [
            "推荐强度",
            "剂量信息",
            "禁忌症",
            "特殊人群考虑",
            "监测建议"
          ],
          "formula": "covered_items / total_items"
        }
      ]
    }
  },

  "metadata": {
    "difficulty": "medium",  # easy/medium/hard
    "scenario_type": "single_backtrack",  # smooth/single_backtrack/multiple_backtrack/no_conclusion
    "clinical_domain": "obstetrics",
    "evidence_availability": "sufficient",
    "expected_challenges": ["证据类型多样性不足"]
  }
}
```

### 4.4 数据收集策略

采用**分层标注 + 合成扩展**的策略：
- **金标准数据**：少量高质量专家标注（10-20个完整路径 + 50-100个关键决策点）
- **合成数据**：基于金标准生成更多测试案例（200-300个）

#### 4.4.1 金标准数据收集

**Step 1: 准备临床问题（10-20个）**

按照不同场景类型分布：
- **顺利型**（30%）：Ask→Acquire→Appraise→Apply→Assess，一次通过
- **单次回溯型**（40%）：某个阶段出问题，回溯一次后成功
- **多次回溯型**（20%）：需要多次调整才能得到满意结果
- **无法完成型**（10%）：证据严重不足，最终无法给出推荐

**Step 2: 专家标注理想路径**

使用**Judge LLM生成 + 专家review**的方式：

```python
# 标注流程
for stage in ["Ask", "Acquire", "Appraise", "Apply", "Assess"]:
    # 1. 执行该阶段的Agent
    output = agent.execute(state)

    # 2. Judge LLM生成observe
    observe = judge_llm.evaluate(output)

    # 3. 专家review和修正observe
    corrected_observe = expert.review_and_correct(observe)
    # 专家可以修改：
    # - dimension_scores
    # - issues的severity
    # - pass的判断
    # - summary

    # 4. 专家标注决策
    expert_decision = expert.annotate_decision(corrected_observe, state)
    # 包含：
    # - action: "proceed" / "backtrack_to_X" / "retry" / "terminate"
    # - reasoning: 详细的决策理由
    # - parameters: 可选的调整建议

    # 5. 记录到金标准数据集
    save_to_reference_path(stage, output, corrected_observe, expert_decision)

    # 6. 按照专家决策继续
    state = apply_expert_decision(expert_decision, state)
```

**专家标注界面示例**：
```
=== Stage: Acquire ===

【输出】
- 证据列表：10篇文献
- 证据类型：RCT(8), 队列研究(2)
- 总检索结果：45篇

【Judge LLM生成的Observe】
overall_score: 0.65
dimension_scores:
  - diversity: 0.5  ← 专家可能觉得这个评分合理

pass: false

issues:
  - [major] diversity: "缺少系统评价类型的证据"

【专家修正】（可选）
✏️ 保持原样 / 修改某些评分

【专家决策标注】
Action: [✓] backtrack_to_acquire  [ ] proceed  [ ] retry  [ ] terminate

Reasoning: "证据类型单一是重大问题，缺少高质量的系统评价可能影响推荐可靠性。
应该调整检索策略，增加meta-analysis和systematic review的检索"

Parameters:
  adjust_strategy: "增加检索词：meta-analysis OR systematic review"
  focus_on: "diversity"
```

#### 4.4.2 合成数据生成

基于金标准案例，通过以下方法生成更多测试案例：

**方法1: 模板化合成**
```python
# 从金标中提取决策模式
pattern = {
    "trigger": "Acquire阶段diversity低 + pass=false",
    "decision": "backtrack_to_acquire",
    "reasoning_template": "证据类型单一，缺少{evidence_type}，应该调整检索策略"
}

# 生成变体
variants = [
    {"evidence_type": "系统评价", "adjust": "增加meta-analysis检索"},
    {"evidence_type": "RCT研究", "adjust": "增加randomized trial检索"},
    {"evidence_type": "队列研究", "adjust": "增加cohort study检索"}
]
```

**方法2: 组合式合成**
```python
# 从不同金标中提取步骤，组合成新路径
new_case = {
    "steps": [
        gold_case_A.steps[0],  # Ask阶段顺利通过
        gold_case_B.steps[1],  # Acquire阶段遇到问题
        gold_case_B.steps[2],  # 回溯后的Acquire
        gold_case_C.steps[3],  # Appraise阶段
        # ...
    ]
}
```

**方法3: 参数化合成**
```python
# 调整金标中的数值参数
synthetic_case = copy.deepcopy(gold_case)
synthetic_case.steps[2].observe.evaluation.overall_score = 0.58  # 从0.65调整
synthetic_case.steps[2].observe.evaluation.dimension_scores["diversity"] = 0.55
# 决策保持不变（因为仍然低于阈值）
```

### 4.5 测试集划分

```python
benchmark_dataset = {
    "dev_set": {
        "gold_standard": 4,      # 金标准的20%
        "synthetic": 0,
        "total": 4,
        "purpose": "快速调试和迭代"
    },
    "validation_set": {
        "gold_standard": 6,      # 金标准的30%
        "synthetic": 100,
        "total": 106,
        "purpose": "调优和超参数选择"
    },
    "test_set": {
        "gold_standard": 10,     # 金标准的50%
        "synthetic": 200,
        "total": 210,
        "purpose": "最终评估和对比"
    }
}
```

### 4.6 评测流程

```python
def evaluate_case(case: BenchmarkCase, system_output: WorkflowOutput) -> EvaluationResult:
    """评测单个案例"""

    scores = {}

    # ===== A) 决策质量指标（自动评分）=====

    # 1. 路由准确率
    scores["routing_accuracy"] = compute_routing_accuracy(
        system_output.decisions,
        case.reference_path.decisions
    )

    # 2. 回溯合理性
    scores["backtrack_appropriateness"] = evaluate_backtrack(
        system_output.decisions,
        case.reference_path.decisions
    )

    # ===== B) 效率指标（自动评分）=====

    # 3. 路径长度比
    scores["path_length_ratio"] = min(1.0,
        len(case.reference_path.steps) / len(system_output.steps)
    )

    # 4. 冗余度
    scores["redundancy"] = 1 - compute_redundancy_rate(system_output.steps)

    # 5. 收敛速度
    scores["convergence_speed"] = evaluate_convergence(
        system_output.steps,
        case.reference_path.steps
    )

    # ===== C) 最终质量指标（混合评分）=====

    # 6. 证据质量分布（自动）
    scores["evidence_quality"] = compare_evidence_distribution(
        system_output.final_evidence,
        case.reference_path.final_evidence
    )

    # 7. 完整性（自动）
    scores["completeness"] = check_completeness(
        system_output.final_recommendation,
        case.rubrics.final_quality.completeness.checklist
    )

    # 8. 推荐一致性（自动部分）
    auto_similarity = semantic_similarity(
        system_output.final_recommendation.text,
        case.reference_path.final_recommendation.text
    )
    scores["recommendation_alignment_auto"] = auto_similarity

    # ===== 需要人工评分的部分 =====
    manual_scores = {
        "reasoning_quality": None,  # 需要专家评分1-5
        "recommendation_clinical_equivalence": None  # 需要专家评分1-5
    }

    # ===== 计算加权总分 =====
    # 注意：人工评分部分需要后续补充

    decision_quality_score = (
        0.4 * scores["routing_accuracy"] +
        0.3 * scores["backtrack_appropriateness"] +
        0.3 * (manual_scores["reasoning_quality"] / 5.0 if manual_scores["reasoning_quality"] else 0)
    )

    efficiency_score = (
        0.4 * scores["path_length_ratio"] +
        0.3 * scores["redundancy"] +
        0.3 * scores["convergence_speed"]
    )

    final_quality_score = (
        0.5 * (0.5 * scores["recommendation_alignment_auto"] +
               0.5 * (manual_scores["recommendation_clinical_equivalence"] / 5.0 if manual_scores["recommendation_clinical_equivalence"] else 0)) +
        0.3 * scores["evidence_quality"] +
        0.2 * scores["completeness"]
    )

    overall_score = (
        0.4 * decision_quality_score +
        0.3 * efficiency_score +
        0.3 * final_quality_score
    )

    return EvaluationResult(
        case_id=case.case_id,
        overall_score=overall_score,
        dimension_scores={
            "decision_quality": decision_quality_score,
            "efficiency": efficiency_score,
            "final_quality": final_quality_score
        },
        detailed_scores=scores,
        manual_scores=manual_scores
    )
```

### 4.7 Benchmark测试协议

为了确保不同版本调度LLM的结果可比，需要**固定其他组件**：

```yaml
# benchmark_config.yaml
components:
  judge_llm:
    version: "v1.0"
    model: "gpt-4"
    frozen: true  # 固定版本，不可更改

  agents:
    ask_agent:
      version: "v1.0"
      model: "gpt-4"
      frozen: true
    acquire_agent:
      version: "v1.0"
      model: "gpt-4"
      frozen: true
    appraise_agent:
      version: "v1.0"
      model: "gpt-4"
      frozen: true
    apply_agent:
      version: "v1.0"
      model: "gpt-4"
      frozen: true
    assess_agent:
      version: "v1.0"
      model: "gpt-4"
      frozen: true

  scheduling_llm:
    version: "v2.0"  # 被测试的组件
    model: "fine-tuned-scheduler"
    frozen: false  # 可以更换不同版本进行对比

evidence_source:
  type: "pubmed"  # 或 "evidence_db"
  version: "2024-01"
  frozen: true

gate_config:
  hard_gates: "v1.0"
  soft_gates: "v1.0"
  frozen: true
```

**评测时的保证**：
- 所有frozen=true的组件保持固定版本
- 只有调度LLM可以变化
- 这样不同版本调度LLM的benchmark结果可以直接对比
- 避免"其他组件升级导致调度LLM表现变化"的混淆

---

**续：Part 4 - 无缝衔接设计**
