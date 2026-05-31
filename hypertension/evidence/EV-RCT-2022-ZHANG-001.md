---
type: RCT
language: en
status: reviewed
extracted_by: api+llm
authors:
- Zhang T
- Liang Z
- Lin T
- Cohen DJ
- Arrieta A
- Wang X
- Qin X
- Wang B
- Huo Y
- Liu GG
- Jiang J
- Zhang Z
tags:
- hypertension
- stroke prevention
- cost-effectiveness
- folic acid
- enalapril
- microsimulation
- China
- primary prevention
title:
  zh: null
  en: Cost-effectiveness of folic acid therapy for primary prevention of stroke in
    patients with hypertension
year: 2022
journal: BMC medicine
pmid: '36280851'
doi: 10.1186/s12916-022-02601-z
pico:
  population:
    condition: hypertension without history of stroke or MI
    sample_size: 20702
  intervention:
    name: enalapril-folic acid (10 mg + 0.8 mg)
  comparison:
    name: enalapril alone (10 mg)
  outcomes:
    primary:
    - name: first stroke
      effect_size:
        metric: HR
        value: 0.79
        ci_low: 0.68
        ci_high: 0.93
        p: 0.003
risk_of_bias:
  tool: RoB2
  overall: some_concerns
grade:
  level: moderate
id: EV-RCT-2022-ZHANG-001
study_type: COHORT
---




## English Abstract

For hypertensive patients without a history of stroke or myocardial infarction (MI), the China Stroke Primary Prevention Trial (CSPPT) demonstrated that treatment with enalapril-folic acid reduced the risk of primary stroke compared with enalapril alone. Whether folic acid therapy is an affordable and beneficial treatment strategy for the primary prevention of stroke in hypertensive patients from the Chinese healthcare sector perspective has not been thoroughly explored.

We performed a cost-effectiveness analysis alongside the CSPPT, which randomized 20,702 hypertensive patients. A patient-level microsimulation model based on the 4.5-year period of in-trial data was used to estimate costs, life years, quality-adjusted life years (QALYs), and incremental cost-effectiveness ratios (ICERs) for enalapril-folic acid vs. enalapril over a lifetime horizon from the payer perspective.

During the in-trial follow-up period, patients receiving enalapril-folic acid gained an average of 0.016 QALYs related primarily to reductions in stroke, and the incremental cost was $706.03 (4553.92 RMB). Over a lifetime horizon, enalapril-folic acid treatment was projected to increase quality-adjusted life years by 0.06 QALYs or 0.03 life-year relative to enalapril alone at an incremental cost of $1633.84 (10,538.27 RMB), resulting in an ICER for enalapril-folic acid compared with enalapril alone of $26,066.13 (168,126.54 RMB) per QALY gained and $61,770.73 (398,421.21 RMB) per life-year gained, respectively. A probabilistic sensitivity analysis demonstrated that enalapril-folic acid compared with enalapril would be economically attractive in 74.5% of simulations at a threshold of $37,663 (242,9281 RMB) per QALY (3x current Chinese per capita GDP). Several high-risk subgroups had highly favorable ICERs < $12,554 (80,976 RMB) per QALY (1x GDP).

For both in-trial and over a lifetime, it appears that enalapril-folic acid is a clinically and economically attractive medication compared with enalapril alone. Adding folic acid to enalapril may be a cost-effective strategy for the prevention of primary stroke in hypertensive patients from the Chinese health system perspective.

The online version contains supplementary material available at 10.1186/s12916-022-02601-z.

## 背景 / Background

Stroke is the second leading cause of death worldwide and the total number of deaths from stroke reached 6.55 million in 2019 [1]. As 77% of strokes are first events, effective primary prevention for stroke is essential to halt or reverse its rising burden [2]. Previous trials and meta-analyses have indicated that supplementation with folic acid might be an effective therapy for the primary prevention of stroke [3–5]. The recent China Stroke Primary Prevention Trial (CSPPT) enrolled a total of 20,702 patients with hypertension without a history of stroke or myocardial infarction (MI). Patients were randomly assigned in a 1:1 ratio to receive 1 tablet containing 10 mg of enalapril and 0.8 mg of folic acid daily (single-pill compound, the enalapril-folic acid group) or 1 tablet containing 10 mg of enalapril daily (the enalapril group). After a median treatment duration of 4.5 years, the hazard ratio (HR) for occurrence of first stroke comparing enalapril-folic acid versus enalapril was 0.79 (95% CI: 0.68 to 0.93), with a 21% reduction in relative risk of first stroke, demonstrating that enalapril-folic acid was more effective for the primary prevention of stroke compared with enalapril alone [6]. A recent meta-analysis including 22 folic acid trials for the primary prevention of cardiovascular disease (CVD) events among Chinese populations, demonstrated an even greater risk reduction [7].

As one of the most common causes of long-term disability, stroke has a substantial impact on the total cost of healthcare worldwide, especially in developing countries [8, 9]. Although the benefits of folic acid treatment for hypertensive patients are evident, it is unknown whether folic acid treatment provides these health benefits at an acceptable cost to society. Given the large population of patients who might benefit from such therapy, this information is critical for physicians, patients, and policy holders to make informed decisions regarding preventive therapies. To address this gap in knowledge, we used data from the CSPPT to perform a formal health assessment of the cost-effectiveness of enalapril-folic acid versus enalapril alone for the primary prevention of stroke in hypertensive patients.

## 方法 / Methods

Baseline characteristics of patients in the economic analysis are shown in Supplemental Additional file 1: Table S2. A total of 10,348 and 10,354 patients were randomized to the enalapril-folic acid group or the enalapril group, respectively. The mean age was 60 (SD, 7.5) years and 8497 (41.0%) were male. There were no significant differences in baseline characteristics between the enalapril-folic acid and enalapril groups (all P > 0.05).

