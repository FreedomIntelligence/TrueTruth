# Stage 5: Assess - 整体评估规格说明

**日期**: 2026-02-04
**阶段**: Assess (整体评估)
**在流程中的位置**: 第五阶段（最后阶段）

---

## 1. 核心职责

### 1.1 主要任务
对整个EBM 5A流程进行**整体质量评估**，检查从问题精炼到推荐生成的**完整推理链**是否逻辑一致、完整合理，识别知识缺口。

### 1.2 为什么这个阶段重要？
- **质量把关**: 最后一道质量检查，确保输出的推荐可靠
- **逻辑验证**: 检查整个推理链是否自洽，有无矛盾
- **完整性检查**: 确认是否完整回答了原始临床问题
- **知识缺口识别**: 明确指出证据不足或不确定的地方

### 1.3 不属于这个阶段的任务
- ❌ 生成新的推荐（这是Apply阶段的任务）
- ❌ 评价单个证据质量（这是Appraise阶段的任务）
- ❌ 检索证据（这是Acquire阶段的任务）

### 1.4 Assess与Appraise的区别

| 维度 | Appraise (证据评价) | Assess (整体评估) |
|------|-------------------|------------------|
| 评价对象 | 单个证据 | 整个推理链 |
| 评价标准 | GRADE、偏倚风险 | 逻辑一致性、完整性 |
| 关注点 | 证据质量 | 推理质量 |
| 有无ground truth | 无（自洽性评价） | 无（自洽性评价） |
| 输出 | 证据评级 | 整体质量评估 |

---

## 2. 输入要求

### 2.1 输入数据结构

```python
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class AssessInput:
    """Assess阶段的输入"""

    original_question: str
    # 用户的原始临床问题

    ask_output: AskOutput
    # Ask阶段的输出

    acquire_output: AcquireOutput
    # Acquire阶段的输出

    appraise_output: AppraiseOutput
    # Appraise阶段的输出

    apply_output: ApplyOutput
    # Apply阶段的输出

    execution_history: List[ExecutionNode]
    # 完整的执行历史（包括回退）
```

### 2.2 输入示例

```python
AssessInput(
    original_question="35岁初产妇，孕20周，血压140/90，是否应该使用阿司匹林预防子痫前期？",
    ask_output=AskOutput(...),
    acquire_output=AcquireOutput(...),
    appraise_output=AppraiseOutput(...),
    apply_output=ApplyOutput(...),
    execution_history=[...]
)
```

---

## 3. 输出规格

### 3.1 输出数据结构

```python
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class LogicalIssue:
    """逻辑问题"""

    issue_type: str
    # 问题类型（如"contradiction", "gap", "inconsistency"）

    severity: str  # "critical" | "major" | "minor"
    # 严重程度

    description: str
    # 问题描述

    location: str
    # 问题位置（如"Ask->Acquire", "Appraise->Apply"）

    impact: str
    # 影响说明

@dataclass
class KnowledgeGap:
    """知识缺口"""

    gap_type: str
    # 缺口类型（如"insufficient_evidence", "conflicting_evidence", "population_mismatch"）

    description: str
    # 缺口描述

    impact_on_recommendation: str
    # 对推荐的影响

    future_research_suggestion: Optional[str]
    # 未来研究建议

@dataclass
class QualityDimension:
    """质量维度评分"""

    dimension_name: str
    # 维度名称

    score: float  # 0.0-1.0
    # 评分

    justification: str
    # 评分理由

@dataclass
class AssessOutput:
    """Assess阶段的完整输出"""

    overall_quality_score: float  # 0.0-1.0
    # 整体质量评分

    dimension_scores: Dict[str, float]
    # 各维度评分
    # {
    #   "answer_completeness": 0.85,
    #   "reasoning_chain": 0.8,
    #   "logical_consistency": 0.9,
    #   "factor_coverage": 0.7,
    #   "gap_identification": 0.75
    # }

    pass_quality_threshold: bool
    # 是否通过质量阈值

    logical_issues: List[LogicalIssue]
    # 发现的逻辑问题

    knowledge_gaps: List[KnowledgeGap]
    # 识别的知识缺口

    strengths: List[str]
    # 推理链的优势

    weaknesses: List[str]
    # 推理链的弱点

    summary: str
    # 整体评估总结

    needs_backtrack: bool
    # 是否需要回退修正

    backtrack_suggestion: Optional[str]
    # 回退建议（如果需要）

    confidence_in_output: float  # 0.0-1.0
    # 对最终输出的信心程度
```

