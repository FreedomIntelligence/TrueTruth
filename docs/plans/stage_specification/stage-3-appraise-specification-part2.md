# Stage 3: Appraise - 证据评价规格说明 (Part 2)

**日期**: 2026-02-04
**阶段**: Appraise (证据评价)
**续Part 1**

---

## 5. 典型问题场景

### 5.1 场景1: GRADE评级不合理

**问题表现**:
```python
# 输出
EvidenceAppraisal(
    evidence=Evidence(title="Small RCT with high attrition", ...),
    grade_level=GradeLevel.HIGH,  # 不合理！
    bias_assessment=BiasAssessment(
        attrition_bias="high",  # 失访率高
        overall_risk="high",
        ...
    ),
    sample_size=50,  # 样本量小
    ...
)
```

**Observe评价**:
```python
{
  "overall_score": 0.52,
  "dimension_scores": {
    "grade_reasonableness": 0.3,  # 很低
    "consistency": 0.7,
    "conflict_identification": 0.6,
    "bias_assessment": 0.7,
    "synthesis_logic": 0.5
  },
  "pass": false,
  "issues": [
    {
      "severity": "critical",
      "dimension": "grade_reasonableness",
      "description": "RCT存在高失访偏倚且样本量小，不应评为'高'质量，应降级至'中'或'低'"
    }
  ],
  "summary": "GRADE评级不符合标准，存在高偏倚风险的小样本RCT被评为高质量，需要重新评价"
}
```

**调度决策**:
- **硬性Gate**: critical issue → 强制回退到Appraise
- **原因**: GRADE评级错误会直接影响Apply阶段的推荐强度

### 5.2 场景2: 偏倚评估不充分

**问题表现**:
```python
# 输出
EvidenceAppraisal(
    evidence=Evidence(
        title="Industry-funded RCT",
        metadata={"funding": "Pharmaceutical Company X"}
    ),
    bias_assessment=BiasAssessment(
        selection_bias="low",
        performance_bias="low",
        detection_bias="low",
        attrition_bias="low",
        reporting_bias="low",
        other_bias=None,  # 没有评估资金来源偏倚！
        overall_risk="low",
        ...
    ),
    ...
)
```

**Observe评价**:
```python
{
  "overall_score": 0.64,
  "dimension_scores": {
    "grade_reasonableness": 0.7,
    "consistency": 0.8,
    "conflict_identification": 0.7,
    "bias_assessment": 0.5,  # 低分
    "synthesis_logic": 0.7
  },
  "pass": false,
  "issues": [
    {
      "severity": "critical",
      "dimension": "bias_assessment",
      "description": "未评估药企资助带来的潜在偏倚风险，这是重要的其他偏倚来源"
    }
  ],
  "summary": "偏倚评估不充分，遗漏了资金来源偏倚，需要补充评估"
}
```

**调度决策**:
- **硬性Gate**: critical issue → 强制回退到Appraise
- **原因**: 资金来源偏倚可能严重影响研究结果的可信度

### 5.3 场景3: 证据冲突未识别

**问题表现**:
```python
# 输出
AppraiseOutput(
    appraisal_results=[
        EvidenceAppraisal(
            key_findings="阿司匹林降低子痫前期风险50% (RR=0.5)",
            ...
        ),
        EvidenceAppraisal(
            key_findings="阿司匹林无显著效果 (RR=0.95, p=0.6)",
            ...
        ),
    ],
    conflict_analysis=ConflictAnalysis(
        has_conflict=False,  # 错误！明显有冲突
        ...
    ),
    ...
)
```

