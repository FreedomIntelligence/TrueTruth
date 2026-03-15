# EBM 5A 循证医学临床决策支持系统

基于 ReAct 模式、实现循证医学"5A"框架（Ask-Acquire-Appraise-Apply-Assess）的多智能体临床决策支持系统。

---

## 系统概述

### 为什么需要这个系统？

通用大语言模型（LLM）在临床决策辅助中存在两个根本性缺陷：

1. **时效性问题**：训练数据有截止日期，无法获取最新 RCT、系统综述和 Meta 分析
2. **可信度问题**：可能产生文献"幻觉"（错误的作者、期刊、药物名称），且推理过程不透明

EBM 5A 系统通过将循证医学方法论（PICO 结构化 → 实时文献检索 → GRADE 证据分级 → 推荐生成 → 质量评估）落地为自动化流水线，弥补上述缺陷。

### 核心价值

- **实时检索**：通过 PubMed API 获取最新文献，突破 LLM 知识截止日期限制
- **可追溯推荐**：每一步均有评分记录、问题清单和决策理由，非黑盒输出
- **标准化证据分级**：采用国际通用 GRADE 框架，推荐强度与证据质量硬性绑定
- **内置质量控制**：Judge LLM 评价每阶段输出，Scheduling LLM 自动检测并修正质量问题

---

## 5A 工作流程

```
临床问题输入
     ↓
① Ask       将临床问题结构化为 PICO 格式（患者/干预/对照/结局）
     ↓
② Acquire   三层检索策略实时搜索 PubMed，Listwise 排序筛选 Top 10 文献
     ↓
③ Appraise  GRADE 框架评价每篇文献质量（High/Moderate/Low/Very Low）
     ↓
④ Apply     综合评价结果生成临床推荐，推荐强度与 GRADE 等级硬性绑定
     ↓
⑤ Assess    审查推理链完整性与逻辑一致性，识别知识缺口
     ↓
临床推荐输出（含推荐强度 + 证据等级 + 注意事项）
```

每个阶段执行后，**Judge LLM** 对输出评分（0~1），**Scheduling LLM** 根据评分决定前进、重试或回退到任意前置阶段。

---

## 系统架构

### 组件构成

| 组件 | 职责 |
|------|------|
| **5 个专门智能体** | 每个智能体有独立提示词，只负责 5A 中的一个步骤 |
| **Judge LLM** | 对每阶段输出评分，识别 Critical / Major / Minor 问题 |
| **Scheduling LLM** | 读取评分，决策下一步行动；内置四条强制决策验证规则 |
| **硬规则引擎** | 证据质量门控、空结果门控、死循环检测、最大迭代门控（上限 20 步） |
| **PubMed API** | 实时文献检索，支持三层查询策略（严格 / 中等 / 宽松） |

### ReAct 循环

```
执行（Act）→ 评价（Observe）→ 推理（Reason）→ 调度（Act）→ ...
  智能体         Judge LLM      Scheduling LLM    下一步行动
```

### Scheduling LLM 四条强制规则

| 规则 | 条件 | 强制行为 |
|------|------|---------|
| Rule 1 | 所有问题均为 Minor 且评分通过 | 必须 proceed，不允许回退 |
| Rule 2 | 同一阶段已回退 ≥2 次且评分无改善 | 不允许再次回退 |
| Rule 3 | 剩余预算 < 5 步且无 Critical 问题 | 优先 proceed |
| Rule 4 | Assess 阶段通过且无 Critical 问题 | 完成工作流，禁止回退 |

---

## 已实施的关键改进

### 1. JSON 解析鲁棒性（`src/agents/base.py`）

LLM 在输出复杂 JSON 时偶发语法错误（缺少逗号、尾部逗号等），原有代码直接崩溃。

