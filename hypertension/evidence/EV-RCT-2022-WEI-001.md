---
type: RCT
language: en
status: reviewed
extracted_by: api+llm
authors:
- Wei Y
- Ma H
- Xu B
- Wang Z
- He Q
- Liu L
- Zhou Z
- Song Y
- Chen P
- Li J
- Zhang Y
- Mao G
- Wang B
- Tang G
- Qin X
- Zhang H
- Xu X
- Huo Y
- Guo H
tags:
- vitamin K1
- vitamin D
- stroke
- hypertension
- vascular calcification
- case-control
- CSPPT
title:
  zh: null
  en: 'Joint Association of Low Vitamin K1 and D Status With First Stroke in General
    Hypertensive Adults: Results From the China Stroke Primary Prevention Trial (CSPPT)'
year: 2022
journal: Frontiers in neurology
pmid: '35645985'
doi: 10.3389/fneur.2022.881994
pico:
  population:
    condition: hypertension
    sample_size: 1208
  intervention:
    name: low vitamin K1 status
  comparison:
    name: high vitamin K1 status
  outcomes:
    primary:
    - name: first total stroke
      effect_size:
        metric: OR
        value: 0.58
        ci_low: 0.36
        ci_high: 0.91
        p: 0.02
    - name: first ischemic stroke
      effect_size:
        metric: OR
        value: 0.34
        ci_low: 0.17
        ci_high: 0.63
        p: 0.001
risk_of_bias:
  tool: RoB2
  overall: some_concerns
grade:
  level: low
id: EV-RCT-2022-WEI-001
study_type: CASE_CONTROL
---



## English Abstract

Vitamin K plays a role in preventing vascular calcification and may have a synergetic influence with vitamin D on cardiovascular health. However, whether this relationship applies to stroke, especially in a high-risk population of hypertensive individuals, remains unclear. The present study aims to study the joint association of low vitamin K1 and D status with first stroke in general hypertensive adults.

This study used a nested, case–control design with data from the China Stroke Primary Prevention Trial. The analysis included 604 first total stroke patients and 604 matched controls from a Chinese population with hypertension. Odds ratios (ORs) and 95% confidence intervals were calculated using conditional logistic regression.

There was a non-linear negative association between plasma vitamin K1 and the risk of first total stroke or ischemic stroke in the enalapril-only group. Compared to participants in vitamin K1 quartile 1, a significantly lower risk of total stroke (OR = 0.58, 95% CI: 0.36, 0.91, P = 0.020) or ischemic stroke (OR = 0.34, 95% CI: 0.17, 0.63, P < 0.001) was found in participants in vitamin K1 quartile 2-4 in the enalapril-only group. When further divided into four subgroups by 25(OH)D and vitamin K1, a significantly higher risk of total stroke or ischemic stroke was observed in participants with both low vitamin K1 and 25(OH)D compared to those with both high vitamin K1 and 25(OH)D in the enalapril-only group. No increased risk was observed in the groups low in one vitamin only.

Low concentrations of both vitamin K1 and 25(OH)D were associated with increased risk of stroke.

## 背景 / Background

Cardiovascular disease (CVD) is the primary cause of morbidity in the world, leading to more than 17 million deaths per year, with about 6.7 million deaths attributed to stroke (1). Ischemic stroke (IS), caused by the blockage of blood vessels to the brain, accounts for about 80% of the stroke population (2). Stroke is a multifactorial disease that is related to modifiable risk factors such as hypertension, diabetes, and nutrient deficiencies (3). Vitamin K1 is a fat-soluble vitamin mainly obtained from green leafy vegetables and is required for the activation of hepatic coagulation factors. Recent studies have shown that vitamin K1 also plays an important role in bone (4) and cardiovascular health (5). For example, vitamin K is responsible for activating vitamin K-dependent Gla-proteins in extrahepatic tissues, such as matrix Gla-protein (MGP), which has the function of inhibiting vascular calcification (6).

