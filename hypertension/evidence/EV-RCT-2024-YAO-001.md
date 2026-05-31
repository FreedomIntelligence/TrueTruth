---
type: RCT
language: en
status: reviewed
extracted_by: api
authors:
- Yao Y
- Gui M
- Cai S
tags: []
title:
  zh: null
  en: A network meta-analysis comparative the efficacy of angiotensin-converting enzyme
    inhibitors and calcium channel blockers in hypertension
year: 2024
journal: Medicine
pmid: '38875375'
doi: 10.1097/MD.0000000000037856
id: EV-RCT-2024-YAO-001
study_type: META_ANALYSIS
risk_of_bias:
  tool: RoB2
  overall: some_concerns
grade:
  level: moderate
---



## English Abstract

Currently, most studies primarily focus on directly comparing the efficacy and safety of angiotensin-converting enzyme inhibitors (ACEIs) and calcium channel blockers (CCBs), the two major classes of antihypertensive drugs. Moreover, the majority of studies are based on randomized controlled trials and traditional meta-analyses, with few exploring the efficacy and safety comparisons among various members of ACEIs and CCBs.

ACEIs and CCB were searched for in randomized controlled trials in CNKI, Wanfang, VIP, China Biology Medicine Disc (Si-noMed), PubMed, EMbase, and Cochrane Library databases. The search can be conducted till November 2022. Stata software (version 16.0) and R 4.1.3 was used for statistical analysis and graphics plotting, applying mvmeta, gemtc, and its packages. Meta-regression analysis was used to explore the inconsistencies of the studies.

In 73 trials involving 33 different drugs, a total of 9176 hypertensive patients were included in the analysis, with 4623 in the intervention group and 4553 in the control group. The results of the analysis showed that, according to the SUCRA ranking, felodipine (MD = −12.34, 95% CI: −17.8 to −6.82) was the drug most likely to be the best intervention for systolic blood pressure, while nitrendipine (MD = −8.01, 95% CI: −11.71 to −4.18) was the drug most likely to be the best intervention for diastolic blood pressure. Regarding adverse drug reactions, nifedipine (OR = 0.32, 95% CI: 0.14–0.74) was the drug most likely to be the safest.

The research findings indicate that nifedipine is the optimal intervention for reducing systolic blood pressure in hypertensive patients, nitrendipine is the optimal intervention for reducing diastolic blood pressure in hypertensive patients, and felodipine is the optimal intervention for safety.

## 背景 / Background

Globally hypertension was a major risk factor leading to cardiovascular disease and death, bringing a serious disease burden to the country and the world.[1] Around the world 350 million adults now have nonoptimal systolic blood pressure (SBP) levels (i.e., >110–115 mm Hg) 874 million adults have SBP ≥ 140 mm Hg, and about a quarter of adults have hypertension. From 1990 to 2015, the total number of healthy life years lost due to hypertension increased by 43% globally due to population growth, population aging and increased prevalence of hypertension.[2] Studies on the global burden of disease show that blood pressure in a nonoptimal state is still one of the biggest risk factors for global burden of disease and global all-cause mortality. Hypertension can cause 9.4 million deaths and 212 million lost healthy life years (accounting for 8.5% of the global total) every year.[3] Global average blood pressure looks fairly stable in recent years, but the prevalence and absolute burden of hypertension is increasing globally, especially in middle-income and low-income countries. An estimated 1.39 billion adults worldwide have high blood pressure, of which 1.04 billion are in middle-income and middle-income countries and 349 million are in high-income countries.[4]

However, hypertension not only poses a health burden but can also have a significant economic impact. Medication for hypertension is arguably the most evidence-based and cost-effective medical intervention ever made, with clear benefits of reducing morbidity and mortality, as well as cost savings, as shown in many clinical trials.[5] Selecting appropriate antihypertensive drugs for the treatment of hypertension patients can often achieve twice the result with half the effort. There are 5 main categories of drugs commonly recommended as initial treatment for hypertension. These include calcium channel blockers (CCB), angiotensin-converting enzyme inhibitors (ACEIs), and angiotensin receptor blockers, diuretic, and beta blockers are classified into 5 categories. The mechanism of action of ACEIs is to inhibit angiotensin-converting enzyme, which can eliminate the constriction effect of angiotensin II on blood vessels so as to reduce blood pressure, while CCB can dilate blood vessels by relaxing vascular smooth muscle and thus play a role in reducing blood pressure.[6]

