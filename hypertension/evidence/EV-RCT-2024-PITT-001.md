---
type: RCT
language: en
status: reviewed
extracted_by: api+llm
authors:
- Pitt B
- Agarwal R
- Anker SD
- Rossing P
- Ruilope L
- Herzog CA
- Greenberg B
- Pecoits-Filho R
- Lambelet M
- Lawatscheck R
- Scalise A
- Filippatos G
tags:
- hypokalaemia
- CKD
- T2D
- finerenone
- cardiovascular outcomes
- arrhythmia
- placebo
- RoB2
title:
  zh: null
  en: 'Hypokalaemia in patients with type 2 diabetes and chronic kidney disease: the
    effect of finerenone—a FIDELITY analysis'
year: 2024
journal: European heart journal. Cardiovascular pharmacotherapy
pmid: '39380152'
doi: 10.1093/ehjcvp/pvae074
pico:
  population:
    condition: chronic kidney disease (CKD) with type 2 diabetes (T2D)
    sample_size: 12990
  intervention:
    name: finerenone
  comparison:
    name: placebo
  outcomes:
    primary:
    - name: cardiovascular composite outcome (CV death, non-fatal MI, non-fatal stroke,
        hospitalization for HF)
      effect_size:
        metric: HR
        value: 0.63
        ci_low: 0.6
        ci_high: 0.66
        p: 0.0
    - name: arrhythmia composite outcome (new AF/atrial flutter, hospitalization due
        to arrhythmia, sudden cardiac death)
      effect_size:
        metric: HR
        value: 0.46
        ci_low: 0.4
        ci_high: 0.53
        p: 0.0
risk_of_bias:
  tool: RoB2
  overall: low
grade:
  level: high
id: EV-RCT-2024-PITT-001
study_type: RCT
---



## English Abstract

Hypokalaemia is associated with cardiovascular events and mortality in patients with chronic kidney disease (CKD). This exploratory FIDELITY analysis, a prespecified pooled patient-dataset from FIDELIO-DKD and FIGARO-DKD, investigated the incidence and effect of hypokalaemia in patients with CKD and type 2 diabetes (T2D) treated with finerenone vs. placebo.

Outcomes include the incidence of treatment-emergent hypokalaemia (serum potassium <4.0 or <3.5 mmol/L) and the effect of finerenone on cardiovascular composite outcome (cardiovascular death, non-fatal myocardial infarction, non-fatal stroke, or hospitalization for heart failure) and arrhythmia composite outcome (new diagnosis of atrial fibrillation/atrial flutter, hospitalization due to arrhythmia, or sudden cardiac death) by baseline serum potassium subgroups. In the FIDELITY population, treatment-emergent hypokalaemia with serum potassium <4.0 and <3.5 mmol/L occurred in 41.1% and 7.5%, respectively. Hazards of cardiovascular and arrhythmia composite outcomes were higher in patients with baseline serum potassium <4.0 vs. 4.0–4.5 mmol/L [hazard ratio (HR) 1.16; 95% confidence interval (CI) 1.02–1.32, P = 0.022 and HR 1.20; 95% CI 1.00–1.44, P = 0.055, respectively]. Finerenone reduced the incidence of hypokalaemia with serum potassium <4.0 mmol/L (HR 0.63; 95% CI 0.60–0.66) and <3.5 mmol/L (HR 0.46; 95% CI 0.40–0.53) vs. placebo. Finerenone lessened the hazard of cardiovascular and arrhythmia events vs. placebo, irrespective of baseline serum potassium.

A substantial proportion of patients with CKD and T2D experienced hypokalaemia, which was associated with an increased hazard of adverse cardiovascular outcomes. Finerenone reduced the incidence of hypokalaemia. Finerenone reduced the hazard of cardiovascular and arrhythmia outcomes irrespective of serum potassium subgroups.

Clinical trials registration: FIDELIO-DKD and FIGARO-DKD are registered with ClinicalTrials.gov, numbers NCT02540993 and NCT02545049, respectively (funded by Bayer AG).

