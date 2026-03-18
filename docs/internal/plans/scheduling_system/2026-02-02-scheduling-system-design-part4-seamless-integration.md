# EBM 5A 调度系统设计文档 - Part 4: 无缝衔接设计

**日期**: 2026-02-02
**项目**: 基于ReAct模式的调度系统设计
**状态**: 设计阶段

---

## 5. 无缝衔接设计

### 5.1 设计目标

确保系统可以无缝衔接：
1. **未来的证据库**：从PubMed切换到专门的产科证据库
2. **训练后的调度LLM**：从通用LLM升级到专门训练的调度模型

### 5.2 证据库接口抽象化

#### 5.2.1 统一的证据源接口

```python
from abc import ABC, abstractmethod
from typing import List
from src.state.schema import PICOQuery, Evidence

class EvidenceSource(ABC):
    """证据源的抽象基类"""

    @abstractmethod
    def search(
        self,
        pico_query: PICOQuery,
        keywords: List[str],
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Evidence]:
        """
        搜索证据

        Args:
            pico_query: 结构化的PICO查询
            keywords: 搜索关键词列表
            filters: 可选的过滤条件（如日期范围、研究类型等）

        Returns:
            证据列表，统一使用Evidence数据结构
        """
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        获取证据源的元数据

        Returns:
            包含版本、覆盖范围、更新时间等信息
        """
        pass
```

#### 5.2.2 当前实现：PubMed

```python
from src.tools.pubmed_api import PubMedAPI

class PubMedSource(EvidenceSource):
    """PubMed证据源实现"""

    def __init__(self, api_key: Optional[str] = None):
        self.api = PubMedAPI(api_key)

    def search(
        self,
        pico_query: PICOQuery,
        keywords: List[str],
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Evidence]:
        """使用PubMed API搜索"""

        # 构建搜索查询
        query_string = self._build_query(pico_query, keywords, filters)

        # 调用PubMed API
        results = self.api.search(query_string)

        # 转换为统一的Evidence格式
        evidence_list = [
            Evidence(
                title=result["title"],
                source="PubMed",
                pmid=result["pmid"],
                abstract=result["abstract"],
                relevance_score=result.get("relevance_score", 0.0),
                grade_level=None  # 需要后续评价
            )
            for result in results
        ]

        return evidence_list

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "source_type": "pubmed",
            "version": "2024-01",
            "coverage": "全球生物医学文献",
            "update_frequency": "daily"
        }

    def _build_query(
        self,
        pico_query: PICOQuery,
        keywords: List[str],
        filters: Optional[Dict[str, Any]]
    ) -> str:
        """构建PubMed查询字符串"""
        # 实现查询构建逻辑
        pass
```

#### 5.2.3 未来实现：产科证据库

```python
class ObstetricsEvidenceDB(EvidenceSource):
    """产科专用证据库实现"""

    def __init__(self, db_url: str, api_key: str):
        self.db_url = db_url
        self.api_key = api_key

    def search(
        self,
        pico_query: PICOQuery,
        keywords: List[str],
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Evidence]:
        """使用证据库API搜索"""

        # 调用证据库API
        response = requests.post(
            f"{self.db_url}/search",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "pico": pico_query.__dict__,
                "keywords": keywords,
                "filters": filters
            }
        )

        results = response.json()["results"]

        # 转换为统一的Evidence格式
        evidence_list = [
            Evidence(
                title=result["title"],
                source="ObstetricsDB",
                pmid=result.get("pmid"),  # 可能有也可能没有
                abstract=result["abstract"],
                relevance_score=result["relevance_score"],
                grade_level=result.get("grade_level")  # 证据库可能已经预评价
            )
            for result in results
        ]

        return evidence_list

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "source_type": "obstetrics_db",
            "version": "2025-06",
            "coverage": "产科专业文献",
            "update_frequency": "weekly",
            "pre_graded": True  # 证据已预评价
        }
```

#### 5.2.4 配置化切换

