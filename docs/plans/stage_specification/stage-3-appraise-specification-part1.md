# Stage 3: Appraise - 证据评价规格说明 (Part 1)

**日期**: 2026-02-04
**阶段**: Appraise (证据评价)
**在流程中的位置**: 第三阶段

---

## 1. 核心职责

### 1.1 主要任务
对Acquire阶段获取的**证据列表**进行**质量评价**，使用GRADE系统评定证据等级，识别证据间的冲突，综合评价证据的可靠性。

### 1.2 为什么这个阶段重要？
- **质量保证**: 不是所有证据都可靠，需要评价研究设计、偏倚风险
- **证据分级**: GRADE系统提供标准化的证据质量评级
- **冲突识别**: 不同研究可能得出矛盾结论，需要识别和解释
- **推荐基础**: Apply阶段的推荐强度直接依赖于证据质量

### 1.3 不属于这个阶段的任务
- ❌ 生成临床推荐（这是Apply阶段的任务）
- ❌ 检索证据（这是Acquire阶段的任务）
- ❌ 评价最终推荐的整体质量（这是Assess阶段的任务）

---

## 2. 输入要求

### 2.1 输入数据结构

```python
from typing import List
from dataclasses import dataclass

@dataclass
class AppraiseInput:
    """Appraise阶段的输入"""

    evidence_list: List[Evidence]
    # 来自Acquire阶段的证据列表

    pico_query: PICOQuery
    # 原始PICO查询（用于评价相关性）
```

### 2.2 输入示例

```python
AppraiseInput(
    evidence_list=[
        Evidence(
            title="Low-dose aspirin for prevention of preeclampsia: meta-analysis",
            study_type="meta-analysis",
            abstract="...",
            ...
        ),
        Evidence(
            title="ASPRE trial: aspirin in high-risk pregnancy",
            study_type="RCT",
            abstract="...",
            ...
        ),
        # ... 更多证据
    ],
    pico_query=PICOQuery(
        patient="35岁初产妇，孕20周，血压140/90",
        intervention="低剂量阿司匹林",
        comparison="不使用或安慰剂",
        outcome="子痫前期发生率"
    )
)
```

### 2.3 输入质量要求
- 至少有3篇证据（来自Acquire阶段的保证）
- 每篇证据必须有标题和摘要
- 证据应该与PICO问题相关

---

## 3. 输出规格

### 3.1 输出数据结构

```python
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

class GradeLevel(Enum):
    """GRADE证据质量等级"""
    HIGH = "High"           # 高质量：进一步研究不太可能改变结论
    MODERATE = "Moderate"   # 中等质量：进一步研究可能改变结论
    LOW = "Low"             # 低质量：进一步研究很可能改变结论
    VERY_LOW = "Very Low"   # 极低质量：结论非常不确定

@dataclass
class BiasAssessment:
    """偏倚风险评估"""

    selection_bias: str  # "low" | "unclear" | "high"
    # 选择偏倚（随机化、分配隐藏）

    performance_bias: str  # "low" | "unclear" | "high"
    # 实施偏倚（盲法）

    detection_bias: str  # "low" | "unclear" | "high"
    # 测量偏倚（结局评价盲法）

    attrition_bias: str  # "low" | "unclear" | "high"
    # 失访偏倚（数据完整性）

    reporting_bias: str  # "low" | "unclear" | "high"
    # 报告偏倚（选择性报告）

    other_bias: Optional[str]
    # 其他偏倚（如资金来源、利益冲突）

    overall_risk: str  # "low" | "unclear" | "high"
    # 总体偏倚风险

    notes: Optional[str]
    # 评估说明

@dataclass
class EvidenceAppraisal:
    """单篇证据的评价结果"""

    evidence: Evidence
    # 原始证据

    grade_level: GradeLevel
    # GRADE质量等级

    bias_assessment: BiasAssessment
    # 偏倚风险评估

    relevance_to_pico: float
    # 与PICO问题的相关性（0.0-1.0）

    sample_size: Optional[int]
    # 样本量

    effect_size: Optional[Dict[str, Any]]
    # 效应量（如RR, OR, HR等）
    # 例如: {"RR": 0.62, "95%CI": [0.49, 0.78], "p": 0.001}

    key_findings: str
    # 关键发现摘要

    limitations: List[str]
    # 研究局限性

    strengths: List[str]
    # 研究优势

@dataclass
class ConflictAnalysis:
    """证据冲突分析"""

    has_conflict: bool
    # 是否存在冲突

    conflicting_evidence: Optional[List[str]]
    # 冲突的证据ID或标题

    conflict_description: Optional[str]
    # 冲突描述

    possible_reasons: Optional[List[str]]
    # 可能的原因（如人群差异、干预剂量不同、结局定义不同）

    resolution_strategy: Optional[str]
    # 解决策略（如按人群分层、按剂量分层、权重分析）

@dataclass
class AppraiseOutput:
    """Appraise阶段的完整输出"""

    appraisal_results: List[EvidenceAppraisal]
    # 每篇证据的评价结果

    grade_distribution: Dict[str, int]
    # GRADE等级分布
    # 例如: {"High": 3, "Moderate": 5, "Low": 2, "Very Low": 0}

    overall_evidence_quality: GradeLevel
    # 整体证据质量（通常取最低等级或加权平均）

    conflict_analysis: ConflictAnalysis
    # 证据冲突分析

    synthesis_summary: str
    # 证据综合总结

    confidence_in_evidence: float
    # 对证据的信心程度（0.0-1.0）

    recommendations_for_apply: Optional[str]
    # 给Apply阶段的建议
```

