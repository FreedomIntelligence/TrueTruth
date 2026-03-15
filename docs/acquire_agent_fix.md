# Acquire阶段修复 - 符合MVP策略

**日期**: 2026-02-07
**状态**: 已完成

## 修复内容

### 1. 更新Evidence数据结构

在 `src/state/schema.py` 中添加了必要字段：
- `study_type`: 研究类型（RCT、系统评价等）
- `publication_date`: 发表日期

### 2. 增强Acquire Agent功能

在 `src/agents/acquire_agent.py` 中实现了MVP文档要求的功能：

#### ✅ 相关性评估 (`_assess_relevance`)
- 使用LLM评估每篇文献与PICO问题的相关性
- 返回0-1的评分
- 根据标题和摘要进行评估

#### ✅ 研究类型推断 (`_infer_study_type`)
- 基于规则的简单推断
- 识别类型：
  - Systematic Review
  - RCT
  - Cohort Study
  - Case-Control Study
  - Cross-Sectional Study
  - Case Report
  - Other

#### ✅ 相关性筛选
- 筛选阈值：relevance_score > 0.6
- 按相关性排序
- 返回前10篇最相关的文献

#### ✅ 研究类型分布统计
- 统计选中文献的研究类型分布
- 用于Judge评估证据多样性

### 3. 增强PubMed API工具

在 `src/tools/pubmed_api.py` 中添加：

#### ✅ 摘要获取功能 (`fetch_abstracts`)
- 使用efetch API获取完整摘要
- 解析XML格式返回
- 支持批量获取

#### ✅ 完整字段返回
- title
- source
- pmid
- abstract（完整摘要）
- publication_date
- relevance_score（由Acquire agent填充）
- study_type（由Acquire agent填充）

## 符合MVP文档要求

根据 `docs/plans/stage_specification/mvp-implementation-strategy.md` 第148-242行：

### ✅ 必须保留的功能
- [x] 真实调用PubMed API
- [x] 基本的相关性筛选
- [x] 研究类型识别（简单版本）

### ✅ 可以省略的功能（按计划省略）
- [ ] 两级筛选（record screening + full-text assessment）
- [ ] 投票机制（T=2）
- [ ] RAG-based full-text matching
- [ ] 内部迭代循环（使用外部调度循环）
- [ ] 复杂的布尔逻辑查询优化

## 输出格式

```python
{
    "evidence_list": [Evidence对象列表],
    "search_query": "实际使用的PubMed查询",
    "total_results": 20,  # 原始搜索结果数
    "selected_count": 10,  # 筛选后的数量
    "study_type_distribution": {
        "RCT": 5,
        "Systematic Review": 2,
        "Cohort Study": 3
    }
}
```

## Judge评价维度匹配

Acquire阶段的输出现在可以被Judge正确评价：

1. **quantity_sufficiency**: 通过 `selected_count` 判断
2. **relevance**: 通过 `relevance_score` 判断
3. **diversity**: 通过 `study_type_distribution` 判断

## 测试建议

1. 测试正常情况：找到10篇以上相关文献
2. 测试边界情况：
   - 0结果（触发证据不足Gate）
   - 结果过多但相关性低
   - 单一研究类型（触发多样性问题）
3. 测试相关性评估的准确性
4. 测试研究类型推断的准确性

## 下一步

Acquire阶段现在完全符合MVP策略要求，可以：
1. 产生真实的变化性（有时找到很多，有时找不到）
2. 提供足够的信息供Judge评价
3. 触发合适的调度决策（回退、继续、人类介入）

---

**修复完成**: 2026-02-07
