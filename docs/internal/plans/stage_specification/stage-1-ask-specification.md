# Stage 1: Ask - 问题精炼规格说明

**日期**: 2026-02-04
**阶段**: Ask (问题精炼)
**在流程中的位置**: 第一阶段

---

## 1. 核心职责

### 1.1 主要任务
将用户提出的**自然语言临床问题**转化为**结构化的PICO查询**和**可用于检索的关键词**。

### 1.2 为什么这个阶段重要？
- **决定检索方向**: 问题精炼的质量直接影响后续能否找到相关证据
- **避免歧义**: 临床问题往往包含模糊表述，需要明确化
- **提高检索效率**: 准确的关键词和术语可以减少无关结果
- **奠定推理基础**: 清晰的PICO结构是整个EBM流程的起点

### 1.3 不属于这个阶段的任务
- ❌ 实际执行文献检索（这是Acquire阶段的任务）
- ❌ 评价证据质量（这是Appraise阶段的任务）
- ❌ 生成临床推荐（这是Apply阶段的任务）

---

## 2. 输入要求

### 2.1 输入数据结构

```python
{
  "original_question": str,  # 用户的原始临床问题
  "context": Optional[Dict[str, Any]]  # 可选的额外上下文信息
}
```

### 2.2 输入示例

**示例1: 简单问题**
```python
{
  "original_question": "孕妇可以用阿司匹林预防子痫前期吗？",
  "context": None
}
```

**示例2: 包含上下文的问题**
```python
{
  "original_question": "我有一个35岁的初产妇患者，孕20周，血压140/90，是否应该使用阿司匹林预防子痫前期？",
  "context": {
    "patient_age": 35,
    "gestational_age": "20周",
    "blood_pressure": "140/90",
    "parity": "初产"
  }
}
```

### 2.3 输入质量要求
- 问题应该是完整的句子或问句
- 至少包含基本的临床情境（患者特征或干预措施）
- 如果问题过于简单（如"阿司匹林"），需要通过交互获取更多信息

---

## 3. 输出规格

### 3.1 输出数据结构

```python
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class PICOQuery:
    """结构化的PICO查询"""

    patient: str
    # Patient/Population - 患者或人群特征
    # 示例: "35岁初产妇，孕20周，血压140/90"

    intervention: str
    # Intervention - 干预措施
    # 示例: "低剂量阿司匹林（75-150mg/日）"

    comparison: str
    # Comparison - 对照措施
    # 示例: "不使用或安慰剂"

    outcome: str
    # Outcome - 关注的结局
    # 示例: "子痫前期发生率、母婴安全性"

    keywords: List[str]
    # 提取的搜索关键词（英文）
    # 示例: ["aspirin", "preeclampsia", "prevention", "pregnancy"]

    mesh_terms: Optional[List[str]]
    # MeSH术语ID（如果能映射）
    # 示例: ["D001241", "D011225"]

    clinical_context: Optional[str]
    # 额外的临床背景信息
    # 示例: "患者为高危人群（高龄初产、血压偏高）"

@dataclass
class AskOutput:
    """Ask阶段的完整输出"""

    pico_query: PICOQuery
    # 结构化的PICO查询

    search_keywords: List[str]
    # 用于检索的关键词列表（可能比PICO.keywords更详细）

    search_strategy_notes: Optional[str]
    # 检索策略建议（给Acquire阶段的提示）
    # 示例: "建议重点检索系统评价和RCT研究"

    clarifications: Optional[List[str]]
    # 如果原始问题有歧义，记录做出的假设或澄清
    # 示例: ["假设患者无阿司匹林过敏史", "假设关注的是预防性用药而非治疗"]
```

### 3.2 输出示例

```python
AskOutput(
    pico_query=PICOQuery(
        patient="35岁初产妇，孕20周，血压140/90（子痫前期高危人群）",
        intervention="低剂量阿司匹林（75-150mg/日）",
        comparison="不使用阿司匹林或使用安慰剂",
        outcome="子痫前期发生率、严重子痫前期、母婴不良结局",
        keywords=["aspirin", "preeclampsia", "prevention", "pregnancy", "high-risk"],
        mesh_terms=["D001241", "D011225", "D011247"],
        clinical_context="患者为子痫前期高危人群（高龄初产、血压偏高），符合预防性用药指征"
    ),
    search_keywords=[
        "aspirin", "acetylsalicylic acid",
        "preeclampsia", "pre-eclampsia", "pregnancy-induced hypertension",
        "prevention", "prophylaxis",
        "pregnancy", "pregnant women",
        "high-risk pregnancy"
    ],
    search_strategy_notes="建议优先检索系统评价和meta-analysis，其次是大样本RCT研究。关注2015年后的研究（ASPRE试验后）。",
    clarifications=[
        "假设患者无阿司匹林禁忌症（如过敏、出血倾向）",
        "关注的是预防性用药，而非已发生子痫前期后的治疗"
    ]
)
```

