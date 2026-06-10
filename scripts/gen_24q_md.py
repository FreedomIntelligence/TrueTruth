"""Generate a human-readable markdown of each of the 24 questions' EBM system
output + scores from measure_full24.json (the text-capture re-run)."""
import json
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
full = json.loads((ROOT / "measure_full24.json").read_text(encoding="utf-8"))
qs = json.loads((ROOT / "scripts" / "baseline_questions_24.json").read_text(encoding="utf-8"))
qmeta = {q["id"]: q["question"] for q in qs}
order = [q["id"] for q in qs]
rows = {x["id"]: x for x in full["rows"]}

DIMS = ["medical_accuracy", "evidence_quality", "relevance", "safety_risk_control",
        "individualization", "clarity_actionability", "uncertainty_boundary"]
DIMZH = {"medical_accuracy": "医学准确", "evidence_quality": "证据质量", "relevance": "相关性",
         "safety_risk_control": "安全风险", "individualization": "个体化",
         "clarity_actionability": "清晰可操作", "uncertainty_boundary": "不确定性"}

allraw, allcap, empty = [], [], []
body = []
for qid in order:
    x = rows.get(qid)
    body.append(f"## {qid}\n")
    body.append(f"**问题:** {qmeta.get(qid, '')}\n")
    if not x or "error" in x:
        body.append(f"> 运行错误: {x.get('error') if x else 'missing'}\n\n---\n")
        continue
    raw, cap, cat = x["raw"], x["capped"], x["safety_category"]
    ds = x.get("dim_scores") or {}
    txt = (x.get("response_text") or "").strip()
    is_empty = len(txt) < 50
    flag = " · **本轮空证据(检索全部低于阈值→无推荐)**" if is_empty else ""
    body.append(f"**评分:** raw **{raw}** / capped **{cap}** · safety_category=**{cat}**{flag}\n")
    dimstr = " | ".join(f"{DIMZH[k]} {ds.get(k)}" for k in DIMS)
    body.append("```\n" + dimstr + "\n```\n")
    viol = x.get("safety_violations") or []
    if viol:
        body.append("**封顶/安全违规:**\n")
        for v in viol:
            body.append(f"- {v}")
        body.append("")
    body.append("**系统输出:**\n")
    body.append(txt if txt else "（空——无证据，未产出推荐）")
    body.append("\n---\n")
    allraw.append(raw); allcap.append(cap)
    if is_empty:
        empty.append(qid)

ind = [(r, c) for qid, r, c in zip(order, allraw, allcap) if qid not in empty]
head = [
    "# EBM 5A — 24 题系统输出与评分（2026-06-04 带正文重跑）\n",
    "> 这是**带正文的重跑**(K=1)。评测有噪声(±)，分数与纯评分轮可能略有出入；本文件里正文与分数自洽配对。",
    "> raw = 封顶前 7 维之和；capped = 封顶后(A→60... A→40 / B→60)。",
    f"> 本轮空证据题(检索全部 < min_score=0.80 → 无推荐 → ~0 分): **{empty or '无'}**。注: B15 儿童高血压在阈值边缘，跨轮有时有答案有时为空。\n",
    f"**均值** — 全 24 题: raw {mean(allraw):.1f} / capped {mean(allcap):.1f}　|　非空 {len(ind)} 题: raw {mean(r for r,c in ind):.1f} / capped {mean(c for r,c in ind):.1f}\n",
    "---\n",
]
out = ROOT / "docs" / "ebm5a_24q_outputs.md"
out.write_text("\n".join(head + body), encoding="utf-8")
print("wrote", out)
print("empty-evidence this run:", empty)
print("means all:", round(mean(allraw), 1), round(mean(allcap), 1))