Graphical AbstractIncidence of hypokalaemia in FIDELITY and the effect of finerenone on the incidence of hypokalaemia as well as CV and arrhythmia outcomes.
aTime to CV death, non-fatal myocardial infarction, non-fatal stroke, or hospitalization for heart failure. bTime to new diagnosis of atrial fibrillation/atrial flutter, hospitalization due to arrhythmia, or sudden cardiac death.CI, confidence interval; CKD, chronic kidney disease; CV, cardiovascular; FIDELITY, FInerenone in chronic kiDney diseasE and type 2 diabetes: Combined FIDELIO-DKD and FIGARO-DKD Trial programme analYsis; HR, hazard ratio; K+, potassium; and T2D, type 2 diabetes.

Incidence of hypokalaemia in FIDELITY and the effect of finerenone on the incidence of hypokalaemia as well as CV and arrhythmia outcomes.

aTime to CV death, non-fatal myocardial infarction, non-fatal stroke, or hospitalization for heart failure. bTime to new diagnosis of atrial fibrillation/atrial flutter, hospitalization due to arrhythmia, or sudden cardiac death.

CI, confidence interval; CKD, chronic kidney disease; CV, cardiovascular; FIDELITY, FInerenone in chronic kiDney diseasE and type 2 diabetes: Combined FIDELIO-DKD and FIGARO-DKD Trial programme analYsis; HR, hazard ratio; K+, potassium; and T2D, type 2 diabetes.

## 背景 / Background

The kidneys have a pivotal role In potassium regulation, and as such abnormal serum potassium levels are often evident in patients with kidney disease.1–3 Serum potassium concentrations of 4.0–5.0 mmol/L are associated with the lowest hazard of major adverse clinical outcomes in patients with chronic kidney disease (CKD), whereas levels either side of this range increase cardiovascular (CV) risk and all-cause mortality.1,4 Hyperkalaemia is well documented and is considered a risk marker for an increased hazard of adverse outcomes associated with underlying conditions in patients with heart failure (HF), such as CKD and type 2 diabetes (T2D).5–8 In contrast, hypokalaemia (defined as a serum potassium <3.5 and <4.0 mmol/L) in patients with CKD and T2D has received less attention, with its prevalence and clinical importance underrecognized.1,9,10 Hypokalaemia is a risk marker and a risk factor for numerous adverse outcomes in patients with CKD, including CV death, major adverse CV events, and end-stage kidney disease.1,3,4,9,11,12 Studies indicate that it occurs at a similar rate to hyperkalaemia across CKD stages 2–5, with prevalences of 12–18%, and 14–20% for serum potassium ≤4.0 and ≥5.0 mmol/L, respectively, relating to an increased hazard of clinical events.1 A 49% increase in the incidence of all-cause mortality has been reported for patients with a serum potassium of 3.5–3.9 mmol/L compared with patients with normokalaemia, and a 3-fold higher risk with serum potassium <3.5 mmol/L.1 In addition, hypokalaemia is linked with primary aldosteronism (PA; and associated hypertension), which has been shown to independently elevate the risk of heart and kidney damage. Therefore, there is a need to describe the incidence of hypokalaemia and its impact on outcomes in patients with CKD and T2D.

Management of hypokalaemia includes treatment with potassium supplements, potassium-sparing diuretics/steroidal mineralocorticoid receptor antagonists (MRAs), or a renin-angiotensin system (RAS) inhibition with angiotensin-converting enzyme inhibitors or angiotensin receptor blockers.9 The effects of MRAs on potassium balance may benefit patients at risk of hypokalaemia, given that a reduced rate of hypokalaemia events has been observed in patients with HF receiving MRAs.13,14 MRAs may also be of value in those patients in whom PA is unmasked.15

Finerenone, a selective, non-steroidal MRA with a favourable benefit-risk profile compared with conventional steroidal MRAs,16,17 improved CV and kidney outcomes vs. placebo in patients with CKD and T2D.18,19

