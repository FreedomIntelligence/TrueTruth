---
type: RCT
language: en
status: reviewed
extracted_by: api+llm
authors:
- Russo E
- Cappadona F
- Macciò L
- Di Vincenzo J
- Piaggio M
- Verzola D
- Chirco G
- Garibotto G
- Esposito P
- Viazzi F
tags:
- SGLT2i
- CKD
- vascular stiffness
- AASI
- blood pressure
- renal protection
- randomized controlled trial
title:
  zh: null
  en: 'Dapagliflozin Reduces Ambulatory Arterial Stiffness Index in CKD Patients with
    and Without Diabetes Independently of Blood Pressure Control: Results from the
    GLUcose Transport and Renal PROtection in Chronic Kidney Disease (GLUTREPRO) Trial'
year: 2025
journal: 'High blood pressure & cardiovascular prevention : the official journal of
  the Italian Society of Hypertension'
pmid: '41366613'
doi: 10.1007/s40292-025-00764-3
pico:
  population:
    condition: albuminuric CKD (eGFR 25–75 ml/min/1.73 m², UACR ≥30 mg/g)
    sample_size: 32
  intervention:
    name: dapagliflozin 10 mg/day
  comparison:
    name: placebo
  outcomes:
    primary:
    - name: ambulatory arterial stiffness index (AASI)
      effect_size:
        metric: MD
        value: -0.12
        ci_low: -0.23
        ci_high: -0.01
        p: 0.04
risk_of_bias:
  tool: RoB2
  overall: some_concerns
grade:
  level: low
id: EV-RCT-2025-RUSSO-001
study_type: RCT
---



## English Abstract

Sodium–glucose cotransporter 2 inhibitors (SGLT2i) confer cardiovascular and renal protection, but their impact on blood pressure (BP) and vascular stiffness in chronic kidney disease (CKD) is not fully defined.

To investigate the effect of dapagliflozin on 24h-BP behavior and ambulatory arterial stiffness index (AASI) as a predefined secondary outcome of the GLUTREPRO trial.

In this randomized trial, 32 patients with albuminuric CKD received dapagliflozin 10 mg/day or placebo on top of optimized standard therapy. Laboratory tests, ambulatory blood pressure monitoring (ABPM), and bioimpedance were performed at baseline and during follow-up. The study comprised a 6-month randomized phase and a 12-month open-label phase, analyzed with mixed-effects models.

Baseline characteristics were balanced (mean age 58 ± 14 years, 37% diabetes, eGFR 50.6 ± 17.3 ml/min/1.73 m2, UACR 582 ± 893 mg/g). Dapagliflozin induced an early eGFR dip (–3 to –6 ml/min/1.73m2) followed by stabilization. Overall, UACR did not change significantly, but patients with baseline microalbuminuria showed lower UACR after six months versus placebo. ABPM revealed no significant differences in BP or dipping status. Conversely, dapagliflozin significantly reduced AASI at 6 months (0.50 vs. 0.62; p = 0.04), with a trend toward sustained improvement thereafter. Multivariable regression identified dapagliflozin as an independent predictor of lower AASI (β = – 0.067; 95% CI –0.130 to –0.002; p = 0.043), independent of diabetes, 24-h Systolic BP, heart rate, kidney function, fractional sodium excretion, and TyG index.

In patients with albuminuric CKD, dapagliflozin lowered AASI independently of BP control and sodium handling, suggesting favorable vascular remodeling in both diabetic and non-diabetic patients.

The study was registered in the EU Clinical Trials Register (EudraCT: 2020-004835-26) and online at the https://www.clinicaltrials.gov (Unique identifier: NCT05998837, 13th April 2021).

The online version contains supplementary material available at 10.1007/s40292-025-00764-3.

## 背景 / Background

