# Stage 2: Acquire - 证据获取规格说明

**日期**: 2026-02-04
**阶段**: Acquire (证据获取)
**在流程中的位置**: 第二阶段

---

## 1. 核心职责

### 1.1 主要任务
基于Ask阶段提供的**PICO查询**和**搜索关键词**，从证据源（如PubMed、专业证据库）中**检索并筛选相关的医学文献**。

### 1.2 为什么这个阶段重要？
- **证据基础**: 后续所有分析和推荐都基于这个阶段找到的证据
- **质量保证**: 证据的数量、相关性、多样性直接影响推荐的可靠性
- **效率平衡**: 既要找到足够的证据，又要避免过多无关文献

### 1.3 不属于这个阶段的任务
- ❌ 评价证据的质量（这是Appraise阶段的任务）
- ❌ 生成临床推荐（这是Apply阶段的任务）
- ❌ 精炼PICO问题（这是Ask阶段的任务，但如果发现问题可以建议回退）

---

## 2. 输入要求

### 2.1 输入数据结构

```python
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class AcquireInput:
    """Acquire阶段的输入"""

    pico_query: PICOQuery
    # 来自Ask阶段的结构化PICO查询

    search_keywords: List[str]
    # 搜索关键词列表

    search_strategy_notes: Optional[str]
    # Ask阶段提供的检索策略建议

    filters: Optional[Dict[str, Any]]
    # 可选的过滤条件
    # 例如: {"date_range": "last_10_years", "study_types": ["RCT", "meta-analysis"]}
```

### 2.2 输入示例

```python
AcquireInput(
    pico_query=PICOQuery(
        patient="35岁初产妇，孕20周，血压140/90",
        intervention="低剂量阿司匹林（75-150mg/日）",
        comparison="不使用或安慰剂",
        outcome="子痫前期发生率",
        keywords=["aspirin", "preeclampsia", "prevention", "pregnancy"],
        mesh_terms=["D001241", "D011225"]
    ),
    search_keywords=[
        "aspirin", "acetylsalicylic acid",
        "preeclampsia", "pre-eclampsia",
        "prevention", "prophylaxis",
        "pregnancy", "high-risk pregnancy"
    ],
    search_strategy_notes="建议优先检索系统评价和RCT研究",
    filters={
        "date_range": "last_10_years",
        "study_types": ["systematic review", "meta-analysis", "RCT"]
    }
)
```

### 2.3 输入质量要求
- PICO查询必须完整（来自Ask阶段的验证）
- 至少有3个有效的搜索关键词
- 关键词应该是英文医学术语

---

## 3. 输出规格

### 3.1 输出数据结构

```python
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Evidence:
    """单篇证据的数据结构"""

    title: str
    # 文献标题

    source: str
    # 来源（如"PubMed", "Cochrane", "ObstetricsDB"）

    pmid: Optional[str]
    # PubMed ID（如果有）

    doi: Optional[str]
    # DOI（如果有）

    authors: Optional[List[str]]
    # 作者列表

    publication_year: Optional[int]
    # 发表年份

    journal: Optional[str]
    # 期刊名称

    abstract: str
    # 摘要

    study_type: Optional[str]
    # 研究类型（如"RCT", "meta-analysis", "cohort study"）

    relevance_score: float
    # 相关性评分（0.0-1.0），由检索系统或初步筛选给出

    full_text_available: bool
    # 是否有全文可用

    metadata: Optional[Dict[str, Any]]
    # 其他元数据

@dataclass
class SearchStrategy:
    """检索策略的记录"""

    query_string: str
    # 实际使用的检索式

    databases: List[str]
    # 检索的数据库列表

    filters_applied: Dict[str, Any]
    # 应用的过滤条件

    search_date: datetime
    # 检索日期

@dataclass
class AcquireOutput:
    """Acquire阶段的完整输出"""

    evidence_list: List[Evidence]
    # 筛选后的证据列表

    search_strategy: SearchStrategy
    # 检索策略记录

    total_results: int
    # 检索到的总结果数（筛选前）

    selected_count: int
    # 筛选后保留的数量

    screening_criteria: Optional[str]
    # 筛选标准说明

    excluded_reasons: Optional[Dict[str, int]]
    # 排除原因统计
    # 例如: {"不相关": 20, "非英文": 5, "无摘要": 3}
```