FInerenone in chronic kiDney diseasE and type 2 diabetes: Combined FIDELIO-DKD and FIGARO-DKD Trial programme analYsis (FIDELITY) is a prespecified pooled analysis of two complementary phase III studies, FInerenone in reducing kidney failure and dIsease progression in Diabetic Kidney Disease (FIDELIO-DKD) and FInerenone in reducinG cArdiovascular moRtality and mOrbidity in Diabetic Kidney Disease (FIGARO-DKD).20 In this post hoc subanalysis of FIDELITY, we assessed the incidence and characteristics of hypokalaemia in patients with CKD following treatment with finerenone or placebo. We also investigated the effect of finerenone on the CV, arrhythmia, and mortality outcomes across baseline serum potassium subgroups.

## 方法 / Methods

The prespecified FIDELITY pooled analysis of individual patient data consisted of 12 990 patients from FIDELIO-DKD (NCT02540993) and FIGARO-DKD (NCT02545049); the study designs and patient populations have been previously reported.18–22 In brief, FIDELIO-DKD and FIGARO-DKD were multicentre, phase III, randomized, parallel-group, placebo-controlled, event-driven global studies. Eligible patients were adults (aged ≥18 years) with T2D and CKD [urine albumin-to-creatinine ratio (UACR) ≥30–<300 mg/g and estimated glomerular filtration rate (eGFR, calculated with the use of the Chronic Kidney Disease Epidemiology Collaboration [CKD-EPI] formula with adjustment for race in Black patients18,22) ≥25–≤90 mL/min/1.73 m2 or UACR ≥300–≤5000 mg/g and eGFR ≥25 mL/min/1.73 m2], treated with a maximum tolerated dose of a RAS inhibitor. Serum potassium was required to be ≤4.8 mmol/L at run-in and screening visits.18,19,21,22 The study protocols were approved by independent ethics committees and international review boards. All patients provided written, informed consent prior to study participation.

The procedures for FIDELIO-DKD and FIGARO-DKD have been described previously.21,22 In brief, patients were randomized 1:1 to finerenone (10 or 20 mg once daily; titrated according to serum potassium and eGFR changes) or placebo. Serum potassium levels were monitored throughout the studies, with specific measurements taken at baseline, month 1, month 4, and every 4 months thereafter. Additionally, hypokalaemia was captured through investigator-reported adverse events throughout the duration of the studies. The main outcomes [CV composite (time to CV death, non-fatal myocardial infarction, non-fatal stroke, or hospitalization for HF (HHF)] and kidney composite [time to first onset of kidney failure, sustained ≥57% decrease in eGFR from baseline over ≥4 weeks or renal death]) in the overall FIDELITY population have been previously described.20

In this post hoc analysis of FIDELITY, treatment-emergent serum potassium levels <4.0 or <3.5 mmol/L were investigated. In addition, efficacy outcomes, including CV composite outcome, arrhythmia composite outcome and all-cause mortality were analysed according to baseline serum potassium category.

Statistical analyses were performed using SAS software, version 9.4 (SAS Institute, Cary, NC, USA). Efficacy analyses were performed in the full analysis set (FAS) [all randomized patients (excluding those with critical Good Clinical Practice violations)] and safety outcomes were performed in the safety analysis set (SAS) [all randomized patients (excluding those with critical good clinical practice violations) who received ≥1 dose of study medication].20

The incidence of serum potassium values <4.0 mmol/L included treatment-emergent values (i.e. protocol-specified and unscheduled measurements during treatment) only, that is, all measurements after the first dose of study drug up to 3 days after any temporary or permanent interruption of study drug. Cumulative incidence of time to first treatment-emergent serum potassium level of <4.0 mmol/L was calculated using the Aalen-Johansen estimator with all-cause mortality as a competing risk. These analyses were repeated for serum potassium <3.5 mmol/L. Cox proportional hazards models stratified by study were calculated.

Time-to-event analyses for the treatment effect on outcomes by baseline serum potassium category (<3.5, 3.5–<4.0, 4.0–4.5, and >4.5 mmol/L) were expressed as hazard ratios (HRs) comparing finerenone vs. placebo with corresponding confidence intervals (CIs) from a stratified Cox regression model using the following stratification factors: region, eGFR category at screening, albuminuria at screening, CV disease history, and study.

