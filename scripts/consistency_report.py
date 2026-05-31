"""
生成两轮 batch test 的一致性对比报告（Markdown 格式）。

用法：
    py scripts/consistency_report.py <full_log_1> <full_log_2> [--out report.md]

依赖：
    - 两个 full_*.log 文件（来自 batch_test_questions.py）
    - 对应的 summary_*.json 文件（自动匹配，需在同目录）
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from datetime import datetime

# ── LLM 方向一致性判断 ────────────────────────────────────────────────────────

_DIRECTION_PROMPT = """你是一名循证医学审计员。以下是同一临床问题的两个推荐答案（来自同一系统的两次独立运行）。

请用以下两个维度评估两者的一致性，每个维度只输出：一致 / 部分一致 / 不一致

维度1【核心推荐对象】：两者推荐的核心药物或治疗方案是否相同（如均推荐ARB、均推荐联合降压、均为证据不足）
维度2【推荐倾向】：两者的推荐方向是否相同（如均有明确偏好且方向一致、均无明确优劣、或一个有偏好而另一个无偏好/方向相反）

注意：忽略适用人群描述的措辞细节差异（如"成人"vs"成年高血压患者"），这类措辞差异不影响推荐方向一致性。

"总体"判定规则：两个维度均为"一致" → 总体"一致"；任一维度"部分一致" → 总体"部分一致"；任一维度"不一致" → 总体"不一致"

仅输出JSON，格式如下，不要任何其他文字：
{{"推荐对象": "一致|部分一致|不一致", "推荐倾向": "一致|部分一致|不一致", "总体": "一致|部分一致|不一致"}}

临床问题：{question}

答案A（Run 1）：
{answer1}