The cost-effectiveness analysis was conducted for the in-trial period and for a lifetime. The in-trial cost-effectiveness analysis was performed using the piggy-back method and included all patients in the CSPPT. Data on survival, CVD events, utilities, and healthcare resource use were collected through the 4.5-year follow-up period for all patients to calculate QALYs and costs for the in-trial period. In the lifetime cost-effectiveness analysis, we constructed a microsimulation model based on the CSPPT population data to compare the lifetime costs, life years, quality-adjusted life years, and cost-effectiveness of enalapril-folic acid versus enalapril. This study was conducted with approval from the Institutional Review Boards of each study site.

The microsimulation model was run at the individual patient level; for each patient, patient characteristics and risk factors were estimated by repeatedly sampling (without replacement) from relevant probability distributions of risk factors and were used to obtain the probability of a health transition during each cycle. Risk factors included age, sex, systolic blood pressure, total cholesterol, high density lipoprotein-cholesterol (HDL-C), the MTHFR C677T polymorphism, folate levels, homocysteine, history of diabetes, and current tobacco smoking.

The structure of our microsimulation model is described in Fig. 4. The model consisted of 6 independent health states: pre-CVD, stroke, coronary heart disease (CHD), post-stroke, post-CHD, and death. In the model, patients with hypertension remained healthy (pre-CVD state) until they developed a stroke (ischemic stroke or hemorrhagic stroke), CHD, or died for any non-CVD-related cause. After the occurrence of a CVD event (including stroke and CHD events in our model), patients were moved to a corresponding post-CVD state, in which they may have a subsequent CVD event or a CVD-related death. The cycle length was set to 1 year. The transition probabilities of our microsimulation model were age-dependent. The parameters of the model are presented in Table 3.Annual probability of a first CVD event◦ For the annual probability of a first stroke, we inferred the cycle transition probabilities from the China Stroke Primary Prevention Trial (CSPPT) data [6]. A Weibull distribution was used to model the survival of patients in the enalapril group and to obtain a hypothetical parameters scale (λ) and a shape (γ). The transition probability of enalapril was estimated as follows:\documentclass[12pt]{minimal}
				\usepackage{amsmath}
				\usepackage{wasysym} 
				\usepackage{amsfonts} 
				\usepackage{amssymb} 
				\usepackage{amsbsy}
				\usepackage{mathrsfs}
				\usepackage{upgreek}
				\setlength{\oddsidemargin}{-69pt}
				\begin{document}$$Annual\ probability=1- {\exp}\left[\lambda \ast {(state)}^{\gamma }-\lambda \ast {\left( state+1\right)}^{\gamma}\right]$$\end{document}Annualprobability=1-expλ*(state)γ-λ*state+1γFor enalapril-folic acid, the transition probabilities were estimated by adjusting the hazard ratio (HR=0.79) for enalapril from the CSPPT.◦ Annual probabilities of first CHD were obtained separately for males and females based on methods from the Chinese Multi-provincial Cohort Study (CMCS) [22]. First, the 10-year CHD risk (P) was calculated based on the distribution of risk factors (age, blood pressure, total cholesterol, high-density lipoprotein cholesterol, diabetes, and smoking status) from the CSPPT data. We assumed that a patient’s risk factor (other than age) remained constant from year to year. The 10-year CHD risk was then converted into a 1-year probability of CHD. The transition probability was estimated as follows:\documentclass[12pt]{minimal}
				\usepackage{amsmath}
				\usepackage{wasysym} 
				\usepackage{amsfonts} 
				\usepackage{amssymb} 
				\usepackage{amsbsy}
				\usepackage{mathrsfs}
				\usepackage{upgreek}
				\setlength{\oddsidemargin}{-69pt}
				\begin{document}$${\displaystyle \begin{array}{c}P=1-S{(t)}^{{\exp}\left(f\left[x,M\right]\right)}\\ {}f\left(x,M\right)={\beta}_1\ast \left({x}_1-{M}_1\right)+\dots +{\beta}_p\ast \left({x}_p-{M}_p\right)\\ {} Annual\ probability=1-{\exp}\left(\left({\ln}\left(1-P\right)\right)/10\right)\end{array}}$$\end{document}P=1-S(t)expfx,Mfx,M=β1*x1-M1+⋯+βp*xp-MpAnnualprobability=1-expln1-P/10Because no statistical difference was found in risk of CHD (p = 0.89) between the treatment strategies, we assumed no difference in annual probabilities of CHD between the enalapril and the enalapril-folic acid groups.Transition to post-CVD event state occurred after one cycle (1 year) with a probability of 100% (tunnel state)Annual probabilities of subsequent CVD events (stroke relapse, post-stroke to CHD, CHD relapse, and post-CHD to stroke) were obtained from other studies as primary data from the CSPPT were not available [23–25]Transition to death (absorbing state)◦ Age- and sex-specific mortality rates for non-CVD deaths were based on the Chinese life tables obtained from the sixth nationwide census [26]. Because no statistical difference was found in the risk of non-CVD death (p = 0.44) between treatment strategies, we assumed no difference in non-CVD mortality rates between the enalapril and the enalapril-folic acid groups.◦ CVD mortality rates at the first year and in subsequent years (after a stroke or after a CHD) were obtained from other studies [23–25]. Because no statistical difference was found in the CVD fatality rate between the enalapril and the enalapril-folic acid groups (p > 0.99), we assumed patients had the same chance of dying once they had a stroke.Fig. 4Microsimulation model. a 1-year probability of first CVD event. b Transition to post-CVD event occurring after one cycle (1 year) with a probability of 100% (tunnel state). c CVD relapse during the first year. d 1-year probabilities of subsequent CVD events (stroke relapse after first year, post-stroke to CHD, CHD relapse after first year, and post-CHD to stroke). e Transition to death (absorbing state). CVD, cardiovascular disease; CHD, coronary heart diseaseTable 3Main assumptions for the cost-effectiveness analysisParametersEstimate (SD or range)DistributionReferencePatient characteristics Age, y60 (7.53)NormalCSPPT [6] Male sex，%41%TableClinical characteristics Total cholesterol, mg/dL213.6 (46)NormalCSPPT [6] HDL-C, mg/dL52 (14)Normal Baseline SBP, mm Hg139.7 (11.1)Normal Smoking,%23%Table Diabetes mellitus,%3%TableRates and probabilities Morbidity rates, annual Primary stroke1 −  exp [λ ∗ (state)γ − λ ∗ (state + 1)γ]WeibullCSPPT [6] Primary CHD1 −  exp ((ln(1 − P))/10)P = 1 − S(t)exp(f[x, M])f(x, M) = β1 ∗ (x1 − M1) + … + βp ∗ (xp − Mp)/CMCS [22] Stroke relapse in 1 year17%βCKB study [23] Stroke relapse after 1 year2–9%β Stroke after CHD0.4%βThe EUROPA study [24] Stroke after post-CHD0.4%β CHD relapse in 1 year2.5%βPEACE [25] CHD relapse after 1 year1.2%βThe EUROPA study [24] CHD after stroke0.4%βCKB study [23] CHD after post-stroke0.4%β Mortality rates, annual Non CVD related1.68–507.28‰ (Age-dependent)βLife table [26] After stroke15%βCKB study [23] After post-stroke3%β After CHD2.8%βPEACE [25] After post-CHD1.5%βThe EUROPA study [24]Drug cost per unit, $ (￥) Enalapril$0.09 ($0.03–$0.22)￥0.56 (￥0.2–￥1.44)γLocal bidding Price or the National centralized drug procurement price [27, 28] (see Additional file 1: Table S3) Enalapril-folic acid$0.74￥4.75γ Angiotensin-converting enzyme inhibitors$0.13 ($0.11–$0.38)￥0.83 (￥0.72–￥2.43)γ Angiotensin II receptor blockers$0.08 ($0.07–$0.54)￥0.53 (￥0.48–￥3.48)γ Calcium channel blockers$0.25 ($0.14–$0.47)￥1.60 (￥0.91–￥3.06)γ Diuretics$0.29 ($0.27–$0.30)￥1.88 (￥1.72–￥1.95)γ β-blockers$0.03 ($0.02–$0.05)￥0.21 (￥0.16–￥0.32)γ Lipid-lowering drugs$0.08 ($0.03–$0.65)￥0.50 (￥0.17–￥4.19)γ Glucose-lowering drugs$0.04 ($0.03–$0.24)￥0.24 (￥0.19–￥1.57)γ Antiplatelet drugs$0.05 ($0.05–$0.08)￥0.34 (￥0.31–￥0.50)γCVD hospitalization costs, $ (￥) (first 30 days) Ischemic stroke$1529.18 (± 20%)￥9863.20 (± 20%)γChina’s Health Statistics Yearbook, 2021 [29] Hemorrhagic stroke$3207.55 (± 20%)￥20,688.70(± 20%)γ Coronary heart disease$4696.39 (± 20%)￥30,291.70(± 20%)γRehabilitation costs per month, $ (￥)a Rehabilitation training$200.93 (± 20%)￥1296.00 (± 20%)γNational Development and Reform Commission [30] (see Additional file 1: Table S4) Rehabilitation checking$7.91 (± 20%)￥51.00 (± 20%)γ Home care$465.12 (± 20%)￥3000.00 (± 20%)γUtility Pre-CVD0.90 (0.12)βCSPPT [6] Primary stroke (first year)0.76βDu [31] Primary stroke (after first year)0.79β Recurrent stroke (first year)0.30βWang [32] Recurrent stroke (after first year)0.33β Primary CHD (first year)0.77 (0.75–0.78)βGoldsmith [33] Primary CHD (after first year)0.89 (0.17)βWang [34] Recurrent CHD (first year)0.64βThomas [35] Recurrent CHD (after first year)0.76βTreatment adherence Enalaparil-folic acid0.692 (± 20%)βCSPPT [6] Enalapril0.691 (± 20%)βHR of primary stroke0.79 (0.68 -0.93)βDisability rate0.39 (0.20–0.8))βSalomon [8]Rehabilitation rate after stroke0.58 (0–0.7)βAsakawa [36]Annual discount rates for life years, costs, and QALYs5% (0–8%)/aPatients with disability after stroke