The effect of serum potassium on efficacy outcomes irrespective of treatment group was analysed using separate Cox proportional hazards models; a first model comparing the risk in baseline potassium categories (<4.0 vs. 4.0–4.5 mmol/L and >4.5 vs. 4.0–4.5 mmol/L) and a second model with time-varying minimum potassium category (comparison categories of <3.5 vs. ≥4.0 mmol/L and 3.5–<4.0 vs. ≥4.0 mmol/L). These models were stratified by study and additionally adjusted for region, CV disease history, sex, race, age, diuretic use, glycated haemoglobin, systolic blood pressure, baseline UACR (log-transformed), and baseline eGFR.

Event probability analyses for outcomes by baseline serum potassium modelled with cubic splines were generated using a Cox proportional hazards model fitted with previously described covariates.

## 结果 / Results

In FIDELITY, 12 990 patients included in the FAS, but four patients were missing baseline serum potassium values, resulting in a total of 12 986 patients for this analysis. The safety population comprised 12 963 patients; 12 823 had available baseline and postbaseline serum potassium data and were included in this analysis.

Baseline characteristics were broadly similar across baseline serum potassium categories, with a serum potassium of <4.0 mmol/L reported in 16.7% (2163/12 986) of patients. Greater use of diuretics and potassium supplementation, were reported for those with a baseline serum potassium of <4.0 mmol/L (Table 1). Systolic blood pressure was elevated for those with serum potassium <4.0 mmol/L compared with the 4.0–4.5 and >4.5 mmol/L groups, respectively (Table 1).

Baseline characteristics according to baseline serum potassium category (full analysis set).

Four patients had missing serum potassium levels at baseline.

aRace, other includes American Indian/Alaskan native, Native Hawaiian/Other Pacific Islander, not reported or multiple.

bCV disease was defined as coronary artery disease, cerebrovascular disease, or peripheral arterial disease.

cIncluding binders.

CV, cardiovascular; eGFR, estimated glomerular filtration rate; HbA1c, glycated haemoglobin; Q, quartile; RASi, renin-angiotensin system inhibitor; SD, standard deviation; and UACR, urine albumin-to-creatinine ratio.

Additional baseline characteristics according to treatment group (Supplementary material online, Table S1), and of patients according to the lowest treatment-emergent potassium category during the trials (Supplementary material online, Table S2) are provided in Supplementary material online.

In the overall FIDELITY safety population, hypokalaemia was reported in 1.8% (114/6489) and 2.9% (185/6474) of patients who received finerenone and placebo, respectively, based on investigator-reported adverse events identified in accordance with the Standardised Medical Dictionary for Regulatory Activities Queries for hypokalaemia (using the following narrow terms: electrocardiogram U-wave prominent, hyperkalaemic syndrome, hypokalaemia, hypomagnesaemia, blood potassium decreased, blood potassium abnormal, or alkalosis hypokalaemia).

For this present analysis, hypokalaemia occurred less frequently with finerenone compared with placebo. Serum potassium <4.0 mmol/L was reported in 33.9% (2174/6420) vs. 48.3% (3094/6403) of patients in finerenone vs. placebo recipients (HR 0.63; 95% CI 0.60–0.66), and serum potassium <3.5 mmol/L was reported in 4.8% (309/6420) vs. 10.2% (650/6403) of patients, respectively (HR 0.46; 95% CI 0.40–0.53; Figure 1). The lower incidence of treatment-emergent serum potassium <3.5 and <4.0 mmol/L observed with finerenone vs. placebo was apparent from month 1 (Supplementary material online, Figure S1).

Incidence of treatment-emergent low serum potassium (safety analysis set). All patients had baseline and postbaseline treatment-emergent potassium values (minimum on-treatment potassium value is captured for each patient).

Assessment of the cumulative incidence of treatment-emergent serum potassium of <3.5, <4.0, >5.5 or >6.0 mmol/L at 4 years in the FIDELITY safety population of the placebo group showed that the frequency of hypokalaemia was higher [13.4% (95% CI 12.3–14.6) for a serum potassium level of <3.5 mmol/L and 57.2% (95% CI 55.6–58.8) for <4.0 mmol/L] than hyperkalaemia [10% (95% CI 9.1–11.0) for >5.5 mmol/L and 1.8% (95% CI 1.4–2.2) for >6.0 mmol/L] (Figure 2).

