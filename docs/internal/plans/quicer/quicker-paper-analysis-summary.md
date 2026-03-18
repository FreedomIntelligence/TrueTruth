# Quicker论文分析与设计对比总结

**日期**: 2026-02-04
**论文**: Streamlining evidence-based clinical recommendations with large language models (Nature npj Digital Medicine)
**目的**: 总结Quicker论文的关键insights及其对本项目的启发

---

## 1. Quicker论文核心要点

### 1.1 系统概述
- **目标**: 将数周的指南制定工作压缩到20-40分钟
- **方法**: LLM驱动的端到端循证医学workflow
- **创新**: Agentic workflow + 人机协作 + 可解释性

### 1.2 五阶段流程
1. **问题分解**: PICO提取（Self-reflection based few-shot）
2. **文献检索**: Agentic迭代搜索（生成→执行→反馈→调整）
3. **研究筛选**: 两级筛选（记录筛选 + 全文评估）+ 投票机制
4. **证据评估**: GRADE框架 + Hierarchical RAG数值提取
5. **推荐制定**: 综合证据生成推荐

### 1.3 关键技术
- **Agentic Search Loop**: 检索阶段的内部迭代优化
- **Two-Level Screening**: 标题/摘要筛选 + RAG全文匹配
- **Hierarchical RAG**: 分层检索提取数值数据
- **Voting Mechanism**: T=2投票平衡敏感度
- **Human-AI Collaboration**: 明确的人类介入点

### 1.4 评测基准
- **Q2CRBench-3**: 基于真实指南（ACR RA 2021, EAN Dementia 2020, KDIGO CKD 2024）
- **评测指标**: 检索召回率、筛选敏感度、数值提取准确率、推荐质量

---

## 2. 对本项目的启发

### 2.1 架构级改进（已采纳）

#### ✅ 增加"人类介入"调度动作
**Quicker的做法**: 明确设计人类介入点（数值验证、偏倚评估）

**我们的改进**:
- 新增`request_human_review`调度动作
- 定义5种review_scope: numerical_data, bias_assessment, evidence_conflict, final_recommendation, ethical_consideration
- 软性Gate触发人类介入信号

**文档**: `2026-02-04-scheduling-system-improvements.md` Section 2.1

---

#### ✅ 优雅失败的终止策略
**Quicker的做法**: 证据不足时明确报告"无法给出推荐"

**我们的改进**:
- 新增"证据不足Gate"（硬性Gate 4）
- 两种场景：
  1. Acquire多次尝试后仍无证据
  2. Appraise发现80%以上证据为Very Low质量
- 输出结构化的终止信息

**文档**: `2026-02-04-scheduling-system-improvements.md` Section 2.2

---

#### ✅ 效率权衡的调度推理
**Quicker的目标**: 20-40分钟完成，明确的时间约束

**我们的改进**:
- 调度LLM prompt中增加效率考虑
- 决策矩阵：问题严重度 × 剩余预算
- 边际收益评估：回退是否能显著改善质量

**文档**: `2026-02-04-scheduling-system-improvements.md` Section 2.3

---

### 2.2 阶段实现细节（MVP暂不采纳，标记为后续增强）

#### ⏸️ Agentic Search Loop（内部循环）
**Quicker的做法**: Acquire阶段内部迭代（生成query → 执行 → 反馈 → 调整）

**我们的决策**:
- MVP阶段：使用外部循环（Acquire → Judge → Scheduler → 回到Acquire）
- 可选：在Acquire内部增加简单的重试逻辑（处理0结果、结果过多）
- Phase 2增强：实现完整的内部agentic loop

**理由**: 外部循环已能达到类似效果，内部循环是优化而非必需

**文档**: `mvp-implementation-strategy.md` Section 2.2 (Acquire阶段)

---

#### ⏸️ Two-Level Screening
**Quicker的做法**:
- Level 1: 标题/摘要筛选（CoT + 投票）
- Level 2: RAG全文匹配

**我们的决策**:
- MVP阶段：简化为单级筛选（标题/摘要相关性）
- Phase 2增强：实现两级筛选 + RAG