### 3.2 输出示例

```python
AssessOutput(
    overall_quality_score=0.83,
    dimension_scores={
        "answer_completeness": 0.85,
        "reasoning_chain": 0.82,
        "logical_consistency": 0.88,
        "factor_coverage": 0.75,
        "gap_identification": 0.8
    },
    pass_quality_threshold=True,
    logical_issues=[
        LogicalIssue(
            issue_type="minor_inconsistency",
            severity="minor",
            description="Ask阶段提到'孕20周'，但Apply阶段建议'孕12周前开始'，时间点略有不一致",
            location="Ask->Apply",
            impact="不影响推荐有效性，但需要向用户说明应尽早开始"
        )
    ],
    knowledge_gaps=[
        KnowledgeGap(
            gap_type="dosage_uncertainty",
            description="75mg vs 150mg的最佳剂量尚无定论",
            impact_on_recommendation="推荐给出了剂量范围（75-150mg），但无法明确最佳剂量",
            future_research_suggestion="需要头对头比较研究"
        )
    ],
    strengths=[
        "PICO结构完整，问题精炼准确",
        "证据数量充足且质量高（3项高质量meta-analysis）",
        "GRADE评级合理，偏倚评估充分",
        "推荐强度与证据质量匹配",
        "注意事项全面，包含禁忌症和监测要求"
    ],
    weaknesses=[
        "特殊人群（如极高危）的证据有限",
        "长期安全性数据不足"
    ],
    summary="整体推理链完整、逻辑清晰。从问题精炼到证据获取、评价、推荐生成，各环节质量良好。推荐有充分证据支持，强度合理，注意事项全面。存在的知识缺口已明确标识。可以输出给用户。",
    needs_backtrack=False,
    backtrack_suggestion=None,
    confidence_in_output=0.83
)
```

### 3.3 输出质量标准

**必须满足的要求**：
- 评估整个推理链的逻辑一致性
- 检查是否完整回答了原始问题
- 识别知识缺口
- 给出明确的质量评分和通过/不通过判断

**建议满足的要求**：
- 列出推理链的优势和弱点
- 如果质量不达标，给出回退建议
- 提供对最终输出的信心程度

---

## 4. Observe评价维度详解

Assess阶段的observe包含5个评价维度，每个维度评分0.0-1.0。

### 4.1 维度1: answer_completeness (问题回答完整性)

**评价内容**: 是否完整回答了用户的原始临床问题，有无遗漏关键方面。

**评分标准**:
- **1.0**: 完整回答了问题的所有方面
- **0.8**: 回答了问题的主要方面，有极少遗漏
- **0.6**: 回答了问题的核心，但有一些方面未涉及
- **0.4**: 回答不够完整，遗漏重要方面
- **0.2**: 回答严重不完整
- **0.0**: 基本没有回答问题

**为什么重要**: 用户提问是为了解决临床问题，不完整的回答无法满足需求。

**原始问题的关键要素**:
- **是否应该使用**: 推荐强度（强推荐/弱推荐/不推荐）
- **什么药物**: 具体药物名称和剂量
- **什么人群**: 是否适用于该患者特征
- **如何使用**: 用法用量、时机、疗程
- **注意什么**: 禁忌症、不良反应、监测

**典型问题**:
- **只回答"是否"**: 说"应该使用"但没说剂量和用法
- **遗漏人群特异性**: 没有说明是否适用于该患者的具体情况
- **缺少安全性信息**: 没有提及禁忌症和不良反应

**触发的调度决策**:
- 如果 `answer_completeness < 0.7` → 可能需要回退补充信息

### 4.2 维度2: reasoning_chain (推理链完整性)

**评价内容**: 从问题→证据→推荐的逻辑链是否完整，各环节是否衔接良好。

**评分标准**:
- **1.0**: 推理链非常完整，各环节衔接完美
- **0.8**: 推理链完整，衔接良好
- **0.6**: 推理链基本完整，但有一些跳跃
- **0.4**: 推理链不够完整，有明显断层
- **0.2**: 推理链严重不完整
- **0.0**: 推理链缺失

**为什么重要**: 完整的推理链确保推荐有据可依，可追溯、可审计。

