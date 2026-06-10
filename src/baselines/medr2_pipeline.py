"""Baseline 4: Med-R² pipeline — EBM-guided query rewriting + evidence reranking + CoT generation.

Adapted from Med-R² (arXiv:2501.11885, github.com/8023looker/Med-RR).
Preserves the core pipeline logic (classify→rewrite→retrieve→rerank→generate)
while swapping retrieval backend (Qdrant) and LLM (project's get_llm()).

Simplification: f_u (usefulness via local model loss) is skipped.
Composite rerank score: F(x) = f_h(x) × f_g(x)
"""
from __future__ import annotations

import json
import re
import time
from typing import TYPE_CHECKING

from src.baselines.protocol import BaselineResult, format_evidence_block
from src.state.schema import Evidence

if TYPE_CHECKING:
    from src.config.llm_config import _LLMClient

# ── Stage 1: Classify + Rewrite ─────────────────────────────────────────────

CLASSIFY_PROMPT = """\
You are an expert in sentence annotation within the medical field.

Task 1 — EBM Classification:
There are seven categories of clinical questions: Prognosis, Therapy, Etiology, Diagnosis, Prevention, Cost, and Other.

Task 2 — NLP Question-Type Classification:
There are 13 categories of question types: Factual, Definitional, Explanatory, Descriptive, Directive, Opinion, Comparative, Evaluative, Hypothetical, Procedural, Referential, Verification, and Other.

Please classify the following text fragment by providing ONLY a JSON object with two keys "ebm" and "nlp", without additional commentary:

{question}"""

EBM_REWRITE_TEMPLATES = {
    "therapy": "Please specify the disease or symptom along with the therapy being considered, and inquire about its effectiveness, safety, or comparison with other therapies.",
    "diagnosis": "Please specify the condition you need to diagnose and ask about the accuracy, sensitivity, or specificity of specific diagnostic tests.",
    "prognosis": "Please specify the disease or condition and ask about long-term outcomes such as survival rates, recovery chances, or disease progression.",
    "etiology": "Please describe the health issue and ask about potential causes, including risk factors, pathogens, or genetic background.",
    "prevention": "Please specify the disease or health issue and ask about the effectiveness of preventive measures or recommendations.",
    "cost": "Please specify the medical intervention or service and ask about cost-effectiveness analyses, including direct and indirect costs and cost-effectiveness ratios.",
    "other": "Please detail the area of interest, such as ethics, legal issues, or patient education, and ask for relevant information or guidelines.",
}

REWRITE_PROMPT = """\
You are a query sentence rewriting expert. {rewrite_instruction}
Directly provide the rewritten query sentence without any additional statements.
Original query sentence:

{question}"""


def _classify_and_rewrite(question: str, llm: "_LLMClient") -> tuple[str, str, str]:
    classify_resp = llm.invoke(CLASSIFY_PROMPT.format(question=question))
    text = classify_resp.content.strip()

    ebm_cat = "therapy"
    nlp_type = "factual"
    try:
        m = re.search(r"\{[^}]+\}", text)
        if m:
            obj = json.loads(m.group())
            ebm_cat = obj.get("ebm", "therapy").lower().strip()
            nlp_type = obj.get("nlp", "factual").lower().strip()
    except (json.JSONDecodeError, AttributeError):
        pass

    if ebm_cat not in EBM_REWRITE_TEMPLATES:
        ebm_cat = "other"

    instruction = EBM_REWRITE_TEMPLATES[ebm_cat]
    rewrite_resp = llm.invoke(REWRITE_PROMPT.format(
        rewrite_instruction=instruction, question=question
    ))
    rewritten = rewrite_resp.content.strip()

    return rewritten, ebm_cat, nlp_type


# ── Stage 3: Rerank ─────────────────────────────────────────────────────────

EVIDENCE_LEVEL_PROMPT = """\
You are an expert in evidence quality annotation within the medical field. There are 9 quality levels of documents: Meta-Analyses, Systematic Reviews, Evidence-Based Practice Guidelines, Randomized Controlled Trials, Non-Randomized Controlled Trials, Cohort Studies, Case Series or Studies, Individual Case Reports, Expert Opinion. Please classify the following text segment based on its purpose and structure, providing only the name of the level, without any additional description:

{doc_text}"""

EVIDENCE_LEVEL_SCORES = {
    "meta-analyses": 9,
    "systematic reviews": 8,
    "evidence-based practice guidelines": 7,
    "randomized controlled trials": 6,
    "non-randomized controlled trials": 5,
    "cohort studies": 4,
    "case series or studies": 3,
    "individual case reports": 2,
    "expert opinion": 1,
}

DOC_CATEGORY_PROMPT = """\
You are an expert in sentence annotation within the medical field. There are 16 categories of documents: Argumentation, Definition, Description, Explanation, Purpose, Narration, Process, Instruction, Command, Problem-Solving, Comparison, Evaluation, Classification, Condition, Prediction, Cause-and-Effect. Please classify the following text fragment based on their purpose and structure by providing the probability distribution of its belonging to each category, in the format of [x1, x2, x3, ..., x16], where the sum of probabilities across all categories equals 1, without additional commentary:

{doc_text}"""

DOC_CATEGORIES = [
    "argumentation", "definition", "description", "explanation",
    "purpose", "narration", "process", "instruction",
    "command", "problem-solving", "comparison", "evaluation",
    "classification", "condition", "prediction", "cause-and-effect",
]

