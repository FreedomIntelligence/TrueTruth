# Hypertension RAG Service Setup

The Acquire stage of EBM 5A queries a local FastAPI service backed by a Qdrant vector database of hypertension landmark trials.

## Docker（推荐）

使用 `docker compose up` 启动主项目时，Qdrant 和 Hypertensiondb API 会自动启动。Qdrant 镜像已预置全部证据向量数据。

## 手动启动

如果不使用 Docker，需要手动启动 Qdrant 和 API 服务：

```bash
# 1. 启动 Qdrant
cd hypertension
docker compose up -d

# 2. 安装依赖并启动 API
pip install -e .
hdb serve run --port 8000
```

验证服务是否正常：
```bash
curl http://localhost:8000/health
```

## 从源文件重建索引

如果你修改了 `hypertension/evidence/` 中的证据文件，需要重建 Qdrant 索引：

```bash
cd hypertension
hdb index rebuild --confirm
```

这需要配置 Embedding API Key（参见 `.env.example`），耗时约 5–10 分钟。

## 配置（`.env`）

```dotenv
HYPERTENSION_API_URL=http://localhost:8000   # API 地址（Docker 模式下自动设置）
HYPERTENSION_API_TIMEOUT=10                  # 每次 /search 请求超时（秒）
RAG_SEARCH_TOP_K=15                          # 每次检索的 chunk 数
RAG_MAX_PAPERS=6                             # 传给下游 Agent 的最大论文数
RAG_MAX_PASSAGES_PER_PAPER=3                 # 每篇论文保留的最大 passage 数
EMBEDDER=zhipu                               # Embedding 提供商
ZHIPU_API_KEY=...                            # 智谱 API Key
```

## 服务不可用时的行为

`hypertension_rag_client.py` 会重试 2 次（指数退避），然后抛出 `RAGUnavailable`。Acquire Agent 捕获该异常并记录错误——流水线在该阶段停止，不会产生空结果。
