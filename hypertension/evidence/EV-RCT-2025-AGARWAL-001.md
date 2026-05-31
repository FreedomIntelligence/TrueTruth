---
type: RCT
language: en
status: reviewed
extracted_by: api+llm
authors:
- Agarwal R
- Green JB
- Heerspink HJ
- Mann JF
- McGill JB
- Mottl AK
- Nangaku M
- Rosenstock J
- Vaduganathan M
- Brinker M
- Scott C
- Li L
- Li N
- Rohwedder K
- Rossing P
tags:
- chronic kidney disease
- type 2 diabetes
- finerenone
- empagliflozin
- SGLT2 inhibitor
- GLP-1 RA
- albuminuria
- combination therapy
title:
  zh: null
  en: Impact of Baseline GLP-1 Receptor Agonist Use on Albuminuria Reduction and Safety
    With Simultaneous Initiation of Finerenone and Empagliflozin in Type 2 Diabetes
    and Chronic Kidney Disease (CONFIDENCE Trial)
year: 2025
journal: Diabetes care
pmid: '40968755'
doi: 10.2337/dc25-1673
pico:
  population:
    condition: chronic kidney disease with albuminuria (UACR ≥100 to <5000 mg/g),
      type 2 diabetes (HbA1c <11%)
    sample_size: 800
  intervention:
    name: finerenone + empagliflozin combination
  comparison:
    name: finerenone monotherapy or empagliflozin monotherapy
  outcomes:
    primary:
    - name: change in urinary albumin-to-creatinine ratio (UACR) from baseline at
        day 180
      effect_size:
        metric: MD
        value: -51
        ci_low: -59
        ci_high: -40
        p: 0.001
risk_of_bias:
  tool: RoB2
  overall: low
grade:
  level: moderate
id: EV-RCT-2025-AGARWAL-001
study_type: RCT
---



## English Abstract

The CONFIDENCE trial demonstrated additive benefits of simultaneous initiation of finerenone, a nonsteroidal mineralocorticoid receptor antagonist, and a sodium–glucose cotransporter 2 (SGLT2) inhibitor compared with monotherapy in reducing the urinary albumin-to-creatinine ratio (UACR). This prespecified analysis evaluated whether safety and efficacy of combination therapy varies by baseline glucagon-like peptide 1 receptor agonist (GLP-1 RA) use.

Adults with chronic kidney disease (UACR ≥100 to <5,000 mg/g; estimated glomerular filtration rate [eGFR] 30–90 mL/min/1.73 m2) and type 2 diabetes (glycated hemoglobin <11% [97 mmol/mol]) were randomized (1:1:1) to once-daily finerenone, empagliflozin, or finerenone plus empagliflozin.

Among 800 participants, 182 (23%) used a GLP-1 RA at baseline. At day 180, UACR change from baseline in participants using a GLP-1 RA was −51% (95% CI −59 to −40%) with combination therapy, −34% (−48 to −18%) with finerenone, and −36% (−48 to −21%) with empagliflozin. Corresponding results in those not using a GLP-1 RA at baseline were −56% (−62 to −50%), −37% (−45 to −28%), and −33% (−41 to −23%), respectively. Hyperkalemia incidence rates with combination therapy were 9.0% and 9.5% among individuals with and without baseline GLP-1 RA use. eGFR changes were consistent among individuals with and without baseline GLP-1 RA use. Acute kidney injury was uncommon. Decreases in systolic blood pressure were observed and were more pronounced with combination therapy.

In CONFIDENCE, simultaneous initiation with finerenone and an SGLT2 inhibitor was effective and well tolerated compared with monotherapy, irrespective of background use of a GLP-1 RA.

## 背景 / Background

Diabetes is the most common cause of kidney failure requiring dialysis or transplantation globally, accounting for approximately half of all new cases of kidney failure in the U.S. (1). Among people with diabetes, chronic kidney disease (CKD) markedly amplifies the risks of kidney failure, atherosclerotic cardiovascular disease, and all-cause mortality (2). For CKD management in people with type 2 diabetes, four classes of drugs are recommended on the basis of outcomes trials: 1) renin-angiotensin system (RAS) inhibitors (e.g., Angiotensin-converting enzyme [ACE] inhibitors or angiotensin receptor blockers [ARBs]), 2) sodium–glucose cotransporter 2 (SGLT2) inhibitors, 3) glucagon-like peptide 1 receptor agonists (GLP-1 RAs) with proven benefit for reducing cardiovascular risk and kidney disease progression, and 4) the nonsteroidal mineralocorticoid receptor antagonist finerenone for people with CKD and albuminuria to reduce cardiovascular events and CKD progression (if estimated glomerular filtration rate [eGFR] ≥25 mL/min/1.73 m2) (2).

