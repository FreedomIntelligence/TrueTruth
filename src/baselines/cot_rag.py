"""Baseline 3: CoT-RAG — retrieve evidence, then reason step by step before recommending."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from src.baselines.protocol import BaselineResult, format_evidence_block
from src.state.schema import Evidence

if TYPE_CHECKING:
    from src.config.llm_config import _LLMClient

PROMPT = """\
你是一位循证医学专家。请使用以下检索到的医学证据，通过逐步分析回答临床问题。

**临床问题：**
{question}

**检索到的医学证据：**
{evidence_block}

请按以下步骤逐步分析：

**第一步：证据评估**
逐条评估每篇证据的质量和相关性：
- 研究类型（RCT、队列研究、荟萃分析等）
- 与问题的相关程度（直接相关/间接相关/边缘相关）
- 研究局限性

**第二步：证据综合**
综合所有证据，分析：
- 各证据的一致性（结果是否一致？）
- 总体证据强度
- 证据缺口

**第三步：治疗推荐**
基于以上分析，给出：
1. 明确的治疗推荐，包括药物选择、剂量和监测要点
2. 推荐强度及依据
3. 注意事项和禁忌证
4. 证据不确定性和局限性说明

请用中文回答，确保每一步的分析都清晰、具体。引用证据时使用 [证据编号] 标注。"""


def run(question: str, evidence: list[Evidence] | None = None, llm: "_LLMClient | None" = None) -> BaselineResult:
    if llm is None:
        from src.config.llm_config import get_llm
        llm = get_llm(temperature=0.0, purpose="baseline_cot")

    if evidence is None:
        from src.tools.hypertension_rag_client import search
        evidence, _ = search(question)

    evidence_block = format_evidence_block(evidence)
    prompt = PROMPT.format(question=question, evidence_block=evidence_block)

    t0 = time.time()
    resp = llm.invoke(prompt)
    elapsed = time.time() - t0

    return BaselineResult(
        pipeline_name="cot_rag",
        question=question,
        response_text=resp.content,
        evidence_used=[e.evidence_id for e in evidence],
        elapsed_s=round(elapsed, 2),
        llm_calls=1,
        metadata={"prompt_length": len(prompt), "evidence_count": len(evidence)},
    )
