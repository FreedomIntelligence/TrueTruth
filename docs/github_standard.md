## 开源仓库文件排布评分标准

### 一、可发现性 (Discoverability) — 25分

| 项目 | 分值 |
|------|------|
| README.md 存在且位于根目录 | 5 |
| README 包含项目简介、快速上手、安装方式 | 5 |
| CONTRIBUTING.md 存在 | 5 |
| LICENSE 文件存在 | 5 |
| CHANGELOG 或 RELEASES 记录存在 | 5 |

> 核心逻辑：陌生人能否在 5 分钟内理解这个项目是什么、怎么用。

---

### 二、结构一致性 (Structural Consistency) — 25分

- 目录命名是否符合该语言/生态的惯例（如 Python 的 `src/`、JS 的 `packages/`）
- 是否有明显的"随手乱放"现象（脚本、配置、源码混在一起）
- 测试文件是否有独立的组织方式（`tests/` 或 `__tests__/`）
- 配置文件是否集中管理或有规律

---

### 三、可维护性信号 (Maintainability Signals) — 20分

- `.gitignore` 是否存在且合理
- CI/CD 配置是否存在（`.github/workflows/`、`.gitlab-ci.yml` 等）
- 依赖声明文件是否存在（`package.json`、`requirements.txt`、`go.mod`）
- 是否有 `Makefile` 或等价的任务入口

---

### 四、噪声与冗余 (Noise Level) — 15分

减分项：
- 根目录堆积大量不相关文件
- 存在明显应该被 gitignore 的文件（编译产物、`.DS_Store` 等）
- 深度嵌套且命名不清的目录

---

### 五、文档与代码的对称性 — 15分

- 核心模块是否有对应的文档或注释入口
- 示例代码（`examples/`）是否与功能覆盖对应
- API 文档是否可以从目录结构中找到路径

---