The COmbinatioN effect of FInerenone anD EmpaglifloziN in participants with CKD and type 2 diabetes using a urinary albumin-to-creatinine ratio (UACR) Endpoint (CONFIDENCE) randomized trial demonstrated that the combination of finerenone and an SGLT2 inhibitor (empagliflozin) provided additive reductions in albuminuria in participants with CKD with albuminuria and diabetes, supporting the use of these agents together in this population to optimize reduction in kidney disease progression (3). The trial confirmed the safety of this combination by monitoring blood pressure, serum potassium, and eGFR and highlighted that current clinical practice based on the stepwise addition of these agents as recommended by expert consensus (1) can potentially be replaced by simultaneous initiation of these two agents.

A 2025 Cochrane review evaluated the efficacy and safety of GLP-1 RAs in people with diabetes and CKD across all CKD stages (4). The review included 42 randomized controlled trials with a total of 48,148 participants and concluded that GLP-1 RAs are likely to provide cardiovascular benefit and reduce all-cause mortality in people with diabetes and CKD (4). The Evaluate Renal Function With Semaglutide Once Weekly (FLOW) trial, which was a large, dedicated kidney outcomes trial in participants with type 2 diabetes and CKD, demonstrated that semaglutide reduced the risk of a composite kidney outcome (kidney failure, ≥50% eGFR decline, kidney or cardiovascular death) by 24% compared with placebo (5). Semaglutide also reduced the risk of major cardiovascular events by 18% and all-cause mortality by 20% (5). The results of the FLOW trial (5) and updated meta-analysis (6) now provide the strongest evidence for a reduction in CKD progression with GLP-1 RAs in this population.

A consensus report stated that the effects of finerenone, SGLT2 inhibitors, and GLP-1 RAs appear additive based on preclinical and limited clinical data, but further research is needed on their combined use (1). In this prespecified analysis of the CONFIDENCE trial, we evaluated the efficacy and safety of simultaneous initiation of finerenone and empagliflozin versus finerenone and empagliflozin monotherapy, with or without GLP-1 RA, on a background of RAS inhibition. Investigating the impact of baseline GLP-1 RA use on the efficacy of finerenone and empagliflozin combination therapy is important in the context of the four drug classes with proven kidney protective effects.

## 方法 / Methods

The CONFIDENCE trial was a double-blind, randomized, active controlled trial of empagliflozin alone, finerenone alone, or the combination of the two in people with CKD with albuminuria and type 2 diabetes. The trial design, study protocol, statistical analysis plan, and primary results have been previously published (3,7,8). The trial was approved by the institutional review board at each participating site. All participants provided written informed consent. An independent data and safety monitoring committee oversaw participant safety. There was no patient or public involvement in the design, conduct, and reporting of the trial. The trial was first registered with ClinicalTrials.gov (NCT05254002) on 23 February 2022.

Adults were eligible if they had type 2 diabetes with a glycated hemoglobin (HbA1c) level <11% (97 mmol/mol), an eGFR between 30 and 90 mL/min/1.73 m2, and albuminuria, defined as a UACR between 100 and <5,000 mg/g confirmed by averaging first morning urine samples collected over 3 consecutive days. All participants were required to be receiving the maximally tolerated dose of an ACE inhibitor or ARB for at least 1 month prior to screening. Exclusion criteria included a serum potassium level >4.8 mmol/L, type 1 diabetes, and use of an SGLT2 inhibitor or potassium binder within 8 weeks before screening. GLP-1 RA treatments were allowed provided that the dosage had remained stable for at least 4 weeks prior to the screening visit. Dose reductions (downtitration of the GLP-1 RA) were allowed during the study. Dose increases (uptitration of the GLP-1 RA) were not allowed.