### 3.2 输出示例

```python
AcquireOutput(
    evidence_list=[
        Evidence(
            title="Low-dose aspirin for the prevention of preeclampsia in high-risk women: a meta-analysis",
            source="PubMed",
            pmid="12345678",
            doi="10.1001/jama.2020.12345",
            authors=["Smith J", "Johnson A", "Williams B"],
            publication_year=2020,
            journal="JAMA",
            abstract="Background: Preeclampsia is a leading cause of maternal and perinatal morbidity...",
            study_type="meta-analysis",
            relevance_score=0.95,
            full_text_available=True,
            metadata={"sample_size": 15000, "countries": ["USA", "UK", "Canada"]}
        ),
        # ... 更多证据
    ],
    search_strategy=SearchStrategy(
        query_string='("aspirin"[MeSH] OR "acetylsalicylic acid") AND ("preeclampsia"[MeSH] OR "pre-eclampsia") AND ("prevention" OR "prophylaxis") AND "pregnancy"[MeSH]',
        databases=["PubMed", "Cochrane Library"],
        filters_applied={
            "date_range": "2014-2024",
            "study_types": ["systematic review", "meta-analysis", "RCT"],
            "language": "English"
        },
        search_date=datetime.now()
    ),
    total_results=156,
    selected_count=12,
    screening_criteria="纳入标准：(1)研究对象为高危孕妇 (2)干预为低剂量阿司匹林 (3)结局包含子痫前期发生率 (4)研究类型为RCT、系统评价或meta-analysis",
    excluded_reasons={
        "不相关（研究对象不符）": 85,
        "不相关（干预措施不符）": 32,
        "不相关（结局指标不符）": 18,
        "研究类型不符（观察性研究）": 9
    }
)
```

### 3.3 输出质量标准

**必须满足的要求**：
- 至少找到3篇相关证据（如果少于3篇，应该考虑调整检索策略）
- 每篇证据必须有标题和摘要
- 记录完整的检索策略（便于审计和复现）

**建议满足的要求**：
- 证据数量在8-15篇之间（太少不够全面，太多难以深入评价）
- 包含不同类型的研究（系统评价、RCT、队列研究等）
- 相关性评分 >= 0.7 的证据占多数
- 包含近5年的最新研究

---

## 4. Observe评价维度详解

Acquire阶段的observe包含5个评价维度，每个维度评分0.0-1.0。

### 4.1 维度1: strategy_quality (检索策略合理性)

**评价内容**: 检索式的构建是否合理，关键词组合、布尔运算符使用是否恰当。

**评分标准**:
- **1.0**: 检索策略非常合理，充分利用了MeSH术语、同义词、布尔运算符
- **0.8**: 检索策略合理，但可能有小的优化空间
- **0.6**: 检索策略基本可用，但有明显的改进空间
- **0.4**: 检索策略不够合理，可能遗漏重要文献或产生过多噪音
- **0.2**: 检索策略有严重问题
- **0.0**: 检索策略完全不当

**为什么重要**: 检索策略直接决定能否找到相关文献，策略不当会导致遗漏或噪音。

**典型问题**:
- **过于简单**: 只用单个关键词，没有组合
- **过于复杂**: 使用过多AND连接，导致结果过少
- **缺少同义词**: 只用"preeclampsia"，没有"pre-eclampsia"
- **没用MeSH**: 只用自由词检索，没有利用MeSH术语的优势

**触发的调度决策**:
- 如果 `strategy_quality < 0.6` → 建议回退到Acquire，调整检索策略

### 4.2 维度2: quantity_sufficiency (证据数量充足性)

**评价内容**: 找到的证据数量是否足够支撑后续的评价和推荐。