```python
# src/config/evidence_config.py

from typing import Type
from src.tools.evidence_source import EvidenceSource, PubMedSource, ObstetricsEvidenceDB

class EvidenceConfig:
    """证据源配置"""

    @staticmethod
    def get_evidence_source() -> EvidenceSource:
        """根据配置获取证据源实例"""

        # 从配置文件读取
        config = load_config("config/evidence.yaml")

        source_type = config["evidence_source"]["type"]

        if source_type == "pubmed":
            return PubMedSource(
                api_key=config["evidence_source"].get("api_key")
            )
        elif source_type == "obstetrics_db":
            return ObstetricsEvidenceDB(
                db_url=config["evidence_source"]["db_url"],
                api_key=config["evidence_source"]["api_key"]
            )
        else:
            raise ValueError(f"Unknown evidence source type: {source_type}")
```

```yaml
# config/evidence.yaml

evidence_source:
  type: "pubmed"  # 或 "obstetrics_db"

  # PubMed配置
  api_key: "your_pubmed_api_key"

  # 产科证据库配置（未来使用）
  # db_url: "https://obstetrics-evidence-db.example.com/api"
  # api_key: "your_db_api_key"
```

#### 5.2.5 在Acquire Agent中使用

```python
# src/agents/acquire_agent.py

from src.config.evidence_config import EvidenceConfig

class AcquireAgent:
    def __init__(self):
        # 通过配置获取证据源，无需关心具体实现
        self.evidence_source = EvidenceConfig.get_evidence_source()

    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        pico_query = state["pico_query"]
        keywords = pico_query.keywords

        # 使用统一接口搜索，无论底层是PubMed还是证据库
        evidence_list = self.evidence_source.search(
            pico_query=pico_query,
            keywords=keywords,
            filters={"date_range": "last_10_years"}
        )

        return {
            "evidence_list": evidence_list,
            "source_metadata": self.evidence_source.get_metadata()
        }
```

**切换证据源的步骤**：
1. 修改 `config/evidence.yaml` 中的 `type` 字段
2. 提供新证据源的配置参数
3. 重启系统，无需修改任何代码

### 5.3 调度LLM的标准化接口

#### 5.3.1 固定的输入输出格式

**输入格式（SchedulingInput）**：
```python
from typing import TypedDict, List, Dict, Any, Optional
from src.state.schema import ExecutionNode

class SchedulingInput(TypedDict):
    """调度LLM的标准输入格式"""

    observe: Dict[str, Any]
    # 结构：
    # {
    #   "stage": str,
    #   "output": Dict[str, Any],
    #   "evaluation": {
    #     "overall_score": float,
    #     "dimension_scores": Dict[str, float],
    #     "pass": bool,
    #     "issues": List[Issue],
    #     "summary": str
    #   }
    # }

    soft_gate_signals: List[str]
    # 触发的软性Gate信号列表
    # 例如：["quality_failed", "major_issues"]

    execution_history: List[ExecutionNode]
    # 完整的执行历史

    original_question: str
    # 原始临床问题

    current_iteration: int
    # 当前迭代次数
```

**输出格式（SchedulingDecision）**：
```python
from typing import Literal, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class SchedulingDecision:
    """调度LLM的标准输出格式"""

    reasoning: str
    # 推理过程，必须包含：
    # - 识别的关键问题
    # - 考虑的因素
    # - 决策依据

    action: Literal[
        "proceed",
        "backtrack_to_ask",
        "backtrack_to_acquire",
        "backtrack_to_appraise",
        "backtrack_to_apply",
        "retry_current",
        "terminate"
    ]
    # 决策动作

    parameters: Optional[Dict[str, Any]] = None
    # 可选参数，例如：
    # - adjust_strategy: str
    # - focus_on: str
    # - reason_for_termination: str
```

#### 5.3.2 调度LLM抽象接口