Annual probability of a first CVD event◦ For the annual probability of a first stroke, we inferred the cycle transition probabilities from the China Stroke Primary Prevention Trial (CSPPT) data [6]. A Weibull distribution was used to model the survival of patients in the enalapril group and to obtain a hypothetical parameters scale (λ) and a shape (γ). The transition probability of enalapril was estimated as follows:

◦ For the annual probability of a first stroke, we inferred the cycle transition probabilities from the China Stroke Primary Prevention Trial (CSPPT) data [6]. A Weibull distribution was used to model the survival of patients in the enalapril group and to obtain a hypothetical parameters scale (λ) and a shape (γ). The transition probability of enalapril was estimated as follows:

\documentclass[12pt]{minimal}
				\usepackage{amsmath}
				\usepackage{wasysym} 
				\usepackage{amsfonts} 
				\usepackage{amssymb} 
				\usepackage{amsbsy}
				\usepackage{mathrsfs}
				\usepackage{upgreek}
				\setlength{\oddsidemargin}{-69pt}
				\begin{document}$$Annual\ probability=1- {\exp}\left[\lambda \ast {(state)}^{\gamma }-\lambda \ast {\left( state+1\right)}^{\gamma}\right]$$\end{document}Annualprobability=1-expλ*(state)γ-λ*state+1γFor enalapril-folic acid, the transition probabilities were estimated by adjusting the hazard ratio (HR=0.79) for enalapril from the CSPPT.◦ Annual probabilities of first CHD were obtained separately for males and females based on methods from the Chinese Multi-provincial Cohort Study (CMCS) [22]. First, the 10-year CHD risk (P) was calculated based on the distribution of risk factors (age, blood pressure, total cholesterol, high-density lipoprotein cholesterol, diabetes, and smoking status) from the CSPPT data. We assumed that a patient’s risk factor (other than age) remained constant from year to year. The 10-year CHD risk was then converted into a 1-year probability of CHD. The transition probability was estimated as follows:

For enalapril-folic acid, the transition probabilities were estimated by adjusting the hazard ratio (HR=0.79) for enalapril from the CSPPT.

◦ Annual probabilities of first CHD were obtained separately for males and females based on methods from the Chinese Multi-provincial Cohort Study (CMCS) [22]. First, the 10-year CHD risk (P) was calculated based on the distribution of risk factors (age, blood pressure, total cholesterol, high-density lipoprotein cholesterol, diabetes, and smoking status) from the CSPPT data. We assumed that a patient’s risk factor (other than age) remained constant from year to year. The 10-year CHD risk was then converted into a 1-year probability of CHD. The transition probability was estimated as follows:

\documentclass[12pt]{minimal}
				\usepackage{amsmath}
				\usepackage{wasysym} 
				\usepackage{amsfonts} 
				\usepackage{amssymb} 
				\usepackage{amsbsy}
				\usepackage{mathrsfs}
				\usepackage{upgreek}
				\setlength{\oddsidemargin}{-69pt}
				\begin{document}$${\displaystyle \begin{array}{c}P=1-S{(t)}^{{\exp}\left(f\left[x,M\right]\right)}\\ {}f\left(x,M\right)={\beta}_1\ast \left({x}_1-{M}_1\right)+\dots +{\beta}_p\ast \left({x}_p-{M}_p\right)\\ {} Annual\ probability=1-{\exp}\left(\left({\ln}\left(1-P\right)\right)/10\right)\end{array}}$$\end{document}P=1-S(t)expfx,Mfx,M=β1*x1-M1+⋯+βp*xp-MpAnnualprobability=1-expln1-P/10Because no statistical difference was found in risk of CHD (p = 0.89) between the treatment strategies, we assumed no difference in annual probabilities of CHD between the enalapril and the enalapril-folic acid groups.

Because no statistical difference was found in risk of CHD (p = 0.89) between the treatment strategies, we assumed no difference in annual probabilities of CHD between the enalapril and the enalapril-folic acid groups.

Transition to post-CVD event state occurred after one cycle (1 year) with a probability of 100% (tunnel state)

Annual probabilities of subsequent CVD events (stroke relapse, post-stroke to CHD, CHD relapse, and post-CHD to stroke) were obtained from other studies as primary data from the CSPPT were not available [23–25]

Transition to death (absorbing state)◦ Age- and sex-specific mortality rates for non-CVD deaths were based on the Chinese life tables obtained from the sixth nationwide census [26]. Because no statistical difference was found in the risk of non-CVD death (p = 0.44) between treatment strategies, we assumed no difference in non-CVD mortality rates between the enalapril and the enalapril-folic acid groups.◦ CVD mortality rates at the first year and in subsequent years (after a stroke or after a CHD) were obtained from other studies [23–25]. Because no statistical difference was found in the CVD fatality rate between the enalapril and the enalapril-folic acid groups (p > 0.99), we assumed patients had the same chance of dying once they had a stroke.

◦ Age- and sex-specific mortality rates for non-CVD deaths were based on the Chinese life tables obtained from the sixth nationwide census [26]. Because no statistical difference was found in the risk of non-CVD death (p = 0.44) between treatment strategies, we assumed no difference in non-CVD mortality rates between the enalapril and the enalapril-folic acid groups.

◦ CVD mortality rates at the first year and in subsequent years (after a stroke or after a CHD) were obtained from other studies [23–25]. Because no statistical difference was found in the CVD fatality rate between the enalapril and the enalapril-folic acid groups (p > 0.99), we assumed patients had the same chance of dying once they had a stroke.

Microsimulation model. a 1-year probability of first CVD event. b Transition to post-CVD event occurring after one cycle (1 year) with a probability of 100% (tunnel state). c CVD relapse during the first year. d 1-year probabilities of subsequent CVD events (stroke relapse after first year, post-stroke to CHD, CHD relapse after first year, and post-CHD to stroke). e Transition to death (absorbing state). CVD, cardiovascular disease; CHD, coronary heart disease

Main assumptions for the cost-effectiveness analysis

1 −  exp ((ln(1 − P))/10)

P = 1 − S(t)exp(f[x, M])

f(x, M) = β1 ∗ (x1 − M1) + … + βp ∗ (xp − Mp)

$0.09 ($0.03–$0.22)

￥0.56 (￥0.2–￥1.44)

$0.74

￥4.75

$0.13 ($0.11–$0.38)

￥0.83 (￥0.72–￥2.43)

$0.08 ($0.07–$0.54)

￥0.53 (￥0.48–￥3.48)

$0.25 ($0.14–$0.47)

￥1.60 (￥0.91–￥3.06)

$0.29 ($0.27–$0.30)

￥1.88 (￥1.72–￥1.95)

$0.03 ($0.02–$0.05)

￥0.21 (￥0.16–￥0.32)

$0.08 ($0.03–$0.65)

￥0.50 (￥0.17–￥4.19)

$0.04 ($0.03–$0.24)

￥0.24 (￥0.19–￥1.57)

$0.05 ($0.05–$0.08)

￥0.34 (￥0.31–￥0.50)

$1529.18 (± 20%)

￥9863.20 (± 20%)

$3207.55 (± 20%)