Placebo group cumulative incidence for time to treatment-emergent serum potassium of <3.5, <4.0, >5.5, and >6.0 mmol/L at 4 yearsa (safety analysis set). aFrom first intake of study medication.

For the overall population, an increased risk for the CV composite and arrhythmia composite outcomes was seen for patients with a baseline serum potassium level of <4.0 mmol/L compared with those with 4.0–4.5 mmol/L (HR 1.16; 95% CI 1.02–1.32, P = 0.022 for CV composite outcome; HR 1.20; 95% CI 1.00–1.44, P = 0.055 for arrhythmia composite outcome), irrespective of treatment group (Figure 3).

Outcomes by baseline serum potassium (<4.0 vs. 4.0–4.5 mmol/L and >4.5 vs. 4.0–4.5 mmol/L) (full analysis set). Hazard ratios were based on a study-stratified Cox proportional hazards model including treatment and serum potassium category calculated at baseline. Additional model adjustments were made for region, CV disease history, sex, race, age, diuretic use at baseline, glycated haemoglobin, systolic blood pressure, log(UACR), and eGFR at baseline. P-values for interaction indicate differences between treatment and baseline serum potassium category. CV composite outcome was time to CV death, non-fatal myocardial infarction, non-fatal stroke, or hospitalization for heart failure; arrhythmia composite outcome was new diagnosis of atrial fibrillation/atrial flutter, hospitalization due to arrhythmia, or sudden cardiac death. CI, confidence interval; CV, cardiovascular; eGFR, estimated glomerular filtration rate; and UACR, urine albumin-to-creatinine ratio.

When the minimum serum potassium level per patient at any time during the study was considered, the data showed that patients with serum potassium levels <3.5 mmol/L were at increased hazard of the CV composite (HR 1.53; 95% CI 1.28–1.81), arrhythmia composite (HR 1.67; 95% CI 1.31–2.13), and all-cause mortality (HR 1.56; 95% CI 1.27–1.91) outcomes compared with patients whose serum potassium levels were always ≥4.0 mmol/L (all P <0.0001; Supplementary material online, Table S3). A trend for higher hazard, although less pronounced, was also observed for the CV composite (HR 1.13; 95% CI 1.02–1.26), arrhythmia composite (HR 1.09; 95% CI 0.93–1.28), and all-cause mortality (HR 1.07; 95% CI 0.94–1.22) outcomes in patients who had a serum potassium level of 3.5–<4.0 vs. ≥4.0 mmol/L (Supplementary material online, Table S3).

Additional analysis of the placebo group showed similar results (Supplementary material online, Table S4).

In terms of treatment effect, finerenone reduced the hazard of the CV composite outcome vs. placebo in the overall FIDELITY population irrespective of serum potassium at baseline [12.7% (823/6498) vs. 14.4% (938/6492), respectively: HR 0.86; 95% CI 0.78–0.95, P-value for interaction 0.95; Figure 4].

CV and arrhythmia composite outcomes and all-cause mortality according to serum potassium at baseline (full analysis set). Stratified Cox proportional hazards model. Events were adjudicated by an independent committee and considered from randomization to end-of-study visit. CV composite outcome was time to CV death, non-fatal myocardial infarction, non-fatal stroke, or hospitalization for heart failure; arrhythmia composite outcome was new diagnosis of atrial fibrillation/atrial flutter, hospitalization due to arrhythmia, or sudden cardiac death. CI, confidence interval; CV, cardiovascular; and PY, patient-years.

Analysis of the individual components of the CV composite outcome reveals overall improvements were primarily driven by HHF outcomes, particularly for those with a baseline serum potassium <4.0 mmol/L (HR 0.65; 95% CI 0.45–0.94), although no significant differences in treatment effect were seen in any of the components between baseline serum potassium categories (Supplementary material online, Table S5).