A network meta-analysis reported that ACEIs, CCB, and thiazide diuretics were effective in reducing overall cardiovascular events, cardiovascular death, and stroke compared with placebo, and that for every 10 mm Hg reduction in SBP and 5 mm Hg reduction in diastolic blood pressure (DBP). Both are significantly associated with reduced risk of cardiovascular death, stroke, and overall cardiovascular events, and research results have shown that lowering blood pressure in hypertensive patients can significantly improve the prognosis of hypertensive patients.[7] Existing systematic reviews and meta-analyses mainly discuss the efficacy of ACEIs compared with placebo in the treatment of SBP/DBP in essential hypertension, and whether there are differences among individual drugs in the same class.[8] Zhu et al studied whether there was a significant difference between CCB and other types of hypertension drugs in the prevention of cardiovascular events.[9] Currently, data on the efficacy and safety comparison of individual members of ACEIs and CCB are only based on randomized controlled trials (RCTs) and traditional meta-analysis.[10–13]

However, in clinical treatment, doctors are often faced with not only how to start treatment, but also how to best reduce blood pressure for patients with different symptoms. Existing systematic reviews and meta-analyses compare the antihypertensive effects of different types of antihypertensive drugs and applicable symptoms, which can solve part of the problems according to the different symptoms of patient groups.[6] However, each class of antihypertensive drugs contains several drugs, and it is not clear whether the efficacy of these drugs is the same. As ACEIs and CCB, 2 classes of antihypertensive drugs recommended as first-line antihypertensive drugs by most clinical guidelines for hypertension, few studies have focused on the comparison of efficacy and safety of individual members under these 2 classes of drugs.[14–18]

This study aims to use network meta-analysis to compare the efficacy and safety of individual members of ACEIs and CCB in the treatment of patients with essential hypertension to provide evidence-based evidence.

## 方法 / Methods

Eligible studies were identified by searching CNKI, Wanfang, VIP, SinoMed, PubMed, EMbase, Cochrane Library databases. All retrieval dates are from the establishment of the database to November 2022. The search strategy was developed according to the Cochrane Systematic Review Manual. The search terms included “hypertension” “blood pressure” “angiotensin converting enzyme inhibitors” “captopril” “zofenopril” “enalapril” “ramipril” “quinapril” “perindopril” “lisinopril” “benzazepines” “fosinopril” “alacepril” “cilazapril” “delapril” “imidapril” “moexipril” “rentiapril” “spirapril” “temocapril” “trandolapril” “calcium channel blockers” “amlodipine” “aranidipine” “azelnidipine” “barnidipine” “benidipine” “cilnidipine” “clevidipine” “darodipine” “efonidipine” “felodipine” “isradipine” “lacidipine” “manidipine” “lercanidipine” “mepirodipine” “nicardipine” “nifedipine” “niludipine” “nilvadipine” “nimodipine” “nisoldipine” “nitrendipine” “oxodipine” “pranidipine” “ryodipine” “anipamil” “devapamil” “emopamil” “falipamil” “gallopamil” “verapamil” “clentiazem” “diltiazem” “dihydropyridines” and the literature records were imported into Endnote. The screening process is a cross-check by 2 independent researchers (Yao and Gui), first screening records and abstracts, then eliminating irrelevant articles before screening full articles. The disagreement was judged by the 2 researchers.

In this study, the inclusion criteria were as follows:

Patients ≥ 18 years of age.

For patients clinically diagnosed as essential hypertension without any complications, the diagnostic basis of hypertension is SBP ≥ 140 mm Hg and/or DBP ≥ 90.

The included studies were RCTs in both Chinese and English and had at least 8 weeks of treatment.

The exclusion criteria were as follows:

Literature for which data could not be obtained.

Study designs not suitable (such as observational studies and reviews).

Hypertension patients with comorbidities.

The addition of other drugs to ACEIs and CCB (drug combination).

SBP ≥ 180 mm Hg or DBP ≥ 110 mm Hg.

The main outcome indexes included SBP; DBP; adverse effects is measured by the proportion of patients who withdraw or stop the trial due to adverse reaction symptoms before the end of treatment to the total population. In cases where there were multiple cycles in the same group in a study, the data for the longest period of preferred treatment was analyzed.