```python
from abc import ABC, abstractmethod

class SchedulingLLM(ABC):
    """调度LLM的抽象基类"""

    @abstractmethod
    def decide(self, input_data: SchedulingInput) -> SchedulingDecision:
        """
        基于输入做出调度决策

        Args:
            input_data: 标准化的输入数据

        Returns:
            标准化的决策输出
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息

        Returns:
            包含模型名称、版本、训练数据等信息
        """
        pass
```

#### 5.3.3 当前实现：通用LLM

```python
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import json

class GeneralSchedulingLLM(SchedulingLLM):
    """使用通用LLM实现的调度器"""

    def __init__(self, model_name: str = "gpt-4", temperature: float = 0.1):
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature
        )
        self.prompt_template = self._load_prompt_template()

    def decide(self, input_data: SchedulingInput) -> SchedulingDecision:
        """使用通用LLM进行决策"""

        # 构建prompt
        prompt = self.prompt_template.format(
            original_question=input_data["original_question"],
            current_stage=input_data["observe"]["stage"],
            current_iteration=input_data["current_iteration"],
            stage_output=json.dumps(input_data["observe"]["output"], indent=2, ensure_ascii=False),
            overall_score=input_data["observe"]["evaluation"]["overall_score"],
            pass_status=input_data["observe"]["evaluation"]["pass"],
            dimension_scores=json.dumps(input_data["observe"]["evaluation"]["dimension_scores"], indent=2),
            issues=json.dumps(input_data["observe"]["evaluation"]["issues"], indent=2, ensure_ascii=False),
            summary=input_data["observe"]["evaluation"]["summary"],
            soft_gate_signals=", ".join(input_data["soft_gate_signals"]) if input_data["soft_gate_signals"] else "无",
            execution_history_summary=self._summarize_history(input_data["execution_history"])
        )

        # 调用LLM
        response = self.llm.invoke(prompt)

        # 解析输出
        try:
            decision_dict = json.loads(response.content)
            decision = SchedulingDecision(
                reasoning=decision_dict["reasoning"],
                action=decision_dict["action"],
                parameters=decision_dict.get("parameters")
            )
        except Exception as e:
            # 解析失败，使用降级策略
            raise ValueError(f"Failed to parse LLM output: {e}")

        return decision

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_type": "general_llm",
            "model_name": "gpt-4",
            "version": "v1.0",
            "training_data": "general",
            "specialized": False
        }

    def _load_prompt_template(self) -> ChatPromptTemplate:
        """加载prompt模板"""
        # 从文件加载或直接定义
        # 参考Part 2中的SCHEDULING_PROMPT
        pass

    def _summarize_history(self, history: List[ExecutionNode]) -> str:
        """总结执行历史"""
        summary_lines = []
        for node in history:
            summary_lines.append(
                f"- {node.agent_type}: {node.status}"
            )
        return "\n".join(summary_lines)
```

#### 5.3.4 未来实现：训练后的调度LLM

```python
class FineTunedSchedulingLLM(SchedulingLLM):
    """使用微调后的专门模型"""

    def __init__(self, model_path: str):
        self.model = self._load_model(model_path)
        self.tokenizer = self._load_tokenizer(model_path)

    def decide(self, input_data: SchedulingInput) -> SchedulingDecision:
        """使用微调模型进行决策"""

        # 将输入转换为模型期望的格式
        model_input = self._prepare_input(input_data)

        # 模型推理
        output = self.model.generate(
            model_input,
            max_length=512,
            temperature=0.1
        )

        # 解析输出
        decision = self._parse_output(output)

        return decision

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_type": "fine_tuned",
            "model_name": "ebm5a-scheduler-v2",
            "version": "v2.0",
            "training_data": "ebm5a_scheduling_dataset",
            "specialized": True,
            "training_date": "2025-06-01"
        }

    def _load_model(self, model_path: str):
        """加载微调后的模型"""
        # 实现模型加载逻辑
        pass

    def _prepare_input(self, input_data: SchedulingInput) -> Any:
        """
        将标准输入格式转换为模型期望的格式

        关键：输入格式是固定的，这里只是做格式转换
        """
        pass

    def _parse_output(self, output: Any) -> SchedulingDecision:
        """
        将模型输出解析为标准决策格式

        关键：输出格式是固定的，确保模型训练时使用相同格式
        """
        pass
```