Using an interactive web response system, participants were randomly allocated in a 1:1:1 ratio to receive either finerenone (10 or 20 mg [target dose] once daily, with a placebo matching empagliflozin), empagliflozin (10 mg once daily, with a placebo matching finerenone), or both drugs in combination. The initial dose of finerenone was determined by kidney function. Participants with an eGFR of ≥60 mL/min/1.73 m2 started at 20 mg daily, while those with a baseline eGFR <60 mL/min/1.73 m2 started at 10 mg daily, with uptitration to 20 mg after 30 days if serum potassium was ≤4.8 mmol/L and the eGFR decrease was <30% compared with the previous visit. In contrast, empagliflozin was administered at a fixed dose of 10 mg, as this has been shown to be effective for kidney and cardiovascular outcomes in relevant populations, including those within the target eGFR range of this study (9). Higher doses do not typically offer additional kidney protective effects. As this was a double-blind study, treatment assignments were concealed from investigators, treating physicians, participants, and outcome assessors.

The study protocol included seven prespecified trial visits. During the screening visit, urine samples for UACR assessment were collected on three consecutive mornings at the participant’s home, while for each subsequent visit, urine was collected on two consecutive mornings. At every visit, blood samples were drawn to measure serum potassium and for calculation of eGFR from serum creatinine. All UACR, serum potassium, and serum creatinine measurements were performed at a central laboratory (3). Seated blood pressure was measured three times after at least 5 min of rest at each visit. The study medication was discontinued 180 (±5) days after randomization, and 30 days later, UACR, blood pressure, eGFR, and serum potassium were reassessed to evaluate the effects of study treatment discontinuation.

The primary efficacy outcome was the change from baseline to 180 days in the log-transformed mean UACR, a surrogate marker for kidney outcomes and response to therapy (10). The proportion of participants achieving a reduction in UACR of >30%, >40%, and >50% at 180 days was a secondary outcome.

Adverse events were recorded, and secondary safety outcomes included the acute change in eGFR by >30% from baseline at 30 days, incidence of acute kidney injury, hyperkalemia events, change in serum potassium from baseline, symptomatic hypotension, severe hypoglycemia, urosepsis or pyelonephritis, and genital mycotic infections. These outcomes were systematically assessed to capture both efficacy and safety signals relevant to the use of finerenone, empagliflozin, and their combination in this population.

All efficacy analyses were performed using the full-analysis set (all randomized participants except those who did not receive at least one dose of study drug or had major Good Clinical Practice violations). The primary analysis used a mixed model for repeated measures with log-transformed UACR as the dependent variable, as previously reported (3). Log-transformed UACR was appropriate due to the skewed distribution of UACR; this transformation satisfied the statistical assumptions for linear mixed models and allowed for calculation of the geometric mean ratios. The model output was expressed as least-squares mean ratio to baseline/treatment, and the geometric mean ratios were back-transformed to show percentage changes from baseline/between treatments.

Our primary interest in this prespecified analysis was to investigate effect modification by baseline GLP-1 RA use, specifically, whether the effect of finerenone and empagliflozin (alone or in combination) on UACR reduction differs across strata of baseline GLP-1 RA use. We did not assess causal interaction in the strict epidemiological sense, as GLP-1 RA use was not randomized in this trial. Logistic regression models were used for analyzing percentage changes in UACR that exceeded 30%, 40%, or 50% reductions from baseline. Logistic regression models were adjusted for eGFR and UACR stratification factors, GLP-1 RA use and its interaction with the treatment term, and odds ratios were generated from stratified models. The mixed model for repeated measures used for the primary efficacy analyses assumed that data were missing at random, while logistic regression outcomes were analyzed using complete case analysis.

Changes in serum potassium, systolic blood pressure, and eGFR were analyzed using a mixed model. eGFR was calculated using the Chronic Kidney Disease Epidemiology Collaboration equation (11) with a modification for Japanese participants (12). Adverse events were reported for participants (n [%]) who had received at least one dose of a trial drug and had an adverse event that had started or worsened after the first dose and up to 3 days after any temporary or permanent interruption of the trial treatment.

Subgroup analyses by GLP-1 RA use were prespecified prior to database lock. Given the exploratory nature of these analyses, models were not adjusted for multiple comparisons.