The hazards for the arrhythmia composite outcome and all-cause mortality were also reduced with finerenone vs. placebo in the overall population. Overall, 5.9% of patients in the finerenone group and 6.8% of patients in the placebo group experienced an arrhythmia event, and 8.5% and 9.5% of patients randomized to finerenone and placebo, respectively, experienced an all-cause mortality event (Figure 4). Event probability analysis of the CV composite, arrhythmia composite, and all-cause mortality outcomes at 4 years, with serum potassium as a continuous variable, revealed a similar treatment effect with finerenone vs. placebo, irrespective of serum potassium levels at baseline (Supplementary material online, Figure S2). The greatest hazard of experiencing the arrhythmia composite outcome at 4 years was seen in individuals with low baseline serum potassium (Supplementary material online, Figure S2B). In all cases, the increased risk of CV composite outcome, arrhythmia composite outcome, and all-cause mortality was apparent between serum potassium of 3.5 and <4.0 mmol/L (Supplementary material online, Figure S2).

## 讨论 / Discussion

This post hoc subanalysis of FIDELITY, provides robust evidence that low serum potassium levels are frequently seen in patients with CKD and T2D. The incidence of treatment-emergent hypokalaemia with a serum potassium level of <3.5 mmol/L (7.5%) and <4.0 mmol/L (41.1%) exceeded the rate of investigator-reported hypokalaemia (1.7%) that was previously reported in the overall FIDELITY population.20 This finding is likely due to the assessment of serum potassium levels at regular intervals in the present analysis resulting in higher detection of low serum potassium levels compared with investigator-reported hypokalaemia. In addition, the cumulative incidences for time to serum potassium of <3.5 and <4.0 mmol/L were shown to be more frequent than for serum potassium of >5.5 and >6.0 mmol/L. Collectively, these data suggest that the true incidence of hypokalaemia in patients with CKD and T2D may be substantially higher than previously thought.

Our analysis also revealed treatment-emergent serum potassium levels (<4.0 mmol/L) over two-fold higher than the prevalence range of 12–18% previously reported for patients with CKD;1 however, study criteria for FIDELIO-DKD and FIGARO-DKD required serum potassium levels ≤4.8 mmol/L at screening.1,18,19 Despite a lack of data in other studies on the prevalence of hypokalaemia (serum potassium of <3.5 and <4.0 mmol/L) in patients with both CKD and T2D, per the FIDELITY population, 23–43% of patients with CKD were found in large-scale prospective observational and electronic health record-based studies investigating low serum potassium to also have T2D.3,23–25 Although a direct comparison cannot be made because of differing study designs, the collective observations suggest that hypokalaemia with serum potassium levels of <3.5 and <4.0 mmol/L is relatively frequent in patients with CKD and T2D. Nevertheless, this FIDELITY subanalysis is, to the best of our knowledge, the first to investigate the incidence of hypokalaemia in this patient population participating in a clinical study on an MRA; several prior clinical studies excluded individuals with a serum potassium <3.5 mmol/L and/or did not report the incidence of hypokalaemia with serum potassium levels of <3.5 or <4.0 mmol/L.26–28

Assessment of treatment effects showed that finerenone reduced the hazard of hypokalaemia with serum potassium level of <3.5 and <4.0 mmol/L vs. placebo in patients with CKD and T2D on optimized RAS inhibitor therapy, as observed from the first study assessment (month 1). As FIDELITY included patients with T2D across the spectrum of CKD severity, these data suggest that finerenone may offer protection from hypokalaemia for a wide range of individuals.

With regard to CV events in the overall population, an increased risk for the CV composite outcomes and arrhythmia composite outcomes was seen for those with a baseline serum potassium level of <4.0 vs. 4.0–4.5 mmol/L (i.e. patients with the lowest hazard for adverse clinical outcomes). In addition, analysis of the placebo group showed an increased risk of CV events for patients with serum potassium levels of <4.0 mmol/L compared with 4.0–4.5 mmol/L, thus emphasizing low potassium as a risk factor for CV events.

