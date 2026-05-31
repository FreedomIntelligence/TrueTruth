---
type: TCM
language: en
status: reviewed
extracted_by: api+llm
authors:
- Kong F
- Liu Q
- Zhou Q
- Xiao P
- Bai Y
- Wu T
- Xia L
tags:
- sodium
- cardiovascular disease
- meta-analysis
- umbrella review
- blood pressure
- dietary intake
title:
  zh: null
  en: 'Dietary salt intake and cardiovascular outcomes: an umbrella review of meta-analyses
    and dose-response evidence'
year: 2025
journal: Annals of medicine
pmid: '41243115'
doi: 10.1080/07853890.2025.2582065
pico:
  population:
    condition: cardiovascular disease risk factors
    sample_size: 91
  intervention:
    name: low sodium intake
  comparison:
    name: normal sodium intake
  outcomes:
    primary:
    - name: CVD mortality
      effect_size:
        metric: RR
        value: 0.83
        ci_low: 0.73
        ci_high: 0.95
        p: 0.007
    - name: stroke mortality
      effect_size:
        metric: RR
        value: 0.74
        ci_low: 0.57
        ci_high: 0.95
        p: 0.019
    - name: all-cause mortality
      effect_size:
        metric: RR
        value: 0.88
        ci_low: 0.82
        ci_high: 0.93
        p: 0.001
    - name: systolic blood pressure
      effect_size:
        metric: MD
        value: -3.39
        ci_low: -4.12
        ci_high: -2.66
        p: 0.0
    - name: diastolic blood pressure
      effect_size:
        metric: MD
        value: -1.54
        ci_low: -2.01
        ci_high: -1.07
        p: 0.0
risk_of_bias:
  tool: RoB2
  overall: some_concerns
grade:
  level: moderate
id: EV-TCM-2025-KONG-001
study_type: SYSTEMATIC_REVIEW
---



## English Abstract

Excessive salt intake is a known cardiovascular disease (CVD) risk factor, but the health impacts of both high and low sodium intake remain debated. This study synthesize meta-analytic evidence on dietary salt intake and cardiovascular outcomes, including subgroup and dose–response analyses.

PubMed, Embase, Web of Science, and Cochrane Library were searched through August 28, 2024, for meta-analyses of randomized controlled trials and observational studies.

21 meta-analyses comprising 91 outcomes were included. Low sodium intake was associated with reduced risks of CVD mortality (RR = 0.83, 95% CI: 0.73–0.95), stroke mortality (RR = 0.74, 95% CI: 0.57–0.95), and all-cause mortality (RR = 0.88, 95% CI: 0.82–0.93), as well as systolic blood pressure (MD = −3.39 mmHg) and diastolic blood pressure (MD = −1.54 mmHg), improved vascular elasticity, and increased heart rate. Urinary sodium excretion and Na/K ratio decreased, while urinary potassium, calcium, and serum potassium increased. No adverse effects on lipid profiles were observed. High salt intake was associated with increased risks of CVD (RR = 1.13, 95% CI: 1.06–1.20), hypertension (OR = 1.33, 95% CI: 1.24–1.42), stroke (OR = 1.34, 95% CI: 1.19–1.51), and stroke mortality (OR = 1.40, 95% CI: 1.21–1.63). Each 1 g/day sodium increase raised systolic blood pressure by 0.60 mmHg and CVD and stroke risks by 4% and 6%, respectively.

High salt intake increases cardiovascular risk, while moderate reduction provides protective benefits without adverse lipid effects. Tailored strategies are needed based on regional, sex-specific, and methodological differences.

## 背景 / Background

Sodium is an essential nutrient required for maintaining normal physiological functions in the human body. It plays a critical role in regulating plasma volume, acid–base balance, nerve impulse transmission, and cellular homeostasis [1,2]. Dietary salt (NaCl) is the primary source of sodium intake, accounting for over 90% of total daily sodium consumption [3]. The World Health Organization (WHO) recommends limiting daily salt intake to less than 5 g (approximately 2 grams of sodium). However, global surveys indicate that the average salt intake reaches 10.78 grams per day (equivalent to 4.31 g of sodium), more than double the recommended level [4]. Excessive salt consumption has profound effects on multiple physiological systems, with the cardiovascular system being particularly sensitive [5]. Dietary salt influences cardiovascular function primarily through modulation of the renin–angiotensin–aldosterone system (RAAS), sympathetic nervous activity, and lipid metabolism [6]. Numerous studies have investigated the association between salt intake and cardiovascular events, reporting a positive correlation between high salt intake and increased risk of adverse cardiovascular outcomes, including hypertension, stroke, myocardial infarction, and heart failure [7–11]. While the need to restrict sodium intake is widely acknowledged, the causal relationship between sodium reduction and cardiovascular risk remains debated. The cardiovascular benefits of low-sodium diets are still controversial [3]. Moreover, several studies suggest that the relationship between sodium intake and cardiovascular outcomes or mortality may be non-linear, following a J-shaped or U-shaped curve, indicating that both excessive and insufficient sodium intake may be detrimental to health [12–14].

