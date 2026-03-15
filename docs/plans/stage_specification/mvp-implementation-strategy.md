# EBM 5A 阶段实现 - MVP策略

**日期**: 2026-02-04
**目的**: 明确MVP阶段的实现策略和范围
**状态**: 设计阶段

---

## 1. MVP设计原则

### 1.1 核心目标

> **目标不是完美实现五个阶段，而是让调度系统有真实的决策场景可以处理。**

### 1.2 设计哲学

- **关注点分离**：调度系统设计 vs 阶段实现细节
- **黑盒视角**：五个阶段作为黑盒，只关注其产出物和observe
- **真实变化性**：阶段输出必须有真实的不确定性，让Judge有东西可评价
- **快速迭代**：2-3周完成MVP，开始测试调度逻辑

---

## 2. 实现策略：简单流程 + 真实变化

### 2.1 必须真实实现的部分

#### ⭐⭐⭐ Judge LLM（必须真实）

**为什么必须真实：**
- Judge的输出（observe）是调度系统的直接输入
- 如果Mock observe，调度系统就没有真实的不确定性可以处理
- 这是我们的核心关注点

**实现方式：**
```python
def judge_stage_output(stage: str, output: Dict, state: WorkflowState) -> Observe:
    """真实调用LLM进行评价"""

    # 获取该阶段的评价维度
    dimensions = get_evaluation_dimensions(stage)

    prompt = f"""
你是EBM 5A系统的质量评估专家。请评价{stage}阶段的输出质量。

## 阶段输出
{json.dumps(output, ensure_ascii=False, indent=2)}

## 评价维度
{format_dimensions(dimensions)}

## 评价要求
1. 对每个维度给出0-1的评分
2. 识别具体问题，标注严重程度（critical/major/minor）
3. 给出整体评分和是否通过的判断
4. 提供自然语言总结

## 输出格式
请以JSON格式输出：
{{
  "overall_score": 0.0-1.0,
  "dimension_scores": {{
    "dimension_1": 0.0-1.0,
    ...
  }},
  "pass": true/false,
  "issues": [
    {{
      "severity": "critical" | "major" | "minor",
      "dimension": "dimension_name",
      "description": "问题描述"
    }}
  ],
  "summary": "自然语言评价总结"
}}
"""

    response = llm.call(prompt, temperature=0.3)
    evaluation = parse_json_response(response)

    return {
        "stage": stage,
        "output": output,
        "evaluation": evaluation
    }
```

**简化点：**
- 初版可以只用3个评价维度（而非5个）
- 评价标准可以简化，但必须真实调用LLM
- 不需要复杂的few-shot示例

---

### 2.2 可以简化实现的部分

#### ⭐⭐ Stage 1: Ask（简单LLM调用）

**实现方式：**
```python
def ask_agent(question: str) -> Dict:
    """简单的PICO提取"""

    prompt = f"""
将以下临床问题转化为PICO格式，并提取搜索关键词。

临床问题：{question}

请返回JSON格式：
{{
  "pico_query": {{
    "patient": "患者或人群特征",
    "intervention": "干预措施",
    "comparison": "对照措施",
    "outcome": "关注的结局"
  }},
  "search_keywords": ["keyword1", "keyword2", ...],
  "mesh_terms": ["可选的MeSH术语"]
}}
"""

    response = llm.call(prompt, temperature=0.2)
    return parse_json_response(response)
```

**不需要：**
- ❌ Self-reflection based few-shot
- ❌ 复杂的MeSH术语映射（可以简化为关键词提取）
- ❌ 知识库参考
- ❌ 用户交互式问题精炼

**为什么可以简化：**
- PICO提取相对简单，基础LLM就能做
- 重点是产生"有时好有时坏"的输出，让Judge有东西可评价
- 调度系统可以通过回退来处理质量问题

**评价维度（简化版）：**
```python
ASK_EVALUATION_DIMENSIONS = {
    "pico_completeness": "PICO四要素是否完整",
    "searchability": "关键词是否足够具体和准确",
    "clarity": "问题是否明确，无歧义"
}
```

---

#### ⭐⭐⭐ Stage 2: Acquire（真实API + 简化筛选）