#### 5.3.5 配置化切换

```python
# src/config/llm_config.py

from src.coordinator.scheduling_llm import SchedulingLLM, GeneralSchedulingLLM, FineTunedSchedulingLLM

class LLMConfig:
    """LLM配置"""

    @staticmethod
    def get_scheduling_llm() -> SchedulingLLM:
        """根据配置获取调度LLM实例"""

        config = load_config("config/llm.yaml")

        scheduler_config = config["scheduling_llm"]
        llm_type = scheduler_config["type"]

        if llm_type == "general":
            return GeneralSchedulingLLM(
                model_name=scheduler_config["model_name"],
                temperature=scheduler_config.get("temperature", 0.1)
            )
        elif llm_type == "fine_tuned":
            return FineTunedSchedulingLLM(
                model_path=scheduler_config["model_path"]
            )
        else:
            raise ValueError(f"Unknown scheduling LLM type: {llm_type}")
```

```yaml
# config/llm.yaml

scheduling_llm:
  type: "general"  # 或 "fine_tuned"

  # 通用LLM配置
  model_name: "gpt-4"
  temperature: 0.1

  # 微调模型配置（未来使用）
  # model_path: "/path/to/fine_tuned_model"
```

#### 5.3.6 在Coordinator中使用

```python
# src/coordinator/coordinator.py

from src.config.llm_config import LLMConfig

class Coordinator:
    def __init__(self, agents: Dict[str, Any]):
        self.agents = agents
        # 通过配置获取调度LLM，无需关心具体实现
        self.scheduling_llm = LLMConfig.get_scheduling_llm()

    def coordinate_next_step(self, observe: Dict, state: WorkflowState) -> SchedulingDecision:
        """协调下一步行动"""

        # 检查硬性Gate
        hard_gate_trigger = check_hard_gates(state)
        if hard_gate_trigger:
            return execute_forced_action(hard_gate_trigger)

        # 检查软性Gate
        soft_gate_signals = check_soft_gates(observe)

        # 准备标准输入
        scheduling_input = SchedulingInput(
            observe=observe,
            soft_gate_signals=soft_gate_signals,
            execution_history=state["execution_history"],
            original_question=state["original_question"],
            current_iteration=state["iteration_count"]
        )

        # 调用调度LLM（无论是通用还是微调模型）
        decision = self.scheduling_llm.decide(scheduling_input)

        # 验证决策
        if is_decision_valid(decision, state):
            return decision
        else:
            return fallback_decision(observe, state)
```

**切换调度LLM的步骤**：
1. 修改 `config/llm.yaml` 中的 `type` 字段
2. 提供新模型的配置参数
3. 重启系统，无需修改任何代码

### 5.4 训练数据格式

为了确保未来训练的调度LLM能够无缝替换，训练数据应该使用相同的输入输出格式：

```python
# 训练数据示例
training_example = {
    "input": {
        "observe": {
            "stage": "Acquire",
            "output": {...},
            "evaluation": {
                "overall_score": 0.65,
                "dimension_scores": {...},
                "pass": false,
                "issues": [...],
                "summary": "..."
            }
        },
        "soft_gate_signals": ["quality_failed", "major_issues"],
        "execution_history": [...],
        "original_question": "...",
        "current_iteration": 3
    },
    "output": {
        "reasoning": "证据类型单一是重大问题...",
        "action": "backtrack_to_acquire",
        "parameters": {
            "adjust_strategy": "增加meta-analysis检索"
        }
    }
}
```

**训练数据来源**：
1. **Benchmark的金标准数据**：专家标注的理想路径
2. **系统运行日志**：记录通用LLM的决策，专家review后作为训练数据
3. **合成数据**：基于模板生成的训练样本

### 5.5 版本管理和兼容性

#### 5.5.1 数据格式版本