Although numerous studies and meta-analyses [15–21] have explored the association between dietary salt intake and cardiovascular health, most existing evidence has focused on single endpoints or specific populations, lacking a comprehensive evaluation of overall cardiovascular outcomes. Furthermore, substantial heterogeneity in study design, methodological quality, population characteristics, and outcome measurement limits the robustness and generalizability of current findings [22]. To address these gaps and inconsistencies, we conducted an umbrella review to systematically synthesize available meta-analytic evidence on the relationship between salt intake and cardiovascular outcomes. By comprehensively mapping the evidence across various cardiovascular indicators and rigorously assessing methodological quality and potential biases, this study aims to provide high-quality evidence to inform dietary sodium guidelines and support clinical and public health decision-making.

## 方法 / Methods

This umbrella review was conducted in accordance with the Preferred Reporting Items for Systematic Reviews and Meta-Analyses (PRISMA) guidelines and was prospectively registered in the PROSPERO database (registration number: CRD42024618180). At the time of registration, the literature search had been completed, whereas screening and data extraction had not yet commenced, in accordance with PROSPERO’s eligibility criteria.

We conducted a thorough search of the PubMed, Embase, Web of Science, and Cochrane Library databases for relevant studies published from database inception to August 28, 2024. The search strategy used the following keywords: (‘salt’ OR ‘sodium’) AND (‘meta-analy*’ OR ‘metaanaly*’ OR ‘meta analy*’). All retrieved references were imported into Zotero software for deduplication and screening. Titles, abstracts, and full texts were independently reviewed by two researchers according to the eligibility criteria. Any disagreements were resolved through discussion with a third reviewer. Additionally, the reference lists of all included studies were manually searched to identify any potentially eligible articles not captured by the initial search.

The inclusion criteria were defined using the PICOS framework:

(1) Participants (P): healthy individuals, patients with hypertension, or general populations without specific disease restrictions; (2) Intervention (I): high-sodium or low-sodium diets; (3) Comparison (C): normal sodium intake or groups with relatively higher/lower sodium intake levels; (4) Outcomes (O): cardiovascular-related outcomes; (4) Study design (S): meta-analyses of randomized controlled trials (RCTs) or observational studies. Network meta-analyses were included only if they provided direct or pairwise comparisons.

Studies were eligible if they assessed the association between sodium intake and cardiovascular outcomes using either continuous or dichotomous effect estimates. If a single study reported multiple outcomes, data were extracted separately for each. When multiple meta-analyses addressed the same exposure, population, intervention, and outcome, the following selection criteria were applied [23,24]: (1) the study with the largest number of included studies was prioritized; (2) if the number of included studies was identical, the meta-analysis with the highest AMSTAR 2 score was selected; (3) if both criteria were identical, the study with the highest evidence quality and most recent publication date was chosen.

Exclusion criteria were as follows: (1) non-English publications; (2) non-clinical studies; (3) network meta-analyses without direct or pairwise comparisons.

From each eligible meta-analysis, the following information was extracted: first author, year of publication, level of sodium intake, study population, study type, number of included studies, total sample size, outcome measures, effect model, effect size, heterogeneity (I2), and publication bias.

The methodological quality of each included meta-analysis was evaluated using the AMSTAR 2 tool, which consists of 16 items and provides a reliable assessment of systematic reviews and meta-analyses [25]. In addition, based on pre-established criteria, the credibility of evidence for each outcome was categorized into five classes: Class I (convincing evidence), Class II (highly suggestive evidence), Class III (suggestive evidence), Class IV (weak evidence), and NS (non-significant) [23,25].

Where sufficient data were available, we reanalyzed effect sizes using either fixed-effects or random-effects models. Effect measures included relative risk (RR), odds ratio (OR), hazard ratio (HR) for binary outcomes, and mean difference (MD) for continuous outcomes. Heterogeneity was assessed using the I2 statistic and Cochran’s Q test. I2 ≤ 40% was considered low heterogeneity, 30% < I2 ≤ 60% indicated moderate heterogeneity, and I2 ≥ 50% indicated high heterogeneity [26]. P-value < 0.05 was considered statistically significant.