**实现方式：**
```python
def acquire_agent(pico: Dict, search_keywords: List[str]) -> Dict:
    """真实调用PubMed，简化筛选"""

    # 1. 构建PubMed查询
    query = build_pubmed_query(search_keywords)

    # 2. 真实调用PubMed API（关键！）
    try:
        results = pubmed_api.search(
            query=query,
            max_results=50,
            date_range="last_10_years"
        )
    except Exception as e:
        return {
            "evidence_list": [],
            "search_query": query,
            "total_results": 0,
            "error": str(e)
        }

    # 3. 简化的相关性筛选
    # 使用LLM判断标题/摘要与PICO的相关性
    filtered = []
    for article in results:
        relevance_score = assess_relevance(article, pico)
        if relevance_score > 0.6:
            filtered.append({
                "title": article.title,
                "abstract": article.abstract,
                "pmid": article.pmid,
                "publication_date": article.pub_date,
                "study_type": infer_study_type(article),  # 简单推断
                "relevance_score": relevance_score
            })

    # 4. 返回前10篇
    return {
        "evidence_list": filtered[:10],
        "search_query": query,
        "total_results": len(results),
        "selected_count": len(filtered[:10]),
        "study_type_distribution": count_study_types(filtered[:10])
    }

def assess_relevance(article: Dict, pico: Dict) -> float:
    """简单的相关性评估"""
    prompt = f"""
评估以下文献与PICO问题的相关性（0-1）。

PICO:
- Patient: {pico['patient']}
- Intervention: {pico['intervention']}
- Comparison: {pico['comparison']}
- Outcome: {pico['outcome']}

文献:
- Title: {article.title}
- Abstract: {article.abstract[:500]}

返回0-1的相关性评分。
"""
    response = llm.call(prompt, temperature=0.1)
    return parse_float(response)
```

**必须保留：**
- ✅ 真实调用PubMed API（这样会有真实的"0结果"、"结果过多"等情况）
- ✅ 基本的相关性筛选
- ✅ 研究类型识别（简单版本）

**可以省略：**
- ❌ 两级筛选（record screening + full-text assessment）
- ❌ 投票机制（T=2）
- ❌ RAG-based full-text matching
- ❌ 内部迭代循环（初版先用外部循环）
- ❌ 复杂的布尔逻辑查询优化

**为什么这样：**
- 真实API调用会产生真实的变化（有时找到很多，有时找不到）
- 这给调度系统提供了真实的决策场景
- 筛选可以简化，因为Judge会评价"相关性"和"多样性"维度

**评价维度（简化版）：**
```python
ACQUIRE_EVALUATION_DIMENSIONS = {
    "quantity_sufficiency": "证据数量是否足够",
    "relevance": "证据与PICO问题的相关性",
    "diversity": "证据类型是否多样（RCT、系统评价等）"
}
```

**内部简单循环（可选）：**
```python
def acquire_agent_with_retry(pico: Dict, search_keywords: List[str]) -> Dict:
    """带简单重试的Acquire"""

    max_internal_retries = 2

    for attempt in range(max_internal_retries):
        result = acquire_agent(pico, search_keywords)

        # 简单反馈：立即处理
        if result["total_results"] == 0:
            # 放宽日期限制
            search_keywords = expand_keywords(search_keywords)
            continue
        elif result["total_results"] > 1000:
            # 增加限制
            search_keywords = narrow_keywords(search_keywords)
            continue
        else:
            break

    result["search_attempts"] = attempt + 1
    return result
```

---

#### ⭐⭐ Stage 3: Appraise（简化GRADE + Mock数值）

**实现方式：**
```python
def appraise_agent(evidence_list: List[Dict]) -> Dict:
    """简化的GRADE评估"""

    appraisal_results = []
    grade_distribution = {"High": 0, "Moderate": 0, "Low": 0, "Very Low": 0}

    for evidence in evidence_list:
        # 简单的GRADE评估
        grade = assess_grade_simple(evidence)
        grade_distribution[grade] += 1

        # Mock数值数据（初版不做真实提取）
        numerical_data = {
            "sample_size": "Mock: 需要从全文提取",
            "effect_size": "Mock: 需要从全文提取",
            "confidence_interval": "Mock: 需要从全文提取",
            "extraction_confidence": 0.5  # 标记为低置信度
        }

        appraisal_results.append({
            "evidence": evidence,
            "grade": grade,
            "bias_risk": assess_bias_simple(evidence),
            "numerical_data": numerical_data
        })

    # 简单的冲突检测
    has_conflict = detect_conflict_simple(appraisal_results)

    return {
        "appraisal_results": appraisal_results,
        "grade_distribution": grade_distribution,
        "has_conflict": has_conflict,
        "overall_quality": calculate_overall_quality(grade_distribution)
    }

def assess_grade_simple(evidence: Dict) -> str:
    """简化的GRADE评估"""
    prompt = f"""
基于GRADE框架，评估以下证据的质量等级。

研究类型：{evidence.get('study_type', 'Unknown')}
标题：{evidence['title']}
摘要：{evidence['abstract'][:300]}

返回质量等级：High, Moderate, Low, Very Low
"""
    response = llm.call(prompt, temperature=0.2)
    return parse_grade(response)

def assess_bias_simple(evidence: Dict) -> str:
    """简化的偏倚风险评估"""
    # 基于研究类型的简单规则
    study_type = evidence.get('study_type', 'Unknown')

    if study_type == "Systematic Review":
        return "Low"
    elif study_type == "RCT":
        return "Low to Moderate"
    else:
        return "Moderate to High"
```

