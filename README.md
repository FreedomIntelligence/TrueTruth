<div align="center">

# TrueTruth

**循证医学临床决策支持系统**

[![CI](https://github.com/Winda0001/ebm5a/actions/workflows/ci.yml/badge.svg)](https://github.com/Winda0001/ebm5a/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenAI Compatible](https://img.shields.io/badge/API-OpenAI%20Compatible-412991.svg)](https://platform.openai.com/)

</div>

> [!CAUTION]
> **仅供科研与教育用途——本系统不是医疗器械**
>
> EBM 5A 是实验性研究工具，未经任何监管机构批准为医疗器械。系统输出**不能替代**持证医疗专业人员的临床判断。任何推荐在用于临床决策前，**必须**由具备资质的临床医生独立审查。作者对依赖本系统输出所导致的任何患者伤害**不承担任何责任**。

---

## 项目简介

TrueTruth 将一段普通的临床问题文本全自动转化为**经过分级的、可独立核实的**临床推荐。

系统实现国际通行的**循证医学 5A 框架**（Ask → Acquire → Appraise → Apply → Assess），以多智能体流水线 + **ReAct 控制循环**驱动，配合内置的高血压证据向量库（Hypertension RAG）提供结构化证据检索。

---

## 快速开始（3 步）

### 前提条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 已安装并运行
- 一个 OpenAI 兼容的 LLM API Key
- 一个[智谱 API Key](https://open.bigmodel.cn/)（用于证据库检索的 Embedding）

### 部署步骤

```bash
# 1. 克隆项目
git clone https://github.com/FreedomIntelligence/TrueTruth.git
cd TrueTruth

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填写以下必填项：
#   LLM_API_KEY      — 你的 LLM API Key
#   LLM_BASE_URL     — LLM API 地址
#   LLM_MODEL        — 模型名称
#   ZHIPU_API_KEY    — 智谱 API Key（用于证据库 Embedding）
#   PUBMED_EMAIL     — 你的邮箱（PubMed API 要求）

# 3. 一键启动
docker compose up
# 首次启动会自动拉取预置证据库镜像（~500MB），约需 3–5 分钟
# 浏览器打开 http://localhost:8080
```

> 停止服务：`docker compose down`

### Docker 会启动以下服务

| 服务 | 说明 | 端口 |
|------|------|------|
| `qdrant` | 向量数据库（预置高血压证据数据） | 6333 |
| `hypertensiondb` | 证据检索 API | 8000（内部） |
| `backend` | EBM 5A 主服务（FastAPI） | 8000（内部） |
| `frontend` | Web 界面（Nginx） | **8080** |

---

## 手动运行（不使用 Docker）

适合需要修改代码或调试的开发者。

### 1. 安装依赖

```bash
# 主项目
pip install -r requirements.txt -r requirements-web.txt

# 证据库服务
cd hypertension
pip install -e .
cd ..
```

### 2. 启动 Qdrant

```bash
cd hypertension
docker compose up -d    # 仅启动 Qdrant 容器
cd ..
```

> 如果是首次使用，需要构建索引：`cd hypertension && hdb index rebuild --confirm`
> 这需要智谱 API Key 并耗时约 5–10 分钟。

### 3. 启动服务

```bash
# 终端 1：启动证据库 API
cd hypertension && hdb serve run --port 8000

# 终端 2：启动主后端
make dev-backend

# 终端 3：启动前端
make dev-frontend
```

或使用 CLI 模式：
```bash
python src/main.py "68岁男性，高血压合并糖尿病，ACEI还是ARB？"
```

---

## 配置说明

所有配置在 `.env` 文件中，详见 `.env.example` 的注释。

| 变量 | 必填 | 说明 |
|------|------|------|
| `LLM_BASE_URL` | ✅ | LLM API 地址 |
| `LLM_API_KEY` | ✅ | LLM API Key |
| `LLM_MODEL` | ✅ | 模型名称 |
| `PUBMED_EMAIL` | ✅ | PubMed API 要求的邮箱 |
| `ZHIPU_API_KEY` | ✅ | 智谱 Embedding API Key（证据库检索） |
| `FAST_LLM_MODEL` | ❌ | Judge/Scheduling 用更快的模型，节省 ~30–40% 耗时 |

---

## 项目结构

```
ebm5a/
├── src/                              # 核心多智能体引擎
│   ├── main.py                       # CLI 入口
│   ├── agents/                       # 5A 各阶段 Agent
│   ├── coordinator/                  # ReAct 主循环 + 安全门控
│   ├── judge/                        # Judge LLM 评分
│   ├── scheduling/                   # Scheduling LLM 决策
│   ├── tools/                        # RAG 客户端
│   └── config/                       # LLM 配置 + 提示词
│
├── web/                              # Web 界面
│   ├── backend/                      # FastAPI + SSE
│   └── frontend/                     # React + Vite
│
├── hypertension/                     # 高血压证据库子项目
│   ├── evidence/                     # 证据源文件（.md）
│   ├── src/hypertensiondb/           # 检索服务代码
│   ├── Dockerfile                    # 证据库 API 镜像
│   └── docker-compose.yml            # 单独启动 Qdrant 用
│
├── docker-compose.yml                # 统一部署（4 个服务）
├── Dockerfile.backend                # 主后端镜像
├── Dockerfile.frontend               # 前端镜像
├── Dockerfile.qdrant                 # 预置数据的 Qdrant 镜像
├── .env.example                      # 配置模板
├── Makefile                          # 常用命令
└── docs/                             # 文档
```

---

## 常用命令

```bash
make dev-backend    # 启动后端（热重载）
make dev-frontend   # 启动前端开发服务器
make dev            # 前后端同时启动
make lint           # 代码检查
make format         # 自动格式化
make check-env      # 验证 .env 配置
make cli QUERY="..."  # CLI 运行查询
```

---

## 维护者：更新证据库

当你修改了 `hypertension/evidence/` 中的证据文件后：

```bash
# 1. 重建 Qdrant 索引
cd hypertension
hdb index rebuild --confirm

# 2. 重建并推送 Docker 镜像
cd ..
./scripts/push_qdrant_image.sh
```

新用户下次 `docker compose pull` 即可获取最新数据。

---

## 文档

| 资源 | 位置 |
|------|------|
| 故障排查 | [docs/troubleshooting.md](docs/troubleshooting.md) |
| 术语表 | [docs/glossary.md](docs/glossary.md) |
| 架构设计 | [docs/architecture.md](docs/architecture.md) |
| 变更记录 | [CHANGELOG.md](CHANGELOG.md) |

---

## License

MIT © Winda0001 — 详见 [LICENSE](LICENSE)
