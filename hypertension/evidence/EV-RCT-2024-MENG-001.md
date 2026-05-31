---
type: RCT
language: en
status: reviewed
extracted_by: api+llm
authors:
- Meng Y
- Liu L
- Chen X
- Zhao L
- She H
- Zhang W
- Zhang J
- Qin X
- Li J
- Xu X
- Wang B
- Hou F
- Tang G
- Liao R
- Huo Y
- Li J
- Yang L
tags:
- hypertension
- retinopathy
- PWV
- microvascular
- macrovascular
- CSPPT
- cross-sectional
title:
  zh: null
  en: 'Associations between brachial‐ankle pulse wave velocity and hypertensive retinopathy
    in treated hypertensive adults: Results from the China Stroke Primary Prevention
    Trial (CSPPT)'
year: 2024
journal: Journal of clinical hypertension (Greenwich, Conn.)
pmid: '38683601'
doi: 10.1111/jch.14820
pico:
  population:
    condition: treated hypertension
    sample_size: 11279
  intervention:
    name: baPWV measurement
  comparison:
    name: no baPWV measurement
  outcomes:
    primary:
    - name: hypertensive retinopathy prevalence
      effect_size:
        metric: OR
        value: 1.05
        ci_low: 1.03
        ci_high: 1.07
        p: 0.001
    - name: highest vs lowest baPWV quartile
      effect_size:
        metric: OR
        value: 1.61
        ci_low: 1.37
        ci_high: 1.89
        p: 0.001
risk_of_bias:
  tool: RoB2
  overall: some_concerns
grade:
  level: moderate
id: EV-RCT-2024-MENG-001
study_type: COHORT
---



## English Abstract

Although the association between persistent hypertension and the compromise of both micro‐ and macro‐circulatory functions is well recognized, a significant gap in quantitative investigations exploring the interplay between microvascular and macrovascular injuries still exists. In this study, the authors looked into the relationship between brachial‐ankle pulse wave velocity (baPWV) and hypertensive retinopathy in treated hypertensive adults. The authors conducted a cross‐sectional study of treated hypertensive patients with the last follow‐up data from the China Stoke Primary Prevention Trial (CSPPT) in 2013. With the use of PWV/ABI instruments, baPWV was automatically measured. The Keith‐Wagener‐Barker classification was used to determine the diagnosis of hypertensive retinopathy. The odds ratio (OR) and 95% confidence interval (CI) for the connection between baPWV and hypertensive retinopathy were determined using multivariable logistic regression models. The OR curves were created using a multivariable‐adjusted restricted cubic spline model to investigate any potential non‐linear dose‐response relationships between baPWV and hypertensive retinopathy. A total of 8514 (75.5%) of 11,279 participants were diagnosed with hypertensive retinopathy. The prevalence of hypertensive retinopathy increased from the bottom quartile of baPWV to the top quartile: quartile 1: 70.7%, quartile 2: 76.1%, quartile 3: 76.7%, quartile 4: 78.4%. After adjusting for potential confounders, baPWV was positively associated with hypertensive retinopathy (OR = 1.05, 95% CI, 1.03–1.07, p < .001). Compared to those in the lowest baPWV quartile, those in the highest baPWV quartile had an odds ratio for hypertensive retinopathy of 1.61 (OR = 1.61, 95% CI: 1.37–1.89, p < .001). Two‐piece‐wise logistic regression model demonstrated a nonlinear relationship between baPWV and hypertensive retinopathy with an inflection point of 17.1 m/s above which the effect was saturated
.

## 背景 / Background

It has been proposed that hypertensive retinopathy is a key indicator of hypertensive target‐organ damage.
1
 The condition of systemic microcirculation is frequently evaluated using the retinal vascular arteries, the only vascular system in the human body that can be directly observed. According to numerous research, retinal microvascular abnormalities (RMAs) can be utilized to forecast the likelihood of developing cardiovascular and cerebrovascular diseases.
2

