---
type: RCT
language: en
status: reviewed
extracted_by: api
authors:
- Kaciroti N
- Levy PD
- Jamerson KA
- Brook RD
tags: []
title:
  zh: null
  en: 'Antihypertensive Combinations Modify Cardiovascular Risk Factor Importance:
    A Machine Learning Analysis of the ACCOMPLISH Trial'
year: 2026
journal: Journal of clinical hypertension (Greenwich, Conn.)
pmid: '42130176'
doi: 10.1111/jch.70278
id: EV-RCT-2026-KACIROTI-003
study_type: COHORT
risk_of_bias:
  tool: RoB2
  overall: some_concerns
grade:
  level: low
---




## English Abstract

Results from the ACCOMPLISH (Avoiding Cardiovascular Events through COMbination Therapy in Patients LIving with Systolic Hypertension) trial suggest that combining benazepril with amlodipine, rather than hydrochlorothiazide, provides superior cardiovascular protection potentially in a BP‐independent manner. We employed random survival forest, a powerful machine learning approach, to compare the relative importance of risk factors (i.e., variable importance factor (VIF)), focusing on in‐trial BP control for predicting the primary composite cardiovascular outcome in the 2 treatment limbs. Among the 6 risk factors with significantly different VIFs between treatments, all were lower under benazepril/amlodipine combination. The VIF for achieved systolic BP at 6‐months was 35% lower in the benazepril/amlodipine (0.082) versus the benazepril/hydrochlorothiazide (0.126) limb. The fact that in‐trial BP control was less important for preventing cardiovascular events during benazepril/amlodipine treatment provides novel support for our contention that this combination regimen provides a degree of clinically‐relevant cardio‐protective actions in a BP‐independent manner.

## 背景 / Background

Most patients with hypertension require multiple medications to achieve blood pressure (BP) control [1, 2]. As such, single‐pill combination medications (SPCMs) have become a mainstay of contemporary hypertension treatment [1, 2]. However, few studies have evaluated the optimal approach to combination therapy. In the ACCOMPLISH (Avoiding Cardiovascular Events through COMbination Therapy in Patients LIving with Systolic Hypertension) trial, patients randomized to a SPCM containing benazepril, a renin angiotensin system inhibitor (RASi), plus amlodipine, a long‐acting dihydropyridine calcium channel blocker (CCB) received a 20% reduction in cardiovascular events compared to those taking benazepril combined with hydrochlorothiazide [3, 4]. It was later shown that most of this risk reduction was not mediated by differences in 24‐h ambulatory BP or time‐averaged systolic BP control during the trial but by treatment with benazepril/amlodipine per se—suggestive of direct cardio‐protective actions beyond BP‐lowering [5, 6]. Given these findings and other potential advantages, we have contended that combination RASi/CCB therapy should be first‐line drug treatment from most patients with hypertension [1, 4].

Despite the well‐established benefits of BP‐lowering, treated hypertensive patients remain at elevated cardiovascular risk compared to naturally normotensive individuals [6]. The degree of residual risk has been related to many variables including traditional risk factors, comorbidities, underlying organ damage, as well as the duration and severity of hypertension [7, 8]. However, prior research has largely employed conventional statistical analyses (e.g., Cox proportional hazards models) with well‐established limitations [9, 10]. To better elucidate the factors responsible for cardiovascular events (i.e., explain residual risk) in treated hypertensive patients, including their relative ranking of importance, we aimed to employ a novel machine learning approach, random survival forest (RSF), to analyze the results of the ACCOMPLISH trial. RSF is a powerful non‐parametric machine learning method that offers a number of advantages over standard statistical methods by capturing complex nonlinear relationships, multiple potential interactions between variables and the outcome and can provide superior overall predictive power for the model [9, 10]. We hypothesized that differences in risk factor importance between treatments, in particular the degree of in‐trial BP‐lowering, might help further explain the reported benefits of benazepril/amlodipine therapy.

## 方法 / Methods

Institutional review board approval was not required as this study was a post hoc statistical analysis of de‐identified data from the ACCOMPLISH trial.

We used RSF to predict the time to primary composite endpoint (death from cardiovascular causes, myocardial infarction, stroke, hospitalization for angina, cardiac resuscitation and coronary revascularization) in the ACCOMPLISH trial (n = 11,506). We implemented a landmark analysis at 6 months (n = 10,187) to capture the treatment effect on the BP during the dose‐adjustment period (i.e., first 6 months of the trial) and consecutively its effect on the primary outcome starting afterward (Figure 1). Factors considered in the model were baseline variables as shown in Table 1, as well as several collected during the trial including achieved systolic BP at 6‐months, cumulative systolic BP reduction and residual BP variability during the first 6 months (determined as previously described) [5] and the number of add‐on BP medications. We fitted the RSF using randomForestSRC package in R software version 4.5.2 (R Core Team, 2026), stratified by treatment group to assess the modifying effect of treatment on the effect of predictor variables on the outcome (i.e., the variable importance factor (VIF)) [11]. VIF shows the percent increase in mean square error attributed to a specific risk factor. Higher VIF indicates greater predictive power for a specific variable, or stronger risk associated with the primary outcome. Lower VIF indicates lower risk (i.e., the specific variable has low or reduced predicted power for the outcome).

