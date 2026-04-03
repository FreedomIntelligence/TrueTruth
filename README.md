<div align="center">

# TrueTruth

**Evidence-Based Medicine Clinical Decision Support System**
**循证医学临床决策支持系统**

[![CI](https://github.com/Winda0001/ebm5a/actions/workflows/ci.yml/badge.svg)](https://github.com/Winda0001/ebm5a/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![LangChain](https://img.shields.io/badge/LangChain-0.1.0-green.svg)](https://python.langchain.com/)
[![OpenAI Compatible](https://img.shields.io/badge/API-OpenAI%20Compatible-412991.svg)](https://platform.openai.com/)
[![PubMed](https://img.shields.io/badge/data-PubMed%20Real--time-326599.svg)](https://pubmed.ncbi.nlm.nih.gov/)

[English](#english) · [中文](#chinese)

</div>

---

> [!CAUTION]
> **FOR RESEARCH AND EDUCATIONAL USE ONLY — NOT A MEDICAL DEVICE**
>
> TrueTruth is an experimental research tool. It has **not** been approved, cleared, or certified as a medical device by the FDA, CE mark, NMPA, or any other regulatory authority.
>
> - Outputs of this system are **not** a substitute for the clinical judgment of a licensed healthcare professional.
> - All recommendations must be **independently reviewed and validated** by a qualified clinician before any clinical decision is made.
> - The authors and contributors accept **no liability** for any patient harm or adverse outcome arising from clinical decisions made based on this system's output.
> - This system is **not** intended for use in emergency situations or for direct patient care without appropriate professional oversight.
> - Evidence retrieval and appraisal may be incomplete, outdated, or contain errors.
>
> By using this software, you agree that you are solely responsible for any clinical decisions and their outcomes.

> [!CAUTION]
> **仅供科研与教育用途——本系统不是医疗器械**
>
> TrueTruth 是一个实验性研究工具，**未经** FDA、CE、国家药品监督管理局（NMPA）或任何其他监管机构批准、许可或认证为医疗器械。
>
> - 本系统的输出**不能**替代持证医疗专业人员的临床判断。
> - 任何推荐建议在用于临床决策前，**必须**由具备资质的临床医生独立审查和验证。
> - 作者及贡献者对因依赖本系统输出而做出的临床决策所导致的任何患者伤害或不良后果**不承担任何责任**。
> - 本系统**不适用**于急诊场景或无专业人员监督下的直接患者诊疗。
> - 文献检索与证据评价结果可能不完整、已过时或包含错误。
>
> 使用本软件即表示您同意，您对所有临床决策及其后果承担全部责任。

---

<a id="english"></a>

### Quick Start

**Docker (recommended — one command, no environment setup):**

```bash
cp .env.example .env      # fill in LLM_API_KEY, PUBMED_EMAIL
make docker-up            # builds and starts backend + frontend
# Open http://localhost
```

**Manual (CLI only):**

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in your values
make check-env            # validate configuration
make cli QUERY="68-year-old with NSTEMI and acute GI bleed: DAPT or clopidogrel monotherapy?"
```

### Interfaces

| Interface | How to start | URL |
|-----------|-------------|-----|
| **Web UI** (Docker) | `make docker-up` | http://localhost |
| **Web UI** (manual) | `make dev-backend` + `make dev-frontend` | http://localhost:5173 |
| **CLI** | `make cli QUERY="..."` | — |

The Web UI provides real-time workflow visualisation, stage-by-stage scores, evidence tables, and history. The CLI outputs the full audit trail to `logs/`.

See [docs/troubleshooting.md](docs/troubleshooting.md) for common issues and [docs/glossary.md](docs/glossary.md) for GRADE/PICO/recommendation strength definitions.

---

## English

### What is TrueTruth?

TrueTruth is a **multi-agent pipeline** that turns a plain-text clinical question into a graded, evidence-backed recommendation — fully automatically, in under 10 minutes.

It operationalises the international **Evidence-Based Medicine 5A framework** (Ask → Acquire → Appraise → Apply → Assess) using a **ReAct** control loop: each stage is scored by a Judge LLM and routed by a Scheduling LLM, so quality failures are caught and corrected before the answer reaches you.

### The Trust Problem in Medical AI

*"Is this recommendation actually based on solid evidence — or is the AI just confident?"*

This is the question that blocks adoption of AI in clinical settings. A clinician cannot act on a recommendation they cannot verify. **Confidence without verifiability is not trust.**

TrueTruth is designed on one principle: trust must be earned through transparency, not claimed through authority. Every output is independently verifiable:

| What you need to verify | How TrueTruth lets you verify it |
|-------------------------|-------------------------------|
| Are the cited papers real? | Every citation carries a real PMID — look it up directly in PubMed |
| Is the evidence quality rating correct? | GRADE level is computed by deterministic Python code from LLM classification labels — the logic is inspectable |
| How did the system reach this conclusion? | Full audit trail: per-stage scores (0–1), issue lists, all backtrack events, all scheduling decisions |
| What if the evidence is weak or absent? | System returns explicit `Insufficient Evidence` — it will not force a recommendation |
| Was the output quality-checked? | Judge LLM scores every stage; system retries or backtracks until quality threshold is met |
| Can the code itself be audited? | Fully open source — every prompt, every scoring rule, every agent is readable |

---

### TrueTruth vs. OpenEvidence

[OpenEvidence](https://www.openevidence.com/) is a widely-adopted clinical AI platform serving over 40% of US physicians. Both systems aim to give clinicians evidence-backed answers at the point of care. The approaches differ substantially:

| Dimension | OpenEvidence | TrueTruth |
|-----------|-------------|--------|
| **Evidence appraisal** | Provides citations; no formal appraisal of evidence quality | Applies GRADE framework to each retrieved article; GRADE level computed deterministically by code |
| **When evidence is weak** | Generates an answer regardless of evidence strength | Returns explicit `Insufficient Evidence` — refuses to force a recommendation when evidence does not support one |
| **Output process** | Single-shot generation | Iterative ReAct loop: Judge LLM scores each stage; Scheduling LLM retries or backtracks until quality threshold is met |
| **Reasoning transparency** | Black-box; internal logic not auditable | Full audit trail: every stage score, every identified issue, every backtrack event, every scheduling decision |
| **Literature access** | Curated corpus via editorial agreements (NEJM, JAMA Network) | Direct real-time PubMed query — no editorial gatekeeping; captures any indexed paper regardless of publisher |
| **Source code** | Closed-source, proprietary | MIT-licensed open source — every prompt, rule, and agent is readable and forkable |

---

### Features

- **5A workflow** — Ask (PICO structuring) → Acquire (PubMed) → Appraise (GRADE) → Apply (recommendation) → Assess (quality check)
- **ReAct control loop** — Judge LLM scores every stage; Scheduling LLM decides proceed / retry / backtrack; hard-coded gate engine enforces safety bounds (max 20 iterations)
- **Real-time evidence** — three-tier PubMed query strategy (strict → moderate → relaxed) with 24-hour disk cache and MedCPT listwise re-ranking
- **Deterministic GRADE** — LLM classifies labels (e.g. `SERIOUS`, `NOT_SERIOUS`); Python computes the GRADE level deterministically — no LLM "interpretation" of grading rules
- **Five question types** — Therapy, Diagnosis, Prognosis, Harm, Prevention; each triggers a different PubMed filter
- **Four recommendation strengths** — Strong, Conditional (indirect evidence), Consensus-based (guideline/expert opinion), Insufficient Evidence
- **Crash-resistant JSON parsing** — three-stage recovery in every agent and the Judge LLM; malformed LLM output never crashes the workflow
- **OpenAI-compatible** — works with any provider exposing an OpenAI-style API; supports a separate fast model for Judge/Scheduling to reduce cost

---

### How It Works

```
Clinical Question
       │
  ┌────▼──────────────────────────────────────────────────────────────┐
  │                         Coordinator                               │
  │                                                                   │
  │   ① Ask ──► ② Acquire ──► ③ Appraise ──► ④ Apply ──► ⑤ Assess   │
  │       ▲          ▲              ▲              ▲          │       │
  │       │          │              │              │          ▼       │
  │       └───────── Scheduling LLM (next action) ◄──────────┘       │
  │                        ▲                                         │
  │                   Judge LLM (score 0–1, issue list)              │
  └───────────────────────────────────────────────────────────────────┘
                                  │
               ┌──────────────────┼──────────────────┐
               ▼                  ▼                  ▼
        Recommendation      Audit Trail        Quality Score
     (strength + quality)  (full history)       (0–1 / 1.0)
```

**Scheduling rules (hard overrides)**

| # | Condition | Forced action |
|---|-----------|---------------|
| 1 | All issues ≤ Minor **and** score passes | Must proceed — backtrack forbidden |
| 2 | Same stage retried ≥ 2× with no score improvement | Further backtrack forbidden |
| 3 | Remaining budget < 5 steps, no Critical issues | Prefer proceed |
| 4 | Assess stage passes, no Critical issues | Terminate — backtrack forbidden |

---

### Getting Started

#### Prerequisites

- Python **3.10+**
- An **OpenAI-compatible API key** (OpenAI, Azure OpenAI, or any compatible provider)
- A free **PubMed e-mail** (required by NCBI's API usage policy)
- *(Optional)* GPU or CPU with ≥ 8 GB RAM for MedCPT re-ranking (falls back to relevance score if unavailable)

#### Installation

```bash
# 1. Clone
git clone https://github.com/your-org/TrueTruth.git
cd ebm5a

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
```

Edit `.env`:

```dotenv
# Required
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4
PUBMED_EMAIL=your_email@example.com

# Optional — use a cheaper/faster model for Judge and Scheduling (~30-40% faster)
# FAST_LLM_MODEL=gpt-3.5-turbo
```

---

### Usage

#### Command line

```bash
python -m src.main "68-year-old male with NSTEMI and acute GI bleed (Hb 78 g/L). \
  Post-PCI antiplatelet strategy: DAPT vs clopidogrel monotherapy?"
```

#### Python API

```python
from src.main import run_clinical_question

result = run_clinical_question(
    "13-year-old male, SCORAD 74, erythroderma, refractory to topical therapy. "
    "Dupilumab vs JAK inhibitors — efficacy and safety comparison?"
)

rec = result["recommendation"]
print(rec.text)
print(f"Strength         : {rec.strength}")        # e.g. "Strong"
print(f"Evidence quality : {rec.evidence_quality}") # e.g. "High"
print(f"Rationale        : {rec.rationale}")

assess = result["assessment"]
print(f"Quality score    : {assess.quality_score:.2f} / 1.0")
```

#### Example output (abbreviated)

```
★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
CLINICAL ANSWER
★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

Q: 13-year-old male, SCORAD 74 ...

A: Dupilumab is recommended as first-line biologic therapy over JAK inhibitors
   for adolescents with severe atopic dermatitis, based on superior efficacy
   and a more established long-term safety profile.

   Recommendation Strength : Strong
   Evidence Quality        : High
   Overall Quality Score   : 0.82 / 1.0
```

> **Tip:** For therapy questions, prefix the question with a confirmed diagnosis:
> `"[Confirmed: severe atopic dermatitis] …"` — this helps Ask correctly classify the question type.

---

### Documentation

| Resource | Location |
|----------|----------|
| Architecture design | [`docs/`](docs/) |
| Internal development notes | [`docs/internal/`](docs/internal/) |
| Change history | [`CHANGELOG.md`](CHANGELOG.md) |
| Quick-start guide | [`QUICKSTART.md`](QUICKSTART.md) |
| Prompt templates | [`src/config/prompts/`](src/config/prompts/) |
| Evaluation dimensions | [`src/config/evaluation_dimensions/`](src/config/evaluation_dimensions/) |

---

### Project Structure

```
TrueTruth/
├── src/
│   ├── main.py                      # CLI entry point
│   ├── agents/
│   │   ├── base.py                  # Shared robust_parse_json() — 3-stage JSON recovery
│   │   ├── ask_agent.py             # PICO structuring + question type detection
│   │   ├── acquire_agent.py         # PubMed retrieval + MedCPT re-ranking
│   │   ├── appraise_agent.py        # GRADE appraisal (parallel batches)
│   │   ├── apply_agent.py           # Recommendation synthesis
│   │   └── assess_agent.py          # Reasoning chain quality check
│   ├── coordinator/
│   │   ├── coordinator.py           # ReAct loop, fast-path logic, timing
│   │   └── gate_engine.py           # Hard-coded safety guards
│   ├── scheduling/
│   │   └── scheduling_llm.py        # Decision LLM + 4 validation rules
│   ├── judge/
│   │   └── judge_llm.py             # Scoring LLM + JSON crash recovery
│   ├── state/
│   │   └── schema.py                # Pydantic/dataclass state definitions
│   ├── tools/
│   │   ├── pubmed_api.py            # PubMed client + 24h disk cache
│   │   └── medcpt.py                # MedCPT listwise re-ranker
│   └── config/
│       ├── llm_config.py            # get_llm() / get_fast_llm()
│       ├── prompts/                 # Agent & judge prompt templates (.txt)
│       └── evaluation_dimensions/   # Judge scoring rubrics (.json)
├── data/cache/                      # PubMed query cache (auto-generated)
├── logs/                            # Run logs with full audit trail
├── docs/                            # Design documents
├── CHANGELOG.md
├── QUICKSTART.md
├── requirements.txt
└── .env.example
```

---

### Contributing

Contributions are welcome — bug reports, feature requests, and pull requests alike.

**Report a bug or request a feature** → [open an issue](../../issues)

**Submit a pull request:**

```bash
# 1. Fork the repository and create a branch
git checkout -b feat/your-feature-name

# 2. Install dev dependencies
pip install -r requirements.txt

# 3. Make changes and verify
pytest

# 4. Commit and push
git commit -m "feat: describe your change"
git push origin feat/your-feature-name

# 5. Open a pull request against main
```

Please keep PRs focused on a single concern. Large refactors or new data-source integrations should be discussed in an issue first.

---

### License

This project is licensed under the **MIT License** — see [`LICENSE`](LICENSE) for details.

---

### Credits

- [NCBI PubMed](https://pubmed.ncbi.nlm.nih.gov/) — real-time biomedical literature database
- [MedCPT](https://github.com/ncbi/MedCPT) — biomedical dense retrieval and re-ranking model by NCBI
- [LangChain](https://python.langchain.com/) / [LangGraph](https://langchain-ai.github.io/langgraph/) — agent orchestration framework
- [GRADE Working Group](https://www.gradeworkinggroup.org/) — evidence grading methodology
- [shields.io](https://shields.io/) — README badges

---
---

<a id="chinese"></a>

### 快速开始

**Docker（推荐——一行命令，无需配置环境）：**

```bash
cp .env.example .env      # 填写 LLM_API_KEY 和 PUBMED_EMAIL
make docker-up            # 构建并启动后端 + 前端
# 访问 http://localhost
```

**手动（仅 CLI）：**

```bash
pip install -r requirements.txt
cp .env.example .env      # 填写相关配置
make check-env            # 验证配置
make cli QUERY="68岁男性，NSTEMI合并急性消化道出血：DAPT还是单用氯吡格雷？"
```

### 界面

| 界面 | 启动方式 | 访问地址 |
|------|---------|--------|
| **Web UI**（Docker） | `make docker-up` | http://localhost |
| **Web UI**（手动） | `make dev-backend` + `make dev-frontend` | http://localhost:5173 |
| **CLI** | `make cli QUERY="..."` | — |

Web UI 提供实时工作流可视化、逐阶段评分、证据表格和历史记录。CLI 将完整审计日志输出到 `logs/`。

常见问题请参阅 [docs/troubleshooting.md](docs/troubleshooting.md)；GRADE / PICO / 推荐强度等术语请参阅 [docs/glossary.md](docs/glossary.md)。

---

## 中文

### EBM 5A 是什么？

EBM 5A 是一个**多智能体流水线**，能将一段普通的临床问题文本全自动转化为经过分级的、有据可查的临床推荐，全程无需人工干预，典型耗时不超过 10 分钟。

系统将国际通行的**循证医学 5A 框架**（Ask → Acquire → Appraise → Apply → Assess）落地为自动化流程，并采用 **ReAct** 控制循环：每个阶段的输出均由 Judge LLM 评分、由 Scheduling LLM 路由，质量缺陷在答案到达用户之前即被发现并纠正。

### 医疗 AI 的信任问题

*"这个推荐真的有扎实的证据支撑吗——还是 AI 只是听起来很自信？"*

这正是阻碍 AI 进入临床场景的核心问题。医生无法对无法验证的推荐采取行动。**没有可验证性的自信，不是信任。**

EBM 5A 遵循一个原则：信任必须通过透明度赢得，而不是通过权威宣称。每一条输出都可以被独立核实：

| 你需要核实的内容 | EBM 5A 如何让你核实 |
|----------------|-------------------|
| 引用的论文是真实存在的吗？ | 每条引用都附带真实 PMID——可直接在 PubMed 中查阅 |
| 证据质量评级是否准确？ | GRADE 等级由确定性 Python 代码从 LLM 分类标签计算而来——逻辑完全可检查 |
| 系统是如何得出这个结论的？ | 完整审计追踪：每阶段评分（0–1）、问题清单、所有回退事件、所有调度决策 |
| 如果证据薄弱或缺失怎么办？ | 系统返回明确的 `Insufficient Evidence`——不会强行给出推荐 |
| 输出结果经过质量检查了吗？ | Judge LLM 对每个阶段评分；未达标则重试或回退，直到通过质量阈值 |
| 代码本身可以被审计吗？ | 完全开源——每一条提示词、每一条评分规则、每一个智能体均可阅读 |

---

### EBM 5A vs. OpenEvidence

[OpenEvidence](https://www.openevidence.com/) 是目前被超过 40% 美国医生使用的临床 AI 平台。两个系统的目标相同：在诊疗现场为临床医生提供有据可查的答案。但实现方式存在本质区别：

| 维度 | OpenEvidence | EBM 5A |
|------|-------------|--------|
| **证据评价机制** | 提供引用；无正式证据质量评价 | 对每篇检索文献应用 GRADE 框架；GRADE 等级由代码确定性计算 |
| **证据薄弱时的行为** | 无论证据强弱，都会生成答案 | 返回明确的 `Insufficient Evidence`——证据不足时拒绝强行推荐 |
| **输出过程** | 单次生成 | 迭代式 ReAct 循环：Judge LLM 对每阶段评分，Scheduling LLM 在质量未通过时重试或回退 |
| **推理透明度** | 黑盒；内部逻辑不可审计 | 完整审计追踪：每阶段评分、每条问题、每次回退事件、每次调度决策均有记录 |
| **文献获取方式** | 通过编辑协议获取策展语料库（NEJM、JAMA Network 等） | 实时直接查询 PubMed——无编辑准入门槛，任何已索引论文均可获取 |
| **源代码** | 闭源商业产品 | MIT 协议完全开源——每一条提示词、规则和智能体均可阅读和 Fork |

---

### 核心特性

- **5A 工作流** — Ask（PICO 结构化）→ Acquire（PubMed 检索）→ Appraise（GRADE 评价）→ Apply（生成推荐）→ Assess（质量审查）
- **ReAct 控制循环** — Judge LLM 对每阶段评分；Scheduling LLM 决定前进/重试/回退；硬编码门控引擎强制安全边界（最多 20 次迭代）
- **实时文献检索** — 三层 PubMed 查询策略（严格 → 中等 → 宽松），24 小时磁盘缓存，MedCPT Listwise 重排序
- **GRADE 确定性计算** — LLM 只负责输出分类标签（如 `SERIOUS`、`NOT_SERIOUS`），Python 代码负责确定性地计算 GRADE 等级，不依赖 LLM 对评级规则的"理解"
- **五种问题类型** — 治疗（Therapy）、诊断（Diagnosis）、预后（Prognosis）、危害（Harm）、预防（Prevention），每种类型触发不同 PubMed 过滤器
- **四级推荐强度** — Strong（强）、Conditional（条件性，间接证据）、Consensus-based（基于共识，指南/专家意见）、Insufficient Evidence（证据不足）
- **鲁棒 JSON 解析** — 每个智能体与 Judge LLM 内置三阶段恢复逻辑，LLM 输出格式错误不会导致流程崩溃
- **OpenAI 兼容** — 支持任何暴露 OpenAI 风格 API 的服务商；Judge/Scheduling 可单独配置更快的轻量模型以降低成本

---

### 工作原理

```
临床问题输入
     │
┌────▼────────────────────────────────────────────────────────────────┐
│                          Coordinator                                │
│                                                                     │
│   ① Ask ──► ② Acquire ──► ③ Appraise ──► ④ Apply ──► ⑤ Assess     │
│       ▲          ▲              ▲              ▲          │         │
│       │          │              │              │          ▼         │
│       └─────── Scheduling LLM（决定下一步行动） ◄──────────┘         │
│                       ▲                                             │
│                  Judge LLM（评分 0–1，输出问题清单）                  │
└─────────────────────────────────────────────────────────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
     临床推荐结果          完整审计追踪          质量评分
  （推荐强度 + 证据质量）  （全历史记录）        （0–1 / 1.0）
```

**Scheduling 四条强制规则（硬覆盖）**

| # | 触发条件 | 强制行为 |
|---|----------|---------|
| 1 | 所有问题 ≤ Minor **且**评分通过阈值 | 必须前进，禁止回退 |
| 2 | 同一阶段已重试 ≥ 2 次且评分无改善 | 禁止继续回退 |
| 3 | 剩余预算 < 5 步且无 Critical 问题 | 优先前进 |
| 4 | Assess 阶段通过且无 Critical 问题 | 终止工作流，禁止回退 |

---

### 快速开始

#### 环境依赖

- Python **3.10+**
- 兼容 OpenAI 的 **API Key**（OpenAI、Azure OpenAI 或其他兼容服务商均可）
- 一个免费的 **PubMed 注册邮箱**（NCBI API 使用规范要求）
- （可选）≥ 8 GB 内存的 GPU 或 CPU，用于 MedCPT 重排序（不可用时自动回退到相关性评分）

#### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/TrueTruth.git
cd ebm5a

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
```

编辑 `.env`：

```dotenv
# 必填
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4
PUBMED_EMAIL=your_email@example.com

# 可选——让 Judge 和 Scheduling 使用更快/更便宜的模型（节省约 30-40% 时间）
# FAST_LLM_MODEL=gpt-3.5-turbo
```

---

### 使用方式

#### 命令行

```bash
python -m src.main "68岁男性，急性NSTEMI合并急性消化道出血（Hb 78 g/L）。\
  PCI术后抗血小板方案：DAPT还是氯吡格雷单药？"
```

#### Python API

```python
from src.main import run_clinical_question

result = run_clinical_question(
    "13岁男性，SCORAD 74分，红皮病，多种外用药无效。"
    "度普利尤单抗与JAK抑制剂——疗效与安全性比较？"
)

rec = result["recommendation"]
print(rec.text)
print(f"推荐强度 : {rec.strength}")        # 例如 "Strong"
print(f"证据质量 : {rec.evidence_quality}") # 例如 "High"
print(f"推荐理由 : {rec.rationale}")

assess = result["assessment"]
print(f"质量评分 : {assess.quality_score:.2f} / 1.0")
```

#### 输出示例（节选）

```
★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
CLINICAL ANSWER
★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

Q: 13岁男性，SCORAD 74分...

A: 对于重度特应性皮炎青少年患者，推荐度普利尤单抗作为一线生物制剂治疗，
   优先于JAK抑制剂。现有证据（含2025年儿科专项网络Meta分析）显示其疗效
   更优，长期安全性数据更为充分。

   推荐强度 : Strong
   证据质量 : High
   质量评分 : 0.82 / 1.0
```

> **建议**：治疗类问题提问前先写明诊断，例如「【已明确诊断：重度特应性皮炎】…」，这有助于 Ask Agent 正确识别问题类型。

---

### 文档

| 资源 | 位置 |
|------|------|
| 架构设计文档 | [`docs/`](docs/) |
| 内部开发记录 | [`docs/internal/`](docs/internal/) |
| 变更记录 | [`CHANGELOG.md`](CHANGELOG.md) |
| 快速开始指南 | [`QUICKSTART.md`](QUICKSTART.md) |
| 提示词模板 | [`src/config/prompts/`](src/config/prompts/) |
| 评价维度定义 | [`src/config/evaluation_dimensions/`](src/config/evaluation_dimensions/) |

---

### 项目结构

```
TrueTruth/
├── src/
│   ├── main.py                      # CLI 入口
│   ├── agents/
│   │   ├── base.py                  # 共享 robust_parse_json()——三阶段 JSON 恢复
│   │   ├── ask_agent.py             # PICO 结构化 + 问题类型识别
│   │   ├── acquire_agent.py         # PubMed 检索 + MedCPT 重排序
│   │   ├── appraise_agent.py        # GRADE 评价（并行批次）
│   │   ├── apply_agent.py           # 推荐综合生成
│   │   └── assess_agent.py          # 推理链质量审查
│   ├── coordinator/
│   │   ├── coordinator.py           # ReAct 循环、FAST-PATH 逻辑、计时埋点
│   │   └── gate_engine.py           # 硬编码安全门控
│   ├── scheduling/
│   │   └── scheduling_llm.py        # 决策 LLM + 四条验证规则
│   ├── judge/
│   │   └── judge_llm.py             # 评分 LLM + JSON 崩溃恢复
│   ├── state/
│   │   └── schema.py                # 状态数据结构定义（dataclass + TypedDict）
│   ├── tools/
│   │   ├── pubmed_api.py            # PubMed 客户端 + 24小时磁盘缓存
│   │   └── medcpt.py                # MedCPT Listwise 重排序
│   └── config/
│       ├── llm_config.py            # get_llm() / get_fast_llm()
│       ├── prompts/                 # 各智能体与 Judge 提示词模板（.txt）
│       └── evaluation_dimensions/   # Judge 评分维度定义（.json）
├── data/cache/                      # PubMed 查询缓存（自动生成）
├── logs/                            # 运行日志（含完整审计追踪）
├── docs/                            # 设计文档
├── CHANGELOG.md
├── QUICKSTART.md
├── requirements.txt
└── .env.example
```

---

### 贡献指南

欢迎提交 Bug 报告、功能建议和 Pull Request。

**报告 Bug 或提交建议** → [提交 Issue](../../issues)

**提交 Pull Request：**

```bash
# 1. Fork 仓库并创建分支
git checkout -b feat/your-feature-name

# 2. 安装依赖
pip install -r requirements.txt

# 3. 完成修改并验证
pytest

# 4. 提交并推送
git commit -m "feat: 简述你的改动"
git push origin feat/your-feature-name

# 5. 向 main 分支发起 Pull Request
```

请保持每个 PR 聚焦于单一改动。大型重构或新数据源集成建议先在 Issue 中讨论。

---

### 开源协议

本项目基于 **MIT 协议**开源，详见 [`LICENSE`](LICENSE)。

---

### 致谢

- [NCBI PubMed](https://pubmed.ncbi.nlm.nih.gov/) — 实时生物医学文献数据库
- [MedCPT](https://github.com/ncbi/MedCPT) — NCBI 开发的生物医学密集检索与重排序模型
- [LangChain](https://python.langchain.com/) / [LangGraph](https://langchain-ai.github.io/langgraph/) — 智能体编排框架
- [GRADE Working Group](https://www.gradeworkinggroup.org/) — 证据分级方法论
- [shields.io](https://shields.io/) — README 徽章生成