```python
# src/state/schema.py

SCHEMA_VERSION = "1.0"

class SchedulingInput(TypedDict):
    """调度LLM的标准输入格式"""
    _schema_version: str  # 添加版本字段
    observe: Dict[str, Any]
    soft_gate_signals: List[str]
    execution_history: List[ExecutionNode]
    original_question: str
    current_iteration: int

class SchedulingDecision:
    """调度LLM的标准输出格式"""
    _schema_version: str  # 添加版本字段
    reasoning: str
    action: str
    parameters: Optional[Dict[str, Any]]
```

#### 5.5.2 向后兼容

```python
def migrate_input_format(input_data: Dict, from_version: str, to_version: str) -> SchedulingInput:
    """迁移输入格式到新版本"""
    if from_version == "1.0" and to_version == "1.1":
        # 添加新字段，保持旧字段
        input_data["_schema_version"] = "1.1"
        input_data["new_field"] = default_value
    return input_data
```

### 5.6 系统升级路径

#### 5.6.1 阶段1：当前（通用LLM + PubMed）
```
证据源：PubMed
调度LLM：GPT-4（通用）
其他Agent：GPT-4（通用）
Judge LLM：GPT-4（通用）
```

#### 5.6.2 阶段2：证据库上线
```
证据源：产科证据库  ← 升级
调度LLM：GPT-4（通用）
其他Agent：GPT-4（通用）
Judge LLM：GPT-4（通用）

升级步骤：
1. 修改 config/evidence.yaml
2. 重启系统
3. 运行benchmark验证
```

#### 5.6.3 阶段3：调度LLM训练完成
```
证据源：产科证据库
调度LLM：微调模型  ← 升级
其他Agent：GPT-4（通用）
Judge LLM：GPT-4（通用）

升级步骤：
1. 修改 config/llm.yaml
2. 重启系统
3. 运行benchmark对比性能
```

#### 5.6.4 阶段4：全面升级（未来）
```
证据源：产科证据库
调度LLM：微调模型
其他Agent：专门训练的模型  ← 升级
Judge LLM：专门训练的模型  ← 升级

注意：
- 其他Agent和Judge LLM的升级不影响调度LLM
- Benchmark仍然固定其他组件版本来评价调度LLM
```

### 5.7 关键设计原则总结

1. **接口抽象**：所有可替换组件都定义抽象接口
2. **格式固定**：输入输出格式标准化，版本化
3. **配置驱动**：通过配置文件切换实现，无需修改代码
4. **向后兼容**：新版本支持旧格式的迁移
5. **独立升级**：各组件可以独立升级，互不影响
6. **Benchmark隔离**：评测时固定其他组件，确保结果可比

---

## 6. 总结

本设计文档完整描述了EBM 5A调度系统的四个核心方面：

### 6.1 Observe设计（Part 1）
- 混合方式：评分 + 问题列表 + 自然语言
- 每个阶段的具体评价维度
- 由Judge LLM生成，作为ReAct的"观察"环节

### 6.2 调度决策机制（Part 2）
- 分层混合方式：硬性Gate + 软性Gate + LLM决策
- 标准化的输入输出格式
- 完整的决策流程和验证机制

### 6.3 Benchmark设计（Part 3）
- Rubrics式评测集：问题 + 理想路径 + 评分标准
- 金标准数据（专家标注）+ 合成数据
- 重点评价决策能力和效率，辅助评价最终结果
- 固定其他组件，确保结果可比

### 6.4 无缝衔接设计（Part 4）
- 证据库接口抽象化
- 调度LLM标准化接口
- 配置化切换，独立升级
- 清晰的系统升级路径

### 6.5 下一步行动

1. **Review设计文档**：与专家讨论，确认设计方向
2. **实现Observe生成**：开发Judge LLM的评价逻辑
3. **实现分层决策**：开发硬性Gate、软性Gate和LLM决策
4. **构建Benchmark框架**：实现评测流程和指标计算
5. **收集金标准数据**：与专家合作标注10-20个案例
6. **迭代优化**：基于实际运行结果调整设计

---

**文档结束**