PWV, a metric denoting the rate at which pressure waves travel through arteries, is recognized as a crucial indicator of arterial stiffness. This measurement holds significant importance as it functions as an autonomous predictor for cardiovascular morbidity, encompassing various adverse cardiac events, and is also associated with all‐cause mortality.
3
 Its independent predictive capability regarding adverse cardiovascular events and mortality highlights its clinical relevance in assessing and prognosticating cardiovascular health. In a meta‐analysis, it was found that for every 1 m/s increase in baPWV, the incidence of cardiovascular and cerebrovascular events, as well as all‐cause mortality, increased by 12%, 13%, and 6%, respectively.
4

Previous studies have substantiated the close correlation between hypertensive retinopathy and elevated risks of all‐cause mortality as well as clinical events related to cardiovascular disease (CVD), encompassing conditions like coronary heart disease, heart failure, and stroke. These findings potentially suggest the existence of shared risk factors or underlying mechanisms that contribute to both micro‐ and macro‐vascular complications stemming from hypertension.
5
, 
6
, 
7
 Many population‐based and cross‐sectional epidemiological investigations have revealed a substantial correlation between elevated PWV and the occurrence of microvascular complications, notably including diabetic retinopathy.
8
, 
9
 However, there is currently a lack of large‐scale epidemiological studies investigating the correlation between PWV and hypertensive retinopathy.

Our research therefore attempts to evaluate the relationship between hypertensive retinopathy and baPWV and investigate the potential impact modifiers using information obtained from the last follow‐up of the CSPPT.
10

## 方法 / Methods

The CSPPT (Clinical Trials. gov identifier: NCT00794885), a significant multi‐community, randomized, double‐blind, and actively controlled trial carried out from May 19, 2008 to August 24, 2013, formed the basis for the design of the current investigation. This study has already been described in detail/10 In the CSPPT, a total of 20,702 participants from rural China, aged 45–75, who had primary hypertension (SBP ≥ 140 mmHg or DBP ≥ 90 mmHg, or who were currently receiving antihypertensive medication) were enrolled. Among a total of 20,702 Chinese hypertensive patients without significant cardiovascular illnesses, the CSPPT found that enalapril with folic acid is more effective at lowering the risk of first stroke than enalapril alone after a median of 4.5 years of follow‐up.
10
 This research protocol adhered to the Helsinki Declaration, received approval from the Ethics Committee of the Biomedical Research Institute at Anhui Medical University (FWA Assurance Number FWA00001263) and got each participant's signed informed permission before collecting any data.

Our current study was a cross‐sectional research design that utilizes data obtained from the final follow‐up of the CSPPT. After excluding patients with missing or low‐quality fundus photographs (n = 7562), missing baPWV data (n = 1494), ankle brachial index (ABI) < 0.9 (n = 357), a total of 11,279 individuals were analyzed (Figure 1).

Study flow chart.

In the case of each patient, high‐quality, macular‐focused fundus photographs were acquired with three nonmydriatic fundus cameras (Kowa Nonmyd 7; Canon CR‐2 AF; Topcon TRC‐NW8) with the patients' pupils in a constricted state. Each image was evaluated separately by four highly qualified, double‐blinded ophthalmologists who were well‐trained and had their consistency checked before the study began. The four ophthalmologists independently assessed their fundus photographs, and consistency was evaluated. In cases of poor consistency, additional training was conducted, controversial photographs were discussed, and the consistency test was repeated with another set of 60 patients. Checks for consistency (kappa value, 0.71–0.95) demonstrate the accuracy of our result.
11
 Hypertensive retinopathy was classified into grades 1−4 according to the Keith‐Wagener‐Barker classification (for details of classification see
12
 Table 1), and these four grades were merged for statistical analysis

The Keith–Wagener–Barker classification system for hypertensive retinopathy.

As previously described,
13
, 
14
 PWV/ABI devices (BP‐203RPE; OmronColin) were used by qualified staff to automatically measure baPWV. Bilateral baPWV measurements were made twice, with the highest reading from each side being chosen for analysis.

After a minimum rest period of 10 min, three seated blood pressure measurements, spaced at least 2 min apart, were obtained using a mercury sphygmomanometer on the same arm. The statistical analysis utilized the average of the three measurements for systolic blood pressure (SBP) and diastolic blood pressure (DBP).

The laboratory exams were conducted at the Core Laboratory of the National Clinical Research Center for Kidney Disease at Nanfang Hospital of Guangzhou, China. Each individual was fasted for 12–15 h before having venous blood samples taken.