**理由**: 单级筛选足以产生变化性，Judge会评价"相关性"维度

**文档**: `mvp-implementation-strategy.md` Section 2.2 (Acquire阶段)

---

#### ⏸️ Hierarchical RAG for Data Extraction
**Quicker的做法**: 分层检索（文档→章节→表格→单元格）提取数值

**我们的决策**:
- MVP阶段：Mock数值数据，标记低置信度（0.5）
- 触发软性Gate信号`low_confidence_data`
- 调度系统决策`request_human_review`
- Phase 3增强：实现真实的Hierarchical RAG

**理由**: 数值提取复杂，MVP重点是验证调度系统，Mock足够触发人类介入决策

**文档**: `mvp-implementation-strategy.md` Section 2.2 (Appraise阶段)

---

#### ⏸️ Voting Mechanism
**Quicker的做法**: T=2投票（3次判断，2次通过则保留）

**我们的决策**:
- MVP阶段：不实现投票
- Phase 2增强：在筛选阶段增加投票机制

**理由**: 投票是优化，不影响调度系统测试

---

### 2.3 Benchmark设计（已采纳核心思想）

#### ✅ 使用真实案例
**Quicker的做法**: Q2CRBench-3基于真实指南

**我们的改进**:
- 使用真实指南案例（中国高血压防治指南、KDIGO等）
- 但只标注**调度决策点**，不标注完整的阶段输出
- 聚焦于"在这个observe下，应该做什么决策"

**文档**: `2026-02-04-scheduling-system-improvements.md` Section 3.2

---

#### ✅ 允许多个可接受的决策
**Quicker的局限**: 评测是与专家输出的精确对比

**我们的创新**:
- 不是唯一的"正确路径"
- 而是"可接受的决策空间"
- 每个alternative_decision有acceptability评级（optimal/acceptable/suboptimal/poor/risky）

**文档**: `2026-02-04-scheduling-system-improvements.md` Section 3.2.2

---

#### ✅ 评测指标聚焦调度质量
**Quicker的评测**: 检索召回率、筛选敏感度、推荐质量（阶段执行质量）

**我们的评测**:
- 决策合理性（与专家决策的一致性）
- 路径效率（最少步骤达到目标）
- 安全性（避免risky决策）

**文档**: `2026-02-04-scheduling-system-improvements.md` Section 3.3

---

## 3. 设计对比总结表

| 维度 | Quicker论文 | 本项目设计 | 差异说明 |
|------|------------|-----------|---------|
| **整体架构** | 端到端workflow | 端到端workflow + 调度系统 | 我们增加了显式的调度层 |
| **调度机制** | 隐式（嵌入在search阶段） | 显式（分层Gate + 调度LLM） | 我们的调度更系统化 |
| **人类介入** | 设计了介入点 | 作为调度动作 | 我们将其纳入调度决策 |
| **失败处理** | 优雅终止 | 硬性Gate + 优雅终止 | 我们有明确的终止策略 |
| **效率权衡** | 20-40分钟目标 | 调度推理中的权衡 | 我们显式建模效率 |
| **Agentic Loop** | Acquire内部迭代 | 外部循环（MVP）+ 可选内部循环 | MVP简化，后续增强 |
| **文献筛选** | 两级筛选 + 投票 | 单级筛选（MVP） | MVP简化，后续增强 |
| **数值提取** | Hierarchical RAG | Mock（MVP） | MVP简化，触发人类介入 |
| **Benchmark** | 端到端质量评测 | 调度决策质量评测 | 我们聚焦调度系统 |
| **评测基准** | 真实指南完整输出 | 真实指南调度决策点 | 我们只标注决策点 |

---

## 4. 我们的创新点

### 4.1 显式的调度系统架构
- **分层决策**: 硬性Gate → 软性Gate → 调度LLM
- **Judge与Scheduler分离**: 评价与决策解耦
- **结构化Observe**: 5维度评分 + 问题列表 + 总结