The 2 researchers read the title and abstract independently, excluded the irrelevant literature according to the preset inclusion and exclusion criteria, and then read the full text to determine whether it was included. EXCEL was used to manage the data, and the extraction content included published information. Study characteristics (first author’s name, title, publication year, duration of treatment, drugs, and doses in trial and control groups, number of lost to follow-up, number of adverse events) and patient characteristics (number of participants in each study trial and control group, age, sex, and weight) were extracted from the included studies.

The Cochrane Handbook versions 5.0.1 RCT bias risk assessment tool was applied to weigh the methodological quality of RCTs. Seven domains were integrated into the evaluation: random sequence generation, allocation concealment, blinding method of subjects and researchers, blinding method of the outcome evaluator, incomplete outcome report, selective outcome report, and other biases. Each item was classified as a “low-risk bias,” “unclear,” or “high-risk bias.” Two reviewers conducted data extraction and methodological evaluation. Any inconsistencies were resolved through discussion.

Network meta-analysis was carried out based on the Bayesian model of Markov chain Monte Carlo method, Stata software (version 16.0) and R 4.1.3 was used for statistical analysis and graphics plotting, applying mvmeta, gemtc, and its packages. When calculating effect size, the data of binary classification variables were expressed as odds ratio (OR) and continuous variables as mean difference (MD), both were calculated with 95% confidence intervals (95%CI). Heterogeneity of comparisons was evaluated using I2. I2 > 30%, >50%, and >70% were considered as moderate, substantial and considerable heterogeneity. In this study, taking into account the potential heterogeneity between studies, a random-effect model was used. The efficacy of different interventions was ranked according to surface under the cumulative ranking curve (SUCRA), The closer the SUCRA value is to 100, the more effective the drug is. For heterogeneity in the study meta-regression analysis were used to explore the source of heterogeneity. Amlodipine was the drug that had the most direct comparison with other drugs in 73 included trials, and it was also a drug that had been on the market for a long time, and its effectiveness and safety had been verified by many clinical trials. Therefore, In the process of statistical analysis, amlodipine was used as the control of all drugs in this study for network meta-analysis. All analyses were based on previous published study, thus no ethical approval and patient consent are required.

## 结果 / Results

In a preliminary search of 7 electronic databases, a total of 5512 studies were retrieved and 2078 replicated studies were excluded. A total of 3230 articles were excluded after reading the titles and abstracts, including meta-analyses, reviews, animal experiments, conference papers, articles whose full text was not available online, articles not in Chinese or English, and articles not related to the research topic. Two hundred four studies were eventually included for full-text reading assessment, of which 25 were excluded because treatment duration was <8 weeks, 89 were excluded because they did not meet inclusion criteria, 10 were excluded because study design did not meet requirements, 5 were excluded because of replication, and 2 were excluded because they were not related to the study. In the end, 73 studies were included. As shown in Figure 1.

PRISMA diagram.

According to the Cochrane Handbook for Systematic Reviews of Interventions, the risk of bias of the included RCTs were evaluated as follows: randomization; allocation concealment; blind method; selective reporting; incomplete outcome data; other bias. The bias of assessment of RCTs are presented in Figure 2.

Methodologic quality of the included trials based on the Cochrane Handbook.

The characteristics of each study have been summarized in Table 1. A total of 73 studies included in this research were published between 1986 and 2021. Among them, 9176 hypertensive patients were included in the network meta-analysis, with 4623 in the intervention group and 4553 in the control group. The sample size of study participants ranged from 20 to 320. Patients’ ages ranged from 30 to 75 years old, and the duration of treatment ranged from 8 to 156 weeks.

Basic characteristics of studies.