**可以Mock的：**
- ❌ 数值提取（Hierarchical RAG、Query Rewriting）
- ❌ 详细的偏倚风险评估（ROB 2.0工具）
- ❌ 全文PDF解析

**必须保留：**
- ✅ 基本的GRADE评级（High/Moderate/Low/Very Low）
- ✅ 简单的冲突检测
- ✅ 研究类型识别

**为什么这样：**
- GRADE评级是核心，必须保留
- 数值提取很复杂，初版Mock，标记低置信度
- Judge会评价"数值提取置信度"，触发人类介入

**评价维度（简化版）：**
```python
APPRAISE_EVALUATION_DIMENSIONS = {
    "grade_reasonableness": "GRADE评分是否合理",
    "conflict_identification": "是否正确识别证据冲突",
    "numerical_confidence": "数值提取的置信度（Mock时为0.5）"
}
```

---

#### ⭐ Stage 4: Apply（简单LLM生成）

**实现方式：**
```python
def apply_agent(appraisal: Dict, pico: Dict) -> Dict:
    """简单的推荐生成"""

    prompt = f"""
基于以下证据评价，生成临床推荐。

原始问题（PICO）：
{json.dumps(pico, ensure_ascii=False, indent=2)}

证据评价：
- 证据数量：{len(appraisal['appraisal_results'])}
- 质量分布：{appraisal['grade_distribution']}
- 整体质量：{appraisal['overall_quality']}
- 是否有冲突：{appraisal['has_conflict']}

请生成：
1. 推荐内容（具体的临床建议）
2. 推荐强度（Strong/Weak）
3. 证据质量等级（High/Moderate/Low/Very Low）
4. 推荐理由
5. 注意事项和禁忌症

返回JSON格式。
"""

    response = llm.call(prompt, temperature=0.3)
    recommendation = parse_json_response(response)

    return {
        "recommendation": recommendation,
        "strength": recommendation.get("strength", "Weak"),
        "evidence_quality": appraisal["overall_quality"],
        "rationale": recommendation.get("rationale", ""),
        "caveats": recommendation.get("caveats", [])
    }
```

**不需要：**
- ❌ 复杂的风险计算（NNT、NNH等）
- ❌ 成本效益分析
- ❌ 患者偏好整合

**为什么可以简化：**
- 推荐生成相对直接，基于证据质量和GRADE
- Judge会评价"证据-推荐匹配度"和"强度合理性"

**评价维度（简化版）：**
```python
APPLY_EVALUATION_DIMENSIONS = {
    "evidence_alignment": "推荐是否与证据匹配",
    "strength_appropriateness": "推荐强度是否合理",
    "actionability": "推荐是否具体可操作"
}
```

---

#### ⭐ Stage 5: Assess（简单LLM评估）

**实现方式：**
```python
def assess_agent(full_chain: Dict) -> Dict:
    """评估整个推理链"""

    prompt = f"""
评估以下完整推理链的质量。

原始问题：{full_chain['original_question']}

PICO查询：{full_chain['pico']}

证据：{len(full_chain['evidence'])}篇，质量分布{full_chain['grade_distribution']}

推荐：{full_chain['recommendation']['text']}
强度：{full_chain['recommendation']['strength']}

请评估：
1. 是否完整回答了原始问题
2. 推理链是否清晰连贯
3. 是否存在逻辑矛盾
4. 是否遗漏重要的临床考虑因素
5. 知识缺口在哪里

返回JSON格式。
"""

    response = llm.call(prompt, temperature=0.3)
    assessment = parse_json_response(response)

    return {
        "assessment": assessment,
        "quality_score": assessment.get("quality_score", 0.7),
        "identified_gaps": assessment.get("gaps", []),
        "logical_consistency": assessment.get("consistency", "Good")
    }
```

