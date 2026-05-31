# 高血压证据库 (Hypertension Evidence DB)

本地化的高血压循证医学证据 RAG 数据库，为下游临床决策支持系统提供混合检索 API。

## 设计文档

`docs/superpowers/specs/2026-05-19-hypertension-rag-design.md`

## 快速开始

```bash
pip install -e .[dev]
hdb --help
```

## 项目状态

- [x] Plan A: 项目骨架 + Schema + 手工数据流
- [ ] Plan B: 索引管线 + Qdrant
- [ ] Plan C: 检索 API + 黄金集
- [ ] Plan D: PDF 入库管线
- [ ] Plan E: 英文 API 采集 + 质量工具
