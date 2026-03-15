#!/usr/bin/env python3
"""
Batch test script for EBM 5A system.
Runs 10 treatment-type questions from patient_profiles_6000-6999.json,
covering a mix of common diseases (sufficient evidence) and rare/complex
conditions (likely insufficient/conditional evidence).

Each case gets its own log file: logs/batch_C01_YYYYMMDD_HHMMSS.log

Usage:
    python run_batch_test.py              # run all 10 cases sequentially
    python run_batch_test.py --dry-run   # print questions without running
    python run_batch_test.py --cases 0 1 2  # run specific cases by 0-based index
"""
import subprocess
import re
import sys
import time
import os
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 10 selected test cases
# Mix of: common (sufficient evidence) / complex or rare (conditional/insufficient)
# ---------------------------------------------------------------------------
CASES = [
    {
        "id": "C01",
        "profile_idx": 103,
        "disease": "2型糖尿病+周围神经病变+高血压",
        "expected_evidence": "充足",
        "question": (
            "70岁女性，2型糖尿病病史十余年，血糖长期控制不佳，近3个月出现双足麻木。"
            "合并原发性高血压（2级，极高危）、冠心病（NYHA I级）、肥胖症、混合型高脂血症。"
            "空腹血糖9.2 mmol/L，HbA1c 9.1%，BMI 28.6 kg/m²，血压156/92 mmHg，"
            "eGFR 62 mL/min，尿白蛋白/肌酐比值85 mg/g。"
            "请给出最佳血糖控制及糖尿病周围神经病变治疗方案的循证医学推荐。"
        ),
    },
    {
        "id": "C02",
        "profile_idx": 6,
        "disease": "慢性心力衰竭急性加重+CKD+高钾血症",
        "expected_evidence": "充足",
        "question": (
            "86岁女性，慢性心力衰竭（射血分数降低，EF 35%）急性加重，呼吸困难加重10余天。"
            "合并慢性肾脏病（eGFR 32 mL/min，CKD 3b期）、高钾血症（血钾6.2 mmol/L）、"
            "高血压、骨质疏松。既往长期服用螺内酯25mg/d，入院后血钾持续偏高。"
            "请给出慢性心力衰竭射血分数降低（HFrEF）合并CKD及高钾血症时的药物治疗方案循证医学推荐，"
            "包括利尿剂、RAAS抑制剂、β受体阻滞剂的使用策略及高钾血症处理。"
        ),
    },
    {
        "id": "C03",
        "profile_idx": 3,
        "disease": "高血压合并CKD+冠心病+脑梗死",
        "expected_evidence": "充足",
        "question": (
            "76岁女性，间断头晕14年，近1月加重伴乏力，偶有耳鸣、失眠多梦。"
            "合并高血压（长期使用比索洛尔+厄贝沙坦）、慢性肾脏病（CKD 3期，eGFR 38 mL/min）、"
            "冠状动脉粥样硬化性心脏病、高脂血症（LDL-C 3.4 mmol/L）、陈旧性腔隙性脑梗死。"
            "血压162/88 mmHg，血肌酐148 μmol/L，尿蛋白(+)。"
            "请给出该患者高血压合并CKD、冠心病、陈旧性脑梗死时的降压目标值和降压药物选择循证医学推荐，"
            "以及血脂管理策略。"
        ),
    },
    {
        "id": "C04",
        "profile_idx": 26,
        "disease": "社区获得性重症侵袭性肺曲霉感染",
        "expected_evidence": "中等",
        "question": (
            "58岁女性，既往体健，无免疫抑制病史，发热伴胸闷气喘、咳嗽咯痰6天，"
            "入院时神志不清，氧合指数156 mmHg，需气管插管机械通气。"
            "支气管肺泡灌洗液GM试验阳性（指数3.2），mNGS检测到烟曲霉核酸序列，"
            "胸部CT示双肺多发浸润影伴空洞形成，确诊社区获得性侵袭性肺曲霉菌病（IPA）。"
            "请给出免疫功能正常宿主发生侵袭性肺曲霉菌病的一线抗真菌治疗方案循证医学推荐，"
            "包括首选药物（伏立康唑vs艾沙康唑vs两性霉素B）、剂量调整及疗程。"
        ),
    },
    {
        "id": "C05",
        "profile_idx": 48,
        "disease": "霍奇金淋巴瘤合并结核性心包炎",
        "expected_evidence": "中等",
        "question": (
            "27岁男性，低热、胸闷15天，加重4天。"
            "心包穿刺液结核分枝杆菌培养阳性，确诊结核性心包炎伴大量心包积液。"
            "同时颈部淋巴结活检病理确诊经典型霍奇金淋巴瘤（混合细胞型，Ann Arbor IIA期）。"
            "ECOG PS 1分，无B症状外的全身症状，LDH正常。"
            "请给出经典型霍奇金淋巴瘤合并活动性结核性心包炎时的治疗策略循证医学推荐，"
            "包括：抗结核治疗与淋巴瘤化疗的先后顺序、一线化疗方案选择（ABVD vs BV-AVD）"
            "及两者合并用药的安全性考量。"
        ),
    },
    {
        "id": "C06",
        "profile_idx": 109,
        "disease": "鹦鹉热衣原体肺炎+中度ARDS",
        "expected_evidence": "中等",
        "question": (
            "67岁男性，有鸟类接触史，高热（39.8℃）、咳嗽、咳痰5天，进行性呼吸困难。"
            "氧合指数108 mmHg（柏林标准中度ARDS），需无创通气。"
            "mNGS及血清抗体检测确诊鹦鹉热衣原体感染（Chlamydia psittaci）。"
            "胸部CT示双肺多叶段实变，CRP 186 mg/L，PCT 2.3 ng/mL。"
            "请给出鹦鹉热衣原体肺炎合并中度ARDS的抗感染治疗循证医学推荐，"
            "包括：首选抗生素（多西环素 vs 阿奇霉素 vs 氟喹诺酮）、剂量、疗程，"
            "以及合并ARDS时的呼吸支持策略。"
        ),
    },
    {
        "id": "C07",
        "profile_idx": 111,
        "disease": "重症SLE合并狼疮性心肌炎（EF降低）",
        "expected_evidence": "不足（罕见）",
        "question": (
            "19岁女性，关节肿痛、咳嗽胸闷2月，突发抽搐1周。"
            "ANA 1:640（+），抗dsDNA抗体高滴度阳性，补体C3/C4显著降低，"
            "24h尿蛋白2.8g，确诊系统性红斑狼疮（SLEDAI-2K评分24分）。"
            "超声心动图示左室收缩功能下降（EF 38%），肌钙蛋白I 2.1 μg/L，"
            "心脏MRI提示心肌水肿及延迟强化，符合狼疮性心肌炎。"
            "合并肺水肿（BNP 1820 pg/mL）及肺部感染。"
            "请给出重症系统性红斑狼疮合并狼疮性心肌炎（EF<40%）的免疫抑制治疗方案循证医学推荐，"
            "包括：激素用法、免疫抑制剂选择（环磷酰胺vs吗替麦考酚酯vs钙调神经磷酸酶抑制剂）"
            "及丙种球蛋白使用指征。"
        ),
    },
    {
        "id": "C08",
        "profile_idx": 87,
        "disease": "Wilson病（肝豆状核变性）神经型",
        "expected_evidence": "不足（罕见）",
        "question": (
            "23岁女性，言语不利4年，双手抖动2个月余，伴站立不稳、强笑，全身皮肤色素沉着。"
            "双眼裂隙灯检查可见K-F环（Kayser-Fleischer ring）。"
            "血清铜蓝蛋白0.08 g/L（参考值>0.20 g/L，明显降低），"
            "24h尿铜456 μg（参考值<100 μg，明显升高）。"
            "肝功能：ALT 68 U/L，AST 72 U/L；腹部超声示肝回声增粗，脾大。"
            "头颅MRI示双侧基底节区T2WI高信号，确诊Wilson病（肝豆状核变性），神经型为主要表现。"
            "请给出Wilson病神经型（有明显神经系统症状）的首选驱铜治疗方案循证医学推荐，"
            "包括：青霉胺 vs 曲恩汀 vs 锌盐的选择依据、剂量、监测要点及神经症状恶化风险处理。"
        ),
    },
    {
        "id": "C09",
        "profile_idx": 51,
        "disease": "重型β-地中海贫血（无HLA全相合供者）",
        "expected_evidence": "不足（罕见）",
        "question": (
            "12岁女孩，自幼重度贫血，确诊重型β-地中海贫血（β0/β0纯合突变）。"
            "需每3-4周输血一次（每次2单位悬浮红细胞），已累计输血超过200单位，"
            "血清铁蛋白3800 μg/L，肝脏MRI R2*值升高提示铁过载（肝脏铁沉积量估算8 mg/g干重）。"
            "无HLA全相合同胞供者，HLA单倍体相合父母可用，患者家庭经济条件有限。"
            "脾脏明显肿大（超声测量脾厚7.2 cm）。"
            "请给出无HLA全相合同胞供者的重型β-地中海贫血综合管理循证医学推荐，"
            "包括：输血策略、去铁治疗方案选择（去铁胺 vs 地拉罗司 vs 地非酮）、"
            "单倍体相合移植可行性评估，以及新兴治疗（luspatercept、基因治疗）的证据现状。"
        ),
    },
    {
        "id": "C10",
        "profile_idx": 75,
        "disease": "BPDCN（母细胞性浆细胞样树突细胞肿瘤）儿童",
        "expected_evidence": "不足（极罕见）",
        "question": (
            "10岁女孩，全身多处皮肤紫褐色斑块3个月，逐渐扩大融合。"
            "皮肤活检免疫组化：CD4(+)、CD56(+)、CD123(+)、TCF4(+)、CD3(-)、CD20(-)，"
            "确诊母细胞性浆细胞样树突细胞肿瘤（BPDCN）。"
            "骨髓活检：肿瘤细胞占15%，流式细胞学证实骨髓累及。"
            "全身PET-CT示皮肤广泛受累及骨髓受累，无淋巴结肿大，无中枢神经系统受累。"
            "ECOG PS 1分，无明显脏器功能障碍。"
            "请给出儿童BPDCN（皮肤+骨髓受累，无CNS累及）的诱导化疗方案循证医学推荐，"
            "包括：儿童与成人方案的差异、是否需要预防性中枢治疗、"
            "达到缓解后造血干细胞移植的指征及最新靶向治疗（tagraxofusp等）的证据。"
        ),
    },
]