## 结果 / Results

A total of 1,869 records were retrieved from the four databases. After removing duplicates and applying predefined eligibility criteria related to cardiovascular outcomes, 63 articles (comprising 698 studies) were initially deemed eligible. Following further screening to ensure consistency in population, intervention, and outcome definitions, 21 meta-analyses (91 outcomes) were ultimately included in this umbrella review (Figure 1). The characteristics of the 21 included meta-analyses are summarized in Supplementary Table 1.

PRISMA flow diagram of study selection.

The methodological quality of the included studies was assessed using the AMSTAR 2 tool. As shown in Supplementary Table 2, the AMSTAR 2 scores ranged from 20 to 31. More than half of the studies (13/21, 61.9%) scored ≥27, indicating generally high methodological quality. Most studies did not provide a detailed list of excluded articles or the reasons for exclusion. Although screening flowcharts were typically available and partially clarified the exclusion process, space limitations may have prevented full disclosure. Furthermore, while all included reviews reported funding sources for their own analyses, none provided details regarding the funding of the original studies. Despite these limitations, the included meta-analyses demonstrated acceptable quality in key methodological domains such as literature search, data extraction, and risk of bias assessment, supporting the overall reliability of the evidence base.

A total of 11 meta-analyses (25 studies) evaluated the association between low sodium intake and cardiovascular outcomes (Figure 2). According to quality assessment results, one outcome was graded as Class III (4%), 13 as Class IV (52%), and 11 as NS (44%).

Associations between low sodium intake and cardiovascular outcomes. *RCTs; **RCTs and non-RCTs; ¶RCTs/RCT follow-ups; ¶¶RCTs and clinical trials; §Cohort studies; §§Prospective cohort studies; NR: Not report. Parenthetical values indicate recalculated P values; All estimates are based on random effects models. SBP: systolic blood pressure; DBP: diastolic blood pressure; LDL-C: low-density lipoprotein cholesterol; HDL-C: high-density lipoprotein cholesterol; 24 h Na/K = 24-hour urinary sodium-to-potassium ratio; 24h UK = 24-hour urinary potassium excretion; CVD: cardiovascular disease; IHD: ischemic heart disease; MACE: major adverse cardiovascular events; MD: mean difference; RR: relative risk.

Low sodium intake was significantly associated with reduced risks of cardiovascular disease (CVD) mortality (RR = 0.83, 95% CI: 0.73 to 0.95, I2 = 5), stroke mortality (RR = 0.74, 95% CI: 0.57–0.95, I2 = 4), and all-cause mortality (RR = 0.88, 95% CI: 0.82–0.93, I2 = 0). No significant associations were observed for CVD (RR = 1.12, 95% CI: 0.93–1.34, I2 = 78), hypertension (RR = 1.09, 95% CI: 0.86–1.38, I2 = 76), or ischemic heart disease (IHD) (RR = 0.99, 95% CI: 0.76–1.29, I2 = 59). Low sodium intake was also associated with a potential reduction in the risk of major adverse cardiovascular events (MACE) (RR = 0.85, 95% CI: 0.71–1.00, I2 = 21), though this finding was marginally significant and should be interpreted with caution.

Hemodynamic and vascular function analyses indicated that low sodium intake significantly reduced systolic blood pressure (SBP) (MD = −3.39 mmHg, 95% CI: −4.31 to −2.46, I2 = 65) and diastolic blood pressure (DBP) (MD = −1.54 mmHg, 95% CI: −2.11 to −0.98, I2 = 60), decreased augmentation index (AIx) (MD = −9.26%, 95% CI: −15.47 to −3.05, I2 = 69.6), and slightly increased heart rate (MD = 1.65 bpm, 95% CI: 1.19–2.11, I2 = 10). No significant changes were observed in pulse wave velocity (PWV) (MD = 0.82 m/s, 95% CI: −0.70 to 2.33, I2 = 0).

Low sodium intake significantly activated the renin–angiotensin–aldosterone system (RAAS), with increases in aldosterone (MD = 73.20 pmol/L, 95% CI: 44.92–101.48, I2 = 62) and plasma renin activity (PRA) (MD = 2.09 ng/mL/h, 95% CI: 1.83–2.36, I2 = 97). However, no significant changes were observed in plasma epinephrine (MD = 6.90 pg/mL, 95% CI: −2.17 to 15.96, I2 = 0) or norepinephrine levels (MD = 8.23 pg/mL, 95% CI: −27.84 to 44.29, I2 = 32).