Sodium–glucose cotransporter 2 inhibitors (SGLT2i) are established therapies for type 2 diabetes (T2D) and chronic kidney disease (CKD). Large, randomized trials consistently demonstrated reduced kidney disease progression, heart failure hospitalization, and major cardiovascular (CV) events, regardless of diabetes status [1–3]. Such robust and reproducible results highlight the unique position of SGLT2i as disease-modifying therapies across different organ systems The mechanisms underlying these benefits remain incompletely understood and extend beyond glycosuria or natriuresis.

A consistent finding across studies is a modest anti-hypertensive effect. A meta-analysis of seven RCTs (2381 participants) showed that SGLT2i reduce both systolic and diastolic blood pressure (BP), comparable to low-dose hydrochlorothiazide [4]. In the CREDENCE trial, canagliflozin lowered systolic BP across all baseline categories, reducing the need for additional antihypertensives [5]. Empagliflozin also decreased BP after 12 weeks, with efficacy preserved despite renal function decline and irrespective of background therapy [6]. Although not primarily antihypertensive, SGLT2i may mitigate hypertension-mediated organ damage (HMOD) [7].

Hypertension and arterial stiffness are major CV risk factors in CKD, especially with albuminuria. Arterial stiffening reflects HMOD and predicts adverse renal and CV outcomes [8]. The 2018 ESC/ESH Guidelines recommend assessing pulse wave velocity (PWV) and wave reflection indices to detect subclinical HMOD [9]. Carotid–femoral PWV (cfPWV) is the gold standard, but alternatives such as brachial–ankle PWV, cardio–ankle vascular index, augmentation index (AIx), and ambulatory arterial stiffness index (AASI) are increasingly employed [10–12]. AASI, derived from 24-h ambulatory BP monitoring (ABPM), correlates with cfPWV and AIx, integrating arterial compliance with BP variability. Elevated AASI associates with microalbuminuria, carotid structural changes, and left ventricular hypertrophy [13]. Furthermore, it has been validated as a prognostic marker, independently predicting CV morbidity, stroke, all-cause mortality, and composite CV outcomes [14, 15].

The influence of SGLT2i on arterial stiffness has been investigated in recent years, though findings remain heterogeneous. Some clinical studies with empagliflozin and dapagliflozin reported neutral results on stiffness parameters [16, 17], whereas others documented favorable vascular effects [18]. Notably, short-term RCTs confirmed modest but significant reductions in PWV, ranging from –0.13 to –0.17 m/s, in patients with T2D treated with SGLT2i [16, 18]. These reports suggest that improvements in arterial properties may be partly independent of BP lowering, potentially mediated by enhanced endothelial function and restoration of the endothelial glycocalyx [19]. Nevertheless, data specifically addressing the effects of SGLT2i on AASI remain scarce.

The GLUcose Transport and Renal PROtection (GLUTREPRO) Trial was designed to investigate dapagliflozin in albuminuric CKD. In this prespecified secondary analysis, we evaluated its impact on 24-h BP and AASI, to determine whether vascular benefits extend to CKD patients with and without diabetes and occur independently of BP lowering.

## 方法 / Methods

The GLUTREPRO trial was designed as a prospective, randomized, placebo-controlled, parallel-group study with a subsequent open-label extension.

This study was approved by the local institutional review committee (the Ethic Committee of the Ligurian Region CE 150193 with the ID D169AL00005) and authorized by the Italian Drug Agency (AIFA). The study was registered in the EU Clinical Trials Register (EudraCT: 2020-004835-26) and online at the https://www.clinicaltrials.gov (Unique identifier: NCT05998837, 13th April 2021). It was conducted in accordance with the GCP/ICH E6 Guidelines and the principles of the Declaration of Helsinki and all patients provided written informed consent. Thirty-two patients with albuminuric CKD were enrolled and randomized in a 1:1 ratio to receive dapagliflozin 10 mg once daily or placebo in addition to standard of care. The study consisted of two phases: a randomized phase lasting six months (T0–T2), during which patients received either dapagliflozin or placebo, followed by an open-label phase of twelve months (T2–T4), in which all participants were treated with dapagliflozin.