**Observe评价**:
```python
{
  "overall_score": 0.58,
  "dimension_scores": {
    "grade_reasonableness": 0.75,
    "consistency": 0.7,
    "conflict_identification": 0.3,  # 很低
    "bias_assessment": 0.7,
    "synthesis_logic": 0.5
  },
  "pass": false,
  "issues": [
    {
      "severity": "major",
      "dimension": "conflict_identification",
      "description": "存在明显的证据冲突（RR从0.5到0.95），但未识别和分析"
    },
    {
      "severity": "major",
      "dimension": "synthesis_logic",
      "description": "在存在冲突的情况下直接综合证据，缺乏合理的冲突处理策略"
    }
  ],
  "summary": "遗漏了明显的证据冲突，证据综合缺乏合理性，需要重新分析"
}
```

**调度决策**:
- **软性Gate**: 触发"major_issues"信号
- **LLM决策**: 回退到Appraise，要求识别冲突并分析原因

### 5.4 场景4: 证据综合逻辑不当

**问题表现**:
```python
# 输出
AppraiseOutput(
    appraisal_results=[
        EvidenceAppraisal(
            grade_level=GradeLevel.HIGH,
            sample_size=15000,
            key_findings="meta-analysis: RR=0.62",
            ...
        ),
        EvidenceAppraisal(
            grade_level=GradeLevel.LOW,
            sample_size=50,
            key_findings="small RCT: RR=1.2",
            ...
        ),
    ],
    overall_evidence_quality=GradeLevel.LOW,  # 不合理！
    synthesis_summary="证据质量低，效果不确定",  # 忽略了高质量大样本研究
    ...
)
```

**Observe评价**:
```python
{
  "overall_score": 0.61,
  "dimension_scores": {
    "grade_reasonableness": 0.8,
    "consistency": 0.75,
    "conflict_identification": 0.7,
    "bias_assessment": 0.75,
    "synthesis_logic": 0.4  # 很低
  },
  "pass": false,
  "issues": [
    {
      "severity": "major",
      "dimension": "synthesis_logic",
      "description": "给低质量小样本研究过高权重，忽略了高质量大样本meta-analysis的结论"
    }
  ],
  "summary": "证据综合逻辑不当，权重分配不合理，应以高质量证据为主"
}
```

**调度决策**:
- **软性Gate**: 触发"major_issues"信号
- **LLM决策**: 回退到Appraise，重新综合证据，合理分配权重

### 5.5 场景5: 证据评价成功

**问题表现**:
```python
# 输出
AppraiseOutput(
    appraisal_results=[
        EvidenceAppraisal(
            grade_level=GradeLevel.HIGH,
            bias_assessment=BiasAssessment(overall_risk="low", ...),
            key_findings="meta-analysis: RR=0.62 [0.49-0.78]",
            ...
        ),
        # ... 更多高质量评价
    ],
    grade_distribution={"High": 3, "Moderate": 5, "Low": 2},
    overall_evidence_quality=GradeLevel.MODERATE,
    conflict_analysis=ConflictAnalysis(
        has_conflict=True,
        conflict_description="两项研究在低危人群中未发现显著效果",
        possible_reasons=["人群风险水平不同", "样本量不足"],
        resolution_strategy="按风险分层分析，高危人群有效，低危人群证据不足"
    ),
    synthesis_summary="基于3项高质量和5项中等质量研究，低剂量阿司匹林在高危孕妇中可有效降低子痫前期风险，证据质量为中等。",
    confidence_in_evidence=0.78,
    ...
)
```

**Observe评价**:
```python
{
  "overall_score": 0.87,
  "dimension_scores": {
    "grade_reasonableness": 0.9,
    "consistency": 0.85,
    "conflict_identification": 0.9,
    "bias_assessment": 0.85,
    "synthesis_logic": 0.85
  },
  "pass": true,
  "issues": [
    {
      "severity": "minor",
      "dimension": "synthesis_logic",
      "description": "可以进一步量化不同质量证据的权重"
    }
  ],
  "summary": "GRADE评级合理，偏倚评估充分，冲突识别准确并提供解决策略，证据综合逻辑清晰，质量优秀"
}
```

**调度决策**:
- **LLM决策**: "proceed" → 继续到Apply阶段
- **原因**: 质量优秀，minor issue不影响整体

