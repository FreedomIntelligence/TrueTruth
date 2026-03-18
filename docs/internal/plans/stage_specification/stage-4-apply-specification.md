# Stage 4: Apply - 推荐生成规格说明

**日期**: 2026-02-04
**阶段**: Apply (推荐生成)
**在流程中的位置**: 第四阶段

---

## 1. 核心职责

### 1.1 主要任务
基于Appraise阶段评价后的证据，生成**具体的临床推荐**，包括推荐内容、强度等级、剂量方案、注意事项等。

### 1.2 为什么这个阶段重要？
- **临床实用性**: 将证据转化为可操作的临床建议
- **个性化**: 考虑患者特征，提供个性化推荐
- **安全性**: 明确禁忌症、不良反应、监测要求
- **可信度**: 推荐强度与证据质量相匹配

### 1.3 不属于这个阶段的任务
- ❌ 评价证据质量（这是Appraise阶段的任务）
- ❌ 评价整体推理链的完整性（这是Assess阶段的任务）
- ❌ 检索证据（这是Acquire阶段的任务）

---

## 2. 输入要求

### 2.1 输入数据结构

```python
from typing import List
from dataclasses import dataclass

@dataclass
class ApplyInput:
    """Apply阶段的输入"""

    appraisal_results: List[EvidenceAppraisal]
    # 来自Appraise阶段的评价结果

    overall_evidence_quality: GradeLevel
    # 整体证据质量

    conflict_analysis: ConflictAnalysis
    # 证据冲突分析

    synthesis_summary: str
    # 证据综合总结

    pico_query: PICOQuery
    # 原始PICO查询（用于生成针对性推荐）

    confidence_in_evidence: float
    # 对证据的信心程度
```

### 2.2 输入示例

```python
ApplyInput(
    appraisal_results=[
        EvidenceAppraisal(
            grade_level=GradeLevel.HIGH,
            key_findings="meta-analysis: RR=0.62 [0.49-0.78]",
            ...
        ),
        # ... 更多评价结果
    ],
    overall_evidence_quality=GradeLevel.MODERATE,
    conflict_analysis=ConflictAnalysis(has_conflict=False, ...),
    synthesis_summary="基于3项高质量和5项中等质量研究，低剂量阿司匹林在高危孕妇中可有效降低子痫前期风险",
    pico_query=PICOQuery(
        patient="35岁初产妇，孕20周，血压140/90",
        intervention="低剂量阿司匹林",
        ...
    ),
    confidence_in_evidence=0.78
)
```

---

## 3. 输出规格

### 3.1 输出数据结构

```python
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

class RecommendationStrength(Enum):
    """推荐强度"""
    STRONG_FOR = "强推荐使用"
    WEAK_FOR = "弱推荐使用"
    WEAK_AGAINST = "弱推荐不使用"
    STRONG_AGAINST = "强推荐不使用"
    INSUFFICIENT = "证据不足，无法推荐"

@dataclass
class DosageRegimen:
    """剂量方案"""

    drug_name: str
    # 药物名称

    dosage: str
    # 剂量（如"75-150mg/日"）

    route: str
    # 给药途径（如"口服"）

    frequency: str
    # 频率（如"每日一次"）

    timing: Optional[str]
    # 用药时机（如"孕12周前开始"）

    duration: Optional[str]
    # 疗程（如"持续至孕36周"）

@dataclass
class Contraindication:
    """禁忌症"""

    condition: str
    # 禁忌情况

    severity: str  # "absolute" | "relative"
    # 绝对禁忌或相对禁忌

    reason: str
    # 禁忌原因

@dataclass
class AdverseEvent:
    """不良反应"""

    event: str
    # 不良反应名称

    incidence: Optional[str]
    # 发生率（如"1-5%"）

    severity: str  # "mild" | "moderate" | "severe"
    # 严重程度

    management: Optional[str]
    # 处理建议

@dataclass
class MonitoringRequirement:
    """监测要求"""

    parameter: str
    # 监测指标（如"血压"、"血小板"）

    frequency: str
    # 监测频率（如"每2周一次"）

    action_threshold: Optional[str]
    # 行动阈值（如"血小板<100,000时停药"）

@dataclass
class SpecialPopulation:
    """特殊人群考虑"""

    population: str
    # 人群（如"肝功能不全"、"高龄"）

    recommendation: str
    # 针对该人群的建议

    evidence_level: Optional[str]
    # 该建议的证据等级

@dataclass
class ClinicalCalculation:
    """临床计算"""

    metric: str
    # 指标名称（如"NNT"、"ARR"）

    value: float
    # 计算值

    interpretation: str
    # 解释

@dataclass
class Recommendation:
    """临床推荐"""

    text: str
    # 推荐内容（简明扼要）

    strength: RecommendationStrength
    # 推荐强度

    evidence_quality: GradeLevel
    # 支持该推荐的证据质量

    rationale: str
    # 推荐理由（基于哪些证据）

    dosage_regimen: Optional[DosageRegimen]
    # 剂量方案（如果适用）

    contraindications: List[Contraindication]
    # 禁忌症

    adverse_events: List[AdverseEvent]
    # 不良反应

    monitoring: List[MonitoringRequirement]
    # 监测要求

    special_populations: List[SpecialPopulation]
    # 特殊人群考虑

    clinical_calculations: Optional[List[ClinicalCalculation]]
    # 临床计算（如NNT）

    alternatives: Optional[List[str]]
    # 替代方案

    patient_preferences: Optional[str]
    # 患者偏好考虑

@dataclass
class ApplyOutput:
    """Apply阶段的完整输出"""

    recommendation: Recommendation
    # 主要推荐

    evidence_summary: str
    # 支持推荐的证据摘要

    certainty_of_recommendation: float
    # 推荐的确定性（0.0-1.0）

    limitations: List[str]
    # 推荐的局限性

    future_research_needs: Optional[List[str]]
    # 未来研究需求
```

