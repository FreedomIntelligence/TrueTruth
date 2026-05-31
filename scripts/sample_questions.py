#!/usr/bin/env python3
"""Sample 30 diverse patient profiles and generate clinical questions.

Outputs JSON to experiments/bug_hunt_30.json.
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = ROOT / "patient_profile"
OUT_PATH = ROOT / "experiments" / "bug_hunt_30.json"

random.seed(42)

# Pick all shard files, then sample evenly across shards for disease diversity.
shards = sorted(PROFILE_DIR.glob("patient_profiles_*.json"))
print(f"Found {len(shards)} shards")

per_shard = max(1, 30 // len(shards) + 1)
candidates = []

for shard in shards:
    with shard.open("r", encoding="utf-8") as f:
        data = json.load(f)
    idxs = random.sample(range(len(data)), min(per_shard, len(data)))
    for idx in idxs:
        p = data[idx]
        candidates.append({"shard": shard.name, "idx": idx, "profile": p})

# Trim to exactly 30, preferring diverse 主要病症
seen_diseases = set()
selected = []
for c in candidates:
    disease = (c["profile"].get("主要病症") or "").strip()
    if not disease:
        continue
    if disease in seen_diseases:
        continue
    seen_diseases.add(disease)
    selected.append(c)
    if len(selected) >= 30:
        break

# If we didn't hit 30 (rare), fill from candidates ignoring dup-check
if len(selected) < 30:
    for c in candidates:
        if c not in selected:
            selected.append(c)
        if len(selected) >= 30:
            break

selected = selected[:30]
print(f"Selected {len(selected)} profiles")

def build_question(p: dict) -> str:
    pub = p.get("publicInfo") or {}
    priv = p.get("privateInfo") or {}

    age = pub.get("年龄") or "成年"
    gender = pub.get("性别") or "患者"
    symptom = priv.get("主要叙述/症状") or priv.get("主诉") or ""
    history = priv.get("现病史") or ""
    history = history.strip().replace("\n", " ")
    if len(history) > 400:
        history = history[:400] + "…"

    main = (p.get("主要病症") or "").strip()
    others = p.get("其他相关病症") or []
    if isinstance(others, list):
        others_str = "、".join(str(x) for x in others if x)
    else:
        others_str = str(others)

    parts = [f"{age}岁{gender}"]
    if symptom:
        parts.append(f"主诉：{symptom}")
    if history:
        parts.append(f"现病史：{history}")
    if main:
        diag = f"诊断：{main}"
        if others_str:
            diag += f"（合并 {others_str}）"
        parts.append(diag)
    parts.append("请给出该患者的循证医学治疗推荐方案，包括首选药物/方案、剂量与疗程、监测要点。")
    return "。".join(parts)

questions = []
for i, c in enumerate(selected, 1):
    p = c["profile"]
    disease = (p.get("主要病症") or "未指定").strip()
    others = p.get("其他相关病症") or []
    others_str = "+".join(str(x) for x in others[:3] if x) if isinstance(others, list) else ""
    label = disease + (f"+{others_str}" if others_str else "")
    questions.append({
        "id": f"Q{i:02d}",
        "shard": c["shard"],
        "profile_idx": c["idx"],
        "disease": label[:60],
        "question": build_question(p),
    })

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with OUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(questions, f, ensure_ascii=False, indent=2)

print(f"Wrote {len(questions)} questions → {OUT_PATH}")
for q in questions[:5]:
    print(f"  [{q['id']}] {q['disease']}")
    print(f"     Q: {q['question'][:140]}…")