Inclusion and exclusion criteria have been previously detailed [20], in brief CKD patients with albuminuria and eGFR between 25 and 75 ml/min with or without T2D were recruited from the Unit of Nephrology, Dialysis and Transplantation in San Martino hospital from April 2021 to April 2023. A run-in phase has been conducted with the aim of optimizing clinical parameters without the need of additional therapy during the trial. Prior to randomization the patient must have undergone at least 4 weeks of therapy with metformin and/or repaglinide. Dosages have been modulated to minimize collateral effects and to optimize glucose control in accordance with ADA guidelines [21]. RAAS-i has been titrated with the aim to reach optimal BP control as defined by European Society of Hypertension (i.e., 120-130/70-80 mmHg) in all subjects [9]. Allocation to treatment group has been done by stratified randomization for diabetics and non-diabetics generated with a designed computer program. Accordingly, patients have been assigned to start with standard therapy and placebo or dapagliflozin at the dose of 10 mg and continued the assigned treatment for 24 weeks in double-blind and with dapagliflozin at the dose of 10 mg for an additional 48 weeks in open label as defined in the Extended treatment phase.

Patients were diagnosed with T2D based on a history of treatment with antidiabetic drugs, or when fasting plasma glucose was ≥ 126 mg/dL in at least two measurements, or hemoglobin A1c was ≥ 6.5%. Kidney function was assessed by serum creatinine and urinary albumin excretion measurements. GFR was estimated using a standardized serum creatinine assay and the Chronic Kidney Disease Epidemiology Collaboration formula [22]. Urine samples for albumin excretion measurements were collected before each study visit. Microalbuminuria was diagnosed if urinary albumin to creatinine ratio (UACR) was ≥ 30 and below 300 mg/g in both genders. Macroalbuminuria was diagnosed if UACR was ≥ 300 mg/g in both genders. The triglyceride–glucose (TyG) index was calculated as follows:

ABPM together with bioimpedance analysis (BIA) were performed according to the study schedule (T0, T2 and T4). Ambulatory BP was monitored over 24 hours using a validated oscillometric device (Spacelabs 90207; SpaceLabs Inc., Redmond, WA, USA). The device was programmed to obtain measurements every 15 minutes during daytime (07:00–23:00 h) and every 30 minutes during nighttime (23:00–07:00 h). Participants were instructed to continue their usual daily activities while avoiding excessive exertion and to keep their non-dominant arm still during recordings. A diary was maintained to record daily activities, bedtime, and wake-up times, which were used to define awake and asleep periods. Nocturnal dipping was defined as a reduction greater than 10% in mean systolic and diastolic pressure during the night compared with daytime values. For AASI calculation, systolic and diastolic BP readings from each identical time point were paired. The AASI was derived as one minus the regression slope of diastolic BP (DBP) plotted against systolic BP (SBP) from individual 24-hour ABPM recordings for each patient. This method was chosen because it reflects the dynamic relationship between SBP and DBP over the cardiac cycle, providing an indirect measure of arterial stiffness. Notably, the regression was performed without forcing the intercept through zero, allowing for a more accurate depiction of the natural variability and the inherent correlation between the two parameters across the range of blood pressures. A diagnosis of hypertension was made if the 24-h BP monitoring was ≥130 mmHg systolic or ≥ 80 mmHg diastolic or in the presence of antihypertensive treatment. Uncontrolled hypertension was defined when 24h ABPM was ≥ 130 mmHg systolic or ≥80 mmHg diastolic in the presence of antihypertensive treatment. Optimal BP control was defined when ABPM showed 24h-SBP and 24h-DBP less than 130/80 mmHg. The night/day systolic ratio (n/dSR) was calculated for each ABPM as the ratio of the average value of SBP during the night and the corresponding average value of SBP during the day. A n/dSR value >1 indicates a non-dipping pattern characterized by an increase of BP levels during the nighttime with respect to day-time (i.e. reverse dipping or rising pattern).