Observational studies and randomized controlled trials have shown that low serum vitamin K1 is significantly associated with coronary artery calcium progression, especially in hypertensive individuals (7, 8). A meta-analysis showed that the presence and severity of coronary artery calcification was related to stroke events during medium and long-term follow-up (9). However, the protective role of vitamin K1 in stroke has not been well-validated in observational studies or clinical trials. A previous study found no association between high dephosphorylated-uncarboxylated Matrix Gla-Protein (dp-ucMGP) levels, reflecting poor vitamin K status, and increased stroke risk in the general population (10). Prior observational studies have also been unable to identify an association between dietary vitamin K1 intake and overall risk of ischemic stroke (11, 12). However, a Mendelian randomization study indicated that a genetic predisposition to higher circulating vitamin K1 levels is associated with an increased risk of large artery atherosclerotic stroke (13). Overall, significant research gaps remain regarding low vitamin K status and stroke, especially among high-risk populations, such as people with hypertension.

Accumulating epidemiological evidence has found that low 25-Hydroxyvitamin D [25(OH)D] levels, which is the general marker of vitamin D status, to be associated with CVD risk factors and increased CVD risk (14). Vitamin D has a potent role in the regulation of the renin–angiotensin aldosterone system, as well as anti-inflammatory, antioxidative (14). It has been reported that 25(OH)D level was inversely related to stroke risk, with a non-linear dose response relationship (15). Previous studies have shown that vitamins D and K have a synergistic effect on cardiovascular health (16, 17). As noted previously, prospective studies of the association between blood concentrations of vitamin K1 and subsequent stroke are sparse, and additionally, the question remains whether a joint association exists between vitamins D and K1, and stroke. This case-control study aimed to investigate the association between plasma vitamin K1 concentrations and the risk of stroke in patients with hypertension, taking into account the possible influence of vitamin D status on this association.

## 方法 / Methods

This study population stems from the China Stroke Primary Prevention Trial (CSPPT) cohort of patients with hypertension. A detailed description of the CSPPT has been provided elsewhere (18). Briefly, CSPPT was a multi-community, randomized, double-blind clinical trial conducted from 2008 to 2013 with 20,702 adults in 32 communities in China. Eligible participants were men and women aged 45–75 years who had hypertension, defined as seated, resting systolic blood pressure (SBP) ≥140 mmHg or diastolic blood pressure (DBP) ≥90 mmHg or who had anti-hypertensive medication at baseline. The major exclusion criteria included history of physician-diagnosed stroke, myocardial infarction (MI), heart failure, post-coronary revascularization, and/or congenital heart disease, and/or current supplementation by folic acid, vitamin B12 or vitamin B6. Eligible participants were randomly assigned in a 1:1 ratio to two treatment group: enalapril-only group and enalapril-folic acid group. In the enalapril-only group, participants received a daily tablet containing 10 mg enalapril only. In the enalapril-folic acid group, participants received a daily tablet containing 10 mg enalapril and 0.8 mg folic acid. Concomitant use of other antihypertensive drugs (mainly calcium channel blockers or diuretics) was allowed during the trial periods, but not B-vitamins.

As shown in Supplementary Figure 1, after a median follow-up of 4.5 years, 637 patients had first stroke in the CSPPT. The present study used a 1:1 matched case–control design. Patients with first stroke were selected as cases (n = 635), excluding two cases that could not be matched to a control. Another 635 participants without stroke, matched by baseline age (±1 year), sex, treatment group and study site, served as controls. After excluding participants with missing 25(OH)D and vitamin K1 data, we obtained 604 stroke case-control pairs, of which 484 were ischemic stroke, 118 were hemorrhagic and 2 were undefined case-control pairs.

A venous blood sample was obtained from each study participant at baseline after overnight fasting. Blood samples were centrifuged and stored at −80°C until analysis. The plasma concentrations of 25(OH)D and vitamin K1 were analyzed to assess the vitamin D and K status of participants. Plasma vitamin K1, 25(OH)D3 and 25(OH)D2 were measured by liquid chromatography with tandem quadrupole mass spectrometry (LC-MS/MS) in a commercial lab (Beijing DIAN Medical Laboratory, China). Total 25(OH)D was used in all analyses and was calculated as the sum of 25(OH)D3 and 25(OH)D2. Season-adjusted vitamin D levels were calculated by adding the residuals from a linear regression model of 25(OH)D by season of blood draw to the overall mean value.