**优势**: 比Quicker的隐式调度更系统化、可解释、可优化

---

### 4.2 调度决策的显式建模
- **人类介入作为调度动作**: 不是系统失败，而是workflow的一部分
- **效率权衡的决策矩阵**: 问题严重度 × 剩余预算
- **优雅失败策略**: 明确的终止条件和输出

**优势**: 调度逻辑更清晰，决策更可控

---

### 4.3 聚焦调度质量的Benchmark
- **只标注调度决策点**: 不标注完整阶段输出
- **允许多个可接受决策**: 不是唯一正确答案
- **评测调度质量**: 决策合理性 + 路径效率 + 安全性

**优势**: 评测目标明确，与设计目标一致

---

### 4.4 黑盒视角的阶段设计
- **关注点分离**: 调度系统 vs 阶段实现
- **MVP策略**: 简化阶段实现，聚焦调度测试
- **渐进增强**: 调度稳定后再优化阶段

**优势**: 快速迭代，避免过早优化

---

## 5. 实施路线图

### Phase 1: MVP（2-3周）
- ✅ 简化的五阶段实现
- ✅ 真实的Judge LLM
- ✅ 完整的调度系统（含人类介入、优雅失败、效率权衡）
- ✅ 基础的Benchmark框架

**目标**: 验证调度系统设计

---

### Phase 2: 阶段增强（4-6周）
- ⏸️ Acquire: 内部agentic loop + 两级筛选
- ⏸️ Appraise: Hierarchical RAG数值提取
- ⏸️ 投票机制

**目标**: 提升阶段执行质量

---

### Phase 3: 系统优化（持续）
- 优化LLM调用效率
- 增加缓存机制
- 扩展Benchmark案例
- 迭代调度策略

**目标**: 生产就绪

---

## 6. 关键决策记录

### 决策1: 外部循环 vs 内部循环
**决策**: MVP使用外部循环，Phase 2增加内部循环

**理由**:
- 外部循环（Acquire → Judge → Scheduler → 回到Acquire）已能达到迭代效果
- 内部循环是优化，不影响调度系统验证
- 可以在Acquire内部增加简单重试逻辑（处理0结果等确定性问题）

---

### 决策2: Mock数值提取
**决策**: MVP阶段Mock数值，标记低置信度，触发人类介入

**理由**:
- 数值提取复杂（Hierarchical RAG + Query Rewriting）
- MVP重点是验证调度系统，不是阶段实现
- Mock足以触发`low_confidence_data`信号和`request_human_review`决策
- 验证了调度系统处理不确定性的能力

---

### 决策3: Benchmark聚焦调度质量
**决策**: 只标注调度决策点，不标注完整阶段输出

**理由**:
- 设计目标是验证调度系统，不是阶段执行质量
- 标注完整输出工作量大，且不是核心关注点
- 调度决策点是关键，体现了调度逻辑的合理性

---

### 决策4: 人类介入作为调度动作
**决策**: 增加`request_human_review`作为调度动作

**理由**:
- Quicker论文明确设计了人类介入点
- 人类介入不是系统失败，而是workflow的一部分
- 某些决策（数值验证、伦理权衡）需要人类判断
- 这是调度系统的职责，不是阶段的职责

---

## 7. 参考文献

**Quicker论文**:
- 标题: Streamlining evidence-based clinical recommendations with large language models
- 期刊: Nature npj Digital Medicine
- 团队: 浙江大学 + 北京协和医院
- 关键贡献: Agentic workflow, Q2CRBench-3, 人机协作

**本项目文档**:
- `2026-02-04-scheduling-system-improvements.md`: 调度系统改进
- `mvp-implementation-strategy.md`: MVP实施策略
- `2026-02-02-scheduling-system-design-part1-overview-observe.md`: Observe设计
- `2026-02-02-scheduling-system-design-part2-decision-mechanism.md`: 调度决策机制
- `2026-02-02-scheduling-system-design-part3-benchmark.md`: Benchmark设计

---

**文档版本**: v1.0
**最后更新**: 2026-02-04