### 3.3 输出质量标准

**必须满足的要求**：
- PICO四个要素都必须明确填写（不能为空或"未知"）
- 至少提供3个有效的英文搜索关键词
- 关键词应该是医学术语，而非日常用语

**建议满足的要求**：
- 提供MeSH术语映射（提高检索精度）
- 包含同义词和变体（如"preeclampsia"和"pre-eclampsia"）
- 提供检索策略建议（帮助Acquire阶段）

---

## 4. Observe评价维度详解

Ask阶段的observe包含5个评价维度，每个维度评分0.0-1.0。

### 4.1 维度1: pico_completeness (PICO完整性)

**评价内容**: PICO四个要素是否都明确提取，是否有遗漏或模糊之处。

**评分标准**:
- **1.0**: P/I/C/O四个要素都非常明确，包含必要的细节
- **0.8**: 四个要素都有，但某些要素略显简单或缺少细节
- **0.6**: 四个要素都有，但有1-2个要素比较模糊
- **0.4**: 缺少1个要素，或多个要素非常模糊
- **0.2**: 缺少2个或以上要素
- **0.0**: PICO结构基本缺失

**为什么重要**: PICO是EBM的基础框架，任何要素缺失都会导致检索方向偏差。

**典型问题**:
- **Patient不明确**: "孕妇" → 应该明确孕周、是否高危等
- **Comparison缺失**: 只说"用阿司匹林"，没说对照是什么
- **Outcome模糊**: "效果" → 应该明确是"子痫前期发生率"还是"母婴死亡率"

**触发的调度决策**:
- 如果 `pico_completeness < 0.5` 且 `severity="critical"` → 可能需要回退到Ask重新精炼
- 如果 `pico_completeness < 0.7` 且 `severity="major"` → 软性Gate触发，LLM决策是否回退

### 4.2 维度2: searchability (可搜索性)

**评价内容**: 提取的关键词是否足够具体，能否有效用于文献检索。

**评分标准**:
- **1.0**: 关键词非常具体，包含同义词和变体，适合检索
- **0.8**: 关键词合理，但可能缺少一些同义词
- **0.6**: 关键词过于宽泛或过于狭窄
- **0.4**: 关键词不够准确，可能导致大量无关结果
- **0.2**: 关键词严重不当
- **0.0**: 没有提供有效关键词

**为什么重要**: 关键词质量直接决定Acquire阶段能否找到相关文献。

**典型问题**:
- **过于宽泛**: "pregnancy" → 应该加上"high-risk pregnancy"
- **过于狭窄**: 只用"ASPRE trial" → 会遗漏其他相关研究
- **术语不规范**: 用"高血压"而非"hypertension"（英文检索）
- **缺少同义词**: 只有"preeclampsia"，没有"pre-eclampsia"或"pregnancy-induced hypertension"

**触发的调度决策**:
- 如果 `searchability < 0.6` → 可能导致Acquire阶段检索结果不佳，建议回退优化关键词

### 4.3 维度3: terminology_accuracy (术语准确性)

**评价内容**: 使用的医学术语是否规范，是否正确映射到标准术语（如MeSH）。

**评分标准**:
- **1.0**: 术语完全规范，正确映射到MeSH，无歧义
- **0.8**: 术语基本规范，有MeSH映射，但可能有小的不准确
- **0.6**: 术语可以理解，但不够规范或MeSH映射不完整
- **0.4**: 术语使用不当，可能导致误解
- **0.2**: 术语严重错误
- **0.0**: 完全没有使用医学术语

**为什么重要**: 规范的术语确保检索的准确性，避免因术语问题遗漏重要文献。

**典型问题**:
- **术语混淆**: "子痫"和"子痫前期"是不同的概念
- **缺少MeSH映射**: 没有将"aspirin"映射到MeSH: D001241
- **使用俗称**: "妊高症"而非规范的"妊娠期高血压疾病"

**触发的调度决策**:
- 如果 `terminology_accuracy < 0.6` → 可能影响检索质量，建议回退修正术语

### 4.4 维度4: clarity (问题明确性)

**评价内容**: 精炼后的问题是否清晰无歧义，是否还存在需要澄清的地方。

**评分标准**:
- **1.0**: 问题完全明确，无任何歧义
- **0.8**: 问题基本明确，有极少的假设但已说明
- **0.6**: 问题大致明确，但有一些未澄清的假设
- **0.4**: 问题仍有明显歧义
- **0.2**: 问题非常模糊
- **0.0**: 问题完全不清楚

**为什么重要**: 歧义会导致后续阶段的方向偏差，影响最终推荐的准确性。