Body composition was assessed by multifrequency bioimpedance spectroscopy using the Body Composition Monitor (BCM, Fresenius Medical Care). Measurements were performed in the supine position with electrodes placed on the forearm and ipsilateral ankle. The device measured resistance and reactance at 50 discrete frequencies ranging from 5 to 1000 kHz. Based on a validated fluid model, extracellular water (ECW), intracellular water (ICW), and total body water (TBW) were estimated. Over hydration was defined as the difference between measured and expected ECW.

All analyses were performed according to the intention-to-treat principle. Continuous variables are presented as mean ± standard deviation, and categorical variables as absolute numbers and percentages. Within-group changes were tested with paired Student’s t-test or the Wilcoxon signed-rank test, while between-group differences were assessed using the independent samples t-test or the Mann–Whitney U test according to the distribution of the variables. Categorical variables were compared using the chi-square test. Separate mixed-effects models were applied to the randomized and the open-label phases in order to assess treatment effects over time. Univariate and multivariate linear regression analyses were performed to evaluate the relationship between clinical and laboratory features and AASI. Covariates considered as potential confounders of the association between treatment and AASI (such as diabetes and eGFR), as well as those showing a p-value < 0.200 in univariate analysis, were included in the multivariate models. A two-tailed p value < 0.05 was considered statistically significant. Statistical calculations were performed by STATA package, version 14.2 (StataCorp, 4905 Lakeway Drive, College Station, Texas 77845 USA).

## 结果 / Results

A total of 32 participants underwent randomization. The baseline characteristics, including GFR and SBP, were balanced between the dapagliflozin and placebo groups (Table 1). The mean (±SD) age was 58 ± 14 years, and 12 participants (37%) were diabetic. The mean estimated GFR was 50.6 ±17.3 ml per minute per 1.73 m2, and the median UACR was 582 ±893 mg/g.Table 1Demographic and clinical characteristics of the participants at baselineALL (N = 32)Placebo (N = 15)Dapagliflozin (N = 17)pAge, years58 ± 1462 ± 1154 ± 150.115Male gender, %91100820.087Diabetes, %3740350.784BMI, Kg/m227.0 ± 2.626.4 ± 2.827.5 ± 2.40.250Fasting glucose, g/l102 ± 21105 ± 26100 ± 140.519HbA1c, %5.94 ± 0.735.87 ± 0.756.00 ± 0.720.613Hypertension, %97100940.340Office systolic BP, mmHg133 ± 12134 ± 14131 ± 100.463Office diastolic BP, mmHg83 ± 884 ± 982 ± 70.456Triglycerides, mg/dl147 ± 70148 ± 67145 ± 750.971HDL-C, mg/dl49 ± 1247 ± 1251 ± 130.383LDL-C, mg/dl83 ± 3090 ± 3278 ± 280.274TyG index4.75 ± 0.224.76 ± 0.204.74 ± 0.240.791Creatinine, mg/dl1.69 ± 0.511.68 ± 0.421.70 ± 0.590.914eGFR, ml/min/1.73m250.6 ± 17.349.6 ± 16.051.4 ± 18.90.773Uric acid, mg/dl6.1 ± 1.46.4 ± 1.45.8 ± 1.40.235Sodium, mEq/l139 ± 2139 ± 3139 ± 20.505Potassium, mEq/l4.32 ± 0.504.46 ± 0.654.19 ± 0.300.130Hemoglobin, g/dl14.1 ± 1.814.4 ± 1.913.8 ± 1.70.398NT-proBNP, pg/l198 ± 302237 ± 343163 ± 2660.502Total body water (TBW), L45.7 ± 7.545.8 ± 7.445.6 ± 7.80.916Extra-Cellular water (ECW), L19.8 ± 3.319.7 ± 3.319.8 ± 3.50.945Intra-Cellular water (ICW), L25.9 ± 4.526.1 ± 4.525.7 ± 4.70.812Over-hydratation (OH), L0.17 ± 1.40-0.11 ± 1.300.42 ± 1.490.300UACR, mg/g (all)582 ± 893586 ± 587579 ± 11150.984UACR (microalbuminuric), mg/g109 ± 86156 ± 11280 ± 540.087Macroalbuminuria, %5060410.288UACR (macroalbuminuric), mg/g1056 ± 1079872 ± 6041293 ± 15180.458Proteinuria, g/die1.10 ± 1.461.17 ± 0.941.04 ± 1.840.806BMI, body mass index; BP, blood pressure; eGFR, estimated glomerular filtration rate; HbA1c, glycated hemoglobin; HDL-C, high density lipoprotein cholesterol; LDL-C, low density lipoprotein cholesterol; NT-proBNP, N-terminal pro-B-type natriuretic peptide; TyG, triglyceride-glucose index UACR, urinary albumin to creatinine ratio.

