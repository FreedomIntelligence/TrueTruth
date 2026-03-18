# EBM 5A系统快速开始指南

## 1. 配置环境

### 创建.env文件

```bash
cp .env.example .env
```

### 编辑.env文件，填入以下信息：

```bash
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-4
PUBMED_EMAIL=your_email@example.com
```

**必填项**:
- `LLM_API_KEY`: 您的OpenAI API密钥
- `PUBMED_EMAIL`: 您的邮箱（用于PubMed API访问）

**可选项**:
- `LLM_MODEL`: 默认gpt-4，也可以使用gpt-3.5-turbo（更便宜但效果稍差）
- `LLM_BASE_URL`: 如果使用其他兼容OpenAI的API，修改此项

## 2. 安装依赖

```bash
pip3 install -r requirements.txt --user
```

## 3. 运行测试

### 方式1: 使用测试脚本（推荐）

```bash
./run_test.sh "您的临床问题"
```

示例：
```bash
./run_test.sh "对于2型糖尿病患者，二甲双胍相比安慰剂是否能降低心血管事件风险？"
```

### 方式2: 直接运行Python

```bash
python3 src/main.py "您的临床问题"
```

## 4. 查看结果

测试结果会：
1. 实时显示在终端
2. 自动保存到 `logs/test_run_YYYYMMDD_HHMMSS.log`

## 5. 输出内容说明

系统会输出以下信息：

### 基本信息
- 原始问题
- PICO结构化查询
- 搜索到的证据列表
- 证据评价结果
- 临床推荐
- 质量评估

### 调度信息
- **STAGE EVALUATIONS**: 每个阶段的Judge评价
  - 整体评分
  - 是否通过阈值
  - 发现的问题（critical/major/minor）

- **SCHEDULING DECISIONS**: Scheduling LLM的决策
  - 决策类型（proceed/backtrack/terminate等）
  - 决策理由

- **BACKTRACK EVENTS**: 回退事件
  - 从哪个阶段回退到哪个阶段
  - 回退原因

- **HUMAN INTERVENTION REQUESTS**: 人类介入请求
  - 请求范围（数值数据、偏倚评估等）
  - 请求原因

### 统计信息
- 总迭代次数
- 剩余预算
- 各Agent调用次数
- 回退次数
- 人类介入次数

## 6. 常见问题

### Q: 运行时间很长？
A: 正常情况下，完整流程需要2-5分钟，因为：
- 需要调用PubMed API搜索文献
- 需要多次调用LLM进行评价和决策
- 可能会发生回退和重试

### Q: 提示API错误？
A: 检查：
1. .env文件是否正确配置
2. API密钥是否有效
3. 网络连接是否正常
4. API配额是否充足

### Q: 找不到证据？
A: 这是正常的MVP行为：
- 系统会尝试3次
- 如果仍然找不到，会优雅终止并给出建议

### Q: 系统一直回退？
A: 系统有死循环检测：
- 连续3次回退到同一阶段会触发终止
- 总迭代次数超过20次会终止
- 单个Agent调用超过5次会终止

## 7. 测试建议

### 简单问题（容易找到证据）
```bash
./run_test.sh "对于高血压患者，ACEI类药物相比安慰剂是否能降低心血管事件？"
```

### 复杂问题（可能触发回退）
```bash
./run_test.sh "对于轻度认知障碍患者，银杏叶提取物是否能改善记忆功能？"
```

### 冷门问题（可能找不到证据）
```bash
./run_test.sh "对于罕见病X患者，新药Y是否有效？"
```

## 8. 下一步

测试成功后，您可以：
1. 查看 `docs/mvp_implementation_complete.md` 了解系统架构
2. 查看 `docs/acquire_agent_fix.md` 了解Acquire阶段的实现
3. 修改 `src/config/evaluation_dimensions/*.json` 调整评价标准
4. 修改 `src/config/prompts/` 下的提示词优化效果

---

**祝您使用愉快！**