NLP_TO_PROJECTION = {
    "factual": ["argumentation", "definition", "description", "explanation", "purpose", "narration"],
    "definitional": ["argumentation", "definition", "description", "explanation", "purpose", "narration"],
    "explanatory": ["argumentation", "definition", "description", "explanation", "purpose", "narration"],
    "descriptive": ["argumentation", "definition", "description", "explanation", "purpose", "narration"],
    "referential": ["argumentation", "definition", "description", "explanation", "purpose", "narration"],
    "directive": ["purpose", "instruction", "command", "problem-solving"],
    "opinion": ["purpose", "instruction", "command", "problem-solving"],
    "procedural": ["purpose", "instruction", "command", "problem-solving"],
    "comparative": ["comparison", "evaluation", "classification"],
    "evaluative": ["comparison", "evaluation", "classification"],
    "verification": ["comparison", "evaluation", "classification"],
    "hypothetical": ["condition", "prediction", "cause-and-effect"],
    "other": DOC_CATEGORIES,
}


def _get_doc_text(ev: Evidence) -> str:
    parts = [ev.title or ""]
    for p in (ev.supporting_passages or [])[:3]:
        parts.append(p.snippet)
    return "\n".join(parts)[:2000]


def _compute_f_h(doc_text: str, llm: "_LLMClient") -> float:
    resp = llm.invoke(EVIDENCE_LEVEL_PROMPT.format(doc_text=doc_text))
    level = resp.content.strip().lower()
    for key, score in EVIDENCE_LEVEL_SCORES.items():
        if key in level:
            return float(score)
    return 1.0


def _compute_f_g(doc_text: str, nlp_type: str, llm: "_LLMClient") -> float:
    resp = llm.invoke(DOC_CATEGORY_PROMPT.format(doc_text=doc_text))
    text = resp.content.strip()

    m = re.search(r"\[([^\]]+)\]", text)
    if not m:
        return 0.5

    try:
        probs = [float(x.strip()) for x in m.group(1).split(",")]
    except ValueError:
        return 0.5

    if len(probs) != 16:
        return 0.5

    projection_cats = NLP_TO_PROJECTION.get(nlp_type, DOC_CATEGORIES)
    projection_indices = [i for i, c in enumerate(DOC_CATEGORIES) if c in projection_cats]

    return sum(probs[i] for i in projection_indices if i < len(probs))


def _rerank(evidence: list[Evidence], nlp_type: str, llm: "_LLMClient") -> tuple[list[Evidence], list[dict], int]:
    scored = []
    llm_calls = 0
    rerank_details = []

    for ev in evidence:
        doc_text = _get_doc_text(ev)
        f_h = _compute_f_h(doc_text, llm)
        llm_calls += 1
        f_g = _compute_f_g(doc_text, nlp_type, llm)
        llm_calls += 1
        composite = f_h * f_g
        scored.append((composite, ev))
        rerank_details.append({
            "evidence_id": ev.evidence_id,
            "f_h": round(f_h, 2),
            "f_g": round(f_g, 3),
            "composite": round(composite, 3),
        })

    scored.sort(key=lambda x: x[0], reverse=True)
    reranked = [ev for _, ev in scored]

    return reranked, rerank_details, llm_calls


# ── Stage 4: CoT Generate ───────────────────────────────────────────────────

COT_PROMPT = """\
Given the provided [Question] and the [Relevant Documents Retrieved through a Query], please provide an answer that includes your thought process. Specifically:

1. **Analyze the Question**: Carefully analyze the [Question] to understand what information is being sought.
2. **Consult Relevant Documents**: Go through the snippets of [Relevant Documents Retrieved through the Query] to identify sections that are directly related to the [Question].
3. **Identify Key Information**: Highlight the key points from the [Relevant Documents Retrieved through the Query] that address the question's requirements.
4. **Construct Thought Process**: Explain how you used the information from the retrieved documents to form your understanding and construct your answer.
5. **Provide Answer**: Finally, give a clear and concise answer to the [Question], supported by the analysis of the [Relevant Documents Retrieved through the Query].
6. **Treatment Recommendation**: Based on the evidence, provide specific treatment recommendations including drug choices, dosages, and monitoring points.

Please present your response in Chinese. Clearly show your reasoning and the sources of information you relied on.

[Question]

{question}

[Relevant Documents Retrieved through a Query]

{evidence_block}"""


# ── Main entry ───────────────────────────────────────────────────────────────

def run(question: str, evidence: list[Evidence] | None = None, llm: "_LLMClient | None" = None) -> BaselineResult:
    if llm is None:
        from src.config.llm_config import get_llm
        llm = get_llm(temperature=0.0, purpose="baseline_med_r2")

    t0 = time.time()
    total_llm_calls = 0

    # Stage 1: Classify + Rewrite
    rewritten_query, ebm_cat, nlp_type = _classify_and_rewrite(question, llm)
    total_llm_calls += 2

    # Stage 2: Retrieve (using rewritten query)
    if evidence is None:
        from src.tools.hypertension_rag_client import search
        evidence, _ = search(rewritten_query)

    # Stage 3: Rerank
    evidence, rerank_details, rerank_calls = _rerank(evidence, nlp_type, llm)
    total_llm_calls += rerank_calls

    # Stage 4: CoT Generate
    evidence_block = format_evidence_block(evidence)
    prompt = COT_PROMPT.format(question=question, evidence_block=evidence_block)
    resp = llm.invoke(prompt)
    total_llm_calls += 1

    elapsed = time.time() - t0

    return BaselineResult(
        pipeline_name="med_r2",
        question=question,
        response_text=resp.content,
        evidence_used=[e.evidence_id for e in evidence],
        elapsed_s=round(elapsed, 2),
        llm_calls=total_llm_calls,
        metadata={
            "ebm_category": ebm_cat,
            "nlp_type": nlp_type,
            "rewritten_query": rewritten_query,
            "rerank_details": rerank_details,
            "evidence_count": len(evidence),
            "prompt_length": len(prompt),
        },
    )