### 3.2 输出示例

```python
ApplyOutput(
    recommendation=Recommendation(
        text="建议35岁高危初产妇从孕12周前开始使用低剂量阿司匹林（75-150mg/日）预防子痫前期，持续至孕36周",
        strength=RecommendationStrength.STRONG_FOR,
        evidence_quality=GradeLevel.MODERATE,
        rationale="基于3项高质量meta-analysis和5项中等质量RCT，低剂量阿司匹林可降低高危孕妇子痫前期风险38%（RR=0.62, 95%CI 0.49-0.78），NNT=25",
        dosage_regimen=DosageRegimen(
            drug_name="阿司匹林",
            dosage="75-150mg/日",
            route="口服",
            frequency="每日一次",
            timing="孕12周前开始",
            duration="持续至孕36周"
        ),
        contraindications=[
            Contraindication(
                condition="阿司匹林过敏或不耐受",
                severity="absolute",
                reason="可能导致严重过敏反应"
            ),
            Contraindication(
                condition="活动性消化道出血或溃疡",
                severity="absolute",
                reason="阿司匹林可能加重出血"
            ),
            Contraindication(
                condition="血小板减少症（<100,000/μL）",
                severity="relative",
                reason="增加出血风险"
            )
        ],
        adverse_events=[
            AdverseEvent(
                event="消化道不适",
                incidence="5-10%",
                severity="mild",
                management="餐后服用，必要时使用胃保护剂"
            ),
            AdverseEvent(
                event="出血风险轻度增加",
                incidence="<1%",
                severity="moderate",
                management="监测血小板，出现异常出血立即停药"
            )
        ],
        monitoring=[
            MonitoringRequirement(
                parameter="血压",
                frequency="每2周一次产检时测量",
                action_threshold="血压≥140/90mmHg时加强监测"
            ),
            MonitoringRequirement(
                parameter="血小板计数",
                frequency="孕早期、中期、晚期各检查一次",
                action_threshold="<100,000/μL时考虑停药"
            )
        ],
        special_populations=[
            SpecialPopulation(
                population="肝功能不全患者",
                recommendation="轻度肝功能不全无需调整剂量，中重度肝功能不全慎用",
                evidence_level="专家共识"
            ),
            SpecialPopulation(
                population="同时使用抗凝药物",
                recommendation="需要权衡出血风险，建议专科会诊",
                evidence_level="专家共识"
            )
        ],
        clinical_calculations=[
            ClinicalCalculation(
                metric="NNT (Number Needed to Treat)",
                value=25,
                interpretation="需要治疗25名高危孕妇，可预防1例子痫前期"
            ),
            ClinicalCalculation(
                metric="ARR (Absolute Risk Reduction)",
                value=0.04,
                interpretation="绝对风险降低4%"
            )
        ],
        alternatives=["密切监测血压，不使用药物预防（适用于低危人群或有禁忌症者）"],
        patient_preferences="应告知患者预期获益和潜在风险，尊重患者选择"
    ),
    evidence_summary="证据来自3项高质量meta-analysis（纳入15,000+孕妇）和5项中等质量RCT。一致显示低剂量阿司匹林可降低高危孕妇子痫前期风险约38%，安全性良好。",
    certainty_of_recommendation=0.82,
    limitations=[
        "部分研究未详细报告不良事件",
        "最佳剂量（75mg vs 150mg）尚无定论",
        "对极高危人群（如既往重度子痫前期）的效果证据有限"
    ],
    future_research_needs=[
        "不同剂量的头对头比较研究",
        "极高危人群的专门研究",
        "长期安全性（儿童发育）的随访研究"
    ]
)
```

