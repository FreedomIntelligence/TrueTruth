<div align="center">

# TrueTruth

**循证医学临床决策支持系统**

[![CI](https://github.com/Winda0001/ebm5a/actions/workflows/ci.yml/badge.svg)](https://github.com/Winda0001/ebm5a/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenAI Compatible](https://img.shields.io/badge/API-OpenAI%20Compatible-412991.svg)](https://platform.openai.com/)
[![RAG](https://img.shields.io/badge/data-Hypertension%20RAG-326599.svg)](https://github.com/FreedomIntelligence/TrueTruth)

</div>

> [!CAUTION]
> **仅供科研与教育用途——本系统不是医疗器械**
>
> EBM 5A 是实验性研究工具，未经任何监管机构批准为医疗器械。系统输出**不能替代**持证医疗专业人员的临床判断。任何推荐在用于临床决策前，**必须**由具备资质的临床医生独立审查。作者对依赖本系统输出所导致的任何患者伤害**不承担任何责任**。

---

## 项目特色

TrueTruth将一段普通的临床问题文本全自动转化为**经过分级的、可独立核实的**临床推荐，典型耗时不超过 10 分钟。

系统将国际通行的**循证医学 5A 框架**（Ask → Acquire → Appraise → Apply → Assess）落地为自动化多智能体流水线，以 **ReAct 控制循环**驱动：每个阶段由 Judge LLM 评分，由 Scheduling LLM 决定前进 / 重试 / 回退，质量问题在答案到达用户之前即被捕获并纠正。

### 核心能力

| 特性 | 说明 |
|------|------|
| **5A 工作流** | Ask（PICO 结构化）→ Acquire（RAG 检索）→ Appraise（GRADE 评价）→ Apply（生成推荐）→ Assess（质量审查） |
| **GRADE 确定性计算** | LLM 输出分类标签，Python 代码确定性地计算 GRADE 等级，不依赖 LLM 对评级规则的理解 |
| **五种问题类型** | Therapy / Diagnosis / Prognosis / Harm / Prevention，每种类型触发不同检索策略 |
| **四级推荐强度** | Strong、Conditional（间接证据）、Consensus-based（指南/专家共识）、Insufficient Evidence |
| **Hypertension RAG** | 基于高血压领域 landmark trial 的向量检索服务，提供结构化证据块与 passage 级引用 |
| **鲁棒 JSON 解析** | 每个 Agent 与 Judge LLM 内置三阶段 JSON 恢复，LLM 输出格式错误不会导致工作流崩溃 |
| **完整审计追踪** | 每阶段评分（0–1）、问题清单、回退事件、调度决策全部记录，每条引用附带真实来源 |
| **OpenAI 兼容** | 支持任何 OpenAI 兼容 API；Judge/Scheduling 可配置独立的快速模型以降低成本 |

### 工作流程

```
临床问题
   │
┌──▼──────────────────────────────────────────────────────────┐
│                        Coordinator                          │
│  ① Ask ──► ② Acquire ──► ③ Appraise ──► ④ Apply ──► ⑤ Assess │
│      ▲          ▲              ▲              ▲        │    │
│      └───────── Scheduling LLM（决定下一步动作）◄───────┘    │
│                      ▲                                      │
│                 Judge LLM（评分 0–1，输出问题清单）           │
└─────────────────────────────────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
    临床推荐结果       完整审计追踪       质量评分
 （推荐强度+证据质量） （全历史记录）    （0–1 / 1.0）
```

---

## 快速开始

### 前提条件

- Python **3.10+**
- 兼容 OpenAI 的 API Key（OpenAI、Azure OpenAI 或其他兼容服务商）
- Hypertension RAG 服务（见下方说明）
- Docker + Docker Compose（仅 Docker 部署方式需要）

### 方式一：Docker（推荐）

```bash
git clone https://github.com/FreedomIntelligence/TrueTruth.git
cd TrueTruth
cp .env.example .env        # 填写 LLM_API_KEY、LLM_BASE_URL、LLM_MODEL
make check-env              # 验证配置（可选但推荐）
make docker-up              # 构建镜像并启动，首次约需 3–5 分钟
# 浏览器打开 http://localhost:8080
```

停止服务：`make docker-down`

### 方式二：手动（CLI）

```bash
git clone https://github.com/FreedomIntelligence/TrueTruth.git
cd ebm5a
pip install -r requirements.txt
cp .env.example .env        # 填写配置
make check-env              # 验证配置
make cli QUERY="68岁男性，NSTEMI合并急性消化道出血，DAPT还是氯吡格雷单药？"
```

### 配置说明（`.env`）

```dotenv
# 必填
LLM_BASE_URL=xxx
LLM_API_KEY=sk-...
LLM_MODEL=xxx

# Hypertension RAG 服务地址（默认本地 8000 端口）
HYPERTENSION_API_URL=http://localhost:8000

# 可选——Judge/Scheduling 使用更快的轻量模型，可节省约 30–40% 耗时
# FAST_LLM_MODEL=gpt-4o-mini
```

### 启动界面汇总

| 界面 | 启动命令 | 访问地址 |
|------|---------|--------|
| Web UI（Docker） | `make docker-up` | http://localhost:8080 |
| Web UI（手动） | `make dev-backend` + `make dev-frontend` | http://localhost:5173 |
| CLI | `make cli QUERY="..."` | — |

Web UI 提供实时工作流可视化、逐阶段评分、证据表格和历史记录。CLI 将完整审计日志输出到 `logs/`。

> 常见问题 → [docs/troubleshooting.md](docs/troubleshooting.md)
> 术语说明 → [docs/glossary.md](docs/glossary.md)

---

## 项目结构

```
ebm5a/
├── src/                              # 核心多智能体引擎
│   ├── main.py                       # CLI 入口
│   ├── agents/
│   │   ├── base.py                   # 共享三阶段 JSON 恢复
│   │   ├── ask_agent.py              # PICO 结构化 + 问题类型识别
│   │   ├── acquire_agent.py          # Hypertension RAG 检索
│   │   ├── appraise_agent.py         # GRADE 评价（并行批次）
│   │   ├── apply_agent.py            # 推荐综合生成
│   │   └── assess_agent.py           # 推理链质量审查
│   ├── coordinator/
│   │   ├── coordinator.py            # ReAct 主循环 + FAST-PATH 规则
│   │   └── gate_engine.py            # 硬编码安全门控
│   ├── judge/
│   │   └── judge_llm.py              # 评分 LLM + 崩溃恢复
│   ├── scheduling/
│   │   └── scheduling_llm.py         # 决策 LLM + 四条强制规则
│   ├── state/
│   │   └── schema.py                 # 状态数据结构（dataclass + TypedDict）
│   ├── tools/
│   │   ├── hypertension_rag_client.py  # Hypertension RAG HTTP 客户端
│   │   └── medcpt.py                 # MedCPT 重排序（可选）
│   └── config/
│       ├── llm_config.py             # get_llm() / get_fast_llm()
│       ├── prompts/                  # 各 Agent 与 Judge 提示词（.txt）
│       └── evaluation_dimensions/    # Judge 评分维度定义（.json）
│
├── web/                              # Web 界面
│   ├── backend/
│   │   ├── app.py                    # FastAPI 应用 + SSE 流式端点
│   │   ├── instrumented_coordinator.py  # 注入事件流的 Coordinator 包装
│   │   ├── serializers.py            # 状态序列化为 SSE 事件
│   │   └── event_types.py            # SSE 事件类型定义
│   └── frontend/                     # React + Vite 前端
│       └── src/
│           ├── components/           # UI 组件（WorkflowPipeline、EvidenceTable 等）
│           ├── hooks/useWorkflowSSE.js  # SSE 连接管理
│           └── store/workflowStore.js   # Zustand 全局状态
│
├── scripts/
│   └── check_env.py                  # 配置验证脚本（make check-env）
├── tests/                            # 测试目录
├── docs/                             # 设计文档与故障排查
├── logs/                             # 运行日志（自动生成）
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── docker-compose.dev.yml            # 开发模式覆盖（源码挂载 + --reload）
├── Makefile                          # 统一命令入口
├── requirements.txt                  # Python 依赖
├── requirements-web.txt              # Web 后端额外依赖
└── .env.example                      # 配置模板
```

---

## 开发指南

### 环境准备

```bash
pip install -r requirements.txt -r requirements-web.txt
cd web/frontend && npm install
```

### 常用命令

```bash
make dev-backend    # 启动 FastAPI 后端，热重载（端口 8000）
make dev-frontend   # 启动 Vite 开发服务器（端口 5173）
make dev            # 前后端同时启动（Ctrl+C 一键停止）

make lint           # ruff 代码检查
make format         # ruff 自动格式化
make test           # pytest 测试套件

make check-env      # 验证 .env 配置
make cli QUERY="..."  # 命令行运行一次查询

make docker-up      # 构建并启动生产 Docker 栈
make docker-down    # 停止 Docker 栈
make docker-logs    # 查看 Docker 日志
```

### 开发模式 Docker（支持热重载）

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

后端源码挂载到容器，保存文件即自动重启，无需重新构建镜像。

### 修改提示词

提示词存放在 `src/config/prompts/`，每个 Agent 和 Judge 各有独立的 `.txt` 文件。修改后直接重启进程生效，无需编译。

### 修改评分维度

评分维度定义在 `src/config/evaluation_dimensions/*.json`。每个维度包含 `name`、`weight`、`scoring_criteria` 字段，由 Judge LLM 在评分时参考。

### 提交代码

```bash
git checkout -b feat/your-feature
# ... 修改 ...
make lint           # 必须通过
make test           # 必须通过
git commit -m "feat: 简述改动"
# 发起 Pull Request，请保持每个 PR 聚焦于单一改动
```

---

## 文档

| 资源 | 位置 |
|------|------|
| 故障排查 | [docs/troubleshooting.md](docs/troubleshooting.md) |
| 术语表（GRADE / PICO / 推荐强度） | [docs/glossary.md](docs/glossary.md) |
| 架构设计 | [docs/architecture.md](docs/architecture.md) |
| 快速开始详细版 | [QUICKSTART.md](QUICKSTART.md) |
| 变更记录 | [CHANGELOG.md](CHANGELOG.md) |

---

## License

MIT © Winda0001 — 详见 [LICENSE](LICENSE)

---

## 致谢

- [MedCPT](https://github.com/ncbi/MedCPT) — NCBI 开发的生物医学密集检索与重排序模型
- [GRADE Working Group](https://www.gradeworkinggroup.org/) — 证据分级方法论