### 3.2 输出示例

```python
AppraiseOutput(
    appraisal_results=[
        EvidenceAppraisal(
            evidence=Evidence(title="Low-dose aspirin meta-analysis", ...),
            grade_level=GradeLevel.HIGH,
            bias_assessment=BiasAssessment(
                selection_bias="low",
                performance_bias="low",
                detection_bias="low",
                attrition_bias="low",
                reporting_bias="low",
                other_bias="low",
                overall_risk="low",
                notes="高质量meta-analysis，纳入15项RCT"
            ),
            relevance_to_pico=0.95,
            sample_size=15000,
            effect_size={"RR": 0.62, "95%CI": [0.49, 0.78], "p": 0.001},
            key_findings="低剂量阿司匹林可降低高危孕妇子痫前期风险38%",
            limitations=["部分研究未报告不良事件", "异质性中等(I²=45%)"],
            strengths=["样本量大", "研究质量高", "结果一致"]
        ),
        # ... 更多评价结果
    ],
    grade_distribution={"High": 3, "Moderate": 5, "Low": 2, "Very Low": 0},
    overall_evidence_quality=GradeLevel.MODERATE,
    conflict_analysis=ConflictAnalysis(
        has_conflict=False,
        conflicting_evidence=None,
        conflict_description=None,
        possible_reasons=None,
        resolution_strategy=None
    ),
    synthesis_summary="基于3项高质量和5项中等质量研究，低剂量阿司匹林可有效降低高危孕妇子痫前期风险，证据质量为中等。主要局限是部分研究样本量较小，且异质性存在。",
    confidence_in_evidence=0.78,
    recommendations_for_apply="可以给出强推荐，但需要注意个体化考虑和不良反应监测"
)
```

### 3.3 输出质量标准

**必须满足的要求**：
- 每篇证据都有GRADE评级
- 每篇证据都有偏倚风险评估
- 识别并分析证据冲突（如果存在）
- 提供证据综合总结

**建议满足的要求**：
- 偏倚评估详细且有依据
- 效应量提取准确（RR, OR, 95%CI等）
- 冲突分析深入，提供解决策略
- 给Apply阶段提供明确建议

---

## 4. Observe评价维度详解

Appraise阶段的observe包含5个评价维度，每个维度评分0.0-1.0。

### 4.1 维度1: grade_reasonableness (GRADE评分合理性)

**评价内容**: GRADE质量评级是否符合GRADE标准，评级依据是否充分。

**评分标准**:
- **1.0**: GRADE评级完全符合标准，依据充分，降级/升级理由明确
- **0.8**: GRADE评级基本合理，有少量可商榷之处
- **0.6**: GRADE评级大致合理，但有明显的不准确
- **0.4**: GRADE评级不够合理，多处不符合标准
- **0.2**: GRADE评级严重不当
- **0.0**: 没有进行GRADE评级或完全错误

**为什么重要**: GRADE是国际公认的证据质量评价标准，评级准确性直接影响推荐强度。

**GRADE评级要点**:
- **起点**: RCT从"高"开始，观察性研究从"低"开始
- **降级因素**: 偏倚风险、不一致性、间接性、不精确性、发表偏倚
- **升级因素**: 大效应量、剂量反应关系、混杂因素减弱效应

**典型问题**:
- **降级不足**: RCT有明显偏倚但仍评为"高"
- **降级过度**: 小的异质性就降两级
- **忽略升级**: 效应量很大(RR<0.5)但没有升级
- **依据不足**: 降级但没有说明原因

**触发的调度决策**:
- 如果 `grade_reasonableness < 0.6` → 可能需要回退重新评价

### 4.2 维度2: consistency (评估一致性)

**评价内容**: 对相似证据的评价是否一致，评价标准是否统一。

**评分标准**:
- **1.0**: 评价标准完全一致，相似研究得到相似评价
- **0.8**: 评价基本一致，有极少的不一致但可以解释
- **0.6**: 评价大致一致，但有一些不一致之处
- **0.4**: 评价不够一致，标准不统一
- **0.2**: 评价严重不一致
- **0.0**: 评价完全混乱