**推理链检查点**:
1. **Ask→Acquire**: PICO是否有效指导了检索
2. **Acquire→Appraise**: 证据是否都得到了评价
3. **Appraise→Apply**: 推荐是否基于评价后的证据
4. **整体**: 推荐是否回答了原始问题

**典型问题**:
- **跳跃**: Ask阶段提到"高危人群"，但Acquire没有针对性检索
- **断层**: Appraise评价了10篇证据，但Apply只用了3篇
- **不一致**: Ask阶段关注"子痫前期"，但Apply推荐关注"早产"

**触发的调度决策**:
- 如果 `reasoning_chain < 0.7` → 可能需要回退修正断层

### 4.3 维度3: logical_consistency (逻辑一致性)

**评价内容**: 各部分之间是否存在矛盾，推理是否自洽。

**评分标准**:
- **1.0**: 完全一致，无任何矛盾
- **0.8**: 基本一致，有极少的小矛盾但可以解释
- **0.6**: 大致一致，但有一些矛盾
- **0.4**: 存在明显矛盾
- **0.2**: 存在严重矛盾
- **0.0**: 完全矛盾

**为什么重要**: 矛盾会降低推荐的可信度，可能误导临床决策。

**常见矛盾类型**:
- **人群矛盾**: Ask说"高危"，Apply说"所有孕妇"
- **剂量矛盾**: Appraise证据支持"75-150mg"，Apply推荐"50mg"
- **强度矛盾**: Appraise证据质量"中等"，Apply给"强推荐"
- **时机矛盾**: 证据是"孕12周前开始"，推荐是"孕20周开始"

**触发的调度决策**:
- 如果 `logical_consistency < 0.7` 且存在critical矛盾 → 强制回退修正

### 4.4 维度4: factor_coverage (关键因素覆盖度)

**评价内容**: 是否考虑了所有重要的临床因素（患者特征、禁忌症、不良反应、成本等）。

**评分标准**:
- **1.0**: 覆盖了所有重要因素
- **0.8**: 覆盖了主要因素，有极少遗漏
- **0.6**: 覆盖了核心因素，但有一些遗漏
- **0.4**: 因素覆盖不足，遗漏重要内容
- **0.2**: 因素覆盖严重不足
- **0.0**: 几乎没有考虑重要因素

**为什么重要**: 临床决策需要综合考虑多方面因素，遗漏可能导致不当决策。

**关键因素清单**:
- **患者特征**: 年龄、孕周、风险因素
- **禁忌症**: 绝对禁忌、相对禁忌
- **不良反应**: 常见和严重不良反应
- **药物相互作用**: 与其他药物的相互作用
- **特殊人群**: 肝肾功能不全、合并症
- **监测要求**: 需要监测的指标
- **患者偏好**: 患者的价值观和偏好
- **成本效益**: 经济学考虑（如果相关）

**典型问题**:
- **遗漏禁忌症**: 没有考虑"活动性出血"
- **忽略患者偏好**: 没有提及患者选择权
- **缺少监测**: 没有说明需要监测血小板
- **特殊人群考虑不足**: 没有考虑肝功能不全

**触发的调度决策**:
- 如果 `factor_coverage < 0.7` → 可能需要回退补充考虑因素

### 4.5 维度5: gap_identification (知识缺口识别)

**评价内容**: 是否明确指出了证据不足、不确定或存在争议的地方。

**评分标准**:
- **1.0**: 准确识别了所有知识缺口，说明清晰
- **0.8**: 识别了主要知识缺口
- **0.6**: 识别了部分知识缺口
- **0.4**: 知识缺口识别不足
- **0.2**: 几乎没有识别知识缺口
- **0.0**: 完全没有识别知识缺口

**为什么重要**: 明确知识缺口有助于：
- 让用户了解推荐的不确定性
- 避免过度自信
- 指导未来研究方向

**常见知识缺口类型**:
- **证据不足**: 某些方面缺乏研究
- **证据冲突**: 不同研究结论矛盾
- **人群不匹配**: 证据人群与患者不完全匹配
- **剂量不确定**: 最佳剂量尚无定论
- **长期效果未知**: 缺乏长期随访数据

**典型问题**:
- **假装确定**: 证据其实有争议，但推荐表现得很确定
- **遗漏不确定性**: 没有说明"最佳剂量尚无定论"
- **忽略人群差异**: 证据来自欧美人群，但没说明对亚洲人群的适用性

**触发的调度决策**:
- 如果 `gap_identification < 0.6` → 可能需要回退补充知识缺口说明