Regarding metabolic parameters, low sodium intake significantly decreased 24-hour urinary sodium (24h UNa) excretion (MD = −53.74 mmol/day, 95% CI: −75.53 to −31.95, I2 = 96.76) and urinary sodium-to-potassium ratio (Na+/K+) (MD = −0.63, 95% CI: −1.00 to −0.26, I2 = 88), while increasing urinary potassium (MD = 14.41 mmol/day, 95% CI: 10.26–18.56, I2 = 88), urinary calcium (MD = 2.39 mmol/day, 95% CI: 0.52–4.26, I2 = 87), and serum potassium levels (MD = 0.18 mmol/L, 95% CI: 0.07–0.30, I2 = 88). Lipid profiles, including triglycerides (MD = 0.04 mmol/L, 95% CI: −0.04 to 0.09, I2 = 0), total cholesterol (MD = 0.02 mmol/L, 95% CI: −0.03 to 0.07, I2 = 0), LDL-C (MD = 0.03 mmol/L, 95% CI: −0.02 to 0.08, I2 = 0), and HDL-C (MD = −0.01 mmol/L, 95% CI: −0.03 to 0.00, I2 = 0), were not significantly affected by sodium intake reduction.

A total of six meta-analyses (12 studies) were included to evaluate the impact of high sodium intake on cardiovascular outcomes (Figure 3). According to the quality assessment, three outcomes (25%) were graded as Class III, four (33%) as Class IV, and five (42%) as NS.

Associations between low sodium intake and cardiovascular outcomes. *RCTs; §Cohort studies; §§Prospective cohort studies; φCase-control, cross-sectional or longitudinal design; RRandom effects model; FFixed effects model; NR: Not report. Parenthetical values indicate recalculated p values. CVD: cardiovascular disease; CHD: coronary heart disease; SBP: systolic blood pressure; DBP: diastolic blood pressure; RR: relative risk; OR: odds ratio; MD: mean difference.

High sodium intake was significantly associated with increased risks of CVD (RR = 1.13, 95% CI: 1.06–1.20, I2 = 72.9), CVD mortality (RR = 1.12, 95% CI: 1.06–1.19, I2 = 57.6), hypertension (OR = 1.33, 95% CI: 1.24–1.42, I2 = 38.4), stroke (OR = 1.34, 95% CI: 1.19–1.51, I2 = 63.7), stroke mortality (OR = 1.40, 95% CI: 1.21–1.63, I2 = 56.7), ischemic stroke (OR = 1.60, 95% CI: 1.11–2.31, I2 = 71.3), and ischemic stroke mortality (OR = 2.15, 95% CI: 1.57–2.95, I2 = 0).

A marginally significant association was observed between high sodium intake and stroke incidence (OR = 1.11, 95% CI: 1.00–1.24, I2 = 40.3), suggesting a potential risk increase that warrants cautious interpretation. No significant associations were found for ischemic stroke attack (OR = 1.07, 95% CI: 0.95–1.20, I2 = 16.1) or coronary heart disease (CHD) (RR = 1.04, 95% CI: 0.86–1.24, I2 = 68). In terms of blood pressure, high sodium intake was not significantly associated with changes in SBP (MD = 4.40 mmHg, 95% CI: −1.41 to 10.40, I2 = 72.2) or DBP (MD = 2.16 mmHg, 95% CI: −0.10 to 4.42, I2 = 0).

Subgroup analyses (Table 1) based on four meta-analyses (36 studies) revealed that low sodium intake significantly reduced both SBP and DBP across multiple geographic regions. Significant blood pressure-lowering effects were observed in populations from the Western Pacific, Europe, and Southeast Asia. However, no significant changes in SBP or DBP were found in populations from the Americas. Race-specific subgroup analyses showed that low sodium intake significantly lowered blood pressure in both hypertensive White and Black individuals. Among normotensive populations, SBP was significantly reduced in both racial groups, while the reduction in DBP was not significant among Black individuals.

Subgroup analyses of sodium intake on blood pressure, urinary sodium, and cardiovascular outcomes.

RCTs.

Prospective population study.

Random effects model.

Fixed effects model.

p > 0.05.

Abbreviations: NR: Not report; SBP: systolic blood pressure; DBP: diastolic blood pressure; 24h UNa = 24-hour urinary sodium excretion; CVD: cardiovascular disease; MD: mean difference; OR: odds ratio; RR: relative risk; CI: confidence interval.