Availability of the data underlying this publication will be determined according to Bayer’s commitment to the European Federation of Pharmaceutical Industries and Associations/Pharmaceutical Research and Manufacturers of America principles for responsible clinical trial data sharing. This pertains to scope, time point, and process of data access. As such, Bayer commits to sharing, upon request from qualified scientific and medical researchers, patient-level clinical trial data, study-level clinical trial data, and protocols from clinical trials in patients for medicines and indications approved in the U.S. and European Union as necessary for conducting legitimate research. This applies to data on new medicines and indications that have been approved by European Union and U.S. regulatory agencies on or after 1 January 2014. Interested researchers can use https://www.vivli.org to request access to anonymized patient-level data and supporting documents from clinical studies to conduct further research that can help advance medical science or improve patient care. Information on the Bayer criteria for listing studies and other relevant information is provided in the member section of the portal. Data access will be granted to anonymized patient-level data, protocols, and clinical study reports after approval by an independent scientific review panel. Bayer is not involved in the decisions made by the independent review panel. Bayer will take all necessary measures to ensure that patient privacy is safeguarded.

## 结果 / Results

Of 800 participants included in the full-analysis set, 182 (22.8%) reported use of a GLP-1 RA at baseline, comprising a similar proportion in the combination (68 of 269 [25.3%]), finerenone (52 of 264 [19.7%]), and empagliflozin (62 of 267 [23.2%]) groups (Supplementary Table 1). Of the 182 patients receiving a GLP-1 RA at baseline, 102 (56%) were prescribed semaglutide, 41 (23%) dulaglutide, 28 (15%) liraglutide, 6 (3%) tirzepatide (a dual glucose insulinotropic peptide and GLP-1 RA), and 5 (3%) lixisenatide. The median duration of baseline GLP-1 RA medication use prior to randomization was 358 (range 1–8,522) days.

Comparison of the baseline demographics and baseline characteristics between participants who did and did not receive a GLP-1 RA at baseline showed some numerical differences (Table 1). Participants prescribed GLP-1 RAs at baseline were less likely to be Asian or from Asia; had a higher mean BMI; had greater use of insulin, β-blockers, diuretics, antiplatelet agents, and statins; and were less likely to be taking dipeptidyl peptidase 4 inhibitors. The median UACR was lower in patients with baseline GLP-1 RA use than in those without (539 [interquartile range 290–1,000] vs. 592 [292–1,167] mg/g). The distribution of finerenone doses (10 mg vs. 20 mg) achieved during the trial was similar between participants with and without baseline GLP-1 RA use.

Baseline clinical characteristics by GLP-1 RA use

DPP-4, dipeptidyl peptidase 4; IQR, interquartile range; SBP, systolic blood pressure.

*Includes American Indian or Alaska Native and Native Hawaiian or Other Pacific Islander.

†Calculated using the Chronic Kidney Disease Epidemiology Collaboration equation (11), which was modified for the Japanese participants (12). Data were missing for 4 participants (2 [0.8%] in the finerenone group [1 in each GLP-1 RA subgroup] and 2 [0.7%] in the empagliflozin group [both in the with GLP-1 RA at baseline subgroup]).

‡Data were missing for 16 participants (4 [1.5%] in the combination therapy group [1 with and 3 without GLP-1 RA at baseline], 6 [2.3%] in the finerenone group [all without GLP-1 RA at baseline], and 6 [2.2%] in the empagliflozin group [2 with and 4 without GLP-1 RA at baseline]).

§Data were missing for 16 participants (4 [1.5%] in the combination therapy group [2 each with and without GLP-1 RA at baseline], 6 [2.3%] in the finerenone group [all with GLP-1 RA at baseline], and 6 [2.2%] in the empagliflozin group [all with GLP-1 RA at baseline]).

‖Based on preferred terms in the Medical Dictionary for Regulatory Activities, version 27.1.

¶Based on a group of preferred terms for coronary artery disease, cerebral infarction, and stroke (a transient ischemic attack alone was not sufficient), as well as for peripheral artery disease and carotid revascularization.