Thirty-two intervention methods were directly or indirectly compared, with 44 groups showing statistically significant differences in results. Amlodipine compares captopril (MD = −10.9, 95% CI: −16.79 to −5.28), cinidipine (MD = −4.38, 95% CI: −8.3 to −0.39), diltiazem SR (MD = −11.44, 95% CI: −19.34 to −3.6), felodipine(MD = −12.34, 95% CI: −17.8 to −6.82), nifedipine (MD = −7.45, 95% CI: −10.91 to −3.78), nitrendipine (MD = −9.47, 95% CI: −14.29 to −4.36), ramipril (MD = −11.25, 95% CI: −16.76 to −5.57), Verapamil (MD = −13.34, 95% CI: −25.95 to −0.82), the difference was statistically significant. Azelnidipine compares captopril (MD = −11.63, 95% CI: −20.36 to −3.32), diltiazem SR (MD = −12.19, 95% CI: −22.34 to −2.19), felodipine (MD = −13.07, 95% CI: −21.4 to −4.71), nifedipine (MD = −8.19, 95% CI: −15.34 to −0.88), nitrendipine (MD = −10.21, 95% CI: −18.11 to −2.12), ramipril (MD = −11.99, 95% CI: −20.36 to −3.51), verapamil (MD = −14.08, 95% CI: −28.22 to −0.1), the difference was statistically significant. Benidipine compares diltiazem SR (MD = −10.05, 95% CI: −19.2 to −1.02), felodipine (MD = −10.94, 95% CI: −18.06 to −3.8), nifedipine (MD = −6.05, 95% CI: −11.73 to −0.23), nitrendipine (MD = −8.07, 95% CI: −14.68 to −1.25), ramipril (MD = −9.84, 95% CI: −17.03 to −2.62), the difference was statistically significant. Cilazapril compares diltiazem SR (MD = −10.8, 95% CI: −21.19 to −0.59), felodipine (MD = −11.69, 95% CI: −20.57 to −2.96), nitrendipine (MD = −8.82, 95% CI: −15.86 to −1.74), ramipril (MD = −10.6, 95% CI: −19.24 to −2), the difference was statistically significant. Cinildipine compares felodipine (MD = −7.95, 95% CI: −14 to −1.92), ramipril (MD = −6.87, 95% CI: −13.34 to −0.27), the difference was statistically significant. Enalapril compares felodipine (MD = −8.98, 95% CI: −15.3 to −2.56), ramipril (MD = −7.9, 95% CI: −14.35 to −1.22), the difference was statistically significant. Lacidipine compares nifedipine (MD = −9, 95% CI: −14.96 to −2.88), nitrendipine (MD = −11.01, 95% CI: −17.85 to −3.96), ramipril (MD = −12.79, 95% CI: −20.18 to −5.27), verapamil (MD = −14.89, 95% CI: −28.38 to −1.49), the difference was statistically significant. Lisinopril compares nifedipine (MD = −5.82, 95% CI: −10.68 to −0.66), nitrendipine (MD = −7.84, 95% CI: −13.68 to −1.69), ramipril (MD = −9.62, 95% CI: −16.11 to −2.89), the difference was statistically significant. Nifedipine GITS compares nitrendipine (MD = −9.82, 95% CI: −16.29 to −3.15), ramipril (MD = −11.61, 95% CI: −18.34 to −4.75), verapamil (MD = −13.69, 95% CI: −26.94 to −0.56), the difference was statistically significant. Nifedipine SR compares ramipril (MD = −8.47, 95% CI: −15.49 to −1.33), the difference was statistically significant. As shown in Figure 3 (Supplementary information SBP 144.xlsx, http://links.lww.com/MD/M523).

Network plot of systolic blood pressure.

Thirty-three intervention methods were directly or indirectly compared, with 18 groups showing statistically significant differences in results. Amlodipine compares captopril (MD = −5.98, 95% CI: −10.03 to −1.82), diltiazem SR (MD = −7.07, 95% CI: −12.84 to −1.27), enalapril (MD = −2.91, 95% CI: −5.81 to −0.01), nifedipine (MD = −4.03, 95% CI: −6.64 to −1.33), nifedipine SR (MD = −3.71, 95% CI: −7.22 to −0.15), nitrendipine (MD = −8.01, 95% CI: −11.71 to −4.18), ramipril (MD = −4.65, 95% CI: −8.61 to −0.64), the difference was statistically significant. Azelnidipine compares nitrendipine (MD = −6.71, 95% CI: −12.75 to −0.447), the difference was statistically significant. Benidipine compares nitrendipine (MD = −6.09, 95% CI: −11.16 to −0.93), the difference was statistically significant. Cinildipine compares nitrendipine (MD = −5.87, 95% CI: −10.47 to −1.19), the difference was statistically significant. Enalapril compares nitrendipine (MD = −5.09, 95% CI: −9.45 to −0.61), the difference was statistically significant. Felodipine SR compares nitrendipine (MD = −5.18, 95% CI: −9.73 to −0.54), the difference was statistically significant. Fosinopril compares nitrendipine (MD = −10, 95% CI: −18.22 to −1.66), the difference was statistically significant. Lacidipine compares nitrendipine (MD = −7.84, 95% CI: −13.22 to −2.39), the difference was statistically significant. Lercanidipine compares nitrendipine (MD = −7.57, 95% CI: −14.14 to −0.89), the difference was statistically significant. Lisinopril compares nitrendipine (MD = −6.07, 95% CI: −10.57 to −1.51), the difference was statistically significant. Manidipine compares nitrendipine (MD = −7.21, 95% CI: −12.56 to −1.7), the difference was statistically significant. Nifedipine GITS compares nitrendipine (MD = −7.06, 95% CI: −12.09 to −1.98), the difference was statistically significant. As shown in Figure 4 (Supplementary information DBP 148.xlsx, http://links.lww.com/MD/M524).

Network plot of diastolic blood pressure.

Twenty-five intervention methods were directly or indirectly compared, with 11 groups showing statistically significant differences in results. Amlodipine compares enalapril (OR = 0.48, 95% CI: 0.24–0.96), nifedipine (OR = 0.32, 95% CI: 0.14–0.74), the difference was statistically significant. Azelnidipine compares benidipine (OR = 0.23, 95% CI: 0.05–0.91), enalapril (OR = 0.21, 95% CI: 0.05–0.82), felodipine SR (OR = 0.18, 95% CI: 0.04–0.83), isradipine (OR = 0.16, 95% CI: 0.03–0.84), nifedipine (OR = 0.14, 95% CI: 0.03–0.59), nifedipine GITS (OR = 0.19, 95% CI: 0.04–0.81), nitrendipine (OR = 0.2, 95% CI: 0.04–0.96), the difference was statistically significant. Lercanidipine compares nifedipine (OR = 0.25, 95% CI: 0.06–0.95), the difference was statistically significant. Manidipine compares nifedipine (OR = 0.2, 95% CI: 0.05–0.92), the difference was statistically significant. As shown in Figure 5 (Supplementary information adverse 53.xlsx, http://links.lww.com/MD/M525).

Network plot of adverse effects.

The results of SUCRA indicate that felodipine may be the best intervention method for reducing SBP in hypertensive patients, nitrendipine may be the best intervention method for reducing DBP in hypertensive patients, and nifedipine may be the best intervention method for safety comparison. As shown in Table 2.

SUCRA ranking.

The I2 values of direct and indirect SBP were 84.41% and 87.90%, respectively. The I2 values of DBP were 90.20% and 91.59%, respectively. The I2 values of adverse reactions were 10.75% and 36.03%, respectively. The global inconsistency test showed that the difference in the inconsistency model test of SBP was statistically significant (P = .009), the difference in the inconsistency model test of DBP was statistically significant (P = .001), and the difference in adverse reactions was not statistically significant (P = .119). Node cutting method was used to test the local inconsistency of the 3 models of SBP, DBP, and adverse reaction, and the results of local inconsistency test of SBP showed that amlodipine (P = .046), captopril and nifedipine (P = .000) were statistically significant. The results of DBP showed that amlodipine and cilapril (P = .03), amlodipine and nifedipine (P = .045), amlodipine and nirendipine (P = .01), cilapril and nirendipine (P = .035), and cinidipine and felodipine (P = .047) had significant differences. The results of adverse reactions showed that there were statistically significant differences between amlodipine and nifedipine sustained-release (P = .01) and benidipine and nifedipine sustained-release (P = .000). After global inconsistency test and local inconsistency test, there were global inconsistency in both systolic and DBP, and local inconsistency in both systolic and DBP and adverse reactions.

In order to explore the source of inconsistencies, this article uses the meta-regression analysis method to analyze the features that can be extracted from 73 studies included, and investigates the influence of various factors on the reduction of SBP and DBP analysis results. If P < .05, the result was considered statistically significant. The table shows the factors studied in the single factor meta-regression analysis. The results of meta-regression showed no significant differences in publication year, baseline blood pressure, age, sample size, and the proportion of males and females. As shown in Table 3.

Meta-regression analysis.

P-value <.05 was considered significant.

SE = standard error.

According to systolic blood pressure, diastolic blood pressure, and safety, funnel plots were constructed. For the funnel plots of systolic and diastolic blood pressure, most points are located in the upper half and are generally symmetrically distributed, indicating a minimal possibility of publication bias. However, in the funnel plot for adverse reactions, the points do not exhibit a symmetric distribution, suggesting potential publication bias, as shown in Figures 6–8.

Funnel plot of systolic blood pressure.

Funnel plot of diastolic blood pressure.

Funnel plot of adverse effects.

## 讨论 / Discussion

Currently, most research primarily focuses on directly comparing the effectiveness and safety of angiotensin-converting enzyme inhibitors (ACEIs) and calcium channel blockers (CCBs), the two major classes of antihypertensive drugs. Additionally, the majority of studies are based on randomized controlled trials and traditional meta-analyses, with limited exploration of the effectiveness and safety comparisons among the various members of ACEIs and CCBs. This study included a total of 73 trials involving 9176 hypertensive patients, with 4623 in the intervention group and 4553 in the control group. The aim was to explore the effectiveness and safety of the various members of ACEIs and CCBs from a novel perspective. The network meta-analysis results indicate that felodipine is the optimal intervention for reducing systolic blood pressure among ACEIs and CCBs, nitrendipine is the optimal intervention for reducing diastolic blood pressure, and nitrendipine is the optimal intervention for safety. Although there was significant heterogeneity observed in the analysis results of systolic and diastolic blood pressure, meta-regression analysis was employed to analyze common characteristics of the 73 studies, including publication year, baseline blood pressure, age, sample size, and gender ratio.

The network meta-analysis results suggest that felodipine ranks highest in SUCRA for systolic blood pressure, nitrendipine ranks highest for diastolic blood pressure, and nitrendipine ranks highest for safety. While most previous studies have primarily compared one class of antihypertensive drugs against another or compared various members within a single class,[91–94] to the best of our knowledge, this study represents the first attempt to compare the various members of ACEIs and CCBs. The study aimed to provide new insights into the effectiveness and safety of antihypertensive drugs from a more granular perspective, thus contributing to the field of hypertension research.

Regarding the heterogeneity observed in the network meta-analysis,[95] meta-regression analysis was conducted, considering variables such as publication year, baseline blood pressure, age, sample size, and gender ratio. The analysis revealed no significant statistical differences in these variables; however, other sources of heterogeneity may exist, such as blood pressure measurement timing and patient ethnicity, which were inadequately reported in the original studies. Therefore, caution is warranted when interpreting the results of systolic and diastolic blood pressure. Nonetheless, the heterogeneity in the network meta-analysis of adverse reactions was low. Finally, funnel plots were employed to assess potential publication bias among the 73 studies.[96] While funnel plots for systolic and diastolic blood pressure exhibited a relatively symmetrical and uniform distribution, an asymmetrical distribution was observed in the funnel plot for adverse reactions, suggesting potential publication bias.

Limitations of the study include potential biases due to differences in blood pressure measurement devices and operators across studies, as well as the inclusion of some low-quality clinical studies and unclear biases in certain studies, which may have led to the underestimation of potential biases. Additionally, the study did not address long-term prognosis factors such as mortality and severe cardiovascular events in hypertensive patients. Although no evidence of nonconvergence was found in any network model, the precision of estimates may have been affected by the small number of studies in each network, and wider credible intervals suggest potential lack of statistical power. Furthermore, the exclusion of patients with other serious illnesses or specific populations with hypertension ensured baseline consistency but limited the generalizability of drug effects. Therefore, further large-scale real-world studies and meta-analyses with increased study numbers are needed to provide evidence-based medicine evidence. Strengths of our network meta-analysis include comprehensive literature searches across multiple electronic databases, attempts to contact authors for missing data, quality assessment of original studies using validated tools, and appropriate methods for data analysis.

In conclusion, the study findings suggest that felodipine is the optimal intervention for reducing systolic blood pressure in hypertensive patients, nitrendipine is the optimal intervention for reducing diastolic blood pressure, and nitrendipine is the optimal intervention for safety.

## 结论 / Conclusion

In this study, we found that felodipine may be the best intervention method for reducing SBP in hypertensive patients, nitrendipine may be the best intervention method for reducing DBP in hypertensive patients, and nifedipine may be the best intervention method for safety comparison.
