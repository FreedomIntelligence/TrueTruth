"""Baseline 1: Direct LLM — answer from parametric knowledge only, no retrieval."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from src.baselines.protocol import BaselineResult

if TYPE_CHECKING:
    from src.config.llm_config import _LLMClient

PROMPT = """\
你是一位临床医学专家。请根据你的专业知识，回答以下临床问题，给出具体的治疗推荐建议。

要求：
1. 给出明确的治疗推荐，包括药物选择、剂量和监测要点
2. 说明推荐依据（指南、共识或临床证据）
3. 指出重要的注意事项和禁忌证
4. 如有不确定性，请明确说明

**临床问题：**
{question}

请用中文回答，内容要具体、可执行。"""


def run(question: str, evidence=None, llm: "_LLMClient | None" = None) -> BaselineResult:
    if llm is None:
        from src.config.llm_config import get_llm
        llm = get_llm(temperature=0.0, purpose="baseline_direct")

    prompt = PROMPT.format(question=question)
    t0 = time.time()
    resp = llm.invoke(prompt)
    elapsed = time.time() - t0

    return BaselineResult(
        pipeline_name="direct_llm",
        question=question,
        response_text=resp.content,
        evidence_used=[],
        elapsed_s=round(elapsed, 2),
        llm_calls=1,
        metadata={"prompt_length": len(prompt)},
    )