Sex-based analyses indicated that low sodium intake was associated with significant reductions in blood pressure among both hypertensive men and women. In normotensive individuals, blood pressure also decreased significantly in both sexes.

Additionally, low sodium intake significantly decreased 24h UNa excretion. In hypertensive populations, both White and Black individuals showed significant reductions in 24h UNa, with similar trends observed in men and women. Among normotensive individuals, 24h UNa was significantly reduced in Whites, men, and women, whereas the reduction was not statistically significant in normotensive Black individuals. Furthermore, high sodium intake was associated with elevated risks of stroke and CVD mortality, with consistent effects observed in both men and women.

As shown in Table 2, dose–response analysis indicated that each 1 g/day increase in sodium intake was significantly associated with an increase in SBP (MD = 0.60, 95% CI: 0.40–0.80). Sex-stratified analysis showed a significant increase in SBP in both men (MD = 0.70, 95% CI: 0.30–1.20) and women (MD = 0.90, 95% CI: 0.60–1.10). This may reflect a modest difference in sodium sensitivity between sexes, though overlapping confidence intervals preclude definitive conclusions.

Effect estimates per 1 g/day increase in dietary sodium intake.

Mixed study designs (RCTs, non-RCTs, non-controlled, crossover, cohort, case–control, cross-sectional).

Cohort studies.

Prospective cohort studies.

Prospective studies.

Observational designs (case-control, cross-sectional or longitudinal design).

Observational designs (prospective & retrospective cohort, nested case–control, case–cohort, case–control, prospective reports). All estimates are based on random effects models.

p > 0.05.

Abbreviations: NR: Not report; SBP: systolic blood pressure; DBP: diastolic blood pressure; CV: cardiovascular; CVD: cardiovascular disease; MD: mean difference; OR: odds ratio; RR: relative risk; HR: hazard ratio; CI: confidence interval.

For DBP, no significant association was found in the overall population (MD = 0.20, 95% CI: −0.20 to 0.60). Similarly, the increase in DBP was non-significant in men (MD = 0.20, 95% CI: −0.30 to 0.60). However, among women, each 1 g/day increase in sodium intake was significantly associated with elevated DBP (MD = 1.20, 95% CI: 0.60–1.80), which may indicate a sex-specific physiological response to sodium.

Regarding cardiovascular outcomes, each 1 g/day increase in urinary sodium excretion was associated with a 4% increase in CVD risk (RR = 1.04, 95% CI: 1.01–1.07). No significant association was observed between each 100 mg/day increase in sodium intake and CVD mortality in the overall population (HR/RR = 1.01, 95% CI: 0.97–1.05). Region-specific analyses revealed no significant association in U.S. populations (HR/RR = 0.99, 95% CI: 0.99–1.00), while Japanese populations showed a 5% increased risk of CVD mortality for each 100 mg/day increase in sodium intake (HR/RR = 1.05, 95% CI: 1.02–1.08). Similarly, all-cause mortality was not significantly associated with sodium intake (HR/RR = 1.01, 95% CI: 0.99–1.02). Each 1 g/day increase in salt intake was associated with a 16% higher prevalence of hypertension (OR = 1.16, 95% CI: 1.12–1.19).

For stroke risk, each 1 g/day increase in dietary sodium intake was associated with a 6% increase in risk (RR = 1.06, 95% CI: 1.02–1.10). Sex-specific analysis showed no significant association in men (RR = 1.05, 95% CI: 0.91–1.19), whereas a borderline significant association was observed in women (RR = 1.18, 95% CI: 1.00–1.36). Region-specific analysis revealed no significant associations in the Americas (RR = 1.08, 95% CI: 0.97–1.19) or Europe (RR = 1.01, 95% CI: 0.96–1.05), while in Asian populations, each 1 g/day increase in sodium intake was significantly associated with a 13% increased risk of stroke (RR = 1.13, 95% CI: 1.03–1.23).

## 讨论 / Discussion

This umbrella review systematically evaluated the associations between dietary salt intake and CVD related outcomes. A total of 21 meta-analyses encompassing 93 outcomes were included. The effects of both low and high sodium intake were examined, along with subgroup differences and dose–response relationships.