答案B（Run 2）：
{answer2}"""


def _load_env(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        if k and k not in os.environ:
            os.environ[k] = v.strip()


def judge_direction(question: str, a1: str, a2: str) -> dict:
    """用 gpt-5.5 对两段 Answer 做三维度 rubric 评分。"""
    try:
        import openai
        _load_env(Path(__file__).parent.parent / "hypertension" / ".env")
        client = openai.OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.huatuogpt.cn/v1"),
            timeout=30,
        )
        prompt = _DIRECTION_PROMPT.format(
            question=question,
            answer1=a1[:500],
            answer2=a2[:500],
        )
        resp = client.chat.completions.create(
            model="gpt-5.5",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=80,
        )
        content = resp.choices[0].message.content or ""
        # 提取 JSON
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as e:
        return {"error": str(e)[:60]}
    return {"error": "no JSON in response"}

# ── 常量 ─────────────────────────────────────────────────────────────────────

OOD_QUESTIONS = {
    "二甲双胍治疗 2 型糖尿病的效果",
    "乳腺癌的筛查推荐年龄",
    "儿童哮喘的阶梯治疗方案",
    "他汀类药物治疗高胆固醇血症",
    "幽门螺旋杆菌的根除方案",
    "阿司匹林用于冠心病二级预防",  # 实际上领域外（证据库无相关文章）
}

STRENGTH_ORDER = {
    "strong": 4, "conditional": 3, "weak": 2,
    "insufficient evidence": 1, "consensus-based": 2,
}
QUALITY_ORDER = {
    "high": 4, "moderate": 3, "low": 2, "very low": 1, "very_low": 1,
}


# ── 解析全文 log ──────────────────────────────────────────────────────────────

def _split_questions(log_text: str) -> list[tuple[int, str, str]]:
    """把 log 按题目分割，返回 [(idx, question, block_text), ...]"""
    pattern = re.compile(
        r"={80}\n\[(\d+)/30\] (.+?)\n={80}\n(.*?)(?=\n={80}\n\[\d+/30\]|\Z)",
        re.DOTALL,
    )
    results = []
    for m in pattern.finditer(log_text):
        idx = int(m.group(1))
        question = m.group(2).strip()
        block = m.group(3)
        results.append((idx, question, block))
    return results


def _extract_clinical_answer(block: str) -> dict:
    """从单道题的 block 中提取 CLINICAL ANSWER 各字段。"""
    data: dict = {
        "answer": "",
        "strength": "",
        "evidence_quality": "",
        "rationale": "",
        "caveats": [],
        "identified_gaps": [],
        "out_of_domain": False,
        "error": None,
        "total_timing_s": None,
    }

    # 错误检测
    if "openai.APITimeoutError" in block or "LLM-RETRY" in block:
        data["error"] = "API Timeout"
        return data

    # OOD 检测
    if "out_of_domain=true" in block.lower() or "专注于高血压" in block:
        data["out_of_domain"] = True

    # Total workflow time
    if m := re.search(r"\[TIMING\] Total workflow time: ([\d.]+)s", block):
        data["total_timing_s"] = float(m.group(1))

    # Identified Gaps（来自 QUALITY ASSESSMENT 或 Assess Identified Gaps）
    gaps_block = re.search(
        r"Identified Gaps:\n((?:    -[^\n]+\n)+)", block
    )
    if gaps_block:
        data["identified_gaps"] = [
            line.strip().lstrip("- ").strip()
            for line in gaps_block.group(1).splitlines()
            if line.strip()
        ]

    # CLINICAL ANSWER 区块
    ca_match = re.search(
        r"CLINICAL ANSWER\s*\n[★\s]+\n(.*?)(?=\n={80}|\Z)", block, re.DOTALL
    )
    if not ca_match:
        return data
    ca = ca_match.group(1)

    # Answer (A: 字段)
    a_match = re.search(r"^A:\s*(.*?)(?=\n\s{3,}Recommendation Strength|\n={80}|\Z)",
                        ca, re.DOTALL | re.MULTILINE)
    if a_match:
        data["answer"] = a_match.group(1).strip()

    # Recommendation Strength
    if m := re.search(r"Recommendation Strength\s*:\s*(.+)", ca):
        data["strength"] = m.group(1).strip()

    # Evidence Quality
    if m := re.search(r"Evidence Quality\s*:\s*(.+)", ca):
        data["evidence_quality"] = m.group(1).strip()

    # Rationale
    rat_match = re.search(
        r"Rationale\s*:\s*(.*?)(?=\n\s{3,}Caveats|\n\s{3,}Evidence Quality|\Z)",
        ca, re.DOTALL
    )
    if rat_match:
        data["rationale"] = rat_match.group(1).strip()

    # Caveats
    cav_match = re.search(r"Caveats\s*:\n((?:\s+[•\-][^\n]+\n)*)", ca)
    if cav_match:
        data["caveats"] = [
            line.strip().lstrip("•- ").strip()
            for line in cav_match.group(1).splitlines()
            if line.strip()
        ]

    return data


def parse_log(log_path: Path) -> dict[int, dict]:
    """解析 full log，返回 {idx: question_data}"""
    text = log_path.read_text(encoding="utf-8", errors="replace")
    questions = _split_questions(text)
    result = {}
    for idx, question, block in questions:
        d = _extract_clinical_answer(block)
        d["question"] = question
        result[idx] = d
    return result


def load_summary(log_path: Path) -> dict[int, dict]:
    """加载对应的 summary JSON，按 idx 索引。"""
    stem = log_path.stem  # full_TIMESTAMP
    ts = stem.replace("full_", "")
    summary_path = log_path.parent / f"summary_{ts}.json"
    if not summary_path.exists():
        return {}
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    return {item["idx"]: item for item in data}


# ── 一致性判断 ────────────────────────────────────────────────────────────────

def _normalize_strength(s: str) -> str:
    return s.strip().lower().replace("_", " ").replace("-", " ")


def _normalize_quality(s: str) -> str:
    return s.strip().lower().replace("_", " ").replace("-", " ")


def compare(d1: dict, d2: dict, use_llm: bool = True) -> dict:
    """比较两轮同一道题的关键维度（含 LLM 方向 rubric）。"""
    s1 = _normalize_strength(d1.get("strength", ""))
    s2 = _normalize_strength(d2.get("strength", ""))
    q1 = _normalize_quality(d1.get("evidence_quality", ""))
    q2 = _normalize_quality(d2.get("evidence_quality", ""))

    result = {
        "strength_match": s1 == s2,
        "quality_match": q1 == q2,
        "strength_1": d1.get("strength", "—"),
        "strength_2": d2.get("strength", "—"),
        "quality_1": d1.get("evidence_quality", "—"),
        "quality_2": d2.get("evidence_quality", "—"),
        "direction_rubric": None,
    }

    a1 = d1.get("answer", "")
    a2 = d2.get("answer", "")
    if use_llm and a1 and a2 and not d1.get("error") and not d2.get("error"):
        result["direction_rubric"] = judge_direction(
            d1.get("question", ""), a1, a2
        )
        time.sleep(0.3)  # rate limit

    return result


# ── 报告生成 ──────────────────────────────────────────────────────────────────

def _yn(b: bool) -> str:
    return "✅" if b else "❌"


def _trunc(s: str, n: int = 300) -> str:
    return (s[:n] + "…") if len(s) > n else s


def generate_report(
    run1: dict[int, dict],
    run2: dict[int, dict],
    sum1: dict[int, dict],
    sum2: dict[int, dict],
    log1_path: Path,
    log2_path: Path,
    use_llm: bool = True,
) -> str:
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines += [
        f"# EBM 5A 一致性测试报告",
        f"",
        f"生成时间：{now}",
        f"",
        f"- **Run 1**：`{log1_path.name}`",
        f"- **Run 2**：`{log2_path.name}`",
        f"",
        "---",
        "",
    ]

    domain_results = []  # [(idx, q, cmp)] for in-domain questions
    ood_indices = set()

    all_idx = sorted(set(run1.keys()) | set(run2.keys()))

    for idx in all_idx:
        d1 = run1.get(idx, {})
        d2 = run2.get(idx, {})
        question = d1.get("question") or d2.get("question", f"Q{idx:02d}")
        s1_info = sum1.get(idx, {})
        s2_info = sum2.get(idx, {})

        is_ood = (d1.get("out_of_domain") or d2.get("out_of_domain")
                  or question in OOD_QUESTIONS)
        if is_ood:
            ood_indices.add(idx)

        if not is_ood and use_llm:
            print(f"  LLM Q{idx:02d} ...", end=" ", flush=True)
        cmp = compare(d1, d2, use_llm=(not is_ood and use_llm))
        if not is_ood and use_llm:
            rb = cmp.get("direction_rubric") or {}
            print(rb.get("总体", rb.get("error", "skipped")))

        lines += [f"## Q{idx:02d}. {question}"]
        if is_ood:
            lines += ["", "> **[OOD 软拒绝]** 此题在领域外，不计入一致性统计。", ""]
        else:
            domain_results.append((idx, question, cmp))

        # 时间
        fc1 = s1_info.get("first_char_time_s", "—")
        tc1 = d1.get("total_timing_s") or s1_info.get("total_timing_s") or "—"
        fc2 = s2_info.get("first_char_time_s", "—")
        tc2 = d2.get("total_timing_s") or s2_info.get("total_timing_s") or "—"
        err1 = d1.get("error") or s1_info.get("error")
        err2 = d2.get("error") or s2_info.get("error")

        lines += [""]
        lines += [f"| | Run 1 | Run 2 |"]
        lines += [f"|--|--|--|"]
        lines += [f"| 首字时间 | {fc1}s | {fc2}s |"]
        lines += [f"| 总时间 | {tc1}s | {tc2}s |"]
        if err1 or err2:
            lines += [f"| 错误 | {err1 or '—'} | {err2 or '—'} |"]
        lines += [""]

        if not is_ood:
            lines += ["### 一致性对比"]
            lines += [""]
            lines += [f"| 维度 | Run 1 | Run 2 | 一致？ |"]
            lines += [f"|------|-------|-------|--------|"]
            lines += [f"| 推荐强度 | {cmp['strength_1']} | {cmp['strength_2']} | {_yn(cmp['strength_match'])} |"]
            lines += [f"| 证据质量 | {cmp['quality_1']} | {cmp['quality_2']} | {_yn(cmp['quality_match'])} |"]

            rb = cmp.get("direction_rubric")
            if rb and "error" not in rb:
                def _icon(v):
                    if v == "一致": return "✅"
                    if v == "部分一致": return "🟡"
                    return "❌"
                lines += [f"| 推荐对象 | — | — | {_icon(rb.get('推荐对象','—'))} {rb.get('推荐对象','—')} |"]
                lines += [f"| 推荐倾向 | — | — | {_icon(rb.get('推荐倾向','—'))} {rb.get('推荐倾向','—')} |"]
                lines += [f"| **综合方向** | — | — | **{_icon(rb.get('总体','—'))} {rb.get('总体','—')}** |"]
            elif rb and "error" in rb:
                lines += [f"| 推荐方向 (LLM) | — | — | ⚠️ {rb['error']} |"]
            lines += [""]

        # Run 1 详情
        if not err1 and not is_ood:
            lines += ["### Run 1 推荐"]
            lines += [""]
            if d1.get("answer"):
                lines += [f"**答案**：", "", _trunc(d1["answer"]), ""]
            if d1.get("rationale"):
                lines += [f"**依据**：", "", _trunc(d1["rationale"]), ""]
            if d1.get("caveats"):
                lines += ["**注意事项**：", ""]
                for c in d1["caveats"]:
                    lines += [f"- {c}"]
                lines += [""]
            if d1.get("identified_gaps"):
                lines += ["**已识别差距**：", ""]
                for g in d1["identified_gaps"]:
                    lines += [f"- {g}"]
                lines += [""]

        # Run 2 详情
        if not err2 and not is_ood:
            lines += ["### Run 2 推荐"]
            lines += [""]
            if d2.get("answer"):
                lines += [f"**答案**：", "", _trunc(d2["answer"]), ""]
            if d2.get("rationale"):
                lines += [f"**依据**：", "", _trunc(d2["rationale"]), ""]
            if d2.get("caveats"):
                lines += ["**注意事项**：", ""]
                for c in d2["caveats"]:
                    lines += [f"- {c}"]
                lines += [""]
            if d2.get("identified_gaps"):
                lines += ["**已识别差距**：", ""]
                for g in d2["identified_gaps"]:
                    lines += [f"- {g}"]
                lines += [""]

        lines += ["---", ""]

    # ── 汇总统计 ──────────────────────────────────────────────────────────────
    n_domain = len(domain_results)
    n_strength = sum(1 for _, _, c in domain_results if c["strength_match"])
    n_quality  = sum(1 for _, _, c in domain_results if c["quality_match"])
    n_both     = sum(1 for _, _, c in domain_results if c["strength_match"] and c["quality_match"])

    # 方向一致性（LLM rubric）
    direction_results = [(idx, q, c) for idx, q, c in domain_results
                         if c.get("direction_rubric") and "error" not in c["direction_rubric"]]
    n_dir = len(direction_results)
    n_obj  = sum(1 for _, _, c in direction_results if c["direction_rubric"].get("推荐对象") == "一致")
    n_tend = sum(1 for _, _, c in direction_results if c["direction_rubric"].get("推荐倾向") == "一致")
    n_overall_dir = sum(1 for _, _, c in direction_results if c["direction_rubric"].get("总体") == "一致")
    n_partial_dir = sum(1 for _, _, c in direction_results if c["direction_rubric"].get("总体") == "部分一致")
    n_incon_dir   = sum(1 for _, _, c in direction_results if c["direction_rubric"].get("总体") == "不一致")

    lines += ["# 汇总统计", ""]
    lines += [f"领域内题目：{n_domain} 道（排除 {len(ood_indices)} 道 OOD）", ""]
    lines += ["## 机器可测指标（精确匹配）", ""]
    lines += ["| 维度 | 一致题数 | 一致率 |"]
    lines += ["|------|---------|-------|"]
    lines += [f"| 推荐强度 | {n_strength}/{n_domain} | {n_strength/n_domain*100:.0f}% |"]
    lines += [f"| 证据质量 | {n_quality}/{n_domain} | {n_quality/n_domain*100:.0f}% |"]
    lines += [f"| 强度+质量均一致 | {n_both}/{n_domain} | {n_both/n_domain*100:.0f}% |"]
    lines += [""]
    if n_dir > 0:
        lines += [f"## LLM 方向 Rubric（gpt-5.5，{n_dir} 道有效评分；依据 GRADE IRR 标准去除适用人群维度）", ""]
        lines += ["| 维度 | 一致 | 部分一致 | 不一致 | 一致率 |"]
        lines += ["|------|------|---------|-------|-------|"]
        lines += [f"| 推荐对象 | {n_obj} | — | {n_dir-n_obj} | {n_obj/n_dir*100:.0f}% |"]
        lines += [f"| 推荐倾向 | {n_tend} | — | {n_dir-n_tend} | {n_tend/n_dir*100:.0f}% |"]
        lines += [f"| **综合方向** | **{n_overall_dir}** | **{n_partial_dir}** | **{n_incon_dir}** | **{n_overall_dir/n_dir*100:.0f}%** |"]
        lines += [""]
        lines += [f"> 学术依据：GRADE IRR 研究（PMID 26845745）显示推荐方向（for/against）kappa≈0.74，"]
        lines += [f"> 适用人群描述差异属于 GRADE indirectness 范畴，不作为独立一致性指标。"]
        lines += [""]

    # 不一致题目列表
    inconsistent = [(idx, q, c) for idx, q, c in domain_results
                    if not (c["strength_match"] and c["quality_match"])]
    if inconsistent:
        lines += ["### 不一致题目", ""]
        for idx, q, c in inconsistent:
            reasons = []
            if not c["strength_match"]:
                reasons.append(f"强度：{c['strength_1']} vs {c['strength_2']}")
            if not c["quality_match"]:
                reasons.append(f"质量：{c['quality_1']} vs {c['quality_2']}")
            lines += [f"- **Q{idx:02d}** {q}：{' | '.join(reasons)}"]
        lines += [""]

    # 推荐方向说明
    lines += [
        "> **注**：推荐方向（Answer 全文对比）需人工审阅——LLM 不会逐字复现，",
        "> 上表仅作为机器可验证的客观指标。完整 Answer 见各题详情。",
        "",
    ]

    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="EBM 5A 一致性报告生成器")
    parser.add_argument("log1", help="第一轮 full_*.log 路径")
    parser.add_argument("log2", help="第二轮 full_*.log 路径")
    parser.add_argument("--out", default="logs/batch_test/consistency_report.md",
                        help="输出 Markdown 文件路径")
    parser.add_argument("--no-llm", action="store_true",
                        help="跳过 LLM 方向 rubric（仅精确匹配统计）")
    args = parser.parse_args()

    log1 = Path(args.log1)
    log2 = Path(args.log2)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"解析 Run 1: {log1.name} ...", flush=True)
    run1 = parse_log(log1)
    sum1 = load_summary(log1)

    print(f"解析 Run 2: {log2.name} ...", flush=True)
    run2 = parse_log(log2)
    sum2 = load_summary(log2)

    use_llm = not args.no_llm
    print(f"生成报告 (LLM方向评分: {'开启 gpt-5.5' if use_llm else '关闭'}) ...", flush=True)
    report = generate_report(run1, run2, sum1, sum2, log1, log2, use_llm=use_llm)

    out_path.write_text(report, encoding="utf-8")
    print(f"报告已保存：{out_path}")

    # 打印汇总
    n_domain = sum(1 for d in run1.values()
                   if not d.get("out_of_domain") and d.get("question") not in OOD_QUESTIONS)
    print(f"领域内题目：~{n_domain} 道")


if __name__ == "__main__":
    main()