Demographic and clinical characteristics of the participants at baseline

BMI, body mass index; BP, blood pressure; eGFR, estimated glomerular filtration rate; HbA1c, glycated hemoglobin; HDL-C, high density lipoprotein cholesterol; LDL-C, low density lipoprotein cholesterol; NT-proBNP, N-terminal pro-B-type natriuretic peptide; TyG, triglyceride-glucose index UACR, urinary albumin to creatinine ratio.

Patients starting the open-phase after 6 months of dapagliflozin showed a similar BP, volume status (i.e., N-terminal pro-B-type natriuretic peptide (NT-proBNP) and BIA parameter) and biochemical profile, as compared to those who have been randomized to placebo. While a tendency to a higher HDL cholesterol, and a lower serum uric acid concentration was observed, these did not reach statistical significance (Supplemental Table 1).

When we stratified patients on the basis of the severity of albuminuria at baseline, patients with microalbuminuria, starting the open-phase after 6 months of dapagliflozin showed a significantly lower UACR as compared to those randomized to placebo (83 ± 72 vs. 265 ± 79 mg/g, p = 0.0003, Supplemental Table 1). This was more evident in non-diabetic patients (98 ± 73 vs. 242 ± 34 mg/g; p = 0.002) and less evident among diabetic patients (116 ± 76 vs. 144 ± 62 mg/g, respectively, p = 0.588).

On the contrary, in patients with diabetes, serum uric acid levels were significantly lower after 6 months of dapagliflozin as compared to those exposed to placebo (5.48 ± 1.70 vs. 7.23 ± 0.71 mg/dl, p = 0.04), whereas in non-diabetic patients this difference was less evident (5.6 ± 1.9 vs. 6.2 ± 1.2 mg/dl, p = 0.48).

Table 2 reports longitudinal eGFR changes. As expected, initiation of dapagliflozin was associated with an early decline in eGFR (≈3–6 ml/min/1.73 m2 within 6 months), while values remained stable in the placebo group. Patients switching from placebo to dapagliflozin showed the same initial drop, whereas those continuously treated with dapagliflozin maintained stable eGFR thereafter.Table 2Adjusted marginal means of eGFR by treatment group and timepointPhaseTimePlacebo (Mean ± SE)Dapagliflozin (Mean ± SE)T0 (Baseline)49.6 ± 4.551.4 ± 4.3RandomizedT1 (3 months)48.9 ± 4.148.1 ± 3.9T2 (6 months)48.8 ± 4.445.2 ± 4.2PhaseTimePlacebo-to-Dapagliflozin(Mean ± SE)Dapagliflozin-to-Dapagliflozin (Mean ± SE)Open-labelT3 (12 months)45.6 ± 4.746.0 ± 4.4T4 (18 months)46.9 ± 4.643.9 ± 4.3Data are presented as mean ± standard error (SE). eGFR, estimated glomerular filtration rate, is expressed in ml/min/1.73 m2

Adjusted marginal means of eGFR by treatment group and timepoint

Data are presented as mean ± standard error (SE). eGFR, estimated glomerular filtration rate, is expressed in ml/min/1.73 m2