The treatment effect by GLP-1 RA use is shown in Table 2 and Fig. 1. At day 180, there was a change in UACR from baseline in participants using a GLP-1 RA of −51% (95% CI −59 to −40%) with combination therapy, −34% (−48 to −18%) with finerenone alone, and −36% (−48 to −21%) with empagliflozin alone. Similar reductions were observed in those not using a GLP-1 RA at baseline (Table 2). In the GLP-1 RA group, changes in UACR at day 180 with combination therapy versus finerenone alone and empagliflozin alone were −25% (−44 to 1%) and −23% (−42 to 3%), respectively, similar to the results in the subgroup not reporting GLP-1 RA use at baseline (Table 2). There appeared to be attenuation of UACR reduction following treatment discontinuation in the combination therapy group for both patients with and without baseline GLP-1 RA use (Fig. 1). In addition, a greater proportion of participants achieved reductions in UACR of >30%, >40%, or >50% with combination therapy versus either finerenone or empagliflozin alone, irrespective of background use of GLP-1 RA (Table 2 and Supplementary Fig. 1). For example, approximately 72.1% (95% CI 65.6 to 78.7%) of participants in the combination group without baseline GLP-1 RA use achieved a >30% reduction in UACR, and 63.8% (51.7 to 75.9%) in the combination group with baseline GLP-1 RA use achieved this goal.

Treatment effect by GLP-1 RA use: percentage change of UACR and the proportion of participants exceeding threshold reductions in UACR at day 180 versus baseline

GLP-1 RA−, without a GLP-1 RA at baseline; GLP-1 RA+, with a GLP-1 RA at baseline; OR, odds ratio.

*Logistic regression model was adjusted for treatment and eGFR and UACR stratification factors.

Percentage change from baseline in UACR in the full-analysis population. Percentage change = (least-squares mean ratio to baseline − 1) × 100.

Adverse events by GLP-1 RA use at baseline are shown in Supplementary Table 2. The incidence of abdominal symptoms was similar between those receiving and not receiving a GLP-1 RA at baseline. Hypoglycemia and hyperglycemia events were uncommon, occurring in 10 and 8 participants overall, respectively, in the trial.

The change from baseline in serum potassium by treatment group is shown in Supplementary Fig. 2. The trends for change in serum potassium over time by treatment group were similar irrespective of GLP-1 RA use at baseline. Combination therapy was associated with a slight increase in mean serum potassium, which declined to baseline following treatment cessation; a similar trend was observed in the finerenone group. Empagliflozin was not associated with changes in serum potassium.

The incidence of hyperkalemia is shown in Supplementary Table 2, and mean serum potassium levels are shown in Table 3. In participants with baseline GLP-1 RA use, treatment-emergent hyperkalemia adverse events occurred in 9.0%, 11.5%, and 6.5% of those in the combination, finerenone alone, and empagliflozin alone groups, respectively. In those without GLP-1 RA use, the proportions were 9.5%, 11.3%, and 2.9%, respectively (Table 3).

Safety laboratory assessments and events of special interest

*Data are n of all participants at risk for an abnormal laboratory result (%). Participants must have had both a baseline and postbaseline (after the first dose and up to 3 days after any temporary or permanent interruption of the trial treatment) value, with the baseline value not exceeding the displayed threshold. The numerator represents the number of participants at risk who had at least one postbaseline laboratory assessment that met the criterion.

†The eGFR was calculated using the Chronic Kidney Disease Epidemiology Collaboration equation (11), which was modified for the Japanese participants (12).

The change from baseline in eGFR by treatment group is shown in Supplementary Fig. 3. An early decline in eGFR was observed in all three groups, which then stabilized and was reversible upon drug discontinuation. The incidence of eGFR decline >30% at day 30 occurred in 30 participants overall, with the distribution of events across treatment groups similar in both GLP-1 RA subgroups (Table 3). The occurrence of acute kidney injury was uncommon in the study (eight participants overall) (Table 3).

The change from baseline in systolic blood pressure by treatment group is shown in Supplementary Fig. 4. In subgroups both with and without GLP-1 RA use at baseline, a reduction from baseline in systolic blood pressure was observed in all three treatment arms, which was more pronounced with combination therapy than either monotherapy. Systolic blood pressure levels returned to baseline following treatment discontinuation. Symptomatic hypotension was reported in three participants randomized to combination therapy (one in a participant receiving a GLP-1 RA at baseline and two in participants not receiving a GLP-1 RA at baseline) (Table 3).