**评分标准**:
- **1.0**: 证据数量充足（8-15篇高质量文献）
- **0.8**: 证据数量较充足（5-7篇或15-20篇）
- **0.6**: 证据数量基本够用（3-4篇）
- **0.4**: 证据数量不足（1-2篇）
- **0.2**: 证据严重不足（只有1篇或质量很低）
- **0.0**: 没有找到相关证据

**为什么重要**:
- 证据太少：可能遗漏重要信息，推荐不够可靠
- 证据太多：评价工作量大，可能包含大量低质量文献

**典型问题**:
- **检索结果为0**: 检索策略过于严格，或该问题确实缺乏证据
- **只有1-2篇**: 可能遗漏了重要文献
- **超过30篇**: 筛选标准可能过于宽松

**触发的调度决策**:
- 如果 `quantity_sufficiency < 0.4` → 可能需要回退调整检索策略
- 如果证据数量为0 → 可能需要回退到Ask重新精炼问题，或者终止workflow（证据不足）

### 4.3 维度3: relevance (证据相关性)

**评价内容**: 检索到的证据是否真正回答PICO问题，是否与临床问题相关。

**评分标准**:
- **1.0**: 所有证据都高度相关，直接回答PICO问题
- **0.8**: 大部分证据相关（>80%），少数略有偏离
- **0.6**: 多数证据相关（60-80%），但有一些不太相关
- **0.4**: 相关证据较少（40-60%），很多证据偏离主题
- **0.2**: 大部分证据不相关
- **0.0**: 几乎所有证据都不相关

**为什么重要**: 不相关的证据会浪费Appraise阶段的评价工作，甚至导致错误的推荐。

**典型问题**:
- **人群不匹配**: 检索到的是"所有孕妇"的研究，而PICO问的是"高危孕妇"
- **干预不匹配**: 检索到的是"高剂量阿司匹林"，而PICO问的是"低剂量"
- **结局不匹配**: 检索到的研究关注"心血管事件"，而PICO问的是"子痫前期"

**触发的调度决策**:
- 如果 `relevance < 0.6` → 建议回退调整检索策略或筛选标准

### 4.4 维度4: diversity (证据类型多样性)

**评价内容**: 证据是否涵盖不同类型的研究（系统评价、RCT、队列研究等）。

**评分标准**:
- **1.0**: 证据类型非常多样，包含系统评价、RCT、队列研究等
- **0.8**: 证据类型较多样，包含2-3种类型
- **0.6**: 证据类型基本多样，但某类研究占主导
- **0.4**: 证据类型单一，主要是一种类型
- **0.2**: 证据类型非常单一
- **0.0**: 只有一种类型

**为什么重要**:
- **系统评价/meta-analysis**: 提供综合性证据，证据等级高
- **RCT**: 提供因果关系证据
- **队列研究**: 提供长期随访数据
- **病例对照**: 适合罕见疾病或不良事件

多样性确保证据的全面性和可靠性。

**典型问题**:
- **只有RCT**: 缺少系统评价的综合视角
- **只有观察性研究**: 缺少高质量的RCT证据
- **只有旧研究**: 缺少最新的研究进展

**触发的调度决策**:
- 如果 `diversity < 0.6` 且 `severity="major"` → 建议回退调整检索策略，增加特定类型研究的检索

### 4.5 维度5: timeliness (证据时效性)

**评价内容**: 证据是否包含最新研究，是否遗漏重要的近期文献。

**评分标准**:
- **1.0**: 包含最新研究（近3年），且覆盖了重要的里程碑研究
- **0.8**: 包含较新研究（近5年），基本覆盖重要研究
- **0.6**: 包含一些新研究，但可能遗漏了重要的近期进展
- **0.4**: 研究较旧（多数>5年），可能遗漏重要更新
- **0.2**: 研究很旧（多数>10年）
- **0.0**: 所有研究都非常陈旧

**为什么重要**:
- 医学知识快速更新，新研究可能改变临床实践
- 旧研究的方法学可能不如新研究严谨
- 某些领域（如药物安全性）需要最新数据

**典型问题**:
- **遗漏重要新研究**: 如ASPRE试验（2017）是阿司匹林预防子痫前期的重要研究
- **只有旧研究**: 可能基于过时的临床实践
- **时间范围设置不当**: 过滤条件排除了重要的近期研究