---

## 5. 典型问题场景

### 5.1 场景1: 问题回答不完整

**问题表现**:
```python
# 原始问题
"35岁初产妇，孕20周，血压140/90，是否应该使用阿司匹林预防子痫前期？"

# Apply输出
Recommendation(
    text="建议使用低剂量阿司匹林",
    # 没有说明剂量、用法、时机！
    ...
)
```

**Observe评价**:
```python
{
  "overall_score": 0.62,
  "dimension_scores": {
    "answer_completeness": 0.5,  # 低分
    "reasoning_chain": 0.7,
    "logical_consistency": 0.8,
    "factor_coverage": 0.6,
    "gap_identification": 0.7
  },
  "pass": false,
  "issues": [
    {
      "severity": "major",
      "dimension": "answer_completeness",
      "description": "推荐过于简略，缺少关键信息：具体剂量、用法、开始时机、疗程"
    }
  ],
  "summary": "推荐方向正确但信息不完整，无法指导临床实践，需要补充具体用法"
}
```

**调度决策**:
- **LLM决策**: 回退到Apply，补充具体信息

### 5.2 场景2: 推理链断层

**问题表现**:
```python
# Ask阶段
PICOQuery(patient="高危孕妇", ...)

# Acquire阶段
# 检索到的证据包含"普通孕妇"和"高危孕妇"的研究

# Appraise阶段
# 评价了所有证据，没有区分人群

# Apply阶段
Recommendation(text="建议所有孕妇使用阿司匹林", ...)
# 推荐扩大到"所有孕妇"，与Ask阶段的"高危"不一致
```

**Observe评价**:
```python
{
  "overall_score": 0.58,
  "dimension_scores": {
    "answer_completeness": 0.7,
    "reasoning_chain": 0.5,  # 低分
    "logical_consistency": 0.5,  # 低分
    "factor_coverage": 0.7,
    "gap_identification": 0.6
  },
  "pass": false,
  "issues": [
    {
      "severity": "major",
      "dimension": "reasoning_chain",
      "description": "推理链断层：Ask关注'高危孕妇'，但Apply推荐'所有孕妇'，缺乏支持这一扩展的证据分析"
    },
    {
      "severity": "major",
      "dimension": "logical_consistency",
      "description": "人群不一致：原始问题针对高危人群，最终推荐扩大到所有人群"
    }
  ],
  "summary": "推理链存在断层，推荐人群与原始问题不一致，需要回退修正"
}
```

**调度决策**:
- **LLM决策**: 回退到Apply或Appraise，按人群分层分析

### 5.3 场景3: 逻辑矛盾

**问题表现**:
```python
# Appraise阶段
overall_evidence_quality=GradeLevel.LOW  # 证据质量低

# Apply阶段
Recommendation(
    strength=RecommendationStrength.STRONG_FOR,  # 强推荐！
    # 矛盾：低质量证据不应给强推荐
    ...
)
```

**Observe评价**:
```python
{
  "overall_score": 0.54,
  "dimension_scores": {
    "answer_completeness": 0.75,
    "reasoning_chain": 0.7,
    "logical_consistency": 0.3,  # 很低
    "factor_coverage": 0.7,
    "gap_identification": 0.6
  },
  "pass": false,
  "issues": [
    {
      "severity": "critical",
      "dimension": "logical_consistency",
      "description": "严重矛盾：Appraise评定证据质量为'低'，但Apply给出'强推荐'，不符合GRADE原则"
    }
  ],
  "summary": "存在严重逻辑矛盾，推荐强度与证据质量不匹配，必须修正"
}
```

**调度决策**:
- **硬性Gate**: critical issue → 强制回退到Apply修正推荐强度

### 5.4 场景4: 知识缺口未识别

**问题表现**:
```python
# Appraise阶段发现
conflict_analysis=ConflictAnalysis(
    has_conflict=True,
    conflict_description="75mg vs 150mg剂量效果存在争议",
    ...
)

# Apply阶段
Recommendation(
    dosage_regimen=DosageRegimen(dosage="100mg/日"),  # 给了具体剂量
    # 但没有说明剂量选择的不确定性！
    ...
)

# Assess阶段
knowledge_gaps=[]  # 没有识别知识缺口！
```