### 3.3 输出质量标准

**必须满足的要求**：
- 推荐内容明确、具体、可操作
- 推荐强度与证据质量相匹配
- 包含剂量方案（如果适用）
- 列出主要禁忌症和不良反应
- 提供监测建议

**建议满足的要求**：
- 提供临床计算（如NNT）
- 考虑特殊人群
- 提供替代方案
- 说明推荐的局限性
- 考虑患者偏好

---

## 4. Observe评价维度详解

Apply阶段的observe包含5个评价维度，每个维度评分0.0-1.0。

### 4.1 维度1: evidence_alignment (证据-推荐匹配度)

**评价内容**: 推荐是否有充分证据支持，是否过度推断或保守不足。

**评分标准**:
- **1.0**: 推荐与证据完美匹配，既不过度推断也不过于保守
- **0.8**: 推荐与证据基本匹配，有极少的不一致
- **0.6**: 推荐与证据大致匹配，但有一些不够精确之处
- **0.4**: 推荐与证据匹配度不足，有明显的过度推断或过于保守
- **0.2**: 推荐与证据严重不匹配
- **0.0**: 推荐完全没有证据支持

**为什么重要**: 推荐必须基于证据，过度推断可能误导临床，过于保守可能错失治疗机会。

**典型问题**:
- **过度推断**: 证据只支持"高危人群有效"，但推荐"所有孕妇使用"
- **过于保守**: 证据质量高且效果显著，但只给"弱推荐"
- **人群不匹配**: 证据来自"孕早期开始用药"，但推荐"孕中期开始"
- **剂量不匹配**: 证据支持"75-150mg"，但推荐"50mg"

**触发的调度决策**:
- 如果 `evidence_alignment < 0.6` → 可能需要回退调整推荐

### 4.2 维度2: strength_appropriateness (推荐强度合理性)

**评价内容**: 推荐强度是否与证据质量、效应量、风险收益比相匹配。

**评分标准**:
- **1.0**: 推荐强度完全合理，与证据质量和效应量完美匹配
- **0.8**: 推荐强度基本合理，有小的可商榷之处
- **0.6**: 推荐强度大致合理，但不够精确
- **0.4**: 推荐强度不够合理，与证据质量不匹配
- **0.2**: 推荐强度严重不当
- **0.0**: 推荐强度完全错误

**为什么重要**: 推荐强度指导临床决策的确定性，强度不当会误导医生和患者。

**推荐强度判断原则**:

| 证据质量 | 效应量 | 风险收益比 | 推荐强度 |
|---------|--------|-----------|---------|
| High | 大(RR<0.5) | 明显获益 | 强推荐 |
| Moderate | 中等(RR 0.5-0.8) | 获益>风险 | 强推荐或弱推荐 |
| Low | 小(RR 0.8-0.95) | 获益略大于风险 | 弱推荐 |
| Very Low | 不确定 | 不确定 | 证据不足 |

**典型问题**:
- **强度过高**: 证据质量低但给"强推荐"
- **强度过低**: 证据质量高、效应量大但只给"弱推荐"
- **忽略风险**: 效应量大但不良反应严重，不应给"强推荐"

**触发的调度决策**:
- 如果 `strength_appropriateness < 0.6` → 可能需要回退调整推荐强度

### 4.3 维度3: calculation_accuracy (计算准确性)