**触发的调度决策**:
- 如果 `timeliness < 0.6` → 建议回退调整时间范围，补充最新研究

---

## 5. 典型问题场景

### 5.1 场景1: 证据数量不足

**问题表现**:
```python
# 输出
AcquireOutput(
    evidence_list=[Evidence(...), Evidence(...)],  # 只有2篇
    total_results=2,
    selected_count=2,
    ...
)
```

**Observe评价**:
```python
{
  "overall_score": 0.45,
  "dimension_scores": {
    "strategy_quality": 0.6,
    "quantity_sufficiency": 0.3,  # 很低
    "relevance": 0.8,
    "diversity": 0.4,
    "timeliness": 0.6
  },
  "pass": false,
  "issues": [
    {
      "severity": "critical",
      "dimension": "quantity_sufficiency",
      "description": "只找到2篇相关文献，证据严重不足，无法支撑可靠的推荐"
    },
    {
      "severity": "major",
      "dimension": "diversity",
      "description": "证据类型单一，都是RCT，缺少系统评价"
    }
  ],
  "summary": "证据数量严重不足，需要调整检索策略或扩大检索范围"
}
```

**调度决策**:
- **硬性Gate**: critical issue → 强制回退到Acquire
- **或者**: 回退到Ask，重新精炼问题（可能问题本身就缺乏证据）
- **或者**: 如果确实无证据，考虑终止workflow

### 5.2 场景2: 证据类型单一

**问题表现**:
```python
# 输出
AcquireOutput(
    evidence_list=[
        Evidence(study_type="RCT", ...),
        Evidence(study_type="RCT", ...),
        Evidence(study_type="RCT", ...),
        # ... 全是RCT，没有系统评价
    ],
    total_results=45,
    selected_count=10,
    ...
)
```

**Observe评价**:
```python
{
  "overall_score": 0.68,
  "dimension_scores": {
    "strategy_quality": 0.7,
    "quantity_sufficiency": 0.8,
    "relevance": 0.75,
    "diversity": 0.5,  # 低分
    "timeliness": 0.8
  },
  "pass": false,
  "issues": [
    {
      "severity": "major",
      "dimension": "diversity",
      "description": "证据类型单一，全部为单个RCT研究，缺少系统评价和meta-analysis"
    }
  ],
  "summary": "证据数量充足但类型单一，建议补充系统评价以获得更全面的证据"
}
```

**调度决策**:
- **软性Gate**: 触发"major_issues"信号
- **LLM决策**:
  - 选项1: 回退到Acquire，调整检索策略增加"systematic review OR meta-analysis"
  - 选项2: 继续（如果RCT质量很高，也可以接受）
  - 权衡: 系统评价能提供更全面的证据，但如果时间紧迫且RCT质量高，也可以继续

### 5.3 场景3: 相关性不足

**问题表现**:
```python
# 输出
AcquireOutput(
    evidence_list=[
        Evidence(title="Aspirin for cardiovascular disease prevention", relevance_score=0.4, ...),
        Evidence(title="Aspirin in general pregnancy", relevance_score=0.5, ...),
        # ... 很多不太相关的文献
    ],
    total_results=120,
    selected_count=15,
    ...
)
```

**Observe评价**:
```python
{
  "overall_score": 0.55,
  "dimension_scores": {
    "strategy_quality": 0.5,
    "quantity_sufficiency": 0.8,
    "relevance": 0.4,  # 很低
    "diversity": 0.7,
    "timeliness": 0.7
  },
  "pass": false,
  "issues": [
    {
      "severity": "major",
      "dimension": "relevance",
      "description": "多数文献相关性不足：5篇关注心血管疾病而非子痫前期，3篇研究对象为普通孕妇而非高危人群"
    },
    {
      "severity": "minor",
      "dimension": "strategy_quality",
      "description": "检索策略过于宽泛，应该增加'high-risk'或'prevention'限定"
    }
  ],
  "summary": "检索到大量文献但相关性不足，需要优化检索策略或筛选标准"
}
```