## 结论 / Conclusion

This prespecified subgroup analysis of the CONFIDENCE trial showed consistent treatment benefits of simultaneous initiation of combination treatment with finerenone and empagliflozin compared with finerenone or empagliflozin alone, irrespective of whether a participant was receiving GLP-1 RA treatment at baseline. Similarly, UACR reduction with empagliflozin or finerenone as monotherapies was not modified by baseline GLP-1 RA use. Together with the previously established evidence base, these current data suggest that therapy with three classes of drugs, ACE inhibitors/ARBs, SGLT2 inhibitors, and finerenone, lead to UACR reduction in the presence or absence of GLP-1 RA. Although our study was neither designed nor had the power to test the additive treatment effect on UACR reduction with GLP-1 RA, the potential effect based on complementary mechanisms supports the growing paradigm in clinical practice that all four classes of drugs, when coadministered, might have additive benefits on cardiovascular and kidney outcomes (13).

In the FLOW trial in patients with type 2 diabetes and CKD, the GLP-1 RA semaglutide was studied at a dose of 1.0 mg weekly, which is the recommended maintenance dose in people with type 2 diabetes and CKD (5). In FLOW, the primary composite outcome included kidney failure, sustained ≥50% reduction in eGFR, kidney death, or cardiovascular death. The overall hazard ratio of 0.76 (95% CI 0.66–0.88) over a median follow-up of 3.4 years was consistent across subgroups, including participants on background SGLT2 inhibitor therapy (P for interaction = 0.109) (14). A 2024 meta-analysis of FLOW and two additional trials of GLP-1 RAs (Effect of Efpeglenatide on Cardiovascular Outcomes [AMPLITUDE-O] and Harmony Outcomes) confirmed that treatment effects on this composite kidney outcome did not vary according to SGLT2 inhibitor use (risk ratio, 0.79 [95% CI 0.66–0.95]) (15).

Finerenone in Chronic Kidney Disease and Type 2 Diabetes (FIDELITY) demonstrated that finerenone significantly reduced UACR in patients with type 2 diabetes and CKD (16). This reduction was persistent regardless of baseline use of GLP-1 RAs (17). The magnitude of UACR reduction with finerenone in FIDELITY was greater in patients with (−38%) versus without GLP-1 RA use (−31%) at baseline (P for interaction = 0.03) (17). The reduction in UACR by baseline GLP-1 RA and/or SGLT2 inhibitor use was consistent with finerenone versus placebo at month 4. The change was –40% in those receiving both a GLP-1 RA and an SGLT2 inhibitor, –38% in those receiving a GLP-1 RA only, and –36% in those receiving an SGLT2 inhibitor only (P for interaction = 0.11) (17).

The consistent effects of SGLT2 inhibitors on cardiovascular and kidney outcomes, regardless of the background use of GLP-1 RAs, has been established in a pooled analysis of randomized controlled trials (18). Likewise, a 2024 meta-analysis evaluated the cardiovascular and kidney efficacy and safety of GLP-1 RAs with and without SGLT2 inhibitor use (15). The review, which included three randomized controlled trials involving 1,743 of 17,072 (10.2%) participants with type 2 diabetes receiving an SGLT2 inhibitor at baseline concluded that the cardiovascular and kidney benefits of GLP-1 RAs are consistent regardless of SGLT2 inhibitor use (15).

Based on the existing literature, the rationale for considering the use of GLP-1 RAs as additive to finerenone, SGLT2 inhibitors, and RAS inhibitors is grounded in their complementary mechanisms and nonredundant cardiorenal benefits (19–23). Each of these drug classes targets distinct pathophysiological pathways: GLP-1 RAs primarily modulate metabolic and inflammatory processes (19), SGLT2 inhibitors act via hemodynamic and metabolic effects (20), and finerenone provides hemodynamic, antifibrotic, and anti-inflammatory actions through mineralocorticoid receptor antagonism (21). Modeling studies and network meta-analyses have demonstrated that combination therapy with these agents yields greater reductions in major adverse cardiovascular events, kidney disease progression, and mortality than any single-agent or dual therapy, with projected gains in event-free survival and absolute risk reduction for people with type 2 diabetes and albuminuria (13,24).