---

## 6. 与其他阶段的接口

### 6.1 从Acquire阶段接收的数据

```python
# Acquire阶段传递过来的
{
  "evidence_list": List[Evidence],
  "pico_query": PICOQuery
}
```

### 6.2 向Apply阶段传递的数据

```python
# Apply阶段需要的
{
  "appraisal_results": List[EvidenceAppraisal],  # 评价后的证据
  "overall_evidence_quality": GradeLevel,  # 整体证据质量
  "conflict_analysis": ConflictAnalysis,  # 冲突分析
  "synthesis_summary": str,  # 证据综合总结
  "confidence_in_evidence": float  # 信心程度
}
```

### 6.3 可能的回退场景

**回退到Acquire**:
- 发现证据质量普遍很低（多数为Very Low）
- 可能需要寻找更高质量的证据

**回退到Appraise自身**:
- GRADE评级不合理
- 偏倚评估不充分
- 证据冲突未识别或分析不当
- 证据综合逻辑有问题

---

## 7. 实现建议

### 7.1 对Appraise Agent实现者的建议

1. **使用标准化工具**:
   - Cochrane Risk of Bias工具（RCT）
   - ROBINS-I工具（观察性研究）
   - AMSTAR工具（系统评价）

2. **GRADE评级流程**:
   - 明确起点（RCT=高，观察性=低）
   - 系统评估降级因素
   - 考虑升级因素
   - 记录降级/升级理由

3. **偏倚评估要点**:
   - 逐项评估各类偏倚
   - 特别关注资金来源、利益冲突
   - 评估发表偏倚（如漏斗图）
   - 记录评估依据

4. **冲突识别策略**:
   - 比较效应量和置信区间
   - 检查异质性（I²统计量）
   - 分析可能原因（人群、剂量、方法学）
   - 提供解决策略（分层、敏感性分析）

5. **证据综合原则**:
   - 高质量证据权重更大
   - 大样本研究更可靠
   - 最新证据优先考虑
   - 结果一致性很重要
   - 明确说明综合逻辑

### 7.2 常见陷阱

- ❌ GRADE评级不遵循标准流程
- ❌ 偏倚评估流于形式，没有实质分析
- ❌ 忽略资金来源和利益冲突
- ❌ 遗漏明显的证据冲突
- ❌ 证据综合时权重分配不当
- ❌ 过度依赖单个研究
- ❌ 忽略证据的局限性

### 7.3 质量检查清单

在输出前，检查以下项目：
- [ ] 每篇证据都有GRADE评级
- [ ] GRADE评级符合标准（起点正确、降级/升级有依据）
- [ ] 偏倚评估完整（6类偏倚都评估）
- [ ] 特别评估了资金来源和利益冲突
- [ ] 识别了证据间的冲突（如果存在）
- [ ] 冲突分析深入，提供了解决策略
- [ ] 证据综合逻辑清晰，权重分配合理
- [ ] 整体证据质量评级合理
- [ ] 提供了给Apply阶段的建议

---

## 8. GRADE系统详解

### 8.1 GRADE评级起点

| 研究类型 | 起始等级 |
|---------|---------|
| 随机对照试验(RCT) | High |
| 观察性研究 | Low |
| 病例报告/专家意见 | Very Low |

### 8.2 降级因素（每个因素可降1-2级）

| 因素 | 说明 | 降级标准 |
|------|------|---------|
| 偏倚风险 | 研究设计或实施缺陷 | 严重偏倚降1级，非常严重降2级 |
| 不一致性 | 研究结果异质性大 | I²>50%或效应量差异大 |
| 间接性 | PICO与问题不完全匹配 | 人群/干预/结局有差异 |
| 不精确性 | 样本量小，置信区间宽 | CI跨越无效线或样本量<300 |
| 发表偏倚 | 阴性结果未发表 | 漏斗图不对称 |

### 8.3 升级因素（观察性研究可升级）

