---
type: RCT
language: en
status: reviewed
extracted_by: api+llm
authors:
- Zhang N
- Mei J
- Fan F
- Zhang Y
- Zhou Z
- Li J
tags:
- hypertension
- stroke prediction
- risk model
- blood pressure
- CSPPT
- TRIPOD
title:
  zh: null
  en: Posttreatment Blood Pressure as a Key Predictor in a 5‐Year Stroke Prediction
    Model
year: 2025
journal: Journal of clinical hypertension (Greenwich, Conn.)
pmid: '39821957'
doi: 10.1111/jch.14974
pico:
  population:
    condition: hypertension without major cardiovascular disease
    sample_size: 20702
  intervention:
    name: enalapril-folic acid combination
  comparison:
    name: enalapril alone
  outcomes:
    primary:
    - name: 5-year stroke risk
      effect_size:
        metric: C-index
        value: 0.74
        ci_low: null
        ci_high: null
        p: null
risk_of_bias:
  tool: RoB2
  overall: low
grade:
  level: moderate
id: EV-RCT-2025-ZHANG-003
study_type: RCT
---



## English Abstract

Evidence suggests that approximately 63.0%–84.2% of stroke survivors have hypertension, yet there is currently no stroke prediction tool specifically designed for individuals with hypertension. Using data from 20 702 hypertensive patients from the China Stroke Primary Prevention Trial (CSPPT), we developed a 5‐year stroke risk prediction model. This prospective study collected treated blood pressure every 3 months, resulting in 22 measurements over the study period. The model was internally validated using bootstrap resampling, and its predictive performance was assessed with the C‐index and calibration curves. We also developed a random forest model to rank the variable importance. The 5‐year stroke risk prediction model for hypertensive individuals includes 10 risk factors, ranked by importance as follows: average systolic blood pressure during treatment, age, average diastolic blood pressure during treatment, baseline systolic blood pressure, history of diabetes, baseline total cholesterol level, baseline folate level, self‐reported stress, smoking, and folic acid supplementation or not. The C statistic of the equation was 0.74 and there were no significant differences by gender or treatment group. Calibration plots indicate good internal consistency between observed and predicted 5‐year stroke risk. We also developed an online calculator to assist clinicians and patients (https://zhouziyi.shinyapps.io/CSPPT/). Our study indicates that for patients with hypertension, long‐term posttreatment blood pressure is the primary predictor of stroke risk.

Trial Registration: The CSPPT (clinicaltrials.gov Identifier: NCT00794885).

## 背景 / Background

Stroke remains a major global public health issue [1]. Evidence shows that by 2019, there were 101 million prevalent cases of stroke, and it was the second leading cause of death worldwide [2]. Over the past 30 years, the prevalence of stroke in China has increased by 36.6%, imposing a heavy disease burden [3]. There is an urgent need for effective prevention strategies to address the growing stroke burden [2]. High systolic blood pressure (BP) continues to be the leading modifiable risk factor for premature cardiovascular death, and optimizing antihypertensive treatment is cost‐effective [4]. Epidemiological evidence indicates that approximately 63.0%–84.2% of stroke survivors had pre‐existing hypertension [5]. However, there is currently no stroke prediction tool specifically designed for this group.

In 1991, Wolf et al. developed the first stroke risk prediction equation, known as the Framingham Stroke Risk Profile (FSRP) [6]. In this tool, baseline systolic BP was a key factor. Over the past 30 years, stroke risk prediction equations have been continuously refined and developed across various populations [7, 8, 9, 10]. However, these models typically only consider baseline BP levels or whether antihypertensive treatment is being used, overlooking the long‐term BP control and medication adherence in hypertensive patients [11]. To address this gap, the FSRP attempted to include a composite variable to roughly estimate the impact of blood pressure control on stroke risk [9]. In practice, traditional cohort studies face challenges in accurately determining medication adherence and consistently collecting long‐term posttreatment BP data in patients with hypertension [11, 12].

This study aims to address several critical scientific questions. First, given the elevated stroke risk and specific characteristics of patients with hypertension, there is a need to develop a stroke prediction model tailored to this population [13]. Second, long‐term post‐treatment BP levels may provide a more accurate reflection of a hypertensive patient's true status and align more closely with clinical practice. However, current stroke prediction models have yet to incorporate this parameter. Third, existing stroke prediction equations, including the Revised FSRP, are more applicable to white populations. Evidence suggests that the Revised FSRP may underestimate stroke events by 40.2% in men and 53.3% in women [7]. This study used data from the China Stroke Primary Prevention Trial (CSPPT). The CSPPT followed participants every three months over a 5‐year period, collecting 22 posttreatment blood pressure measurements in total [14]. Our goal is to use the CSPPT data to develop a stroke risk prediction model specifically tailored for the Chinese hypertensive population.

## 方法 / Methods

Our article adheres to the Transparent Reporting of a multivariable prediction model for Individual Prognosis or Diagnosis (TRIPOD) Statement. The parent study (CSPPT) received approval from the Ethics Committee of the Institute of Biomedicine, Anhui Medical University, Hefei, China. Written, informed consent was obtained from all participants. The data, analytical methods, and study materials supporting the findings of this study will be made available by the corresponding author upon reasonable request. Such requests will be subject to formal review and approval by the Ethics Committee of the Institute of Biomedicine, Anhui Medical University.

The rationale and study design for the CSPPT have been previously described in detail [14]. In brief, the CSPPT was a randomized, double‐blind, actively controlled trial conducted between May 2008 and August 2013 in 32 communities across Anhui and Jiangsu provinces in China. The study included a total of 20 702 adults with hypertension and no history of major cardiovascular disease (CVD).

Participants were randomly assigned to one of two groups: the enalapril‐folic acid group, which received a daily oral dose of one tablet containing 10 mg enalapril and 0.8 mg folic acid as a single pill combination; or the enalapril group, which received one tablet containing 10 mg enalapril only. Additionally, other classes of antihypertensive medications, primarily dihydropyridine calcium channel blockers and hydrochlorothiazide, could be prescribed concurrently if deemed necessary.

During the baseline enrollment, patients underwent a physical examination and completed an epidemiologic questionnaire where information on demographic characteristics, medical history, family history, dietary frequency, and lifestyle was collected.

Blood pressure was measured according to a standardized protocol and measurements were taken at baseline and during follow‐up. Blood pressure measurements were performed in a bright, quiet room at a comfortable temperature. Prior to blood pressure measurement, patients rested in a seated position for 10 min and were not allowed to drink coffee or tea. Blood pressure was measured using a mercury sphygmomanometer where three consecutive readings were obtained on the same arm, with an interval of at least 2 min between each measurement, according to the standardized protocol. Baseline blood pressure was determined as the average of the three blood pressure measurements on the same visit. Follow‐up blood pressure/posttreatment blood pressure measurements were taken every 3 months by qualified study staff, for a total of 22 measurements per participant throughout the follow‐up period. Posttreatment blood pressure was calculated as the average of all post‐baseline BP results up to the last visit before the occurrence of stroke, death, or the end of follow‐up for patients without events.

At the outset of the baseline investigation, a blood sample was collected from each participant. The MTHFR C677T (rs1801133) polymorphism was identified using the TaqMan assay on an ABI Prism 7900HT sequence detection system from Life Technologies. Serum folate and vitamin B12 levels were assessed through a chemiluminescent immunoassay performed by a commercial laboratory (New Industrial). Serum homocysteine, fasting lipids, and glucose levels were measured using automated clinical analyzers (Beckman Coulter) at the core laboratory of the National Clinical Research Center for Kidney Disease, located at Nanfang Hospital in Guangzhou, China.

The primary outcome was the occurrence of a first nonfatal or fatal stroke, encompassing both ischemic and hemorrhagic strokes, while excluding subarachnoid hemorrhages and silent strokes. It is essential to underline that all study outcomes underwent meticulous scrutiny and adjudication by an autonomous endpoint adjudication committee, adhering to standardized criteria.

Continuous variables were expressed as means ± standard deviations or medians (25th–75th percentiles), while categorical variables were presented as proportions. Cox regression analyses were employed to ascertain hazard ratios (HRs), accompanied by their corresponding 95% confidence intervals (CIs) or p values. This methodological approach was integral to the development of a 5‐year stroke risk equation. Prior to this stage, we conducted an essential step in the process by employing the Least Absolute Shrinkage and Selection Operator (LASSO) regression to identify the optimal number of variables. Secondly, a total of 56 variables depicting information on demographic characteristics, disease history, biochemical indicators, dietary habits, and lifestyle were added into the model and stepwise regression was used for variable selection and modeling (Table S1). The prediction ability of the model was evaluated by the C‐index. The 95% CIs were obtained by the bootstrap resampling method. The random forest method was used to rank the importance of the filtered variables.

For internal validation, the predictive accuracy of the model was assessed using the bootstrap resampling method, a well‐established approach for evaluating model performance and generalizability. A total of 1000 bootstrap samples were generated by resampling with replacement from the original dataset, preserving the sample size and allowing duplicate observations. The model was refitted to each bootstrap sample, and its predictive accuracy was evaluated either on the out‐of‐bag samples or the original dataset. Key performance metrics, including discrimination and calibration, were computed for each iteration and averaged across the 1000 resamples to obtain robust estimates. Calibration plots were constructed to visually assess the agreement between predicted and observed outcomes, illustrating the model's performance across the risk spectrum.

Lifetime stroke risk is defined as the cumulative risk from the baseline age of the study participants to the endpoint age (set at 75 years). We also developed the Fine and Gray model, which accounts for the competing risk of non‐stroke deaths, to estimate lifetime stroke risk. The model assumes that competing risks are not independent and allows for the simultaneous estimation of stroke risk in the presence of competing risks. The variables selected for the 5‐year risk equations were included directly in the lifetime risk model. The cumulative incidence function for stroke, adjusted for competing risks, can be determined. A 2‐tailed p < 0.05 was considered to be statistically significant in all analyses. R software, version 4.1.2 (http://www.R‐project.org/), was used for all statistical analyses.

## 结果 / Results

Table 1 presents the characteristics of stroke risk factors in the total population by sex. The mean age of all participants was 60 years (SD, 7.5 years) and 41% were male. The average baseline systolic blood pressure was 166.9 mmHg (SD, 20.4 mmHg). During a mean follow‐up period of 4.5 years, the mean treated systolic blood pressure for all hypertensive patients was 139.8 mmHg (SD, 11.4 mmHg) and the mean treated diastolic blood pressure was 83.1 mmHg (SD, 7.7 mmHg). During follow‐up, there were 637 strokes, for a stroke rate of 3.1%. Compared with males, females were younger, had higher baseline systolic blood pressure, higher total cholesterol, a higher proportion of diabetes mellitus, and a greater proportion of high, self‐reported stress. The male population had higher rates of current smoking and higher rates of former smoking.

Characteristics of all participants in the China Stroke Primary Prevention Trial.

We first determined the optimal number of variables for the stroke prediction equations to be 10, based on the results of the LASSO regression analysis (Figure S1). Based on the results of the stepwise regression analysis (Table S2), we constructed 5‐year stroke risk equations that included 10 key factors: age, baseline systolic blood pressure, systolic, and diastolic blood pressure during treatment, smoking status, diabetes mellitus, total cholesterol level, folic acid level, folic acid supplementation, and stress status (Table 2). The results were generally consistent when stratified by sex (Table S3). We also examined multicollinearity, and the results showed that the generalized variance‐inflation factor (GVIF) values for all variables were less than 3, indicating no multicollinearity (Table S4).

Multivariable hazard ratios: Evaluating the association between risk factors and 5‐year stroke incidence.

Note: Harrell's C‐index for the 5‐year stroke model was 0.74. The standard deviation values for each continuous variable are as follows: age (SD = 7.5 y), baseline SBP (SD = 20.4 mmHg), treatment SBP (SD = 11.4 mmHg), treatment DBP (SD = 7.7 mmHg), total cholesterol (SD = 1.2 mmol/L), and baseline folate (SD = 3.9 ng/mL).

Abbreviations: DBP, diastolic blood pressure; HR, hazard ratio; SBP, systolic blood pressure; SD, standard deviation.

Figure 1 shows a nomogram of 3‐ and 5‐year stroke prediction equations for the hypertensive study population. As shown in the figure, the variables in the equations correspond to a point, and the total points are obtained by summing the points of the ten variables. By making a vertical line at the total points, the 3‐year stroke risk and the 5‐year stroke risk of the hypertensive patients can then be calculated. We also developed a dynamic nomogram for stroke prediction (https://zhouziyi.shinyapps.io/CSPPT/) in parallel for clinical reference, where the 5‐year stroke risk can be obtained by entering a patient's information for the 10 key variables.

Nomogram for predicting 3‐ and 5‐year incidence of stroke in hypertensive adults from rural China dynamic nomogram for stroke prediction: An illustrative guide from the CSPPT study—Explore online at https://zhouziyi.shinyapps.io/CSPPT/.

Our results show that the C statistic of the 5‐year stroke prediction equation was 0.74. A similar performance was also observed across sex, treatment group, and stroke type subgroups, and the C statistics all stabilized around 0.74 (Table S5). Calibration plots for 5‐year stroke risk equations are presented in Figure 2, with good internal consistency between observed and predicted 5‐year stroke risk. The results of the lifetime risk model in Table S6 show a C‐statistic of 0.72.

Calibration plots for 5‐year stroke risk equation in hypertensive individuals from China Hazard ratios using 1000 bootstrap resamplings are reported.

Variables identified by stepwise regression were also used to construct a random forest model (Figure 3). After parameter adjustment, the error rate of the model reached a stable point when ntree was set to 800 (Figure 3A). Figure 3B shows the results of the risk factor importance ranking, with mean systolic blood pressure during treatment, age, and mean diastolic blood pressure during treatment as the top three influences for the hypertensive population. The other risk factors were ranked accordingly as baseline systolic blood pressure, history of diabetes mellitus, baseline total cholesterol level, baseline folate level, self‐reported stress status, smoking, and folate supplementation status.

Randomized forest analysis of stroke risk: (A) Survival forest error rate; (B) Out‐of‐bag variable importance ranking. DBP = diastolic blood pressure; SBP = systolic blood pressure.

We established an equivalent model in our database based on the China‐PAR 10‐year stroke prediction model. Subsequently, we conducted a comparative analysis between our model and the China‐PAR model. The results revealed that, across both male and female populations, the 5‐year stroke prediction model of the CSPPT exhibited higher C‐values in comparison to the China‐PAR stroke model (Table S7). Moreover, the integrated discrimination improvement (IDI) value displayed a statistically significant enhancement of 2.5% and 2.7% in males and females, respectively.

## 讨论 / Discussion

This equation is the first stroke prediction model tailored for hypertensive individuals. The C‐statistic of the model was 0.74, demonstrating good internal consistency. In addition to the traditional factors included in previous equations, this model is the first to incorporate long‐term posttreatment BP, making it more relevant to clinical practice. We also developed an online calculator for easy use by clinicians and patients. Furthermore, we examined the effects of nutrition, lifestyle, and psychological factors on stroke, ultimately including self‐reported stress levels and folate status in the model.

Stroke risk equations for various populations have been developed and improved over the decades. In 1991, Wolf et al. developed the Framingham Stroke Risk Profile (FSRP) [6]. The stroke risk factors included age, systolic blood pressure, the use of antihypertensive therapy, diabetes mellitus, cigarette smoking, prior cardiovascular disease, and other vascular risk factors. In the last decade, stroke risk equations from Europe, the United States and China have been developed. In 2013, J. Hippisley‐Cox developed the QStroke risk algorithm using data provided by 451 general practices in England and Wales to predict ischemic stroke risk for patients in primary care without prior stroke or transient ischemic attack at baseline [10]. In addition to traditional risk factors, this equation identified the impact of nine categories of self‐assigned ethnicity (including White, Indian, Black Caribbean, Chinese, etc.) on stroke. To better predict stroke risk in the Framingham Heart Study and other cohorts, in 2017, Dufouil et al. used the most recent epoch‐specific risk factor prevalence and hazard ratios, to compute a revised version of the FSRP, demonstrating higher stroke predictive ability [8]. In 2019, Xing et al. utilized a Chinese population cohort to establish 10‐year and lifetime stroke risk equations, demonstrating good stroke predictive ability for those without atherosclerotic cardiovascular disease [7]. However, there are no stroke risk prediction models based on hypertensive populations.

The present study established the first stroke risk model for a population with hypertension. We ranked the importance of the ten selected variables, with systolic and diastolic BP during treatment emerging as the top two predictors, respectively. High‐quality evidence indicates that consistently lowering blood pressure to target levels over the long term is key to stroke prevention [13, 15]. Our findings contribute to a comprehensive assessment of the impact of long‐term blood pressure control on stroke risk. Previous study suggested that blood pressure control should be distinguished from the use of antihypertensive medication and considered as an independent risk factor in stroke risk assessment models. Agostino et al. attempted to create a new variable by combining baseline blood pressure levels with the use of antihypertensive medication to better assess the effectiveness of antihypertensive treatment [9]. The introduction of this new variable represents a significant methodological advance; however, the estimation of antihypertensive treatment effects remains imprecise and requires validation through real, long‐term posttreatment blood pressure data. The CSPPT study, a clinical trial of antihypertensive medication, followed up on post‐treatment blood pressure every three months and assessed patients' medication adherence, providing an accurate reflection of long‐term BP control in hypertensive patients. Our findings are consistent with previous research, indicating that long‐term post‐treatment BP, rather than simply the use of antihypertensive medication or baseline blood pressure levels, is the most critical factor influencing stroke risk. This result further underscores the importance of consistent, long‐term blood pressure management [11].

In addition to traditional risk factors, this study comprehensively examined the influence of nutrition, diet, exercise, and sleep on stroke risk. For the first time, folate status and self‐reported stress were also included in the model. Meta‐analysis results indicated that in Asia, folic acid supplementation significantly reduced stroke risk by 22%, consistent with our findings [16]. Supplementing with folic acid, a safe, low‐cost, and effective nutrient, may hold significant public health value in further reducing the residual risk of stroke in countries and regions with relative folate deficiency. The INTERSTROKE study indicates that increased stress levels are associated with a higher risk of stroke [17], with the greatest contributions from family (OR = 1.95, 95% CI: 1.77–2.15) and work‐related (OR = 2.70, 95% CI: 2.25–3.23) stress [18]. Meta‐analysis also confirmed that higher stress levels were associated with a 24% increase in ischemic stroke risk [19]. In our study, self‐reported high stress was associated with a 41% increased risk of stroke. We believe that timely psychological counseling and intervention are necessary for individuals at high risk of stroke.

This study has important clinical and public health implications. First, we developed the first stroke risk prediction model specifically tailored for patients with hypertension. As a high‐risk population for stroke, hypertensive patients have distinct characteristics that necessitate a targeted predictive tool [20]. Second, this model innovatively incorporates long‐term post‐treatment blood pressure, aligning more closely with clinical practice. A single blood pressure measurement cannot fully capture the stroke risk in hypertensive patients. Third, we created an online prediction tool to facilitate use by both clinicians and patients, as well as for educational purposes.

The present study has some limitations. First, due to the fact that traditional cohorts do not consistently collect post‐treatment blood pressure data in hypertensive populations, we were unable to identify a suitable cohort for external validation. However, internal validation using the bootstrap method yielded satisfactory results. Second, the participants in the CSPPT were hypertensive individuals aged 45–75 years, with major exclusion criteria including a history of physician‐diagnosed stroke, myocardial infarction, heart failure, coronary revascularization, or congenital heart disease. As a result, the model's predictive ability may be limited for secondary prevention populations. Third, the study population is from China, which may limit the generalizability of the results to other populations. Fourth, our study was unable to further define embolic stroke, and the risk may differ from that of other stroke types. Future studies could address this issue. Finally, the CSPPT study is a randomized controlled clinical trial, and the intervention may have influenced the model's predictive performance. Our findings still require validation in large cohorts.

## 结论 / Conclusion

This is the first well‐performing 5‐year stroke risk prediction model specifically developed for individuals with hypertension. Our study demonstrates that long‐term blood pressure management is the most significant factor influencing stroke risk in hypertensive patients.