Variable importance by random survival forest for predicting the primary composite cardiovascular outcome for both treatment groups ranked by the benazepril/hydrochlorothiazide limb. All variables were measured at study baseline except for number of add‐on medications, SBP at 6‐months, cumulative SBP and residual systolic BPV which were determined over the first 6 months of the trial. Y‐axis represents variable importance factor (VIF) which is the increase in prediction error for the outcome attributed to a specific predictor (% increase in means square error). *VIFs that are statistically significantly different between treatment limbs (p < 0.05). †VIF with a p‐value between 0.1 and 0.05. B + A, benazepril/amlodipine treatment; B + H, benazepril/hydrochlorothiazide treatment; BMI, body mass index; BPV, blood pressure variability; CVD, any preexisting cardiovascular disease; eGFR, estimated glomerular filtration rate; HDL‐C, high‐density lipoprotein cholesterol; LVH, left ventricular hypertrophy; meds, medications; SBP, systolic blood pressure.

Patient characteristics.

Abbreviations: A, amlodipine; B, benazepril; BP, blood pressure; BPM, beats per minute; CVD, presence of any pre‐existing cardiovascular disease; H, hydrochlorothiazide; HDL, high‐density lipoprotein; LVH, left ventricular hypertrophy; SD, standard deviation.

Cumulative SBP and Residual SBP are standardized as described previously [5].

To minimize model overfitting, we used the following tuning parameters for RSF: 1500 trees and node size of 250, the number of splits was set at 3, and the number of variables selected at each split point was set at 3. To assess the modifying effect of benazepril/amlodipine therapy, variables were ranked by VIF for predicting cardiovascular events in the benazepril/hydrochlorothiazide limb. Bootstrapping was performed using the subsample package in R with subsample B = 1000 to obtain VIF, corresponding 95% confidence intervals (CI) and statistical significance (defined as p < 0.05).

## 结果 / Results

Patient characteristics are provided in Table 1. For the benazepril/amlodipine group, the Brier score was 0.055 showing a good model fit with Harrell's C‐index for the training (group of interest) and the remaining group data sets being 0.721 (95%CI 0.709, 0.738) and 0.652 (95%CI 0.643, 0.659), respectively. These values were similar, Brier score of 0.049, and Harrell's C‐Index 0.716 (95%CI 0.703, 0.732) and 0.649 (95%CI 0.641, 0.657), for the benazepril/hydrochlorothiazide limb. While the C‐indices were good (>0.7) for the training data (regardless of the treatment group), such models performed less well when applied to the other group, C‐indices < 0.7. This indicates that the RSF models derived based on each treatment group differ (i.e., the model trained on B+A group data perform poorly when applied to B+H group data and vice versa). Specifically, among the 6 risk factors with significantly different VIFs between treatments, all were lower under benazepril/amlodipine combination (Figure 1). The VIF for achieved systolic BP at 6‐months during the trial was 35% lower in the benazepril/amlodipine (0.082) versus the benazepril/hydrochlorothiazide (0.126) limb. The VIF of on‐treatment cumulative systolic BP reduction was marginally significant (p<0.07) and trended lower under benazepril/amlodipine (−35%), whereas residual BPV did not. However, the relative importance (i.e., absolute VIFs) for residual BPV were substantially lower than for systolic BP at 6‐months.

## 讨论 / Discussion

Our study shows that worse pre‐trial health status (preexisting cardiovascular disease, older age) and hypertension severity (more add‐on medications required to achieve BP control in the trial) rank as the most important factors for predicting cardiovascular events while on antihypertensive treatment. Other leading variables (VIFs >10%) were creatinine, glucose, heart rate, and a metric of BP control during the trial (achieved systolic BP at 6‐months). While these findings accord with studies using traditional statistical methods, our approach was novel as few analyses have employed machine learning to evaluate the results of a hypertension clinical trial. As far as we are aware, no study has specifically evaluated the relative importance of factors for predicting cardiovascular events [9, 10].

We showed for the first time that different combination regimens modify the importance and relative ranking of risk factors for cardiovascular events. Among the 6 risk factors that significantly differed between treatments, all showed lower VIFs under benazepril/amlodipine combination. Of particular interest, the VIF of achieved systolic BP at 6‐months was significantly lower by 35% under benazepril/amlodipine, whereas that for cumulative systolic BP trended lower by 35%. This may help to explain the primary ACCOMPLISH study results whereby cardiovascular events were significantly reduced by benazepril/amlodipine despite near identical BP levels during the trial in both treatment limbs [5, 6]. The fact that a powerful machine learning approach showed that in‐trial BP levels were rendered less important under benazepril/amlodipine treatment provides additional support for our belief that this combination regimen provides a degree of clinically‐relevant cardio‐protective actions in a BP‐independent manner [4]. Any 1 or many possible pleiotropic effects could in theory play a role as we previously outlined—improved endothelial function, reduced aortic stiffness, decreased atherosclerosis progression or vulnerability, anti‐inflammatory or oxidant actions. It is also plausible that relatively unfavorable actions of hydrochlorothiazide (e.g., electrolyte, glucose, and lipid changes) might be additionally responsible in part [4].

We acknowledge several limitations including the fact this this study was a post hoc analysis of a previously completed clinical trial. The results represent changes in predictive associations only and causality cannot be directly inferred. The specific BP‐independent protective action(s) responsible for the clinical benefit of benazepril/amlodipine combination therapy also remain speculative.

## 结论 / Conclusion

Two or more antihypertensive drugs are required to control BP in most patients [1, 2]. This novel analysis shows that BP control during treatment is less important for predicting cardiovascular events when benazepril is combined with amlodipine versus hydrochlorothiazide, supporting that BP‐independent benefits (e.g., pleiotropic actions) may explain the more favorable clinical outcomes of this combination regimen in the ACCOMPLISH trial. Taken together, these findings support our contention, and the conclusions of a recent scientific statement by the American Heart Association, that a SPCM incorporating a RASi plus long‐acting dihydropyridine CCB should be the preferred initial drug treatment for hypertension in most patients [1, 4].