After serum or plasma samples were collected, they were separated in less than 30 min and kept for long‐term storage at −70°C. All blood samples were analyzed for creatinine, lipids, total homocysteine (tHcy), blood urea nitrogen, alkaline phosphatase, uric acid, and glucose using an automatic clinical analyzer (Beckman Coulter, California, USA). The TaqMan assay was employed to detect methylenetetrahydrofolate reductase (MTHFR)‐defined all abbreviations C677T (rs1801133) polymorphisms, and this analysis was conducted on the ABI Prism 7900HT Sequence Detection System from Life Technologies, based in Carlsbad, California.

All participants completed a comprehensive standardized questionnaire, which assessed demographic, nutritional, lifestyle, and medical parameters.
15

Whereas continuous data were shown as means with matching standard deviations (SDs), categorical variables were displayed as percentages. The analysis included stratification, interaction testing, and covariate screening. Binary logistic regression analyses were employed to investigate the relationships between hypertensive retinopathy (represented as a binary variable) and baPWV. Hypertensive retinopathy was assessed as a binary categorical variable, with the amalgamation of participants ranging from grade 1 to grade 4 for the analysis. BaPWV was assessed as both a continuous variable and a categorical variable divided into quartiles (quartile 1: 9.02–14.74 m/s; quartile 2: 14.75–16.63 m/s; quartile 3: 16.64–18.92 m/s; quartile 4: ≥18.93 m/s). The findings were presented in the form of odds OR and 95% CI, with adjustments made for key variables. Interaction and subgroup analyses were carried out to see if the association between baPWV and hypertensive retinopathy was consistent across populations. Logistic regression models and likelihood ratio tests were utilized to evaluate heterogeneity and interactions among the subgroups, respectively. Covariables that were considered clinically relevant or that showed a univariate relationship with outcome were entered into a multivariate logistic regression adjusted model.

In addition, we examined the threshold of the relationship between hypertensive retinopathy and baPWV using a two‐piece‐wise logistic regression model with smoothing in the adjusted model. Inflection spots were found using the bootstrap resampling approach and the likelihood‐ratio test.

The statistical software program R 3.4.3 (R Foundation for Statistical Computing, Vienna, Austria) and Free Statistics software version 1.8 were used for all analyses. p < .05 was regarded as statistically significant in the two‐tailed analysis.

## 结果 / Results

There were 11,279 participants in the current study, as indicated by the flow chart (Figure 1). Table 2 displays the demographic features of the study participants categorized according to baPWV quartiles. The average age was 63.8 ± 7.2 years, with 4520 (40.1%) being male. Hypertensive retinopathy was observed in 8514 (75.5%) of the participants, with a prevalence of 77.6% among males and 74.1% among females.

Basic characteristics of study participants.

Note: For continuous variables, values are presented as the mean (standard deviation). For categorical variables, values are presented as frequencies.

Abbreviations: ABI, ankle brachial index; BMI, body mass index; DBP, diastolic blood pressure; HDL‐C, high‐density lipoprotein; MTHFR, methylenetetrahydrofolate reductase; SBP, systolic blood pressure.

The prevalence of hypertensive retinopathy exhibited an ascending trend across the baPWV quartiles: quartile 1: 70.7%, quartile 2: 76.1%, quartile 3: 76.7%, and quartile 4: 78.4%. Age, heart rate, SBP, DBP, diabetes status, fasting glucose, and uric acid demonstrated an upward trajectory from the lowest quartile of baPWV to the highest quartile. No significant differences in high‐density lipoprotein cholesterol (HDL‐c), creatinine, treatment group, MTHFR C677T genotypes, smoking status, and alcohol consumption were found among baPWV quartiles.

The univariate analysis revealed associations between hypertensive retinopathy and variables such as sex, SBP, DBP, baPWV, total cholesterol, HDL‐c, creatinine, uric acid, center, MTHFR C677T TT genotype, and current alcohol consumption (Table S1).

Multivariable logistic regression analyses were employed to evaluate the relationships between baPWV and hypertensive retinopathy (Table 3). BaPWV was positively correlated with hypertensive retinopathy in the unadjusted model (OR = 1.04, 95% CI, 1.03–1.06, p < .001). The connection held significance even after accounting for all possible confounders (OR = 1.05, 95% CI, 1.03–1.07, p < .001).

