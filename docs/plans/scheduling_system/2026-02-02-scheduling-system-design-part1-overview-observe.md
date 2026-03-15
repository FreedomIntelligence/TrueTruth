# EBM 5A 调度系统设计文档 - Part 1: 概述与Observe设计

**日期**: 2026-02-02
**项目**: 基于ReAct模式的调度系统设计
**状态**: 设计阶段

---

## 1. 概述

### 1.1 背景

基于已实现的EBM 5A临床决策支持系统第一版（参考 `docs/plans/stage1`），本文档聚焦于**系统调度体系**的设计，暂时将五个阶段（Ask/Acquire/Appraise/Apply/Assess）当作黑盒看待。

### 1.2 设计目标

1. **强化ReAct模式**：明确体现Reason（推理）→ Act（行动）→ Observe（观察）的循环
2. **灵活的调度决策**：调度LLM根据observe进行推理，决定下一步行动（前进/回退/重试）
3. **可评价的系统**：设计benchmark来评价调度LLM的决策能力
4. **可扩展架构**：无缝衔接未来的证据库和训练后的LLM

### 1.3 核心设计原则

- **医疗可靠性优先**：使用分层决策机制，硬性规则保证底线
- **可解释性**：所有决策都有明确的reasoning和审计追踪
- **标准化接口**：固定的输入输出格式，便于组件升级
- **渐进式复杂度**：从简单规则到复杂推理，分层处理

---

## 2. Observe设计

### 2.1 设计思路

每个阶段执行后，由**Judge LLM**对该阶段的输出进行评价，生成结构化的observe。Observe采用**混合方式**，包含：
- 数值评分（量化质量）
- 问题列表（具体缺陷）
- 自然语言总结（整体评价）

### 2.2 通用Observe结构

```python
{
  "stage": "Ask" | "Acquire" | "Appraise" | "Apply" | "Assess",
  "output": {...},  # 该阶段的实际输出
  "evaluation": {
    "overall_score": 0.0-1.0,        # 整体评分
    "dimension_scores": {             # 各维度评分
      "dimension_1": 0.0-1.0,
      "dimension_2": 0.0-1.0,
      ...
    },
    "pass": true/false,               # 是否通过质量阈值
    "issues": [                       # 具体问题列表
      {
        "severity": "critical" | "major" | "minor",
        "dimension": "dimension_name",
        "description": "问题描述"
      }
    ],
    "summary": "自然语言评价总结"
  }
}
```

### 2.3 各阶段的评价维度

#### 2.3.1 Ask阶段 - 问题精炼质量评价

**Judge LLM评价内容**：
- **pico_completeness** (PICO完整性): P/I/C/O四个要素是否都明确提取
- **searchability** (可搜索性): 关键词是否足够具体，能否有效检索
- **terminology_accuracy** (术语准确性): 术语使用是否规范（如是否正确映射到MeSH）
- **clarity** (问题明确性): 是否还存在歧义或模糊之处
- **clinical_context** (临床背景充分性): 是否包含必要的患者特征、临床情境

**Observe示例**：
```python
{
  "stage": "Ask",
  "output": {
    "pico_query": PICOQuery(...),
    "search_keywords": ["aspirin", "preeclampsia", "prevention"],
    "mesh_terms": ["D001241", "D011225"]
  },
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
    "issues": [
      {
        "severity": "minor",
        "dimension": "searchability",
        "description": "关键词'妊娠期高血压'可能过于宽泛，建议细化为具体亚型"
      }
    ],
    "summary": "PICO结构完整，关键词基本合理，但可进一步细化以提高检索精度"
  }
}
```

#### 2.3.2 Acquire阶段 - 证据获取质量评价

**Judge LLM评价内容**：
- **strategy_quality** (检索策略合理性): 关键词组合、布尔运算符使用是否恰当
- **quantity_sufficiency** (证据数量充足性): 找到的证据数量是否足够支撑分析
- **relevance** (证据相关性): 检索结果是否真正回答PICO问题
- **diversity** (证据类型多样性): 是否涵盖不同类型研究（RCT、系统评价、队列研究等）
- **timeliness** (证据时效性): 是否包含最新研究，是否遗漏重要近期文献

**Observe示例**：
```python
{
  "stage": "Acquire",
  "output": {
    "evidence_list": [Evidence(...), ...],
    "search_strategy": {...},
    "total_results": 45,
    "selected_count": 10
  },
  "evaluation": {
    "overall_score": 0.75,
    "dimension_scores": {
      "strategy_quality": 0.8,
      "quantity_sufficiency": 0.7,
      "relevance": 0.75,
      "diversity": 0.7,
      "timeliness": 0.8
    },
    "pass": true,
    "issues": [
      {
        "severity": "major",
        "dimension": "diversity",
        "description": "缺少系统评价类型的证据，主要为单个RCT研究"
      },
      {
        "severity": "minor",
        "dimension": "relevance",
        "description": "3篇文献关注的outcome与PICO中的outcome不完全匹配"
      }
    ],
    "summary": "检索到足够数量的相关证据，但证据类型偏向单一，建议补充系统评价"
  }
}
```