In terms of blood pressure, low sodium intake was significantly associated with reductions in both SBP and DBP [2], whereas high sodium intake did not demonstrate a statistically significant effect [27]. Subgroup analyses revealed that low sodium intake led to significant reductions in SBP and DBP among populations in the Western Pacific, Europe, and Southeast Asia, but not in the Americas [28]. Furthermore, regardless of hypertension status, low sodium intake consistently lowered SBP and DBP in White individuals, as well as in men and women. Among Black individuals, however, the blood pressure-lowering effect was observed only in those with hypertension [29]. Dose-response analysis in children and adolescents aged 0–18 years showed that increased sodium intake was associated with elevated SBP in both males and females, whereas DBP increased significantly only in females, with no statistically significant change observed in males [20]. These findings are noteworthy given that elevated blood pressure is a major modifiable risk factor for CVD and mortality [2]. Evidence from a U.S.-based study suggests that reductions in blood pressure are associated with decreased risks of developing hypertension, coronary heart disease, and stroke [30].

In terms of electrolyte metabolism, low sodium intake significantly reduced the Na/K ratio[31] and 24h UNa excretion [32], while increasing urinary potassium [31], urinary calcium excretion [33], and serum potassium levels [34]. Subgroup analyses indicated that 24h UNa excretion was significantly reduced among White individuals, males, and females, regardless of hypertension status. However, in Black individuals, this effect was significant only in those with hypertension [29]. 24h UNa excretion is an important biomarker for assessing sodium balance in the body, reflecting both sodium intake and renal elimination [35]. In the present study, reduced sodium intake led to a corresponding decrease in 24h UNa excretion, which was positively correlated with reductions in blood pressure. Sodium absorption and excretion are primarily regulated by renal function. Under normal physiological conditions, the majority of ingested sodium is excreted by the kidneys, making 24h UNa a widely accepted surrogate marker for daily sodium intake [36].

Aldosterone is a key hormone regulating renal sodium reabsorption, and its secretion is stimulated by angiotensin II, which is in turn regulated by renin [37,38]. Renin secretion is influenced by multiple factors, including baroreceptor-mediated sympathetic nervous system (SNS) activation, arteriolar pressure, and sodium concentration delivered to the distal nephron [3]. Additionally, atrial natriuretic peptide (ANP), released in response to increased plasma volume, contributes to sodium homeostasis [39]. Together, plasma volume status and serum sodium concentration govern renin release, thereby affecting sodium reabsorption and excretion [3]. Renin, angiotensin, and aldosterone form the RAAS, which plays a central role in maintaining blood pressure and fluid homeostasis [40]. Short-term RAAS activation helps preserve perfusion and electrolyte balance during volume depletion [41]. However, chronic or excessive RAAS activation may be detrimental, contributing to the development of hypertension, heart failure, and chronic kidney disease [42,43]. Previous studies suggest that short-term sodium restriction (less than two weeks) may reduce plasma volume and lead to compensatory activation of the RAAS and SNS, resulting in elevated plasma epinephrine and norepinephrine levels [44]. However, in this study, low sodium intake did not significantly affect plasma levels of epinephrine or norepinephrine [2], but did result in modest increases in plasma aldosterone[29] and PRA [45], indicating partial RAAS activation. This may be attributed to reduced extracellular fluid volume (ECV) following sodium restriction, which triggers a compensatory response via RAAS and SNS. Nonetheless, this response appears to be mild with sustained moderate sodium restriction [29]. It is also important to note that the duration of sodium restriction may influence the extent of RAAS activation [46]. In this study, outcomes were assessed after 4–8 weeks of dietary intervention, which may not reflect the long-term physiological adaptations. Evidence suggests that with prolonged sodium reduction exceeding one-year, compensatory RAAS activation diminishes over time [47]. Moreover, the physiological effects of sodium restriction may resemble those of certain antihypertensive medications (e.g. thiazide diuretics), in that they transiently activate RAAS and SNS but confer long-term cardiovascular benefits [2,48].

Regarding lipid metabolism, some studies have raised concerns that low sodium intake may adversely affect lipid profiles [44,49]. However, our findings did not reveal any significant changes in triglycerides, total cholesterol, LDL-C, or HDL-C associated with reduced sodium intake [2]. These results suggest that long-term moderate sodium restriction may achieve blood pressure control and cardiovascular protection without negatively impacting lipid metabolism.

In terms of CVD risk, high sodium intake was found to be associated with an increased risk [50], whereas low sodium intake did not show a statistically significant effect [2]. Dose–response analysis demonstrated a clear upward trend in CVD risk with increasing sodium intake [51]. Additionally, low sodium intake was associated with reduced CVD mortality [34], while high sodium intake was linked to an elevated risk of death, with consistent patterns observed in both men and women [52]. Notably, dose–response analysis revealed that high sodium intake was not significantly associated with CVD mortality in U.S. populations, whereas in Japanese populations, mortality risk increased significantly with higher sodium intake [53]. This discrepancy may reflect differences in dietary habits and salt sensitivity among Asian populations. One study suggested that a daily sodium intake between 1,700 and 2,300 mg may be optimal for CVD risk reduction, while intake exceeding 5,000 mg substantially increases the risk of both CVD incidence and mortality [50].