**典型问题**:
- **剂量不明**: "阿司匹林" → 应该明确"低剂量（75-150mg）"还是"常规剂量"
- **时机不明**: "预防子痫前期" → 应该明确是"孕早期开始"还是"孕中期"
- **人群不明**: "孕妇" → 应该明确是"所有孕妇"还是"高危孕妇"

**触发的调度决策**:
- 如果 `clarity < 0.6` 且存在major issues → 可能需要回退澄清问题

### 4.5 维度5: clinical_context (临床背景充分性)

**评价内容**: 是否包含必要的患者特征、临床情境，是否足以支持后续的证据应用。

**评分标准**:
- **1.0**: 临床背景非常充分，包含所有关键患者特征
- **0.8**: 临床背景较充分，包含主要患者特征
- **0.6**: 临床背景基本够用，但缺少一些有用信息
- **0.4**: 临床背景不足，缺少重要信息
- **0.2**: 临床背景严重不足
- **0.0**: 几乎没有临床背景信息

**为什么重要**: 充分的临床背景有助于：
- 在Acquire阶段筛选更相关的证据
- 在Apply阶段生成更个性化的推荐
- 识别特殊人群的注意事项

**典型问题**:
- **缺少患者特征**: 没有提及年龄、孕周、既往史
- **缺少风险因素**: 没有说明是否为高危人群
- **缺少禁忌症信息**: 没有考虑患者是否有用药禁忌

**触发的调度决策**:
- 如果 `clinical_context < 0.5` → 可能影响Apply阶段的推荐质量，但通常不需要回退（可以在Apply阶段补充通用注意事项）

---

## 5. 典型问题场景

### 5.1 场景1: PICO要素缺失

**问题表现**:
```python
# 输出
PICOQuery(
    patient="孕妇",  # 太模糊
    intervention="阿司匹林",
    comparison="",  # 缺失！
    outcome="预防子痫前期",
    keywords=["aspirin", "pregnancy"]
)
```

**Observe评价**:
```python
{
  "overall_score": 0.45,
  "dimension_scores": {
    "pico_completeness": 0.4,  # 低分
    "searchability": 0.5,
    "terminology_accuracy": 0.6,
    "clarity": 0.4,
    "clinical_context": 0.3
  },
  "pass": false,
  "issues": [
    {
      "severity": "critical",
      "dimension": "pico_completeness",
      "description": "Comparison要素缺失，无法明确对照组是什么"
    },
    {
      "severity": "major",
      "dimension": "clinical_context",
      "description": "患者特征过于模糊，缺少孕周、风险因素等关键信息"
    }
  ],
  "summary": "PICO结构不完整，Comparison缺失，患者特征不明确，需要重新精炼问题"
}
```

**调度决策**:
- **硬性Gate**: 检测到critical issue → 强制回退到Ask
- **或者**: 如果系统支持交互，可以向用户询问缺失信息

### 5.2 场景2: 关键词不够具体

**问题表现**:
```python
# 输出
AskOutput(
    pico_query=PICOQuery(...),  # PICO结构完整
    search_keywords=["pregnancy", "drug", "prevention"],  # 太宽泛！
    ...
)
```

**Observe评价**:
```python
{
  "overall_score": 0.65,
  "dimension_scores": {
    "pico_completeness": 0.85,
    "searchability": 0.5,  # 低分
    "terminology_accuracy": 0.6,
    "clarity": 0.75,
    "clinical_context": 0.7
  },
  "pass": false,
  "issues": [
    {
      "severity": "major",
      "dimension": "searchability",
      "description": "关键词过于宽泛（'pregnancy', 'drug'），会导致大量无关检索结果"
    },
    {
      "severity": "minor",
      "dimension": "terminology_accuracy",
      "description": "缺少MeSH术语映射"
    }
  ],
  "summary": "PICO结构完整，但关键词过于宽泛，建议细化为具体的药物名称和疾病名称"
}
```

**调度决策**:
- **软性Gate**: 触发"major_issues"信号
- **LLM决策**: 权衡是否回退
  - 如果回退成本低 → 回退到Ask优化关键词
  - 如果继续 → Acquire阶段可能检索到大量无关文献，需要更多筛选工作

### 5.3 场景3: 术语使用不规范

**问题表现**:
```python
# 输出
PICOQuery(
    patient="怀孕的女性",
    intervention="阿司匹林药物",
    comparison="不吃药",
    outcome="不得妊高症",  # 术语不规范
    keywords=["怀孕", "阿司匹林", "妊高症"],  # 中文关键词！
    mesh_terms=None
)
```