No differences in UACR trajectories were observed between the two treatment arms throughout the trial (Fig. 1).Fig. 1Change from baseline in urinary albumin to creatinine ratio (UACR). Urinary albumin to creatinine ratio (UACR) mean change from baseline are represented in Placebo-to-Dapagliflozin (blue) and Dapagliflozin-to-Dapagliflozin (red) groups with 95% CI. Data are estimated from a linear mixed-effects model including all study time points; values represent model-based predictions of UACR trajectories over the course of the trial. T0 = baseline, T1 = 3 months, T2 = 6 months, T3 = 12 months, T4 = 18 months

Change from baseline in urinary albumin to creatinine ratio (UACR). Urinary albumin to creatinine ratio (UACR) mean change from baseline are represented in Placebo-to-Dapagliflozin (blue) and Dapagliflozin-to-Dapagliflozin (red) groups with 95% CI. Data are estimated from a linear mixed-effects model including all study time points; values represent model-based predictions of UACR trajectories over the course of the trial. T0 = baseline, T1 = 3 months, T2 = 6 months, T3 = 12 months, T4 = 18 months

BP behavior assessed by ABPM was described in Supplemental Table 2. About 97% of patients were hypertensive (of whom 76% had suboptimal control), 25% non-dippers and 3% risers at baseline. While a marked improvement in overall BP control was observed during the study period (optimal BP control from 22 to 47%), no substantial differences emerged between patients treated with dapagliflozin and those in the placebo group.

Dapagliflozin treatment did not significantly affect pulse pressure or dipping status. Conversely, patients in the dapagliflozin arm showed a significantly lower AASI as compared to those in the placebo group after 6 months of the randomized phase (AASI 0.50 vs. 0.62, respectively; p = 0.04, Supplemental table 2 and Fig. 2) and maintained similar values up to the end of the 18-month study period (AASI 0.51 after 18 months of dapagliflozin). During the open-label phase, patients who crossed over from placebo to dapagliflozin showed a non-significant trend toward lower AASI values at the study’s conclusion (passing from 0.62 to 0.60, Fig. 2).Fig. 2Boxplots of Ambulatory Arterial Stiffness Index (AASI) at baseline (T0), 6 months (T2), and 18 months (T4) by treatment arm. * dapagliflozin vs placebo after 6 months of randomized phase, p = 0.04. Abbreviations: AASI, ambulatory arterial stiffness index

Boxplots of Ambulatory Arterial Stiffness Index (AASI) at baseline (T0), 6 months (T2), and 18 months (T4) by treatment arm. * dapagliflozin vs placebo after 6 months of randomized phase, p = 0.04. Abbreviations: AASI, ambulatory arterial stiffness index

Table 3 summarizes determinants of AASI across study time points. In univariate analysis, dapagliflozin treatment and 24-h systolic BP were significantly associated with AASI. In multivariable models, dapagliflozin remained independently associated with lower AASI (β = –0.067; 95% CI –0.130 to –0.002; p = 0.043), irrespective of diabetes status, 24-h systolic BP, heart rate, eGFR, fractional excretion of sodium, and TyG index.Table 3Determinants of Ambulatory Arterial Stiffness IndexUnivariate analysisMultivariable analysisCoef95% CIpCoef95% CIpFemale gender0.047− 0.058/0.1520.377Dapagliflozin− 0.074− 0.135/− 0.0120.002− 0.067− 0.132/− 0.0020.047Diabetes0.024− 0.040/0.0890.454− 0.028− 0.095/0.0390.405Hypertension− 0.065− 0.242/0.1100.46124h-SBP, mmHg0.0040.002/0.006< 0.0010.0010.002/0.007< 0.00124h-HR, bpm0.003− 0.001/0.0070.188− 0.001− 0.004/0.0040.952TyG0.061− 0.049/0.1700.2070.021− 0.089/0.1310.709eGFR, ml/min/1.73 m2− 0.001− 0.003/0.0010.1890.000− 0.002/0.0020.988NT− proBNP, pg/ml0.0010.000/0.0010.0620.000− 0.001/0.0020.126FeNa, %0.024− 0.007/0.0550.1220.021− 0.011/0.0550.200FeGlu, %0.120− 0.271/0.5120.534OH, l− 0.002− 0.030/0.0270.909Univariate and multivariate linear regression models were applied. Variables with p < 0.200 in univariate analysis were included in the multivariate model.eGFR, estimated glomerular filtration rate; FEGlu, fractional excretion of glucose; NT-proBNP, N-terminal pro-B-type natriuretic peptide; OH, over hydratation, TyG, triglyceride-glucose index; 24h-SBP, 24 hour systolic blood pressure; 24h-HR, 24 hour heart rate.