#### 2.3.3 Appraise阶段 - 证据评价质量评价

**Judge LLM评价内容**：
- **grade_reasonableness** (GRADE评分合理性): 质量评级是否符合GRADE标准
- **consistency** (评估一致性): 对相似证据的评价是否一致
- **conflict_identification** (冲突识别准确性): 是否正确识别了证据间的矛盾
- **bias_assessment** (偏倚风险评估): 是否充分考虑了研究设计缺陷、利益冲突等
- **synthesis_logic** (证据综合逻辑性): 多个证据的整合是否合理

**Observe示例**：
```python
{
  "stage": "Appraise",
  "output": {
    "appraisal_results": AppraisalResults(...),
    "grade_distribution": {"High": 2, "Moderate": 5, "Low": 3},
    "conflicts_detected": true
  },
  "evaluation": {
    "overall_score": 0.7,
    "dimension_scores": {
      "grade_reasonableness": 0.75,
      "consistency": 0.8,
      "conflict_identification": 0.9,
      "bias_assessment": 0.6,
      "synthesis_logic": 0.65
    },
    "pass": false,
    "issues": [
      {
        "severity": "critical",
        "dimension": "bias_assessment",
        "description": "未充分评估2篇研究的资金来源偏倚风险"
      },
      {
        "severity": "major",
        "dimension": "synthesis_logic",
        "description": "对冲突证据的权重分配缺乏明确依据"
      }
    ],
    "summary": "GRADE评分基本合理，但偏倚评估不够深入，冲突证据的综合逻辑需要加强"
  }
}
```

#### 2.3.4 Apply阶段 - 推荐生成质量评价

**Judge LLM评价内容**：
- **evidence_alignment** (证据-推荐匹配度): 推荐是否有充分证据支持，是否过度推断
- **strength_appropriateness** (推荐强度合理性): 强度等级是否与证据质量相匹配
- **calculation_accuracy** (计算准确性): 风险评分、NNT等计算是否正确
- **caveat_completeness** (注意事项完整性): 禁忌症、特殊人群考虑是否充分
- **actionability** (临床可操作性): 推荐是否具体、可执行

**Observe示例**：
```python
{
  "stage": "Apply",
  "output": {
    "recommendation": Recommendation(...),
    "calculations": {"NNT": 25, "risk_score": 0.15},
    "strength": "weak"
  },
  "evaluation": {
    "overall_score": 0.82,
    "dimension_scores": {
      "evidence_alignment": 0.85,
      "strength_appropriateness": 0.9,
      "calculation_accuracy": 1.0,
      "caveat_completeness": 0.7,
      "actionability": 0.8
    },
    "pass": true,
    "issues": [
      {
        "severity": "minor",
        "dimension": "caveat_completeness",
        "description": "未提及肝功能不全患者的剂量调整"
      }
    ],
    "summary": "推荐与证据匹配良好，强度合理，计算准确，但注意事项可以更全面"
  }
}
```

#### 2.3.5 Assess阶段 - 整体质量评价

**Judge LLM评价内容**：
- **answer_completeness** (问题回答完整性): 是否完整回答了原始临床问题
- **reasoning_chain** (推理链完整性): 从问题→证据→推荐的逻辑链是否清晰
- **logical_consistency** (逻辑一致性): 各部分之间是否存在矛盾
- **factor_coverage** (关键因素覆盖度): 是否遗漏重要的临床考虑因素
- **gap_identification** (知识缺口识别): 是否明确指出证据不足或不确定的地方

**Observe示例**：
```python
{
  "stage": "Assess",
  "output": {
    "assessment": Assessment(...),
    "quality_score": 0.78,
    "identified_gaps": [...]
  },
  "evaluation": {
    "overall_score": 0.8,
    "dimension_scores": {
      "answer_completeness": 0.85,
      "reasoning_chain": 0.8,
      "logical_consistency": 0.9,
      "factor_coverage": 0.7,
      "gap_identification": 0.75
    },
    "pass": true,
    "issues": [
      {
        "severity": "minor",
        "dimension": "factor_coverage",
        "description": "未考虑患者依从性因素"
      }
    ],
    "summary": "整体推理链清晰，逻辑一致，基本回答了原始问题，但部分临床因素考虑不够充分"
  }
}
```

### 2.4 Observe的作用

Observe作为ReAct循环中的"观察"环节，将被输入到调度LLM进行下一步决策：
- **量化信息**（overall_score, dimension_scores）帮助快速判断质量
- **结构化问题**（issues）明确指出需要关注的具体缺陷
- **自然语言总结**（summary）提供整体评价和建议

---

**续：Part 2 - 调度决策机制**
