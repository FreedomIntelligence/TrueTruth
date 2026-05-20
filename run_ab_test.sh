#!/bin/bash
# A/B comparison test: 11-type GRADE vs 4-type GRADE
# Usage: ./run_ab_test.sh "clinical question"
#
# Runs the question twice:
#   A: current code (11 GRADE study types)
#   B: patched code (4 GRADE study types, original)
# PubMed results are cached after run A, so run B network time ≈ 0.

set -e
export PYTHONPATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    exit 1
fi

mkdir -p logs

QUESTION="${1:-对于2型糖尿病患者，SGLT2抑制剂（达格列净）与二甲双胍相比是否能更有效地降低心血管事件风险？}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

AGENT_FILE="src/agents/appraise_agent.py"
PROMPT_FILE="src/config/prompts/appraise_agent.txt"

# ---------- helper: patch to 4-type GRADE ----------
patch_to_4types() {
    python3 - "$AGENT_FILE" <<'PYEOF'
import sys, re

path = sys.argv[1]
with open(path) as f:
    content = f.read()

# Replace _INITIAL_POINTS block
old_points = '''_INITIAL_POINTS: Dict[str, int] = {
    "RCT": 4,
    "SYSTEMATIC_REVIEW": 4,   # Starts High (synthesizes RCTs or best available evidence)
    "META_ANALYSIS": 4,        # Starts High
    "NMA": 4,                  # Network meta-analysis: starts High
    "COHORT": 2,
    "CASE_CONTROL": 2,
    "CROSS_SECTIONAL": 2,      # Observational: starts Low
    "NARRATIVE_REVIEW": 1,     # Expert synthesis without systematic search: Very Low
    "CASE_REPORT": 1,
    "GUIDELINE": 3,            # Typically based on SR: starts Moderate
    "EXPERT_OPINION": 1,       # No systematic search: Very Low
}'''
new_points = '''_INITIAL_POINTS: Dict[str, int] = {
    "RCT": 4,
    "COHORT": 2,
    "CASE_CONTROL": 2,
    "CASE_REPORT": 1,
}'''
content = content.replace(old_points, new_points)

# Replace _GRADE_CODE_TO_LABEL block
old_label = '''_GRADE_CODE_TO_LABEL: Dict[str, str] = {
    "RCT": "RCT",
    "SYSTEMATIC_REVIEW": "Systematic Review",
    "META_ANALYSIS": "Meta-Analysis",
    "NMA": "Network Meta-Analysis",
    "COHORT": "Cohort Study",
    "CASE_CONTROL": "Case-Control Study",
    "CROSS_SECTIONAL": "Cross-Sectional Study",
    "NARRATIVE_REVIEW": "Narrative Review",
    "CASE_REPORT": "Case Report",
    "GUIDELINE": "Clinical Practice Guideline",
    "EXPERT_OPINION": "Expert Opinion",
}'''
new_label = '''_GRADE_CODE_TO_LABEL: Dict[str, str] = {
    "RCT": "RCT",
    "COHORT": "Cohort Study",
    "CASE_CONTROL": "Case-Control Study",
    "CASE_REPORT": "Case Report",
}'''
content = content.replace(old_label, new_label)

# Fix upgrade factors condition
content = content.replace(
    'if study_type in ("COHORT", "CASE_CONTROL", "CROSS_SECTIONAL"):',
    'if study_type in ("COHORT", "CASE_CONTROL"):'
)

with open(path, 'w') as f:
    f.write(content)
print("Patched to 4-type GRADE.")
PYEOF
}

# ---------- helper: restore to 11-type GRADE ----------
restore_to_11types() {
    python3 - "$AGENT_FILE" <<'PYEOF'
import sys

path = sys.argv[1]
with open(path) as f:
    content = f.read()

old_points = '''_INITIAL_POINTS: Dict[str, int] = {
    "RCT": 4,
    "COHORT": 2,
    "CASE_CONTROL": 2,
    "CASE_REPORT": 1,
}'''
new_points = '''_INITIAL_POINTS: Dict[str, int] = {
    "RCT": 4,
    "SYSTEMATIC_REVIEW": 4,   # Starts High (synthesizes RCTs or best available evidence)
    "META_ANALYSIS": 4,        # Starts High
    "NMA": 4,                  # Network meta-analysis: starts High
    "COHORT": 2,
    "CASE_CONTROL": 2,
    "CROSS_SECTIONAL": 2,      # Observational: starts Low
    "NARRATIVE_REVIEW": 1,     # Expert synthesis without systematic search: Very Low
    "CASE_REPORT": 1,
    "GUIDELINE": 3,            # Typically based on SR: starts Moderate
    "EXPERT_OPINION": 1,       # No systematic search: Very Low
}'''
content = content.replace(old_points, new_points)

old_label = '''_GRADE_CODE_TO_LABEL: Dict[str, str] = {
    "RCT": "RCT",
    "COHORT": "Cohort Study",
    "CASE_CONTROL": "Case-Control Study",
    "CASE_REPORT": "Case Report",
}'''
new_label = '''_GRADE_CODE_TO_LABEL: Dict[str, str] = {
    "RCT": "RCT",
    "SYSTEMATIC_REVIEW": "Systematic Review",
    "META_ANALYSIS": "Meta-Analysis",
    "NMA": "Network Meta-Analysis",
    "COHORT": "Cohort Study",
    "CASE_CONTROL": "Case-Control Study",
    "CROSS_SECTIONAL": "Cross-Sectional Study",
    "NARRATIVE_REVIEW": "Narrative Review",
    "CASE_REPORT": "Case Report",
    "GUIDELINE": "Clinical Practice Guideline",
    "EXPERT_OPINION": "Expert Opinion",
}'''
content = content.replace(old_label, new_label)

content = content.replace(
    'if study_type in ("COHORT", "CASE_CONTROL"):',
    'if study_type in ("COHORT", "CASE_CONTROL", "CROSS_SECTIONAL"):'
)

with open(path, 'w') as f:
    f.write(content)
print("Restored to 11-type GRADE.")
PYEOF
}

# ---------- Run A: 11-type GRADE (current) ----------
LOG_A="logs/ab_11types_${TIMESTAMP}.log"
echo "=============================================="
echo "[A] Running with 11-type GRADE..."
echo "    Log: $LOG_A"
echo "=============================================="
python3 src/main.py "$QUESTION" 2>&1 | tee "$LOG_A"
echo ""

# ---------- Patch to 4-type, Run B ----------
patch_to_4types

LOG_B="logs/ab_4types_${TIMESTAMP}.log"
echo "=============================================="
echo "[B] Running with 4-type GRADE..."
echo "    Log: $LOG_B"
echo "=============================================="
python3 src/main.py "$QUESTION" 2>&1 | tee "$LOG_B"
echo ""

# ---------- Restore to 11-type ----------
restore_to_11types

# ---------- Summary ----------
echo "=============================================="
echo "A/B COMPARISON SUMMARY"
echo "=============================================="
echo "Question: $QUESTION"
echo ""
echo "--- Run A (11-type GRADE) ---"
grep -E 'Total workflow|Agent Calls:|FAST-PATH|Appraise.*agent:|Apply.*agent:' "$LOG_A" | head -20
echo ""
echo "--- Run B (4-type GRADE) ---"
grep -E 'Total workflow|Agent Calls:|FAST-PATH|Appraise.*agent:|Apply.*agent:' "$LOG_B" | head -20
echo ""
echo "Logs: $LOG_A  |  $LOG_B"
echo "=============================================="