# ---------------------------------------------------------------------------
# Log parsing
# ---------------------------------------------------------------------------
def parse_log(log_path: str) -> dict:
    result = {
        "question_type": "N/A",
        "strength": "N/A",
        "quality_score": "N/A",
        "duration_s": "N/A",
        "apply_calls": "N/A",
        "status": "unknown",
    }
    try:
        text = Path(log_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        result["status"] = "log_not_found"
        return result

    m = re.search(r"\[DEBUG\] question_type=(\w+)", text)
    if m:
        result["question_type"] = m.group(1)

    m = re.search(r"Recommendation Strength\s*:\s*(.+)", text)
    if m:
        result["strength"] = m.group(1).strip()

    m = re.search(r"Overall Quality Score\s*:\s*([\d.]+)", text)
    if m:
        result["quality_score"] = m.group(1)

    m = re.search(r"Total workflow time:\s*([\d.]+)s", text)
    if m:
        result["duration_s"] = m.group(1)

    m = re.search(r"'Apply':\s*(\d+)", text)
    if m:
        result["apply_calls"] = m.group(1)

    if "No recommendation generated" in text or result["strength"] == "N/A":
        result["status"] = "incomplete"
    elif "Traceback" in text or "InternalServerError" in text or "JSON parse failed" in text:
        result["status"] = "error"
    elif result["strength"] not in ("N/A",) and result["quality_score"] not in ("N/A",):
        result["status"] = "success"
    else:
        result["status"] = "incomplete"

    return result


def print_summary(results: list):
    sep = "─" * 115
    print(f"\n{'='*115}")
    print("BATCH TEST SUMMARY")
    print(f"{'='*115}")
    print(f"{'ID':<5} {'Disease':<38} {'Expected':<12} {'Type':<12} {'Strength':<22} {'Score':<7} {'Time':<8} {'Apply':<6} Status")
    print(sep)
    for r in results:
        c = r["case"]
        m = r["metrics"]
        print(
            f"{c['id']:<5} {c['disease'][:37]:<38} {c['expected_evidence']:<12} "
            f"{m['question_type']:<12} {m['strength'][:21]:<22} {m['quality_score']:<7} "
            f"{m['duration_s']+'s':<8} {'x'+m['apply_calls']:<6} {m['status']}"
        )
    print(sep)

    successes = [r for r in results if r["metrics"]["status"] == "success"]
    by_strength = {}
    for r in successes:
        s = r["metrics"]["strength"]
        by_strength[s] = by_strength.get(s, 0) + 1

    print(f"\n完成: {len(successes)}/{len(results)}")
    for s, n in sorted(by_strength.items()):
        print(f"  {s}: {n}")
    print('='*115)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    dry_run = "--dry-run" in sys.argv

    selected_indices = None
    if "--cases" in sys.argv:
        idx = sys.argv.index("--cases")
        selected_indices = set(int(x) for x in sys.argv[idx + 1:] if x.isdigit())

    cases_to_run = [
        c for i, c in enumerate(CASES)
        if selected_indices is None or i in selected_indices
    ]

    batch_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    Path("logs").mkdir(exist_ok=True)
    summary_log = f"logs/batch_summary_{batch_ts}.tsv"

    print(f"{'='*65}")
    print(f"EBM 5A Batch Test  —  {len(cases_to_run)} cases")
    print(f"Batch timestamp: {batch_ts}")
    print(f"Summary: {summary_log}")
    print(f"Case logs: logs/batch_<ID>_<TIMESTAMP>.log")
    print(f"{'='*65}\n")

    if dry_run:
        for i, c in enumerate(cases_to_run):
            print(f"[{c['id']}] {c['disease']}  (expected: {c['expected_evidence']})")
            print(f"  Q: {c['question'][:120]}...")
            print()
        return

    # Write TSV header
    with open(summary_log, "w", encoding="utf-8") as f:
        f.write("id\tdisease\texpected_evidence\tquestion_type\tstrength\tquality_score\t"
                "duration_s\tapply_calls\tstatus\tlog_file\n")

    results = []

    for i, case in enumerate(cases_to_run):
        case_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"logs/batch_{case['id']}_{case_ts}.log"

        print(f"\n{'─'*65}")
        print(f"[{i+1}/{len(cases_to_run)}] {case['id']}: {case['disease']}")
        print(f"  Expected evidence: {case['expected_evidence']}")
        print(f"  Log: {log_file}")
        print(f"{'─'*65}")

        # Set PYTHONPATH and run main.py directly, tee to case-specific log
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).parent)

        cmd = f'python3 src/main.py "$QUESTION" 2>&1 | tee "{log_file}"'

        start = time.time()
        try:
            subprocess.run(
                ["bash", "-c", cmd],
                env={**env, "QUESTION": case["question"]},
                timeout=900,
            )
            elapsed = time.time() - start
            metrics = parse_log(log_file)
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start
            metrics = {
                "question_type": "N/A", "strength": "TIMEOUT",
                "quality_score": "N/A", "duration_s": str(int(elapsed)),
                "apply_calls": "N/A", "status": "timeout",
            }
        except Exception:
            elapsed = time.time() - start
            metrics = {
                "question_type": "N/A", "strength": "ERROR",
                "quality_score": "N/A", "duration_s": str(int(elapsed)),
                "apply_calls": "N/A", "status": f"exception",
            }

        results.append({"case": case, "metrics": metrics, "log_file": log_file})

        print(f"\n  → type={metrics['question_type']}  strength={metrics['strength']}"
              f"  score={metrics['quality_score']}  time={metrics['duration_s']}s"
              f"  apply×{metrics['apply_calls']}  [{metrics['status']}]")

        # Append to TSV summary
        with open(summary_log, "a", encoding="utf-8") as f:
            f.write(
                f"{case['id']}\t{case['disease']}\t{case['expected_evidence']}\t"
                f"{metrics['question_type']}\t{metrics['strength']}\t"
                f"{metrics['quality_score']}\t{metrics['duration_s']}\t"
                f"{metrics['apply_calls']}\t{metrics['status']}\t{log_file}\n"
            )

        if i < len(cases_to_run) - 1:
            print("  (5s pause before next case...)")
            time.sleep(5)

    print_summary(results)
    print(f"\nFull results saved to: {summary_log}")
    print("Individual logs: logs/batch_C0*_*.log")


if __name__ == "__main__":
    main()