**Observe评价**:
```python
{
  "overall_score": 0.55,
  "dimension_scores": {
    "pico_completeness": 0.7,
    "searchability": 0.3,  # 很低
    "terminology_accuracy": 0.4,  # 很低
    "clarity": 0.6,
    "clinical_context": 0.7
  },
  "pass": false,
  "issues": [
    {
      "severity": "critical",
      "dimension": "searchability",
      "description": "关键词使用中文，无法用于英文文献检索"
    },
    {
      "severity": "major",
      "dimension": "terminology_accuracy",
      "description": "术语不规范：'妊高症'应为'妊娠期高血压疾病'或'子痫前期'"
    }
  ],
  "summary": "术语使用严重不规范，关键词为中文无法检索，必须重新精炼"
}
```

**调度决策**:
- **硬性Gate**: critical issue → 强制回退到Ask
- **原因**: 中文关键词无法用于PubMed检索，必须修正

### 5.4 场景4: 问题精炼成功

**问题表现**:
```python
# 输出
AskOutput(
    pico_query=PICOQuery(
        patient="35岁初产妇，孕20周，血压140/90（子痫前期高危人群）",
        intervention="低剂量阿司匹林（75-150mg/日）",
        comparison="不使用阿司匹林或使用安慰剂",
        outcome="子痫前期发生率、严重子痫前期、母婴不良结局",
        keywords=["aspirin", "preeclampsia", "prevention", "pregnancy", "high-risk"],
        mesh_terms=["D001241", "D011225", "D011247"],
        clinical_context="患者为子痫前期高危人群"
    ),
    search_keywords=[
        "aspirin", "acetylsalicylic acid",
        "preeclampsia", "pre-eclampsia",
        "prevention", "prophylaxis",
        "pregnancy", "pregnant women",
        "high-risk pregnancy"
    ],
    search_strategy_notes="建议优先检索系统评价和RCT研究",
    clarifications=["假设患者无阿司匹林禁忌症"]
)
```

**Observe评价**:
```python
{
  "overall_score": 0.88,
  "dimension_scores": {
    "pico_completeness": 0.9,
    "searchability": 0.85,
    "terminology_accuracy": 0.9,
    "clarity": 0.9,
    "clinical_context": 0.85
  },
  "pass": true,
  "issues": [
    {
      "severity": "minor",
      "dimension": "searchability",
      "description": "可以考虑添加'ASPRE'作为关键词（重要临床试验名称）"
    }
  ],
  "summary": "PICO结构完整，关键词准确且包含同义词，术语规范，临床背景充分，质量优秀"
}
```

**调度决策**:
- **LLM决策**: "proceed" → 继续到Acquire阶段
- **原因**: 质量优秀，minor issue不影响整体，可以继续

---

## 6. 与其他阶段的接口

### 6.1 向Acquire阶段传递的数据

```python
# Acquire阶段需要的输入
{
  "pico_query": PICOQuery,  # 完整的PICO结构
  "search_keywords": List[str],  # 搜索关键词
  "search_strategy_notes": Optional[str]  # 检索策略建议
}
```

### 6.2 Acquire阶段对Ask输出的期望

- **必须有**: 明确的PICO结构、至少3个有效关键词
- **最好有**: MeSH术语、同义词列表、检索策略建议
- **质量要求**: `overall_score >= 0.7` 或 `pass = true`

### 6.3 如果Ask质量不达标会怎样？

- **Acquire阶段**: 可能检索到大量无关文献，或者遗漏重要文献
- **Appraise阶段**: 如果证据不相关，评价工作会浪费
- **Apply阶段**: 基于不相关证据的推荐会出错
- **最终结果**: 可能给出错误的临床推荐

**因此**: Ask阶段的质量控制非常重要，宁可多花时间精炼问题，也不要匆忙进入Acquire。

---

## 7. 实现建议

### 7.1 对Ask Agent实现者的建议

1. **使用结构化提示**: 明确要求LLM输出PICO四个要素
2. **术语标准化**: 集成MeSH术语库，自动映射关键词
3. **同义词扩展**: 使用医学同义词库（如UMLS）扩展关键词
4. **交互式澄清**: 如果问题模糊，主动向用户询问
5. **质量自检**: 在输出前自我评估PICO完整性

### 7.2 常见陷阱

- ❌ 直接使用用户的原始表述，不做规范化
- ❌ 关键词只有中文，没有英文翻译
- ❌ PICO某个要素留空或填"未知"
- ❌ 关键词过于宽泛（如"drug", "disease"）
- ❌ 没有考虑同义词和变体

### 7.3 质量检查清单

在输出前，检查以下项目：
- [ ] P/I/C/O四个要素都已填写且具体
- [ ] 至少有3个英文关键词
- [ ] 关键词是医学术语，不是日常用语
- [ ] 如果可能，提供了MeSH术语映射
- [ ] 包含了关键词的同义词和变体
- [ ] 临床背景信息充分（年龄、孕周、风险因素等）
- [ ] 如果有歧义，已在clarifications中说明假设

---

**文档版本**: v1.0
**最后更新**: 2026-02-04