**为什么重要**: 一致性确保评价的公平性和可靠性，避免双重标准。

**典型问题**:
- **双重标准**: 两个相似的RCT，一个评为"高"，另一个评为"中"，但没有合理解释
- **偏倚评估不一致**: 相似的方法学缺陷，在不同研究中给出不同的偏倚评级
- **效应量解读不一致**: 相似的效应量，在不同研究中给出不同的解读

**触发的调度决策**:
- 如果 `consistency < 0.6` → 建议回退重新评价，统一标准

### 4.3 维度3: conflict_identification (冲突识别准确性)

**评价内容**: 是否正确识别了证据间的矛盾，冲突分析是否深入。

**评分标准**:
- **1.0**: 准确识别所有冲突，分析深入，提供解决策略
- **0.8**: 识别主要冲突，分析较深入
- **0.6**: 识别部分冲突，分析基本合理
- **0.4**: 遗漏重要冲突或分析不足
- **0.2**: 严重遗漏冲突或分析错误
- **0.0**: 完全没有识别冲突

**为什么重要**: 证据冲突是临床决策的关键挑战，需要识别并合理解释。

**什么是证据冲突**:
- **结论矛盾**: 一些研究支持干预有效，另一些研究认为无效
- **效应量差异大**: 不同研究的效应量相差很大（如RR从0.5到1.2）
- **亚组差异**: 在不同人群中效果不同

**冲突分析要点**:
- **识别冲突**: 明确指出哪些研究存在矛盾
- **分析原因**: 人群差异？剂量不同？方法学问题？
- **解决策略**: 分层分析？敏感性分析？权重调整？

**典型问题**:
- **遗漏冲突**: 明显的结论矛盾但没有识别
- **分析肤浅**: 只说"存在异质性"，没有深入分析原因
- **没有解决策略**: 识别了冲突但不知道如何处理

**触发的调度决策**:
- 如果 `conflict_identification < 0.6` 且存在明显冲突 → 可能需要回退重新分析

### 4.4 维度4: bias_assessment (偏倚风险评估)

**评价内容**: 偏倚风险评估是否充分，是否考虑了研究设计缺陷、利益冲突等。

**评分标准**:
- **1.0**: 偏倚评估非常充分，考虑了所有关键偏倚类型
- **0.8**: 偏倚评估较充分，考虑了主要偏倚类型
- **0.6**: 偏倚评估基本充分，但有遗漏
- **0.4**: 偏倚评估不足，遗漏重要偏倚
- **0.2**: 偏倚评估严重不足
- **0.0**: 没有进行偏倚评估

**为什么重要**: 偏倚会导致研究结果失真，必须识别和评估。

**关键偏倚类型**:
- **选择偏倚**: 随机化方法、分配隐藏
- **实施偏倚**: 盲法（患者、医生）
- **测量偏倚**: 结局评价盲法
- **失访偏倚**: 失访率、ITT分析
- **报告偏倚**: 选择性报告结局
- **其他偏倚**: 资金来源、利益冲突、提前终止

**典型问题**:
- **遗漏资金来源**: 药企资助的研究可能有偏倚
- **忽略失访**: 失访率>20%但没有评估影响
- **盲法评估不足**: 没有区分患者盲法和评价者盲法
- **没有考虑发表偏倚**: 阴性结果可能未发表

**触发的调度决策**:
- 如果 `bias_assessment < 0.6` 且 `severity="critical"` → 强制回退重新评估
- 如果 `bias_assessment < 0.7` 且 `severity="major"` → 软性Gate，LLM决策

### 4.5 维度5: synthesis_logic (证据综合逻辑性)

**评价内容**: 多个证据的整合是否合理，权重分配是否恰当，结论是否有充分支持。

**评分标准**:
- **1.0**: 证据综合非常合理，权重恰当，结论有充分支持
- **0.8**: 证据综合较合理，逻辑基本清晰
- **0.6**: 证据综合基本合理，但有一些逻辑问题
- **0.4**: 证据综合不够合理，逻辑有明显缺陷
- **0.2**: 证据综合严重不合理
- **0.0**: 没有进行证据综合或完全混乱

**为什么重要**: 单个研究可能有局限，需要综合多个证据得出可靠结论。

**证据综合要点**:
- **权重分配**: 高质量研究权重更大
- **一致性考虑**: 结果一致的证据更可信
- **样本量考虑**: 大样本研究更可靠
- **最新证据**: 新研究可能改变结论
- **冲突处理**: 如何处理矛盾的证据

**典型问题**:
- **权重不当**: 给低质量研究过高权重
- **忽略冲突**: 有矛盾证据但没有合理处理
- **过度推断**: 基于少量证据得出过强结论
- **忽略局限**: 没有考虑证据的局限性

**触发的调度决策**:
- 如果 `synthesis_logic < 0.6` → 可能需要回退重新综合证据

---

**续：Part 2 - 典型问题场景和实现建议**