| 因素 | 说明 | 升级标准 |
|------|------|---------|
| 大效应量 | 效应非常显著 | RR<0.5或>2.0升1级，<0.2或>5.0升2级 |
| 剂量反应 | 存在剂量反应关系 | 明确的剂量-效应梯度 |
| 混杂因素 | 混杂因素会减弱效应 | 调整后效应更强 |

### 8.4 GRADE评级示例

**示例1: RCT降级**
```
起点: High (RCT)
- 偏倚风险: 失访率25%，降1级 → Moderate
- 不精确性: 样本量200，CI宽，降1级 → Low
最终: Low
```

**示例2: 观察性研究升级**
```
起点: Low (队列研究)
- 大效应量: RR=0.2，升1级 → Moderate
- 剂量反应: 明确梯度，升1级 → High
最终: High
```

---

## 9. 偏倚评估详解

### 9.1 Cochrane Risk of Bias工具（RCT）

| 偏倚类型 | 评估要点 | 判断标准 |
|---------|---------|---------|
| 选择偏倚 | 随机序列生成、分配隐藏 | 低风险：中央随机、密封信封 |
| 实施偏倚 | 患者和医生盲法 | 低风险：双盲且盲法维持良好 |
| 测量偏倚 | 结局评价盲法 | 低风险：评价者不知分组 |
| 失访偏倚 | 数据完整性、ITT分析 | 低风险：失访<10%且ITT分析 |
| 报告偏倚 | 选择性报告结局 | 低风险：预先注册且报告所有结局 |
| 其他偏倚 | 资金来源、提前终止等 | 低风险：无利益冲突 |

### 9.2 偏倚评估示例

**高质量RCT**:
```python
BiasAssessment(
    selection_bias="low",  # 中央随机，分配隐藏良好
    performance_bias="low",  # 双盲
    detection_bias="low",  # 结局评价者盲法
    attrition_bias="low",  # 失访率5%，ITT分析
    reporting_bias="low",  # 预先注册，报告所有结局
    other_bias="low",  # 无利益冲突
    overall_risk="low"
)
```

**有偏倚风险的RCT**:
```python
BiasAssessment(
    selection_bias="unclear",  # 随机方法未说明
    performance_bias="high",  # 开放标签，无盲法
    detection_bias="unclear",  # 未说明评价者是否盲法
    attrition_bias="high",  # 失访率22%
    reporting_bias="low",  # 报告完整
    other_bias="high",  # 药企资助，作者有利益冲突
    overall_risk="high"
)
```

---

## 10. 证据冲突处理策略

### 10.1 识别冲突

**定量指标**:
- 异质性检验：I² > 50%
- 效应量差异：置信区间不重叠
- 方向矛盾：有的RR<1，有的RR>1

**定性判断**:
- 结论矛盾：有的支持有效，有的认为无效
- 推荐不一致：不同指南给出不同推荐

### 10.2 分析原因

| 原因类别 | 具体原因 | 示例 |
|---------|---------|------|
| 人群差异 | 风险水平、年龄、种族 | 高危vs低危孕妇 |
| 干预差异 | 剂量、时机、疗程 | 75mg vs 150mg阿司匹林 |
| 结局差异 | 定义、测量方法 | 轻度vs重度子痫前期 |
| 方法学差异 | 研究设计、质量 | 高质量RCT vs 低质量观察性 |
| 随机误差 | 样本量小 | 小样本研究结果不稳定 |

### 10.3 解决策略

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| 分层分析 | 按人群/剂量分层 | 人群或干预差异导致的冲突 |
| 敏感性分析 | 排除低质量研究 | 方法学质量差异导致的冲突 |
| Meta回归 | 探索异质性来源 | 多因素导致的冲突 |
| 权重调整 | 高质量研究权重更大 | 研究质量参差不齐 |
| 保守结论 | 承认不确定性 | 无法解释的冲突 |

---

**文档版本**: v1.0
**最后更新**: 2026-02-04