In the overall FIDELITY population, finerenone lessened the hazard of CV and arrhythmia composite outcomes by 14% and 13%, respectively, compared with placebo, with HHF primarily driving the reduced hazard of adverse CV events. Patients who received finerenone vs. placebo also had a lower hazard of all-cause mortality events. It is noteworthy that the hazards of the CV and arrhythmia composite outcomes were higher in patients with a baseline serum potassium level of <4.0 mmol/L compared with 4.0–4.5 mmol/L, and the effect of finerenone was not modified by serum potassium at baseline. However, it is not known if the reductions in these hazard outcomes with finerenone are in part mediated by the prevention of hypokalaemia; further investigation will be required to address these observations.

Data from this analysis highlight the importance of considering hypokalaemia in patients with CKD and T2D, given its frequent occurrence in these patients and its association with adverse CV events in an already at-risk population. The findings in this subanalysis correspond with previous studies that showed an association between serum potassium levels ≤4.0 mmol/L and increased mortality in patients with CKD.3,23,24 Furthermore, excess potassium can be eliminated through the colon.5 Mechanisms include increased aldosterone levels and increased expression of the mineralocorticoid receptors in the colon, which are critically involved in electrolyte balance,29,30 regulating potassium in the kidneys and influencing electrolyte transport in extrarenal tissues including the colon.30,31 Inappropriately increased levels of aldosterone may occur in conditions such as PA,12 and also in patients with CKD,32 and are associated with target damage to the heart and kidney. 12,33–35 These changes induce mineralocorticoid receptor-dependent endothelial dysfunction within the gut resulting in increased intestinal permeability29,36; a physiologic effect shown to be reduced with the steroidal MRA spironolactone in animal models.29,36 Consequently, mineralocorticoid receptor blockade with finerenone (a non-steroidal MRA) in patients with CKD and T2D may be an important mechanism to mitigate the occurrence of hypokalaemia, CV risks associated with CKD and low serum potassium levels, along with additional benefits on electrolyte balance and gut permeability.

The FIDELITY pooled analysis enabled evaluation of finerenone across a large number of patients with a broad spectrum of CKD and T2D and provided precision that exceeded evaluation of the studies individually, but one of the limitations is that individuals with non-albuminuric CKD were not included. Thus, the incidence and risks associated with hypokalaemia in these individuals remain to be investigated. Furthermore, most study participants were White or Asian, and few Black/African American individuals were included.

The FIDELITY studies were not designed to compare risk in clinical outcome events based on serum potassium values at baseline or during the study, that is, patients with serum potassium <4.0 mmol/L differ in baseline characteristics compared with patients with 4.0–4.5 and >4.5 mmol/L. This is accounted for in the analyses by using relevant adjustment factors; however, further differences between the groups cannot be excluded.

Additionally, the assessment of serum potassium levels was conducted at regular intervals with the minimum potassium category over the course of the study, including baseline, applied in this current analysis. Consequently, it is possible that the minimum value a patient may have experienced was a transient state. Future analyses could consider investigating median or mean values to assess if consistently lower potassium confers and increases the risk of outcome events.

## 结论 / Conclusion

In conclusion, findings from this FIDELITY analysis reveal that a substantial proportion of patients with CKD and T2D experience serum potassium levels of <3.5 and <4.0 mmol/L despite optimal treatment with a RAS inhibitor. Hypokalaemia, defined as a serum potassium level of <3.5 and <4.0 mmol/L, occurred with a higher incidence compared with hyperkalaemia (defined as serum potassium levels of >5.5 and >6.0 mmol/L) and was found to be associated with an elevated hazard of adverse CV outcomes. However, this risk was rarely acknowledged, as evidenced by the relative lack of potassium supplementation and/or serum potassium correction in these patients especially in those with a serum potassium <4.0 mmol/L and may be of considerable clinical importance given the association with increased hazard of CV outcomes. Although finerenone was well tolerated, with a low incidence of patients discontinuing therapy because of hyperkalaemia,18,20 finerenone offered protection from hypokalaemia in patients with T2D across the spectrum of CKD severity, providing a consistent effect on reducing the risk of CV outcomes, including arrhythmias and all-cause mortality across baseline serum potassium subgroups.