Prevalence of hypertensive retinopathy and the association between baPWV and hypertensive retinopathy.

Abbreviations: CI, confidence interval; HR, hypertensive retinopath.

Adjusted for age, sex, BMI, heart rate, study center, treatment group, SBP, DBP, MTHFR C677T genotypes, smoking and drinking consumption status, total cholesterol, triglycerides, fasting blood glucose, serum creatinine, uric acid, folate, and total homocysteine.

After controlling for possible variables, a significant positive correlation between baPWV and hypertensive retinopathy was found when the data was examined using quartiles. The adjusted OR values for baPWV and hypertensive retinopathy in Q2 (14.75–16.63 m/s), Q3 (16.64–18.92 m/s), and Q4 (≥18.93 m/s) were 1.37 (95% CI: 1.20–1.56, p < .001), 1.43 (95% CI: 1.24–1.64, p < .001), and 1.61 (95% CI: 1.37–1.89, p < .001) (Table 3), respectively, in comparison to participants with lower baPWV Q1 (9.02–14.74 m/s). Trend p < .001.

To evaluate the relationship between hypertensive retinopathy and baPWV in different subgroups, stratified analyses were carried out (Figure 2). Younger individuals (<60 years, OR = 1.10, 95% CI, 1.05–1.14; vs. ≥60 years, OR = 1.04, 95% CI, 1.02–1.06; p for interaction = .002) showed a greater correlation between baPWV and hypertensive retinopathy. The relationship between baPWV and hypertensive retinopathy was not substantially affected by any of the other factors, including sex, BMI, SBP, DBP, diabetes, tHcy, treatment group, or MTHFR C677T genotype.

Association between baPWV and hypertensive retinopathy.*Adjusted for age, sex, BMI, heart rate, study center, treatment group, SBP, DBP, MTHFR C677T genotypes, smoking and drinking consumption status, total cholesterol, triglycerides, fasting blood glucose, serum creatinine, uric acid, folate, and total homocysteine.

After making adjustments for several covariates, we detected a non‐linear dose‐response correlation between baPWV and hypertensive retinopathy (Figure 3). We found that the threshold for baPWV in our investigation was 17.1 m/s using a two‐piecewise linear regression model (Table 4). The adjusted OR for hypertensive retinopathy was 1.106 (95% CI, 1.055–1.159, p < .001) below the threshold, meaning that for every 1 m/s increase in baPWV was significantly associated with a 10.6% higher odds of hypertensive retinopathy. The computed dose‐response curve demonstrated a virtually horizontal pattern that was stable above the threshold (OR = 1.008, 95% CI, 0.974–1.042, p = .648; Table 4 and Figure 3).

Association between baPWV and hypertensive retinopathy odds ratio. Solid and dashed lines represent the predicted value and 95% confidence intervals. They were adjusted for age, sex, BMI, heart rate, study center, treatment group, SBP, DBP, MTHFR C677T genotypes, smoking and drinking consumption status, total cholesterol, triglycerides, fasting blood glucose, serum creatinine, uric acid, folate, and total homocysteine. Only 99% of the data is shown.

Threshold effect analysis of the relationship of baPWV with hypertensive retinopathy.

Notes: Adjusted for age, sex, BMI, heart rate, study center, treatment group, SBP, DBP, methylenetetrahydrofolate reductase C677T genotypes, smoking and drinking consumption status, total cholesterol, triglycerides, fasting blood glucose, serum creatinine, uric acid, folate, and total homocysteine. Only 99% of the data is displayed.

Abbreviations: CI, confidence interval; OR, odds ratio.

## 结论 / Conclusion

In summary, this cross‐sectional study identified a non‐linear correlation between baPWV and hypertensive retinopathy in Chinese adults receiving treatment for hypertension with an inflection point of 17.1 m/s above which the effect was saturated. The findings of this investigation serve to capture the interest of individuals concerning the relationship between microcirculation and macrocirculation. Furthermore, they suggest that the utilization of baPWV screening could be of significance in assessing the target organ damage among individuals with hypertension.