实现了三阶段恢复机制 `robust_parse_json()`，覆盖全部 5 个智能体和 Judge LLM：
1. 直接解析
2. 提取 ` ```json ` 代码块后解析
3. 启发式正则修复后解析（移除尾部逗号、补全缺失逗号）

### 2. Scheduling LLM 决策验证层（`src/scheduling/scheduling_llm.py`）

早期版本（2026-02-07）因调度 LLM 过度保守触发死循环（12 次迭代，异常终止）。实现决策验证层后，系统可正常完成，迭代次数降至 7 次。

### 3. Appraise 阶段 GRADE 计算确定性化（`src/agents/appraise_agent.py`）

原设计让 LLM 直接输出 GRADE 等级，结果不一致。改为：
- LLM 只负责**分类**（输出标签：SERIOUS / NOT_SERIOUS 等）
- Python 代码负责**确定性计算**最终 GRADE 等级

确保 GRADE 规则被严格执行，而非依赖 LLM 的"理解"。

### 4. Acquire 三层检索策略（`src/agents/acquire_agent.py`）

单一查询策略在特定问题上返回 0 结果或过多无关结果。改为内部自动调整：
- **严格查询**：全部 PICO 关键词 + MeSH 术语 + 研究类型过滤
- **中等查询**：核心关键词 + 适当放宽
- **宽松查询**：仅核心术语，不限制发表年份

内部处理查询失败，不再触发全局回退到 Ask 阶段。

---

## 测试结果

### 案例一：NSTEMI 合并消化道出血

**问题**：68 岁男性，急性非 ST 段抬高型心肌梗死（NSTEMI），同时合并急性消化道出血（Hb 78 g/L）。PCI 术后 DAPT 方案如何选择？

**系统表现**：
- 检索到 OPT-BIRISK 研究（PMID 39382876，2024 年）：出血高风险患者 PCI 后氯吡格雷单药治疗证据
- 直接询问 LLM：错误记忆 OPT-BIRISK 中的药物名（混淆为替格瑞洛）及发表期刊
- **质量评分：0.78 / 1.0**，推荐强度：Strong，证据质量：Moderate

### 案例二：青少年重度特应性皮炎

**问题**：13 岁男性，SCORAD 74 分，红皮病，多种外用药物无效。度普利尤单抗 vs JAK 抑制剂的疗效与安全性比较？

**系统表现**：
- 检索到 PMID 39992967、39936572（2025 年儿科专项网络 Meta 分析），LLM 因训练截止日期无法获取
- 推荐结论（度普利尤单抗首选）与临床实际一致
- **质量评分：0.82 / 1.0**，推荐强度：Strong，证据质量：High

---

## 使用方式

### 适合的问题类型

- 治疗方案比较（A vs B 在某人群中的疗效/安全性）
- 预防或干预策略选择
- 已明确诊断后的管理方案

> **建议**：提问前先写明诊断（如"【已明确诊断：重度特应性皮炎】"），系统对治疗类问题的表现最佳。

### 不适合的问题类型

- 纯诊断推理（"这个患者得了什么病？"）
- 需要实时患者数据的剂量计算

### 命令行

```bash
python -m src.main "13岁重度特应性皮炎患者，度普利尤单抗与JAK抑制剂疗效安全性如何比较？"
```

### Python API

```python
from src.main import run_clinical_question

result = run_clinical_question("你的临床问题")

print(result["recommendation"].text)
print(f"推荐强度: {result['recommendation'].strength}")
print(f"证据质量: {result['recommendation'].evidence_quality}")
```

---

## 安装配置

```bash
pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`：

```
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_api_key_here
LLM_MODEL=gpt-4
PUBMED_EMAIL=your_email@example.com
```

---

## 项目结构

```
ebm5a/
├── src/
│   ├── agents/          # 5 个专门智能体（Ask/Acquire/Appraise/Apply/Assess）
│   ├── coordinator/     # 工作流编排、门控引擎
│   ├── scheduling/      # Scheduling LLM（含决策验证层）
│   ├── judge/           # Judge LLM
│   ├── state/           # 状态管理与数据结构
│   ├── tools/           # PubMed API、MedCPT 检索工具
│   ├── config/          # LLM 配置、提示词模板
│   └── main.py          # 入口
├── tests/               # 测试套件
├── logs/                # 运行日志（含完整审计追踪）
└── docs/                # 设计文档
```

---

## 测试

```bash
pytest                                      # 全部测试
pytest --cov=src --cov-report=html         # 覆盖率报告
pytest tests/agents/test_ask_agent.py -v   # 单个模块测试
```

---

## 局限性与下一步计划

### 当前局限

- **速度**：典型运行时间 6-10 分钟（多次串行 LLM 调用；配置 `FAST_LLM_MODEL` 可节省约 30%）
- **数据源**：仅限 PubMed，不包含 ACC/AHA、ESC 等主要临床指南全文（Consensus-based 推荐可引用指南知识）
- **语言**：文献检索为英文；中文指南、国内共识暂不支持
- **问题类型**：已支持 Therapy/Diagnosis/Prognosis/Harm/Prevention 五类；复合多 PICO 问题仍以主要 PICO 处理

### 性能优化说明

系统已实施多项优化（详见 [CHANGELOG.md](CHANGELOG.md)）：FAST-PATH 快速跳过、PubMed 并行 fetch + 磁盘缓存、Appraise 并行批次等。

**最有效的未实施优化**：在 `.env` 中配置 `FAST_LLM_MODEL=claude-sonnet-4-6`，让 Judge/Scheduling 使用轻量模型，可节省总时间约 30-40%。

### 计划中的改进

- 集成主要临床指南数据源（ACC/AHA、ESC 全文索引）
- NNT/NNH 等数值数据自动提取
- 支持多 PICO 分解（复合问题拆分为独立子问题并行处理）
- 中文指南与国内共识数据库接入

---

## License

MIT