**评价内容**: 临床计算（如NNT、ARR、RR等）是否准确。

**评分标准**:
- **1.0**: 所有计算完全准确
- **0.8**: 计算基本准确，有极小的舍入误差
- **0.6**: 计算大致准确，但有一些小错误
- **0.4**: 计算有明显错误
- **0.2**: 计算严重错误
- **0.0**: 没有进行计算或完全错误

**为什么重要**: 临床计算帮助医生和患者理解治疗的实际效果，错误的计算会误导决策。

**常见临床计算**:
- **NNT (Number Needed to Treat)**: 需要治疗多少人才能预防1例不良结局
- **ARR (Absolute Risk Reduction)**: 绝对风险降低
- **RRR (Relative Risk Reduction)**: 相对风险降低
- **NNH (Number Needed to Harm)**: 需要治疗多少人会出现1例不良反应

**计算示例**:
```
对照组风险: 20%
干预组风险: 12%
ARR = 20% - 12% = 8% = 0.08
NNT = 1 / ARR = 1 / 0.08 = 12.5 ≈ 13
RR = 12% / 20% = 0.6
RRR = (20% - 12%) / 20% = 40%
```

**典型问题**:
- **NNT计算错误**: 用RR而非ARR计算
- **单位错误**: 百分比和小数混用
- **解释错误**: NNT=25理解为"25%有效"

**触发的调度决策**:
- 如果 `calculation_accuracy < 0.8` → 可能需要回退修正计算

### 4.4 维度4: caveat_completeness (注意事项完整性)

**评价内容**: 禁忌症、不良反应、特殊人群考虑、监测要求是否充分。

**评分标准**:
- **1.0**: 注意事项非常完整，涵盖所有重要方面
- **0.8**: 注意事项较完整，涵盖主要方面
- **0.6**: 注意事项基本完整，但有一些遗漏
- **0.4**: 注意事项不够完整，遗漏重要内容
- **0.2**: 注意事项严重不足
- **0.0**: 没有提供注意事项

**为什么重要**: 注意事项关系到用药安全，遗漏可能导致严重后果。

**必须包含的注意事项**:
- **禁忌症**: 绝对禁忌和相对禁忌
- **不良反应**: 常见和严重不良反应
- **药物相互作用**: 与其他药物的相互作用
- **特殊人群**: 肝肾功能不全、老年人、儿童等
- **监测要求**: 需要监测的指标和频率

**典型问题**:
- **遗漏禁忌症**: 没有提及"活动性出血"是阿司匹林的禁忌症
- **不良反应不全**: 只提到"消化道不适"，没提"出血风险"
- **特殊人群考虑不足**: 没有考虑肝功能不全患者的剂量调整
- **缺少监测建议**: 没有说明需要监测血小板

**触发的调度决策**:
- 如果 `caveat_completeness < 0.7` → 可能需要回退补充注意事项

### 4.5 维度5: actionability (临床可操作性)

**评价内容**: 推荐是否具体、明确、可执行，临床医生能否直接应用。

**评分标准**:
- **1.0**: 推荐非常具体明确，可以直接执行
- **0.8**: 推荐较具体，基本可以执行
- **0.6**: 推荐大致明确，但需要一些补充信息
- **0.4**: 推荐不够具体，难以直接执行
- **0.2**: 推荐非常模糊
- **0.0**: 推荐完全无法执行

**为什么重要**: 推荐的目的是指导临床实践，模糊的推荐无法落地。

**可操作性要素**:
- **明确的药物名称**: "阿司匹林"而非"抗血小板药物"
- **具体的剂量**: "75-150mg/日"而非"低剂量"
- **明确的时机**: "孕12周前开始"而非"孕早期"
- **明确的疗程**: "持续至孕36周"而非"长期使用"
- **具体的监测**: "每2周测血压"而非"定期监测"

**典型问题**:
- **剂量模糊**: "低剂量阿司匹林" → 应该明确"75-150mg/日"
- **时机不明**: "尽早开始" → 应该明确"孕12周前"
- **监测不具体**: "定期监测" → 应该明确"每2周一次"
- **缺少操作细节**: 没有说明"餐后服用"等细节

**触发的调度决策**:
- 如果 `actionability < 0.7` → 可能需要回退补充具体信息

---

**续：典型问题场景和实现建议将在下一部分**