**调度决策**:
- **LLM决策**: 回退到Acquire，调整检索策略
  - 增加限定词："high-risk pregnancy" AND "prevention"
  - 排除无关主题：NOT "cardiovascular disease"
  - 收紧筛选标准

### 5.4 场景4: 证据获取成功

**问题表现**:
```python
# 输出
AcquireOutput(
    evidence_list=[
        Evidence(title="Low-dose aspirin for prevention of preeclampsia: meta-analysis", study_type="meta-analysis", relevance_score=0.95, ...),
        Evidence(title="ASPRE trial: aspirin in high-risk pregnancy", study_type="RCT", relevance_score=0.92, ...),
        # ... 共12篇高质量相关文献
    ],
    total_results=156,
    selected_count=12,
    search_strategy=SearchStrategy(...),
    ...
)
```

**Observe评价**:
```python
{
  "overall_score": 0.86,
  "dimension_scores": {
    "strategy_quality": 0.85,
    "quantity_sufficiency": 0.9,
    "relevance": 0.88,
    "diversity": 0.85,
    "timeliness": 0.9
  },
  "pass": true,
  "issues": [
    {
      "severity": "minor",
      "dimension": "relevance",
      "description": "2篇文献的outcome略有偏离（关注早产而非子痫前期），但仍有参考价值"
    }
  ],
  "summary": "检索策略合理，证据数量充足，类型多样，相关性高，包含最新研究，质量优秀"
}
```

**调度决策**:
- **LLM决策**: "proceed" → 继续到Appraise阶段
- **原因**: 质量优秀，minor issue不影响整体

---

## 6. 与其他阶段的接口

### 6.1 从Ask阶段接收的数据

```python
# Ask阶段传递过来的
{
  "pico_query": PICOQuery,
  "search_keywords": List[str],
  "search_strategy_notes": Optional[str]
}
```

### 6.2 向Appraise阶段传递的数据

```python
# Appraise阶段需要的
{
  "evidence_list": List[Evidence],  # 证据列表
  "pico_query": PICOQuery  # 原始PICO（用于评价相关性）
}
```

### 6.3 可能的回退场景

**回退到Ask**:
- 证据数量为0或极少（<3篇）
- 可能是PICO问题本身有问题，需要重新精炼

**回退到Acquire自身**:
- 证据数量不足但>0
- 证据类型单一
- 相关性不足
- 需要调整检索策略或筛选标准

---

## 7. 实现建议

### 7.1 对Acquire Agent实现者的建议

1. **构建合理的检索式**:
   - 使用MeSH术语
   - 包含同义词
   - 合理使用布尔运算符（AND, OR, NOT）

2. **分阶段检索**:
   - 第一阶段：高精度检索（严格条件）
   - 如果结果不足，第二阶段：扩大范围

3. **记录检索过程**:
   - 完整记录检索式
   - 记录筛选标准和排除原因
   - 便于审计和复现

4. **初步筛选**:
   - 基于标题和摘要进行相关性筛选
   - 排除明显不相关的文献
   - 但不要过度筛选（避免遗漏）

5. **质量自检**:
   - 检查证据数量是否充足
   - 检查证据类型是否多样
   - 检查是否包含最新研究

### 7.2 常见陷阱

- ❌ 检索式过于简单，只用单个关键词
- ❌ 检索式过于复杂，导致结果为0
- ❌ 筛选标准过于严格，遗漏重要文献
- ❌ 筛选标准过于宽松，包含大量无关文献
- ❌ 没有记录检索过程，无法复现
- ❌ 忽略最新研究，只检索旧文献

### 7.3 质量检查清单

在输出前，检查以下项目：
- [ ] 至少找到3篇相关证据
- [ ] 证据类型包含至少2种（如系统评价+RCT）
- [ ] 包含近5年的最新研究
- [ ] 相关性评分>=0.7的证据占多数
- [ ] 完整记录了检索策略
- [ ] 记录了筛选标准和排除原因
- [ ] 每篇证据都有标题和摘要

---

**文档版本**: v1.0
**最后更新**: 2026-02-04