￥20,688.70(± 20%)

$4696.39 (± 20%)

￥30,291.70(± 20%)

$200.93 (± 20%)

￥1296.00 (± 20%)

$7.91 (± 20%)

￥51.00 (± 20%)

$465.12 (± 20%)

￥3000.00 (± 20%)

aPatients with disability after stroke

The model was developed using TreeAge Pro software (TreeAge Software, Inc., Williamstown, MA, USA) (Additional file 2: Fig. S1) and validated by comparing first stroke rates with the 4.5-year in-trial data (Additional file 2: Fig. S2).

Medical care costs included pre-CVD drug costs, CVD costs (cost incurred through the first 30 days after a CVD event and for the rest of the first year), and post-CVD costs (cost incurred after the first year) and were assessed from the Chinese healthcare sector perspective. Because the primary endpoint of the CSPPT was first stroke, follow-up was stopped when a stroke occurred. Health care resource use in the in-trial analysis included only pre-stroke drug costs and the first 30 days of hospitalization after CVD events.

Information on pre-CVD medication use and adherence, including the two study drugs (enalapril, enalapril-folic acid) and concomitant medications, was collected for all patients in the CSPPT over a median follow-up period of 4.5 years. Concomitant medications included the five standard antihypertensive drug classes (angiotensin converting enzyme inhibitors, beta blockers, angiotensin II receptor antagonists, long-acting calcium channel blockers, and diuretics), antiplatelet drugs, lipid-lowering drugs, and hypoglycemic drugs. Pre-CVD drug costs were calculated by multiplying the average annual cost of pre-CVD drugs by the number of follow-up years over the in-trial period or the lifetime period and were adjusted by the average treatment adherence time and the percentage of concomitant medication use reported in the CSPPT. The unit price of each medication pill was estimated according to market share values and the National Centralized Drug Procurement (NCDP) prices or the median bidding price of local official documents from 2021 (Additional file 1: Table S3) [27, 28].

