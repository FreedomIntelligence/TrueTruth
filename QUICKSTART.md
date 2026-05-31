# EBM 5A 快速开始指南

## 方式一：Docker（推荐）

最快的上手方式——一行命令启动全部服务。

**前提：** 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/) 并确保已启动。

```bash
# 1. 克隆并进入项目
git clone https://github.com/Winda0001/ebm5a.git
cd ebm5a

# 2. 复制并填写配置文件
cp .env.example .env
# 编辑 .env，填写：
#   LLM_API_KEY    — LLM API 密钥
#   ZHIPU_API_KEY  — 智谱 Embedding API Key
#   PUBMED_EMAIL   — 你的邮箱

# 3. 启动所有服务
docker compose up

# 4. 浏览器打开 http://localhost:8080
```

首次启动会自动拉取预置证据库镜像（~500MB）并构建后端/前端镜像，约需 3–5 分钟。

停止服务：
```bash
docker compose down
```

---

## 方式二：手动安装（开发者）

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt -r requirements-web.txt

# 2. 安装证据库服务
cd hypertension && pip install -e . && cd ..

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填写 API Key 等

# 4. 启动 Qdrant（仍需 Docker）
cd hypertension && docker compose up -d && cd ..

# 5. 启动证据库 API
cd hypertension && hdb serve run --port 8000 &

# 6a. Web 模式
make dev    # 同时启动前后端，访问 http://localhost:5173

# 6b. CLI 模式
make cli QUERY="68岁男性，高血压合并糖尿病，ACEI还是ARB？"
```

---

## 常见问题

### Q: 运行时间很长？
正常情况下完整流程需要 2–5 分钟（多次 LLM 调用 + 证据检索 + 可能的回退重试）。

### Q: 提示 API 错误？
检查 `.env` 配置：API Key 是否有效、API 地址是否可达、配额是否充足。
运行 `make check-env` 可自动验证。

### Q: 证据库连接失败？
确认 Qdrant 和 Hypertensiondb 服务是否正在运行。Docker 模式下 `docker compose ps` 查看状态。