Sodium intake may influence CVD risk through multiple biological mechanisms. One pathway involves oxidative stress and inflammation, whereby high sodium intake impairs endothelial function by disrupting the microenvironment of endothelial cells and tissues [54]. Studies have shown that excess sodium promotes the production of pro-oxidative enzymes and reactive oxygen species (ROS) while reducing nitric oxide (NO) synthesis [55,56]. Sodium may also modulate CVD risk via activation of the RAAS. Furthermore, elevated sodium levels have been found to disrupt immune homeostasis, promoting the activation of pro-inflammatory M1 macrophages and Th17 cells, while inhibiting the differentiation of anti-inflammatory M2 macrophages and regulatory T (Treg) cells [40]. In addition, sodium concentration may alter the composition and diversity of the gut microbiota, which in turn can influence the development of cardiovascular-related diseases through gut–immune–vascular interactions [55,57,58].

Regarding hypertension risk, high sodium intake was significantly associated with an increased risk of developing hypertension [59], whereas low sodium intake did not show a statistically significant effect [34]. Dose–response analysis further confirmed a progressive increase in hypertension risk with higher levels of sodium intake [59]. The associations between sodium intake and the risks of CHD[2] and IHD [60] were not statistically significant. In terms of all-cause mortality, low sodium intake was associated with a reduced risk of death [34]; however, no significant dose–response trend was observed [53]. For MACE, no significant association was found with low sodium intake [34]. Additionally, low sodium intake was associated with an increase in heart rate [61] and a reduction in augmentation index [62], whereas no significant effect was observed on PWV [63].

In this study, the association between sodium intake and stroke-related outcomes remains uncertain. High sodium intake was found to be associated with an increased risk of stroke, affecting both men and women [64]. Dose–response analysis indicated a positive overall correlation between increased sodium intake and stroke risk [65]. Moreover, high sodium intake significantly elevated the risk of stroke-related mortality [64], whereas low sodium intake was associated with a reduced risk of stroke mortality [34]. High sodium intake was also significantly associated with increased risk of ischemic stroke and ischemic stroke–related mortality, although it did not significantly increase the risk of overall stroke incidence or ischemic stroke incidence [64]. Further dose–response subgroup analysis revealed that a 1 g/day increase in dietary sodium intake did not reach statistical significance for stroke risk in either men or women, nor in populations from the Americas or Europe. However, a significant increase in stroke risk was observed in Asian populations [65]. These findings suggest that a low-sodium diet may contribute to a reduced risk of stroke and stroke-related mortality. Nonetheless, whether increased sodium intake directly leads to a higher risk of stroke-related events remains inconclusive and warrants further investigation.

There are substantial regional differences in dietary salt intake worldwide, which may be influenced by various factors, including dietary habits, food processing practices, policy interventions, and genetic or physiological characteristics. In our dose–response analysis, we observed that Asian populations appeared more susceptible to the adverse effects of high sodium intake compared to Western populations. This may be partly attributed to the higher baseline levels of sodium intake in many Asian countries. A meta-analysis of cross-sectional studies [66] reported that the global average sodium intake is approximately 3.95 g/day. In particular, the average intake in Asia and Eastern Europe exceeds 4.2 g/day, while that in Central Europe, the Middle East, and North Africa ranges between 3.6 and 4.2 g/day. In contrast, lower average intakes are observed in North America, Western Europe, and Australia, typically ranging from 3.4 to 3.8 g/day. These differences may reflect distinct dietary patterns across regions [3]. In many Asian countries, the primary sources of dietary sodium include added salt during cooking and sodium-rich condiments such as soy sauce [67,68]. In some regions like Japan and South Korea, traditional dietary practices also include high-sodium foods such as salty soups, pickled vegetables, and seafood [69]. In contrast, sodium intake in Western countries is primarily derived from processed foods such as bread, cured meats, and canned products [70,71].

This umbrella review systematically synthesized evidence from 21 meta-analyses investigating the relationship between dietary salt intake and cardiovascular disease outcomes. All included studies were rigorously selected based on criteria such as sample size, publication year, and methodological quality. By integrating findings at a higher level of evidence, this study provides a comprehensive overview of the potential link between sodium intake and cardiovascular health, offering a robust basis for public health policy and future research planning.