Determinants of Ambulatory Arterial Stiffness Index

Univariate and multivariate linear regression models were applied. Variables with p < 0.200 in univariate analysis were included in the multivariate model.

eGFR, estimated glomerular filtration rate; FEGlu, fractional excretion of glucose; NT-proBNP, N-terminal pro-B-type natriuretic peptide; OH, over hydratation, TyG, triglyceride-glucose index; 24h-SBP, 24 hour systolic blood pressure; 24h-HR, 24 hour heart rate.

## 讨论 / Discussion

We report the effects of dapagliflozin on BP behavior as a prespecified secondary analysis of the GLUcose Transport and Renal PROtection in chronic kidney disease (GLUTREPRO) Trial. The main finding was a significant reduction in the AASI after 6 months of dapagliflozin treatment in patients with or without T2D and albuminuric CKD, compared to standard of care. These results suggest a favorable vascular effect that may contribute to the overall cardioprotective profile widely attributed to SGLT2 inhibitors.

Arterial stiffness is a well-recognized marker of CV risk, independently associated with CV morbidity, mortality, and all-cause mortality [23]. Arterial stiffness also has prognostic implications in ESRD and T2D, where it correlates not only with CV outcomes but also with microvascular complications such as nephropathy, neuropathy, and retinopathy [24].

SGLT2i have emerged as disease-modifying therapies in diabetes and CKD, demonstrating consistent benefits in CV and renal outcomes irrespective of glycemic status. Their mechanisms extend well beyond glucose lowering, involving hemodynamic, vascular, and renal pathways. Although some studies have reported improvements in PWV [25–27], a meta-analysis by Rizos et al. concluded that SGLT2i had no significant effect on classical vascular measures of arterial stiffness [28]. However, it is important to consider that this analysis includes only 13 studies characterized by small sample sizes (ranging from 15 to 76 patients) and short durations of SGLT2 inhibitor exposure (up to 32 weeks). Moreover, this conclusion appears somewhat in contrast to the beneficial effects demonstrated by these drugs in the development and progression of subclinical atherosclerosis, such as the reduction of intima-media thickness [17].

In the EMPEROR-Preserved trial, the modest reduction in SBP in patients randomized to empagliflozin resulted in a moderate increase in time at target and reduced hypertensive urgencies. Interestingly, this BP effect did not appear to account for the overall CV benefit [29], supporting the hypothesis that gliflozins may improve vascular stiffness and organ protection via mechanisms independent of BP lowering. Our findings are consistent with this concept, providing evidence of a direct favorable effect of dapagliflozin on vascular stiffness, independently by BP changes.

Large artery and microcirculation alterations are tightly interconnected, creating a vicious cycle in hypertension. Increased arterial stiffness enhances pulsatile energy transmission into small arteries, causing subclinical damage in high-flow, low-impedance organs such as the brain and kidneys [30]. Simultaneously, structural and functional alterations of the microvasculature may lead to increases in total peripheral resistance and mean BP, which in turn promotes long-term large artery stiffening [31]. As a matter of fact, correlation of atherosclerosis and impaired microcirculation in adult patients both with and without T2D (or with CKD) has been increasingly documented [32]. Interestingly, we described a reduction in AASI and in microalbuminuria that evidences a simultaneous effect both on large arteries and microcirculation which might suggest that dapagliflozin actuates its CV effects by inducing favorable changes both at the macro- and micro-vascular level. A recent meta-analysis in hypertensive patients found that the reduction in PWV after antihypertensive treatment was largely explained by BP lowering [18]. In contrast, the mechanisms underlying SGLT2i-induced improvements in arterial stiffness remain incompletely understood. Proposed contributors include natriuresis and osmotic diuresis [33], vasodilation with reduced vascular resistance and preservation of the endothelial glycocalyx [34] which regulates vascular tone and sodium buffering through nitric oxide release [35, 36].