The costs of a CVD event during the first 30-days of hospitalization included stroke-related costs (ischemic stroke and hemorrhagic stroke) and CHD-related costs, which were sourced from the China Health Statistics Yearbook 2021 [29]. Treatment procedures for the rest of the first year and the post-CVD phase followed the clinical pathway of rehabilitation for stroke and medication guidance for CHD, respectively [31, 32]. Costs for each treatment procedure were calculated by multiplying the item counts by their respective unit prices, determined by the average prices of the National Development and Reform Commission of the People’s Republic of China in 2021 (Additional file 1: Table S4) [32, 37]. Taking into account that some people may suffer from disability after stroke, we introduced a disability rate and a rehabilitation rate after stroke based on published literature, to adjust for the costs of the rest of the first year and the costs of post-CVD (for cost Estimation see (Additional file 1: Cost estimates for the rest of the first year or in post-CVD phase) [8, 36].

Costs were reported in US dollars and Chinese renminbi (RMB) according to the 2021 exchange rate ($1.00 =6.45 RMB) [30]. All costs were converted to 2021 with the medical care component of the Consumer Price Index (CPI) [38].

Utility scores [range 0 (equivalent to death) to 1 (equivalent to perfect health)] were obtained from the CSPPT and the medical literature. Utility values of pre-CVD for enalapril or enalapril-folic acid treatment were calculated by using the EuroQOL five-dimension, three-level questionnaire (EQ-5D-3L), which was completed by the CSPPT patients at the exit visit. The calculation formula was based on the Chinese specific EQ-5D-3L value set system [39]. The health state utility scores of stroke (primary and relapse), CHD (primary and relapse), and post-CVD that are presented in Table 3 were derived from published research [31–35]. Quality-adjusted life-years (QALYs) were calculated by multiplying the length of time in a health state by the utility scores associated with that health state.

Cost-effectiveness was expressed as incremental cost-effectiveness ratios (ICERs), which were calculated as the incremental costs divided by the incremental life-years and the incremental QALYs between the two treatments of enalapril-folic acid vs. enalapril. All future costs, life-years, and QALYs were discounted at 5% annually.

The willingness-to-pay (WTP) threshold for cost-effectiveness was set on the WHO-CHOICE-recommended gross domestic product (GDP) per capita-indexed threshold [40]. A treatment strategy was considered “highly cost-effective” if the WTP for cost-effectiveness was less than one time the GDP per capita; “cost-effective” if the WTP was less than three times the GDP per capita; otherwise, the strategy was considered “not cost-effective.” The GDP per capita for China in 2021 was assumed to be $12,544 (80,976 RMB) and the WTP was assumed to be $37,663 (242,928 RMB) [30].

The hazard ratios for first stroke in pre-specified subgroups (including sex, age, smoking status, diabetes mellitus, systolic blood pressure at baseline, total cholesterol, high density lipoprotein-cholesterol (HDL-C), the MTHFR C677T polymorphism, folate levels and homocysteine) have been published previously. The pre-estimated λ, γ parameters, and hazard ratios (Additional file 1: Table S5) within each subgroup were used for re-calculating the annual probability of first stroke. The relevant distributions of risk factors in each subgroup were refitted based on the CSPPT data and were used to obtain the annual probability of CHD. Other parameters of the model in the subgroup analysis, such as CVD relapse rates, mortality rates, costs, and utilities, were the same as in the base case analysis.

We performed extensive sensitivity analyses to assess the robustness of our results to plausible variation in model parameters including utility scores, HRs, and discount rates. One-way sensitivity analyses were performed for each model parameter and displayed as a tornado diagram. The upper and lower bounds of drug costs were derived from the National Centralized Drug Procurement prices from different manufacturers or from bidding prices in different provinces from 2021 [41]. The price range of rehabilitation treatment was derived from prices set by the Development and Reform Commission from various regions in China [42, 43]. The discount rate was set to vary from 0 to 8%. Ranges of other parameters were obtained from reported 95% CIs or by ± 20% of the base-case values if a 95% CI was not available. Probabilistic sensitivity analyses were also performed to evaluate the impact of simultaneous changes in all of the above model parameters by means of Monte Carlo simulation (10,000 replicates). Distributional assumptions for each model parameter are summarized in Table 3.

In China, pharmaceutical companies provide a 50% discount of their original price to eligible patients through the Patients Aid Program (PAP). Therefore, the impact of the PAP was also evaluated in the scenario analyses. Additionally, the base case analysis assumed that the stroke HR for enalapril-folic-acid versus enalapril was fixed throughout the lifetime (HR = 0.79). In scenario analyses, the survival benefit of enalapril-folic acid was assumed to either (a) remain constant for 10 years, with no benefit beyond year 10, or (b) remain constant for 5 years only with no benefit beyond year 5.

## 结果 / Results

Table 1 presents the results of the in-trial cost-effectiveness analyses per person. The mean costs of study drugs were $1170.46 (7549.47 RMB) and $137.41 (886.29 RMB) in the enalapril-folic acid and enalapril groups, respectively. The ischemic stroke costs and hemorrhagic stroke costs were both lower for the enalapril-folic acid group, but the costs of CHD events were higher for the enalapril-folic acid group. Total in-trial mean cost remained significantly higher for the enalapril-folic acid group [$923.74 (5958.14 RMB) versus $217.71 (1404.22 RMB) for the enalapril group, difference: $706.03 (4553.92 RMB)]. The QALY was 0.016 higher in the enalapril-folic acid group during the in-trial period, indicating that the addition of folic acid to enalapril offered a benefit in quality-adjusted life-years. In the in-trial period, the ICER of enalapril-folic acid compared with enalapril was $44,127.13 (284,620 RMB) per QALY, which was higher than the WHO recommended willingness-to-pay threshold of 3 times the GDP per capita ($37,663; 242,928 RMB).Table 1In-trial cost-effectiveness resultsOutcomesEnalapril-folic acid (n = 10348)Enalapril (n = 10354)∆ (Enalapril-folic acid–Enalapril) (95%CI)P valueEnalapril/enalapril-folic acid cost ($/￥)$1170.46￥7549.47$137.41￥886.29$1033.05 (1029.51 to 1036.59)￥6663.18 (6640.35 to 6686.01)< 0.001Concomitant drug cost ($/￥)$75.13￥484.60$73.01￥470.91$2.12 (− 2.20 to 6.44)￥13.69 (− 14.16 to 41.54)0.335Stroke-related costs ($/￥) Ischemic stroke$32.95￥212.55$43.13￥278 .16$− 10.17 (− 16.66 to − 3.68)￥− 65.61 (− 107.45 to − 23.76)0.002 Hemorrhagic stroke$17.98￥115.96$19.21￥123.88$− 1.23 (− 7.86 to 5.41)￥− 7.93 (− 50.72 to 34.87)0.717Other CVD-related costs ($/￥)$10.89￥70.25$9.98￥64.36$0.91 (− 5.11 to 6.94)￥5.89 (− 32.97 to 44.75)0.766Total costs ($/￥)$923.74￥5958.14$217.71￥1404.22$706.03 (695.28 to 716.79)￥4553.92 (4484.56 to 4623.27)< 0.001QALY3.923.900.016 (− 0.001 to 0.033)0.064ICER ($/QALY)/(￥/QALY)$44,127.13￥284,620QALY quality-adjusted life-year, ICER incremental cost-effectiveness ratio

In-trial cost-effectiveness results

$1170.46

￥7549.47

$137.41

￥886.29

$1033.05 (1029.51 to 1036.59)

￥6663.18 (6640.35 to 6686.01)

$75.13

￥484.60

$73.01

￥470.91

$2.12 (− 2.20 to 6.44)

￥13.69 (− 14.16 to 41.54)

$32.95

￥212.55

$43.13

￥278 .16

$− 10.17 (− 16.66 to − 3.68)

￥− 65.61 (− 107.45 to − 23.76)

$17.98

￥115.96

$19.21

￥123.88

$− 1.23 (− 7.86 to 5.41)

￥− 7.93 (− 50.72 to 34.87)

$10.89

￥70.25

$9.98

￥64.36

$0.91 (− 5.11 to 6.94)

￥5.89 (− 32.97 to 44.75)

$923.74

￥5958.14

$217.71

￥1404.22

$706.03 (695.28 to 716.79)

￥4553.92 (4484.56 to 4623.27)

$44,127.13

￥284,620

QALY quality-adjusted life-year, ICER incremental cost-effectiveness ratio

Table 2 shows the results of the lifetime cost-effectiveness analyses for base case and scenarios using a microsimulation model. Total lifetime cost remained significantly higher (by $1633.84; 10,538.27 RMB) for the enalapril-folic acid group ($3903.69 versus $2269.85). The enalapril-folic acid treatment offered an advantage over the enalapril treatment of 0.06 QALY or 0.03 life-year. The ICER for the enalapril-folic acid treatment, compared to the enalapril treatment, was $26,066.13 (168,126.54 RMB) per QALY gained and $61,770.73 (398,421.21 RMB) per life-year gained, respectively. When the unit price of enalapril-folic acid was reduced by 50% under the PAP scenario, the ICER for lifetime enalapril-folic acid treatment strategies was reduced to $8279.10 (53,400.20 RMB) per QALY. Scenario analyses of the survival benefit of enalapril-folic acid show that, when the survival benefit of enalapril-folic acid was assumed to remain constant through 10 years, the ICER for lifetime enalapril-folic acid treatment was $33,012.65 (212,931.59 RMB) per QALY, less than the threshold of 3 times the GDP per capita; however, when the duration of benefit was limited to 5 years, the ICER for enalapril-folic acid treatment increased to $45,246.92 (291,842.63 RMB) per QALY, which is greater than the WHO-recommended threshold.Table 2Lifetime cost-effectiveness results for base case and scenario analysesOutcomesCost ($/￥)Effectiveness (QALY or life-years)ICER% < 1 time of GDP/capita per QALY% < 2 times of GDP/capital per QALY% < 3 times of GDP/capita per QALYEnalapril-folic acidEnalapril∆Enalapril-folic acidEnalapril∆Base case analyses Quality-adjusted life-year$3903.69￥25,178.80$2269.85￥14,640.53$1633.84￥10,538.2711.0611.000.06$26,066.13￥168,126.542.6%47.6%74.5% Life-year$3903.69￥25,178.80$2269.85￥14,640.53$1633.84￥10,538.2722.5922.560.03$61,770.73￥398,421.216.4%27.1%38.6%Scenario analyses Enalapril-folic acid at 1/2 cost$2788.79￥17,987.70$2269.85￥14,640.53$5018.94￥3347.1611.0611.000.06$8279.10￥53,400.2073.8%91.3%94.7% Enalapril-folic acid has no benefit beyond year 5$4034.69￥26,023.75$2251.04￥14,519.21$1783.66￥11,504.6111.04511.010.04$45,246.92￥291,842.6309.4%32.7% Enalapril-folic acid has no benefit beyond year 10$3965.16￥25,575.28$2247.02￥14,493.28$1718.15￥11,082.0711.0611.010.05$33,012.65￥212,931.590.1%29.5%59.5%QALY quality-adjusted life-year, ICER incremental cost-effectiveness ratio

Lifetime cost-effectiveness results for base case and scenario analyses

$3903.69

￥25,178.80

$2269.85

￥14,640.53

$1633.84

￥10,538.27

$26,066.13

￥168,126.54

$3903.69

￥25,178.80

$2269.85

￥14,640.53

$1633.84

￥10,538.27

$61,770.73

￥398,421.21

$2788.79

￥17,987.70

$2269.85

￥14,640.53

$5018.94

￥3347.16

$8279.10

￥53,400.20

$4034.69

￥26,023.75

$2251.04

￥14,519.21

$1783.66

￥11,504.61

$45,246.92

￥291,842.63

$3965.16

￥25,575.28

$2247.02

￥14,493.28

$1718.15

￥11,082.07

$33,012.65

￥212,931.59

QALY quality-adjusted life-year, ICER incremental cost-effectiveness ratio

The results of the one-way sensitivity analyses are summarized in Fig. 1. The model was most sensitive to the HR for stroke with enalapril-folic acid vs. enalapril monotherapy. The ICER for enalapril-folic acid exceeded the WHO-recommended threshold for acceptable cost-effectiveness in China at a HR >0.84, and at the upper bound of the 95% CI for the HR, the ICER for enalapril-folic acid was $96,887.41 (624,923.79 RMB) per QALY gained. Other variables, such as adherence rate of enalapril-folic acid and enalapril treatment, discount rate, unit price of enalapril, and disability rate after stroke, had a moderate or mild impact on the economic outcomes.Fig. 1Tornado plot demonstrating the impact of varying each of the model parameters on the ICER for enalapril-folic acid versus enalapril

Tornado plot demonstrating the impact of varying each of the model parameters on the ICER for enalapril-folic acid versus enalapril

Our probabilistic sensitivity analyses demonstrated that the strategy of enalapril-folic acid compared with enalapril was cost-effective in 74.5% of simulations at a WTP threshold of 3 times the GDP per capita ($37,663; 242,928 RMB) (Fig. 2). The impact of alternative assumptions regarding the cost and duration of benefit of enalapril-folic acid are displayed as cost-effectiveness acceptability curves in Fig. 3. When outcomes were assessed under the PAP scenario, the probability that enalapril-folic acid would be cost-effective improved to 94.7%. The cost effectiveness of enalapril-folic acid was also sensitive to the duration of benefit compared with enalapril monotherapy. When we assumed that enalapril-folic acid would continue to incur costs but have no benefit after 10 years, the probability of enalapril-folic acid being cost-effective based on a threshold of 3 times the GDP per capita fell to 59.5%, and when we assumed that enalapril-folic acid would have no effect after 5 years, the probability of its being cost-effective fell to only 32.7%.Fig. 2Scatterplot of enalapril-folic acid vs enalapril in the cost-effectiveness planeFig. 3Cost-effectiveness acceptability curve of enalapril-folic acid versus enalapril. Cost-effectiveness acceptability curve of enalapril-folic acid versus enalapril, for the base case (red line), life year (blue), and scenario analyses: no effect of enalapril-folic acid after 5 years (green); no effect of enalapril-folic acid after 10 years (orange); enalapril-folic acid at 1/2 price (gray). QALY, quality-adjusted life-year

Scatterplot of enalapril-folic acid vs enalapril in the cost-effectiveness plane

Cost-effectiveness acceptability curve of enalapril-folic acid versus enalapril. Cost-effectiveness acceptability curve of enalapril-folic acid versus enalapril, for the base case (red line), life year (blue), and scenario analyses: no effect of enalapril-folic acid after 5 years (green); no effect of enalapril-folic acid after 10 years (orange); enalapril-folic acid at 1/2 price (gray). QALY, quality-adjusted life-year

Results from prespecified subgroup analyses are summarized in Additional file 1: Table S1. The ICER of males was $14,091.71 (90,891.71 RMB) per QALY gained and the probability that enalapril-folic acid therapy would be more cost-effective at a threshold ICER of 3 times the GDP per QALY was 92.0%; in contrast to what has been shown in females; however, the ICER was $65,634.34 (423,341.49 RMB) per QALY, which was far beyond the threshold ICER of 3 times the GDP per QALY and the probability at that threshold was only 13.0%. The ICER for people aged 55 to 64 was lower [$15,956.14 (102,917.10 RMB) per QALY], with a 91.1% probability below the threshold ICER of 3 times the GDP per QALY, compared to people younger than 55 years [$64,893.23 (418,561.33 RMB) per QALY] or older than 65 years [$56,003.24 (102,917.10 RMB) per QALY]. In the smoking status subgroup, the cost-effectiveness was more favorable in former smokers [$18,146.57 (117,045.38 RMB) per QALY] compared with current smokers [$24,746.65 (159,615.89 RMB) per QALY]. For people with the MTHFR CT genotype, the probability was 2.6% at a threshold ICER of 3 times the GDP per capita for all patients, while the probabilities of people with the MTHFR CC and TT genotypes being below the threshold were both over 90% at that threshold. Compared to patients with lower risk factor levels, the lifetime ICER was more favorable in patients with higher risk factor levels (diabetes, higher SBP, higher total cholesterol, higher HDL-C, lower folate, and higher homocysteine).

## 讨论 / Discussion

The CSPPT is the first, large-scale, randomized, controlled trial to demonstrate that treatment with enalapril-folic acid resulted in a significant reduction of primary stroke compared with treatment with enalapril alone for patients with hypertension [6, 10]. The results from this prospectively designed health economic analysis carried out alongside the CSPPT revealed that the ICER for enalapril-folic acid versus enalapril was $44,127.13 (284,620.00 RMB) per QALY gained during the 4.5-year follow-up period and $26,066.13 (168,126.54 RMB) per QALY gained over the remaining lifetime. These results were robust to a broad range of sensitivity analyses over a series of alternative assumptions, with an acceptability rate of 74.5% at the WHO-recommended WTP threshold of $37,663 (242,928 RMB) per QALY gained. In terms of the general population, these results suggest that enalapril-folic acid therapy is a cost-effective strategy for primary stroke prevention in hypertensive patients in China.

The subgroup analyses revealed some heterogeneity in the ICER estimates. The results indicated that, lifetime enalapril-folic acid treatment generally yielded ICERs below the “cost-effective” (< 3 times the GDP/capita) threshold for most patients, and some patients were even in the “highly cost-effective” range, such as patients with higher-risk factor levels (diabetes, baseline SBP ≥ 180 mm Hg, total cholesterol ≥ 6.2 mmol/L, or folate < 5.6 ng/mL). In a resource-constrained healthcare environment, targeting therapy to these subgroups of patients would be a highly efficient strategy for maximizing health benefits while minimizing the incremental costs of therapy. On the other hand, there were several subgroups of patients (e.g., female patients, aged < 55 or ≥ 65 years, MTHFR CT genotype, SBP < 160 mm Hg, total cholesterol < 5.2 mmol/L, folate ≥ 10.5 ng/mL, or homocysteine ≦ 10.0 μmol/L), for whom lifetime enalapril-folic acid therapy is “not cost-effective” (ICERs > 3 times the GDP/capita). These results reflect that for younger female patients with the MTHFR CT genotype and lower-risk factor levels, prolonged enalapril-folic acid therapy is not an economical strategy. Since the reduced sample sizes in each subgroup may lead to greater uncertainty, further studies are warranted to confirm the clinical and cost-effectiveness of enalapril-folic acid therapy for patients with different levels of risk factors of stroke at baseline.

Many previous studies have evaluated the cost-effectiveness of strategies for the primary prevention of CVD [11–13]. However, few studies have investigated the cost-effectiveness of CVD prevention in China. Xie et al. showed that intensive hypertension control would prevent about 2.2 million CHD events and 4.4 million stroke events for all hypertensive patients in 10 years. Additionally, intensive hypertension treatment has been shown to be more cost-effective than standard hypertension control in China, with an ICER of $1190 per QALY [14]. Basu et al. predicted that the simple benefit-based tailored treatment (BTT) strategy was more effective than the treat-to-target (TTT) or hybrid strategies in reducing CVD mortality, with $142–$182 less per disability-adjusted-life-years gained (DALY) than either the TTT or hybrid strategies [15]. In another study, Gu et al. demonstrated that it is necessary to provide low-cost essential antihypertensive medicines to expand hypertension treatment. Treating all hypertensive patients (primary and secondary prevention) would prevent about 800,000 CVD events annually and is borderline cost-effective compared with treating only CVD and stage two patients ($13,000 per QALY gained in 2015) [16].

These previous studies, as well as guidelines from the American Heart Association (AHA), confirm the cost-effectiveness of traditional strategies for CVD prevention such as the management of blood pressure, lipid levels, and glucose levels, as well as some other well-recognized risk factor controls [17–19]. According to our study, folic acid supplementation, as a novel CVD preventive strategy, has proven to be cost-effective, especially for patients with specific characteristics. In addition, our study has the unique aspect that it does not rely solely on epidemiologic modeling but is based largely on empirical outcomes data from a large, prospective randomized clinical trial.

## 结论 / Conclusion

Based on empirical data from the CSPPT, we discovered that enalapril-folic acid therapy is a more cost-effective strategy for primary stroke prevention than enalapril alone among most hypertensive patients in China. Males between the ages of 55 and 65 who have a higher risk of stroke (e.g. diabetes, higher SBP, higher total cholesterol, higher HDL-C, lower folate, and higher homocysteine levels at baseline) drive the outcomes. Some subgroups with a potential lower risk of stroke may not be cost-effective. However, under the Patients Aid Program which offers a significant reduction in drug price, enalapril-folic acid therapy probably would be cost-effective in more patients of more subgroups. Although our findings should be interpreted with caution, as China bears the largest hypertensive population and stroke incidence of any country, these findings can inform health care policy and treatment guidelines. Finally, our study may also serve as a model for other countries with similar economic status and demographic characteristics, especially those whose populations have low folate intake.
