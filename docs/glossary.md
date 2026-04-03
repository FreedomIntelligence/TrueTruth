# Glossary

Key terms used in EBM 5A and the Evidence-Based Medicine framework.

---

## 5A Framework

The international EBM workflow operationalised by this system:

| Stage | Full name | What it does |
|-------|-----------|-------------|
| **Ask** | Ask a structured question | Converts a free-text clinical question into a structured PICO format and identifies the question type |
| **Acquire** | Acquire the evidence | Searches PubMed with appropriate filters, re-ranks results with MedCPT |
| **Appraise** | Appraise the evidence | Rates each article's study type and assigns a GRADE evidence level |
| **Apply** | Apply to the patient | Synthesises the evidence into a recommendation with strength and quality ratings |
| **Assess** | Assess the outcome | Reviews the full workflow and produces a final structured summary |

---

## PICO

A framework for structuring clinical questions:

- **P** — Patient / Population / Problem
- **I** — Intervention (treatment, test, exposure)
- **C** — Comparison (alternative intervention, placebo, or no treatment)
- **O** — Outcome (what you are trying to measure or achieve)

Example: *"In [P: 68-year-old with NSTEMI and GI bleed], does [I: DAPT] compared to [C: clopidogrel monotherapy] reduce [O: recurrent MI] without increasing [O: GI bleeding]?"*

---

## Question Types

EBM 5A automatically identifies the question type during the Ask stage to apply the appropriate PubMed search filter:

| Type | Description | Search filter used |
|------|-------------|-------------------|
| **Therapy** | Does treatment X work better than Y? | High Sensitivity Search Strategy (HSSS) — RCTs and SRs |
| **Diagnosis** | How accurate is test X for condition Y? | Diagnostic test accuracy studies |
| **Prognosis** | What is the likely outcome for a patient with X? | Observational studies (cohort) |
| **Harm** | Does exposure X cause harm Y? | Observational studies (cohort + case-control) |
| **Prevention** | Does intervention X prevent condition Y? | RCTs and observational studies |

---

## GRADE Evidence Quality

GRADE (Grading of Recommendations Assessment, Development, and Evaluation) is the international standard for rating evidence quality. In EBM 5A, GRADE levels are **computed by deterministic Python code** — the LLM classifies study types and design features; Python calculates the final grade.

| Level | Meaning | Typical study types |
|-------|---------|-------------------|
| **High** | Very confident the effect estimate is close to the true effect | Systematic review / meta-analysis, well-designed RCT |
| **Moderate** | Moderately confident; true effect likely close to estimate, but may differ | RCT with limitations, well-designed observational |
| **Low** | Limited confidence; true effect may differ substantially | Observational study (cohort, case-control) |
| **Very Low** | Very little confidence in the effect estimate | Case series, expert opinion, narrative review |

Factors that **downgrade** evidence: risk of bias, inconsistency, indirectness, imprecision, publication bias.
Factors that **upgrade** evidence: large effect size, dose-response gradient, all plausible confounders reduce effect.

---

## Recommendation Strength

The Apply agent assigns a recommendation strength based on evidence quality and clinical context:

| Strength | Meaning | When used |
|----------|---------|-----------|
| **Strong** | Benefits clearly outweigh harms for most patients | High/Moderate GRADE evidence with consistent direction |
| **Conditional** | Benefits probably outweigh harms, but uncertainty exists | Lower GRADE evidence, indirect evidence, or significant patient variability |
| **Consensus-based** | No direct evidence; based on clinical guidelines or expert consensus | Diagnosis questions, topics covered by major guidelines (ESC, AHA, etc.) |
| **Insufficient Evidence** | Cannot make a recommendation — evidence is absent, conflicting, or too weak | No relevant studies retrieved or all studies critically flawed |

---

## Judge Score

Each stage's output is evaluated by the Judge LLM, which produces a score from 0.0 to 1.0.

- **Threshold:** 0.70 — stages scoring below this threshold are flagged for retry or backtrack.
- **Composition:** The Judge classifies individual quality dimensions as `pass` / `minor` / `major` / `critical`. Python code converts these labels to a numerical score.
- **Purpose:** Prevents low-quality intermediate outputs from propagating to the final recommendation.

---

## ReAct Loop

**Re**asoning + **Act**ing — the control loop pattern used by EBM 5A's coordinator:

1. Run stage → produce output
2. Judge scores the output
3. Scheduling LLM decides: proceed / retry / backtrack
4. Repeat until all stages pass or max iterations reached

This loop ensures quality gates are enforced at every stage and allows the system to recover from poor intermediate outputs.

---

## MedCPT

A biomedical dense retrieval model (from NCBI) used to re-rank PubMed search results by relevance to the clinical question. Runs locally using PyTorch (CPU inference). Improves article relevance compared to keyword-only BM25 ranking.