The median GLP-1 RA use duration was 13 months, which implies that any UACR lowering would largely have occurred prior to study entry. The novel aspect of the study was therefore to evaluate outcomes in patients receiving the four pillars of CKD care. Numerically lower rates of severe hyperkalemia in patients with baseline GLP-1 RA use were observed, which align with previous literature (25), suggesting a possible protective or mitigating effect of GLP-1 RAs on hyperkalemia risk (26). There was a numerically greater proportion of participants in the GLP-1 RA group, particularly those receiving combination therapy, who experienced an eGFR decline >30% (Table 3 and Supplementary Fig. 3). This threshold is clinically significant for medication and medical management and suggests a need for closer monitoring in this subgroup. Overall, simultaneous initiation of finerenone and empagliflozin, even in patients already taking GLP-1 RAs did not lead to an increased risk of poor kidney outcomes, such as significant eGFR decline or acute kidney injury.

The subgroup analysis reported here had several limitations. First, patients receiving GLP-1 RAs at baseline had a higher mean BMI and differences in baseline characteristics compared with those not receiving GLP-1 RAs, which may have confounded observed associations and limited the ability to attribute outcomes solely to GLP-1 RA use. For example, a cohort study reported loss of body weight to be an important determinant of UACR reduction (27). Baseline differences can introduce confounding by indication, as patients selected for GLP-1 RA therapy may differ systematically from those not receiving these agents in ways that are not fully captured or adjusted for in the analysis (4,6).

Second, subgroup analyses by GLP-1 RA use were observational within randomized trials or pooled data sets, as randomization was not stratified by GLP-1 RA use. This nonrandomized exposure introduced potential selection bias, making it difficult to distinguish the effects of GLP-1 RAs from those of other unmeasured factors (4,6). The internal validity of comparing treatment effects within the GLP-1 RA user/nonuser subgroups relied on assumptions about balanced baseline characteristics, which were not perfectly met. This reinforces that while randomization of finerenone/empagliflozin was valid for the overall trial, the comparison between GLP-1 RA use subgroups was observational in nature, making inference about causal interaction challenging.

Third, the statistical power to detect additive or synergistic effects of GLP-1 RAs in combination with other therapies (e.g., finerenone, SGLT2 inhibitors, RAS inhibitors) was limited by the relatively small number of patients receiving combination therapy at baseline. For example, visual trends in Fig. 1, particularly for the combination group, could suggest a numerically smaller absolute reduction in UACR among GLP-1 RA recipients. This reinforces the possibility that the smaller subgroup of patients with baseline GLP-1 RA use may have lacked sufficient power; therefore, less pronounced effects cannot be definitively ruled out (26).

Fourth, differences in quality of care at recruiting centers and socioeconomic disparities may have influenced both the likelihood of GLP-1 RA use and the burden or progression of CKD. This limitation may have further confounded subgroup comparisons and potentially biased the results (28).

Fifth, subgroup analysis by specific GLP-1 RA agent (e.g., dulaglutide, liraglutide, semaglutide) was not possible due to small sample sizes, and detailed dose information for individual GLP-1 RAs at baseline was not systematically collected or available. We acknowledge that exploring the impact of baseline covariate adjustment would be valuable for understanding the true effect of GLP-1 RA use and the subsequent response to finerenone/empagliflozin. These limitations emphasize the need for dedicated randomized studies to assess the true additive effects and safety of combination therapy in this population.

In conclusion, in this prespecified subgroup analysis of the CONFIDENCE trial, the consistent numerical trends suggest that the benefits of simultaneous initiation of combination treatment with finerenone and empagliflozin compared with finerenone or empagliflozin alone occur irrespective of baseline GLP-1 RA use. Similarly, UACR reduction with empagliflozin or finerenone as monotherapies was not modified by baseline GLP-1 RA use. These findings demonstrate that finerenone and SGLT2 inhibitors (alone or in combination) lead to UACR reduction regardless of baseline GLP-1 RA usage. While our study did not assess the statistical additivity of all four classes, the rationale for exploring their combined use stems from their nonoverlapping pathways for cardiorenal protection. Future dedicated studies are needed to fully characterize potential additive or synergistic effects on clinical outcomes.