Nevertheless, this review has certain limitations. For instance, variability in sodium intake assessment methods across the included studies may have introduced systematic bias, affected the accuracy of pooled estimates, and contributed to between-study heterogeneity. Currently, sodium intake is commonly assessed using dietary questionnaires and urinary sodium excretion monitoring. Questionnaire-based methods-such as food frequency questionnaires and 24-hour dietary recalls-are widely used in epidemiological research due to their simplicity and low cost. However, these methods rely on self-reporting and are prone to recall bias and estimation errors, potentially leading to over- or underestimation of actual sodium intake [72]. Urinary sodium excretion monitoring is considered a more accurate method for assessing sodium intake and includes 24-hour urine collection, brief timed collections, and spot urine tests [55,73]. Among these, 24 h UNa excretion is regarded as the ‘gold standard’ for estimating intake, as over 90% of ingested sodium is excreted through urine, providing a reliable reflection of actual consumption [74]. Nonetheless, this method also has limitations. Urinary sodium excretion may be influenced by the timing of collection, seasonal factors, and other variables, which may not fully represent an individual’s long-term sodium intake [75,76]. Moreover, in large-scale population studies, complete 24-hour urine collection is logistically challenging, often resulting in sample attrition and reduced statistical power [77,78]. Therefore, when interpreting the results of this umbrella review, it is important to consider the potential bias introduced by inconsistencies in sodium intake measurement. Future research should aim to improve the accuracy and comparability of sodium assessment methods to enhance data quality and strengthen the evidence base. Furthermore, as an umbrella review, this study synthesized evidence from existing meta-analyses. Although the majority were based on RCTs, which strengthens the overall level of inference, causal relationships cannot be definitively established and require further investigation using dedicated causal inference methodologies. In addition, the limited number of dose–response meta-analyses on sodium intake restricts our ability to comprehensively assess the shape of the dose–effect relationship (e.g. linear, non-linear, or U-shaped). Future research should focus on conducting high-quality studies with robust and consistent dose–response modeling to better elucidate the relationship between sodium intake and health outcomes.

Although global public health agencies, including the World Health Organization, have long advocated for reduced salt consumption to lower cardiovascular risk, sodium intake in most populations remains substantially above the recommended threshold. While some outcomes remain inconclusive, the overall evidence supports a positive association between high sodium intake and adverse cardiovascular outcomes, whereas sodium reduction appears to confer protective effects. These findings underscore the public health importance of promoting low-sodium dietary patterns in the general population. However, palatability remains a practical barrier to the adoption of low-sodium diets. To address this, several alternative strategies have been proposed, such as potassium-enriched salt substitutes and naturally low-sodium, culturally acceptable dietary patterns-most notably, the Mediterranean diet [79]. These approaches offer promising, sustainable, and population-acceptable pathways to reducing sodium intake and improving cardiovascular health. In addition, whether sodium sensitivity varies by sex remains uncertain. Although our sex-stratified subgroup analyses indicated that women showed slightly greater changes than men in certain outcomes, suggesting a potential sex-related difference, the absence of formal interaction testing and the overlapping confidence intervals preclude definitive conclusions. These findings should therefore be interpreted with caution. Further large-scale, sex-stratified randomized controlled trials are needed to clarify whether sodium-related effects differ between men and women.

## 结论 / Conclusion

This umbrella review indicates that high dietary salt intake is significantly associated with various adverse cardiovascular outcomes, while low salt intake is linked to cardiovascular protective effects, including reductions in blood pressure and CVD risk. Dose–response analyses further support a positive correlation between higher sodium intake and increased cardiovascular risk, with more pronounced associations observed in Asian populations, suggesting greater sensitivity to sodium-related cardiovascular effects in this group. Given that sodium intake in most regions worldwide exceeds recommended levels, it is advisable to limit daily salt consumption to less than 5 g (approximately 2 g of sodium) and to promote low-sodium, potassium-rich, and sustainable dietary patterns, such as the Mediterranean diet. To advance cardiovascular disease prevention and control more effectively, it is essential to integrate individual behavioral interventions with public health education and policy measures, including salt reduction legislation, front-of-pack nutrition labeling, and reformulation of high-sodium food products. Special attention should be directed toward high-risk populations and regions with elevated baseline sodium intake, particularly in Asia. Future research should aim to improve the accuracy of sodium intake assessment, investigate inter-individual variability in sodium sensitivity, and evaluate the long-term health effects of dietary interventions, thereby informing the development of more precise and scalable salt reduction strategies.