**Observe评价**:
```python
{
  "overall_score": 0.68,
  "dimension_scores": {
    "answer_completeness": 0.8,
    "reasoning_chain": 0.75,
    "logical_consistency": 0.8,
    "factor_coverage": 0.7,
    "gap_identification": 0.4  # 很低
  },
  "pass": false,
  "issues": [
    {
      "severity": "major",
      "dimension": "gap_identification",
      "description": "未识别重要知识缺口：Appraise发现剂量存在争议，但Assess没有标识这一不确定性"
    }
  ],
  "summary": "推荐质量尚可，但未充分说明不确定性，用户可能误以为剂量选择很确定"
}
```

**调度决策**:
- **LLM决策**: 回退到Assess，补充知识缺口识别

### 5.5 场景5: 整体评估通过

**问题表现**:
```python
AssessOutput(
    overall_quality_score=0.85,
    dimension_scores={
        "answer_completeness": 0.88,
        "reasoning_chain": 0.85,
        "logical_consistency": 0.9,
        "factor_coverage": 0.8,
        "gap_identification": 0.82
    },
    pass_quality_threshold=True,
    logical_issues=[],  # 无严重问题
    knowledge_gaps=[...],  # 已识别
    strengths=[...],
    summary="整体推理链完整、逻辑清晰，可以输出",
    needs_backtrack=False,
    confidence_in_output=0.85
)
```

**Observe评价**:
```python
{
  "overall_score": 0.87,
  "dimension_scores": {
    "answer_completeness": 0.9,
    "reasoning_chain": 0.85,
    "logical_consistency": 0.9,
    "factor_coverage": 0.85,
    "gap_identification": 0.85
  },
  "pass": true,
  "issues": [],
  "summary": "整体评估质量优秀，推理链完整，逻辑一致，知识缺口已识别，可以输出给用户"
}
```

**调度决策**:
- **LLM决策**: "terminate" → 结束workflow，输出最终推荐

---

## 6. 与其他阶段的接口

### 6.1 从前面阶段接收的数据

```python
# 接收所有阶段的输出
{
  "original_question": str,
  "ask_output": AskOutput,
  "acquire_output": AcquireOutput,
  "appraise_output": AppraiseOutput,
  "apply_output": ApplyOutput,
  "execution_history": List[ExecutionNode]
}
```

### 6.2 输出给用户的数据

```python
# 最终输出
{
  "recommendation": Recommendation,  # 来自Apply
  "evidence_summary": str,  # 来自Appraise
  "quality_assessment": AssessOutput,  # 来自Assess
  "knowledge_gaps": List[KnowledgeGap]  # 来自Assess
}
```

### 6.3 可能的回退场景

**回退到Apply**:
- 推荐不完整或不具体
- 推荐强度与证据不匹配
- 注意事项不全

**回退到Appraise**:
- 发现证据综合有问题
- 逻辑矛盾源于证据评价

**回退到Acquire**:
- 发现证据严重不足
- 需要补充特定类型的证据

**回退到Ask**:
- 发现问题本身有歧义
- 需要重新精炼问题

---

## 7. 实现建议

### 7.1 对Assess Agent实现者的建议

1. **系统性检查**:
   - 逐个检查5个维度
   - 使用checklist确保不遗漏

2. **追溯推理链**:
   - 从原始问题开始
   - 逐步检查每个环节的衔接

3. **识别矛盾**:
   - 比较不同阶段的关键信息（人群、剂量、强度等）
   - 标记不一致之处

4. **知识缺口识别**:
   - 检查Appraise的冲突分析
   - 检查Apply的局限性说明
   - 补充遗漏的不确定性

5. **给出明确判断**:
   - 是否通过质量阈值
   - 是否需要回退
   - 如果回退，回退到哪里

### 7.2 常见陷阱

- ❌ 只关注Apply输出，忽略整个推理链
- ❌ 没有检查逻辑一致性
- ❌ 假装没有知识缺口
- ❌ 评价过于宽松，放过明显问题
- ❌ 评价过于严格，吹毛求疵

### 7.3 质量检查清单

在输出前，检查以下项目：
- [ ] 检查了问题回答的完整性
- [ ] 追溯了完整的推理链
- [ ] 检查了逻辑一致性（人群、剂量、强度等）
- [ ] 评估了关键因素覆盖度
- [ ] 识别了知识缺口
- [ ] 给出了明确的通过/不通过判断
- [ ] 如果不通过，给出了回退建议

---

**文档版本**: v1.0
**最后更新**: 2026-02-04
