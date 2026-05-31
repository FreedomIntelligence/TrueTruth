# Section 1.1 — Evidence-Based Medicine: An Overview and Its Current Limitations
## Outline (English)

---

### Part I: Definition and Historical Origins

**Opening / Core Definition**
- Sackett's (1996) canonical definition: "the conscientious, explicit, and judicious use of current best evidence in making decisions about the care of individual patients"
- EBM as an integrative framework: best research evidence + clinical expertise + patient values and preferences

**Historical Development**
- Intellectual precursors: the Paris Clinical School of the 19th century (Pierre Louis and numerical methods); Avicenna's 11th-century proto-experimental thinking
- Modern foundations: Alvan Feinstein (1950s, clinical epidemiology and quantitative clinical reasoning); Archie Cochrane (1972, *Effectiveness and Efficiency*)
- Formal emergence: Gordon Guyatt (1991, *ACP Journal Club*) coined the term "evidence-based medicine"; David Sackett at McMaster University systematized EBM teaching
- Institutionalization: founding of the Cochrane Collaboration (1993); development of the GRADE framework (Guyatt et al., 2004) as the international standard for evidence grading

**The Three Pillars of EBM**
1. Best available research evidence
2. Clinical expertise and judgment
3. Patient values, preferences, and circumstances

---

### Part II: The 5A Framework — Standard EBM Workflow

**Five Steps (one sentence each)**
- **Ask**: Translate clinical uncertainty into a structured, searchable question using frameworks such as PICO, PIRD, or PEO
- **Acquire**: Systematically search for the best available evidence from databases such as PubMed, MEDLINE, and the Cochrane Library
- **Appraise**: Critically evaluate retrieved evidence for validity, magnitude of effect, and applicability — assessed using the GRADE methodology
- **Apply**: Integrate appraised evidence with clinical judgment and patient preferences to formulate a recommendation (graded as Strong, Conditional, or Weak)
- **Assess**: Evaluate the outcome of applying the recommendation in practice and feed findings back into the cycle

**The GRADE Methodology** *(one dedicated paragraph)*
- Four levels of evidence quality: High, Moderate, Low, Very Low
- Recommendation strength is determined by three factors: evidence quality, benefit-to-harm ratio, and patient values
- Currently the standard method adopted by WHO, the Cochrane Collaboration, and most major clinical guideline bodies worldwide

---

### Part III: Limitations and Criticisms of EBM in Practice

**(1) Time Burden and Practical Barriers**
- A complete 5A EBM cycle takes approximately 2–6 hours per clinical question — fundamentally incompatible with the pace of clinical practice
- Studies show that a hospitalist making rounds on just six patients faces roughly 100 decision points per session; full systematic literature searches are unrealistic in this context
- Barriers fall into two categories (Straus & Glasziou): *logistical* (time constraints, questions forgotten before they can be pursued, reliance on a single convenient resource) and *educational* (limited search skills, lack of familiarity with the hierarchy of evidence)

**(2) The Evidence-to-Individual-Patient Gap**
- The strict inclusion/exclusion criteria of RCTs mean study populations often poorly represent the patients clinicians actually treat — multimorbid patients, the elderly, pregnant women, and minority groups are routinely excluded
- Population-level statistical findings cannot be directly mapped onto individual clinical decisions without substantial judgment
- A 2024 article in *Intensive Care Medicine* argues explicitly that the limitations of EBM are driving a shift toward personalized medicine

**(3) Evidence Quality and Coverage Gaps**
- Literature explosion: over 75,000 new RCTs are published annually, far exceeding the capacity of any individual clinician or guideline panel to review
- Coverage gaps: many clinical questions — particularly in rare diseases, pediatrics, and special populations — have little or no high-quality RCT evidence
- RCT fetishism: dogmatic privileging of RCT evidence marginalizes observational studies and real-world evidence; the COVID-19 pandemic exposed the cost of this rigidity when RCT timelines could not meet the pace of a rapidly evolving outbreak

**(4) Information Overload and Guideline Conflicts**
- Different guideline bodies frequently reach conflicting conclusions on the same clinical question (e.g., target blood pressure thresholds differ across ESC, ACC/AHA, and JNC guidelines)
- In practice, EBM is often reduced to consulting a single convenient resource (e.g., UpToDate) rather than conducting a genuine systematic search — a degradation of the original framework

**(5) Subjectivity and Limited Reproducibility**
- GRADE downgrade factors (risk of bias, inconsistency, indirectness, imprecision, publication bias) are inherently subjective judgment calls
- Inter-rater reliability studies show that two trained reviewers assessing the same question independently reach the same GRADE recommendation strength with a κ of only approximately 0.39 (Guyatt et al., PMID 26845745)
- This low reproducibility undermines the authority and trustworthiness of evidence-based recommendations

**(6) "Cookbook Medicine" and the Threat to Clinical Autonomy**
- Critics argue that EBM, when applied rigidly, replaces clinical judgment with standardized protocols — the so-called "cookbook medicine" critique
- Over-reliance on guidelines may suppress the recognition of rare but clinically significant presentations that fall outside the evidence base

---

### Part IV: AI and LLMs as a Potential Path Forward *(Bridge to the rest of the paper)*

- NLP and LLMs offer a technical pathway to automating the most time-intensive EBM steps: a 2025 scoping review (arXiv) covering 129 studies confirmed NLP contributions across all five steps of the 5A framework
- LLMs are particularly well-positioned to accelerate Acquire (semantic literature retrieval), Appraise (evidence grading), and Apply (recommendation synthesis) — the three steps that currently consume the most clinician time
- However, existing LLM tools face critical unresolved challenges: hallucination of citations and effect sizes, lack of structured GRADE execution, and insufficient traceability of reasoning
- This motivates the system presented in this paper: a multi-agent LLM pipeline that operationalizes the full EBM 5A workflow with deterministic GRADE scoring, structured evidence citation, and automated quality audit loops

---

### Key References

- Sackett DL et al. (1996). *BMJ*, 312:71
- Guyatt G et al. (1991). *ACP Journal Club*
- Guyatt G et al. (2011). *J Clin Epidemiol*, PMID 26845745
- Straus SE et al. (2018). *Evidence-Based Medicine: How to Practice and Teach EBM*, 5th ed. Elsevier
- [PMC — EBM: History, Review, Criticisms, and Pitfalls](https://pmc.ncbi.nlm.nih.gov/articles/PMC10035760/)
- [Intensive Care Medicine (2024) — Limitations of EBM compel personalized medicine](https://link.springer.com/article/10.1007/s00134-024-07528-y)
- [arXiv (2025) — NLP in Support of Evidence-Based Medicine: A Scoping Review](https://arxiv.org/pdf/2505.22280)
- [Frontiers in Digital Health (2025) — LLMs in real-world clinical workflows](https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2025.1659134/full)
- [NEJM AI — Assessment of LLMs in Clinical Reasoning](https://ai.nejm.org/doi/full/10.1056/AIdbp2500120)