The stroke outcome in this study was a first non-fatal or fatal stroke (ischemic or hemorrhagic), excluding subarachnoid hemorrhage and silent stroke. All participants underwent brain CT and/or magnetic resonance imaging (MRI). The diagnosis of stroke and stroke subtypes was based on medical records and imaging data that were reviewed by at least two adjudicators who were senior stroke neurologists. Source data for all suspected stroke cases including medical records and imaging data as well as event report forms were submitted to the event adjudication committee for further verification. Stroke etiology in our study was identified by the ICD10 codes of diagnosis. The outcomes were total stroke (ICD9 430,431, 433,434 and 436 or ICD10 I60, I61, I63 and I64), ischemic stroke (ICD9 433 and 434 or ICD10 I63) and hemorrhagic stroke (ICD9 430 and 431 or ICD10 I60 and I61).

Information on age, sex, body mass index (BMI), smoking status, alcohol consumption and other demographic factors, was collected using a standardized questionnaire. Current smokers were defined as smoking at least 1 cigarette per day or smoking >18 packs for the past 12 months; ex-smokers were those who had not smoked in at least 12 months before enrollment, and all others were defined as never smokers. Current alcohol drinkers were defined as individuals who consumed ≥3 drinks per week over the past year; former drinkers were those who had quit drinking for more than 1 year, and all others were defined as never alcohol drinkers (19, 20). Fasting venous blood samples were also collected at enrollment and at the exit visit. Seated blood pressure was measured by trained research staff after participants had rested for 10 min. Baseline plasma fasting glucose, serum fasting lipids, homocysteine and fasting serum total calcium (arsenazo-III method) levels were measured using automatic clinical analyzers (Beckman Coulter). Serum folate levels were measured in a commercial laboratory using a chemiluminescent immunoassay (New Industrial). The MTHFRC677T (rs1801133) polymorphism of methylenetetrahydrofolate reductase (MTHFR), the main regulatory enzyme for folate metabolism, was detected using the Taq Man assay.