In our multivariate analysis, dapagliflozin use was independently associated with lower AASI, regardless of classical determinants of vascular stiffness such as BP, heart rate, diabetes, and renal function. This inverse correlation suggests that the beneficial effect of dapagliflozin on vascular rigidity may reflect a direct action on vessel structure. Supporting this hypothesis, the reduction in AASI was not related to changes in volume status. Indeed, despite the osmotic diuresis and natriuresis typically induced by SGLT2 inhibition at the proximal tubule [37], and the well-established efficacy of these agents in alleviating hypervolemia in heart failure [38], the observed association between dapagliflozin and AASI reduction was independent of both fractional sodium excretion and plasma NT-proBNP levels, in diabetic as well as non-diabetic patients. Although SGLT2 is not typically expressed in vascular endothelial or smooth muscle cells under physiological conditions, SGLT2i have demonstrated notable vascular effects. Several potential mechanisms have been proposed to explain this apparent paradox. One involves off-target effects, including the inhibition of NHE1 and modulation of ion channels, which directly influence vascular tone and endothelial function. Notably, the reduction of intracellular Na+ and Ca2+ levels via inhibition of NHE1 appears to be a key mechanism underlying SGLT2i-induced endothelial protection, reducing reactive oxygen (ROS) species generation and proinflammatory signaling [39]. Alternatively, some evidence suggests that pathological conditions such as hypertension, diabetes, or tumors may induce abnormal SGLT2 expression within the vasculature, potentially driven by altered metabolic demands. Data also indicate that SGLT2 expression in human vasculature correlates with low-grade inflammation and contributes to an imbalance between endothelial nitric oxide synthase (eNOS) and ROS production [40]. Therefore, SGLT2i might favorably impact on vascular function by reducing oxidative stress and inflammatory status or inhibiting the sympathetic nervous system [41]. Moreover, they decrease endothelial cell activation, stimulating direct vasorelaxation and ameliorating endothelial dysfunction or the expression of pro-atherogenic cells and molecules [42]. Although SGLT2i have consistently been shown to improve vascular function in patients with T2D, evidence in CKD and non-diabetic cohorts remains limited. Larger, adequately powered studies are needed to confirm whether these vascular benefits extend broadly across diverse clinical populations.

This study has several strengths that warrant highlighting, including its randomized design, a relatively long follow-up period, and a run-in phase aimed at optimizing clinical parameters without the need for additional therapy during the trial. Moreover, the assessment of volume status through NT-proBNP and BIA enabled us to ensure that changes in vascular stiffness and BP behavior were not influenced by variations in hydration status. This study has some limitations. Firstly, we did not employed the gold standard c-fPWV measurement of arterial stiffness. Moreover, the modest sample size, the predominance of males and single-center design may restrict the generalizability of the findings. Further validation in larger, multicenter cohorts is warranted, and additional research is needed to elucidate the specific molecular mechanisms potential sex differences underlying the observed effects. Further validation in larger, multicenter cohorts is warranted, and additional research is needed to elucidate the specific molecular mechanisms underlying the observed effects.

## 结论 / Conclusion

Our findings suggest that dapagliflozin favorably impacts vascular stiffness, extending the evidence base for SGLT2i as vascular-protective drugs [18] to albuminuric CKD patients with and without diabetes. Given the prognostic value of arterial stiffness in predicting CV and renal outcomes, these results are hypothesis-generating and call for larger, long-term studies to determine whether improvements in arterial stiffness independent of BP lowering translate into meaningful clinical benefits.