**评价维度（简化版）：**
```python
ASSESS_EVALUATION_DIMENSIONS = {
    "answer_completeness": "是否完整回答原始问题",
    "reasoning_chain": "推理链是否清晰",
    "logical_consistency": "是否存在逻辑矛盾"
}
```

---

## 3. MVP实现总结表

| 阶段 | 实现方式 | 复杂度 | 工作量 | 原因 |
|------|---------|--------|--------|------|
| **Judge LLM** | ✅ 真实实现 | 中 | 2-3天 | 调度系统的直接输入，必须真实 |
| **Ask** | ✅ 简单LLM | 低 | 1天 | PICO提取相对简单 |
| **Acquire** | ✅ 真实API + 简化筛选 | 中 | 2-3天 | 需要真实的变化性 |
| **Appraise** | ⚠️ 简化GRADE + Mock数值 | 中 | 2天 | GRADE评级保留，数值提取Mock |
| **Apply** | ✅ 简单LLM | 低 | 1天 | 基础推荐生成即可 |
| **Assess** | ✅ 简单LLM | 低 | 1天 | 整体评估即可 |
| **总计** | - | - | **10-12天** | - |

---

## 4. 实施计划

### Week 1: 核心阶段实现
**Day 1-2: Ask + Judge**
- 实现Ask阶段（简单PICO提取）
- 实现Judge LLM（Ask阶段评价）
- 测试：输入临床问题 → PICO → Observe

**Day 3-5: Acquire + Judge**
- 实现Acquire阶段（真实PubMed API + 简化筛选）
- 实现Judge LLM（Acquire阶段评价）
- 测试：PICO → 证据列表 → Observe

**Day 6-7: Appraise/Apply/Assess + Judge**
- 实现Appraise阶段（简化GRADE + Mock数值）
- 实现Apply阶段（简单推荐生成）
- 实现Assess阶段（整体评估）
- 实现对应的Judge评价
- 测试：完整流程（无调度，顺序执行）

### Week 2: 调度系统实现
**Day 8-10: 调度系统**
- 实现硬性Gate（包括新增的证据不足Gate）
- 实现软性Gate
- 实现调度LLM（包括人类介入决策）
- 测试：手工构造几个场景，验证调度逻辑

**Day 11-12: 集成测试**
- 端到端测试
- 修复bug
- 准备进入Benchmark阶段

### Week 3: Benchmark准备
- 收集真实案例
- 标注调度决策点
- 实现评测指标

---

## 5. 质量保证

### 5.1 必须验证的点

**Ask阶段：**
- ✅ 能够提取基本的PICO结构
- ✅ Judge能够识别PICO不完整的情况

**Acquire阶段：**
- ✅ 能够真实调用PubMed API
- ✅ 能够处理"0结果"、"结果过多"等情况
- ✅ Judge能够识别证据类型单一的问题

**Appraise阶段：**
- ✅ 能够给出基本的GRADE评级
- ✅ Mock数值标记为低置信度
- ✅ Judge能够识别数值置信度低的问题

**Apply阶段：**
- ✅ 能够生成基本的推荐
- ✅ Judge能够识别推荐强度不匹配的问题

**Assess阶段：**
- ✅ 能够评估整体推理链
- ✅ Judge能够识别逻辑矛盾

**调度系统：**
- ✅ 硬性Gate能够正确触发
- ✅ 软性Gate能够识别需要关注的情况
- ✅ 调度LLM能够做出合理决策
- ✅ 能够处理人类介入请求

### 5.2 不需要验证的点（留待后续）

- ❌ 复杂的MeSH术语映射
- ❌ 两级文献筛选
- ❌ RAG-based全文匹配
- ❌ 精确的数值提取
- ❌ 详细的偏倚风险评估
- ❌ 复杂的风险计算

---

## 6. 后续增强路径

### Phase 2: 增强Acquire阶段
- 实现两级筛选（record + full-text）
- 增加RAG-based相关性匹配
- 优化检索策略

### Phase 3: 增强Appraise阶段
- 实现真实的数值提取（Hierarchical RAG）
- 增加详细的偏倚风险评估
- 支持全文PDF解析

### Phase 4: 增强Apply阶段
- 增加风险计算（NNT、NNH）
- 增加成本效益分析
- 整合患者偏好

### Phase 5: 系统优化
- 优化LLM调用效率
- 增加缓存机制
- 提升响应速度

---

**文档版本**: v1.0
**最后更新**: 2026-02-04