Normally distributed continuous variables were presented as mean ± standard deviation and compared using t-tests. Non-normally distributed continuous variables were presented as median (75th percentile−25th percentile) and compared using rank-sum tests. Categorical variables were presented as number (percentage) and were compared using chi-square tests. All covariates had <5% total missing data. Missing values of continuous variables were replaced by the median and missing values of categorical variables were replaced by a large proportion of values. Logarithmic transformation was performed to normalize the distribution of vitamin K1. Multivariate conditional logistic regression analysis was performed to evaluate the association between vitamin K1 and stroke. All of the potential confounders in the univariate analyses were included in a stepwise conditional logistic regression analysis as the adjustment variable-selection process. The inclusion criterion for the stepwise regression analysis was P = 0.3 and the elimination criterion was P = 0.2. The adjusted variables in the final model included: body mass index (BMI, kg/m2), baseline SBP (mmHg), time-averaged SBP and DBP, baseline fasting blood glucose (mmol/L), total cholesterol (mmol/L), triglycerides (mmol/L), serum folate (ng/mL), antihypertensive medication usage at baseline (yes vs. no), smoking status (ever vs. never) and antiplatelet drug usage at baseline (yes vs. no). Potential interactions were examined by including the interaction terms in the logistic regression models. A two tailed P < 0.05 was considered statistically significant in all analyses. R software, version 3.2.5 (http://www.R-project.org/) was used for all statistical analyses.

## 结果 / Results

Individuals with missing vitamin K1 and/or D data and unpaired cases or controls were excluded from the analysis. The final analyses included 604 total stroke cases matched with 604 controls (Supplementary Figure 1). A total of 672 (55.6%) participants were in the enalapril-only group and 536 (44.4%) participants were in the enalapril-folic acid group. The mean age of the study population was 62.2 years, and 46.9% were male. Baseline characteristics of total participants by case-control status and by treatment group are presented in Table 1. In the enalapril-only group, stroke cases had high total cholesterol and high blood pressure at baseline and during follow-up. In the enalapril-folic acid group, stroke cases had high body mass index and high blood pressure at baseline and during follow-up.

Characteristics of the participants by case-control status and by treatment groupa.

DBP, diastolic blood pressure; HDL-C, high-density lipoprotein cholesterol; MTHFR, methylenetetrahydrofolate reductase; SBP, systolic blood pressure; 25(OH)D, 25-hydroxyvitamin D.

Table 2 presents the results of the independent associations between vitamin K1 levels and the risk of stroke (total and subtypes) adjusted by potential confounding factors. For the total population, no significant results were seen between the risk of total stroke and its subtypes. The participants in the second, third and fourth quartiles of vitamin K1 showed a decreased odds of risk of ischemic stroke compared to those in quartile 1 in the unadjusted and adjusted models, although these associations did not reach statistical significance.

The relationship of baseline plasma vitamin K1 with the risk of stroke (total and subtypes)a.

CI, confidence interval; OR, odds ratio; Q1, quartile 1; Q2, quartile 2; Q3, quartile 3; Q4, quartile 4.

Conditional logistic regression models were used. Adjusted models included the following covariables: body mass index, baseline systolic blood pressure, time-averaged systolic blood pressure and diastolic blood pressure during treatment, baseline fasting blood glucose, total cholesterol, triglycerides, folate, antihypertensive medications, smoking status and antiplatelet drug usage at baseline.

Conditional logistic regression models were used. Adjusted models included the following covariables: time-averaged systolic blood pressure and diastolic blood pressure during treatment and antihypertensive treatment at baseline.

Subgroup analyses were performed based on the potential confounding factors (Supplementary Figures 2, 3). A significantly stronger inverse association between plasma vitamin K1 (quartile 2–4 vs. quartile 1) and total stroke risk or ischemic stroke risk was observed in the enalapril-only group, while the association was slightly positive for participants in the enalapril-folic acid group. The interaction was significant (P = 0.010 for total stroke and P = 0.024 for ischemic stroke). Moreover, a trend of lower risk of total stroke or ischemic stroke with higher concentrations of vitamin K1 was observed in participants with serum calcium levels ≥9.7 mg/dL but not in participants with low serum calcium levels. Tests for interaction were significant (P = 0.022 for total stroke and P = 0.046 for ischemic stroke).

Given that folic acid treatment might affect the association between vitamin K1 and stroke risk, the possible effect of treatment group on the vitamin K1—first stroke association was further investigated. Overall, there was a non-linear, negative association between plasma vitamin K1 and the risk of first total stroke or ischemic stroke in the enalapril-only group (Table 3). Compared to participants with vitamin K1 in quartile 1, a significantly lower risk of total stroke (OR = 0.58, 95% CI: 0.36, 0.91, P = 0.020) or ischemic stroke (OR = 0.34, 95% CI: 0.17, 0.63, P < 0.001) was found in participants with vitamin K1 in quartile 2–4 in the enalapril-only group. However, in the enalapril-folic acid group, a significantly higher first total stroke risk, but not ischemic stroke risk, was found in participants with vitamin K1 in quartile 2–4 (OR = 2.43; 95% CI: 1.31, 4.66, P = 0.006), compared to those with vitamin K1 in quartile 1. Furthermore, there was no significant association between plasma vitamin K1 and first hemorrhagic stroke in either treatment group.

Baseline plasma vitamin K1 and the risk of first stroke (total and subtypes) by treatment groupa.

CI, confidence interval; OR, odds ratio; Q1, quartile 1; Q2, quartile 2; Q3, quartile 3; Q4, quartile 4; for total stroke: Q1 (<0.26), Q2 (0.26- <0.54), Q3 (0.54- <1.08), Q4 (≥1.08); for ischemic stroke: Q1 (<0.28), Q2 (0.28- <0.58), Q3 (0.58- <1.13), Q4 (≥1.13); for hemorrhagic stroke: Q1 (<0.22), Q2 (0.22- <0.40), Q3 (0.40- <0.85), Q4 (≥0.85).

Conditional logistic regression models were used. Adjusted models included the following covariables: body mass index, baseline systolic blood pressure, time-averaged systolic blood pressure and diastolic blood pressure during treatment, baseline fasting blood glucose, total cholesterol, triglycerides, folate, antihypertensive treatment, smoking status and antiplatelet drug usage at baseline.

Conditional logistic regression models were used. Adjusted models included the following covariables: time-averaged systolic blood pressure and diastolic blood pressure during treatment and antihypertensive treatment at baseline.

Plasma 25(OH)D and vitamin K1 were divided into categorical variables using clinical cut points for 25(OH)D (20 ng/mL) and the first quartile value for vitamin K1. Using high levels of both plasma 25(OH)D and vitamin K1 as the reference, only the combination of low 25(OH)D and low vitamin K1 was associated with increased risk of total stroke (OR = 2.36, 95%CI: 1.17,4.90, P = 0.018) in the enalapril-only group (Table 4). The test of interaction was significant (P = 0.040). The combination of low 25(OH)D and low vitamin K1 was associated with increased risk of ischemic stroke (OR = 3.81, 95% CI: 1.70, 9.00, P = 0.002) in the enalapril-only group. The test of interaction was significant (P = 0.036). No increased risk was observed in the groups low in one vitamin only. In addition, no significant association between the combination of low 25(OH)D and low vitamin K1 with the risk of first total stroke or ischemic stroke was found in the enalapril-folic acid group. Moreover, the combination of low 25(OH)D and low vitamin K1 was not associated with the risk of hemorrhagic stroke, regardless of the group of treatment.

The association of plasma vitamin K1 and 25 hydroxyvitamin D [25(OH)D] status with stroke (total and subtypes)a.

CI, confidence interval; OR, odds ratio; 25(OH)D, 25-hydroxyvitamin D.

Conditional logistic regression models were used. Adjusted models included the following covariables: body mass index, baseline systolic blood pressure, time-averaged systolic blood pressure and diastolic blood pressure during treatment, baseline fasting blood glucose, total cholesterol, triglycerides, folate, antihypertensive treatment, smoking status and antiplatelet drug usage at baseline.

Conditional logistic regression models were used. Adjusted models included the following covariables: time-averaged systolic blood pressure and diastolic blood pressure during treatment and antihypertensive treatment at baseline.

## 讨论 / Discussion

In this population-based case-control study, we reported on the association of plasma vitamin K1 with stroke in hypertensive patients. There was a significant interactive effect of vitamin K1 and folic acid treatment on total stroke or ischemic stroke. A combination of low vitamin D and K status was statistically associated with increased risk of total stroke or ischemic stroke, especially in those participants in the enalapril-only group.

A large body of evidence supports the beneficial effects of vitamin K1 on musculoskeletal health as well as cardiovascular health. Low nutritional intake and bioavailability of vitamin K appears to be a plausible risk factor for stroke, via the importance of vitamin K in the maturation of MGP (one of the vitamin K–dependent proteins) as an inhibitor of tissue calcification (21). Two possible explanations for the results of our study are that the vitamin K concentrations were relatively low and participants were patients with hypertension. There is increasing evidence that the role of vitamin K in CVD may be particularly important in certain high-risk subgroups. Results from the Health, Aging, and Body Composition Study suggest that low plasma vitamin K1 is associated with a higher CVD risk in older adults treated for hypertension (22). Notably, treatment intervention in our study might be a significant modifier: a stronger association was found in participants treated with enalapril alone. Since adults with hypertension in our study were more likely to have lower serum folate than in US (medium 7.82 vs. 11.5 ng/mL) (23). Folic acid has a potent antioxidant and antithrombotic effect in the prevention of cardiovascular disease (24). Therefore, we hypothesize that folic acid treatment may have possibly attenuated the relationships between low vitamin K1 and high stroke risk. It has previously been reported that the combined use of enalapril and folic acid can significantly reduce the risk of first stroke compared with enalapril alone (18).

A meta-analysis reported an association between vitamin D deficiency and stroke (15). Researchers have also presented a potential physiological role of vitamin D in regulating vascular calcification (25). To our knowledge, the associations between vitamin D and K concentrations on stroke have only been studied in isolation. While prior studies have examined vitamins D and K together, they did not focus on stroke. Previous prospective studies have reported substantial interactions for the combined effect of insufficient vitamin D and K status in terms of blood pressure (26) and aortic stiffness (27). The first study of a double-blind placebo-controlled trial to explore the combined effect of vitamin D and K supplementation on cardiovascular health revealed that supplementation of vitamin K1, vitamin D, and minerals was superior to vitamin D and minerals alone in preventing a decrease of elastic properties of the carotid artery, over a 3-year follow-up (28). A recent, large, prospective cohort study in the Netherlands showed that the combined association of low vitamin D and K status with mortality risk was greater than the sum of low vitamin D and K status alone (29). Another clinical study also demonstrated that combined vitamin D and K deficiency is highly prevalent in kidney transplant recipients and is associated with increased mortality and graft failure risk compared with high vitamin D and K status (30). Our results corroborate the findings of this trial: combined low vitamin D and vitamin K status was associated with a higher risk of stroke compared to those with high vitamin D and K status.

We have not yet discovered the exact physiological mechanisms explaining the joint association between vitamin K, vitamin D and stroke. However, some potential overlaps in their action exist. Both vitamin D and K can stimulate the γ-carboxylase system of vitamin K–dependent proteins. Two of these proteins are osteocalcin and MGP, which play a role in cardiovascular health (31, 32). Osteocalcin has been shown to regulate bone mineralization and calcium homeostasis, with the potential to prevent calcium build-up in soft tissues, thereby preventing vascular calcification (33). Similarly, MGP limits calcium incorporation into the extracellular matrix of soft tissues, thus acting as a potent inhibitor of soft tissue calcification. The MGP gene contains a vitamin D (calcitriol) responsive element in its promoter region (34). Circulating vitamin D has been shown to upregulate MGP expression in vascular smooth muscle cells of rats (35). It has also been demonstrated that vitamin K promotes 1,25-dihydroxyvitamin D–stimulated osteocalcin accumulation and mineralization (36). In addition, vitamin D and K have prominent anti-inflammatory effects (37), which is a modifiable risk factor for cardiovascular and cerebrovascular diseases. Thus, vitamins K and D can mutually enhance each other's physiological roles and our results provide a plausible clinical correlate to these experimental findings.

The main strength of our study is that it was conducted on a large population-based cohort, with well-designed quality assurance and quality control throughout. We assessed the joint associations of 25(OH)D and vitamin K1 in relation to first stroke in a population free of baseline stroke through a 1:1 case-control matching design, minimizing potential bias and misclassification. Despite these advantages, our study has several limitations. First, our study faces the same limitations as all case-control studies. A large randomized interventional trial that comparts a placebo, each vitamin separately, and both vitamins combined, would fully elucidate the real clinical impact of vitamin K-D in terms of stroke benefit. Second, although we adjusted for multiple confounding factors, our results may have been influenced by other unknown factors that should be better accounted for in future studies. High vitamin K1 and D levels might reflect healthy dietary and lifestyle patterns, rather than the nutrient itself, however, we were not able to exclude the effects of dietary/lifestyle habits on the results, as these data were not available in our study. Third, given the specificity of our study population (elderly Chinese with hypertension), findings from this study cannot be readily generalized to other populations. Furthermore, since our study population only included Han Chinese, further confirmatory studies in other ethnic groups are needed. Finally, expression levels of MGP were not measured in our study and further studies are needed to determine whether vitamin K is associated with stroke through this pathway.

In conclusion, in the present study, we observed that the simultaneous presence of low vitamin K and D status was associated with a significantly higher risk of ischemic stroke in a hypertensive, population-based sample. We speculate that this phenomenon reflects an overlap in the pleiotropic functions of both vitamins, resulting in a synergistic magnification of disease risk when both are insufficient. Larger, prospective interventional studies are needed to verify these findings.
