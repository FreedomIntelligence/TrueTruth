"""Baseline 2: Vanilla RAG — retrieve evidence and concatenate into a single prompt."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from src.baselines.protocol import BaselineResult, format_evidence_block
from src.state.schema import Evidence

if TYPE_CHECKING:
    from src.config.llm_config import _LLMClient

PROMPT = """\
你是一位临床医学专家。请根据以下检索到的医学证据，回答临床问题并给出治疗推荐。

**临床问题：**
{question}

**检索到的医学证据：**
{evidence_block}

请根据以上证据回答问题：
1. 给出明确的治疗推荐，包括药物选择、剂量和监测要点
2. 引用相关证据支持你的推荐（使用 [证据编号] 标注）
3. 指出重要的注意事项和禁忌证
4. 如证据不足，请明确说明

请用中文回答。"""


def run(question: str, evidence: list[Evidence] | None = None, llm: "_LLMClient | None" = None) -> BaselineResult:
    if llm is None:
        from src.config.llm_config import get_llm
        llm = get_llm(temperature=0.0, purpose="baseline_vanilla")

    if evidence is None:
        from src.tools.hypertension_rag_client import search
        evidence, _ = search(question)

    evidence_block = format_evidence_block(evidence)
    prompt = PROMPT.format(question=question, evidence_block=evidence_block)

    t0 = time.time()
    resp = llm.invoke(prompt)
    elapsed = time.time() - t0

    return BaselineResult(
        pipeline_name="vanilla_rag",
        question=question,
        response_text=resp.content,
        evidence_used=[e.evidence_id for e in evidence],
        elapsed_s=round(elapsed, 2),
        llm_calls=1,
        metadata={"prompt_length": len(prompt), "evidence_count": len(evidence)},
    )
