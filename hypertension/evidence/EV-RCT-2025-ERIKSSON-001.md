---
type: RCT
language: en
status: reviewed
extracted_by: api+llm
authors:
- Eriksson JW
- Fanni G
- Lundqvist MH
- Jansson S
- Rådholm K
- Sofizadeh S
- Patsoukaki V
- Nilsson A
- Lindholm D
- Rolandsson O
- Norhammar A
- Granstam E
- Eliasson B
- Bennet L
- Sundström J
tags:
- type 2 diabetes
- metformin
- SGLT2 inhibitor
- microvascular complications
- RRCT
- decentralized trial
- blinded endpoint
title:
  zh: null
  en: SGLT2 inhibitor or metformin as standard treatment in early‐stage type 2 diabetes?
    Baseline data in SMARTEST, a novel, decentralised, register‐based randomised trial
    on prevention of diabetic complications
year: 2025
journal: Diabetes, obesity & metabolism
pmid: '41311237'
doi: 10.1111/dom.70320
pico:
  population:
    condition: early type 2 diabetes (<4 years duration), no major cardiovascular
      or renal disease
    sample_size: 2072
  intervention:
    name: dapagliflozin 10 mg/day
  comparison:
    name: metformin individualized dose
  outcomes:
    primary:
    - name: time to first event of myocardial infarction, stroke, heart failure (MACE),
        microvascular complications or all-cause death
      effect_size:
        metric: event rate
        value: 11.7
        ci_low: 0
        ci_high: 0
        p: 0
risk_of_bias:
  tool: RoB2
  overall: some_concerns
grade:
  level: moderate
id: EV-RCT-2025-ERIKSSON-001
study_type: RCT
---



## English Abstract

Metformin has hitherto not been proven superior to other type 2 diabetes (T2D) medications for the prevention of organ complications. The aim of this study is to report baseline data and blinded interim analyses in the register‐based randomised clinical trial (RRCT) SMARTEST, which compares metformin and the SGLT2 inhibitor dapagliflozin in early T2D. We also present learnings from the novel decentralised methodology of this first RRCT in diabetes care.

Participants with T2D since <4 years and without major cardiovascular or renal disease were included at 36 centres across Sweden between 2019 and 2023 at on‐site visits or via remote inclusion using digital informed consent. Participants were randomised 1:1 to open‐label dapagliflozin 10 mg/day or metformin at an individualised dose, and they are followed for 2–6 years, with blinding of researchers to endpoints per treatment arm. The composite primary endpoint is time to first event of: myocardial infarction, stroke, heart failure (MACE), appearance or progression of microvascular complications or all‐cause death. These events are collected from the Swedish National Diabetes Register and the National Patient Register using automated extraction.

A total of 2072 patients, mean age 61.2 years, 39% women, entered randomised treatment. Signs of nephropathy, retinopathy and foot‐at‐risk were found in 6.1%, 13.2%, and 5.7%, respectively. Hypertension was present in 64.4%, and dyslipidaemia in 57.1%. In blinded interim analyses at a mean follow‐up time of 19.0 months, the preliminary event rate of the primary composite endpoint was 11.7/100 patient‐years (py) in the whole study population, mainly driven by microvascular complications. In contrast, rates of cardiovascular events and all‐cause death were 0.6 and 0.3/100 py, respectively.

This decentralised RRCT in newly onset T2D demonstrates a highly feasible option for large‐scale trials in the primary care setting, enabling representative participant recruitment. Blinded interim analyses showed a low risk of MACE or death, but unexpectedly high rates of microvascular complications. Study completion is event‐driven and is expected by January 2026. The study will challenge or reinforce the current metformin paradigm in early T2D. (EUDRA‐CT number 2019‐001046‐17; EU number 2024‐516228‐33‐00; ClinicalTrials.gov Identifier: NCT03982381)

## 背景 / Background

Type 2 diabetes (T2D) is a major public health concern affecting almost 10% of the global population, and its prevalence is still rising.
1
, 
2
 Its health burden is associated with long‐term vascular complications: (1) macrovascular complications, that is, incident atherosclerotic cardiovascular disease (CVD), including coronary artery disease, cerebrovascular disease, and peripheral artery disease; and (2) microvascular complications, including diabetic retinopathy, nephropathy, and neuropathy.
3
, 
4
, 
5
 Other common diabetic complications, such as heart failure and diabetic foot lesions, involve vascular and metabolic mechanisms.
4
, 
6
 T2D also represents a remarkable economic burden, estimated to account for more than 2% of the global GDP by 2030.
7
 From the onset of diabetes onwards, it is thus important to reduce risk factors for long‐term complications. Notably, there is no convincing evidence that metformin, the current first‐line treatment for T2D, offers superior prevention of diabetes complications.
8
 Few head‐to‐head trials have directly compared antidiabetic agents with respect to macro‐ and/or microvascular complications in early T2D. Superiority has typically not been demonstrated, for example in trials on DPP4 or SGLT2 inhibitors versus glimepiride.
9
, 
10
 Of note, sodium/glucose cotransporter 2 (SGLT2) inhibitors have repeatedly been shown to reduce mortality and cardiorenal morbidity in large clinical outcome trials enrolling patients with T2D and high cardiovascular risk, but also in patients with kidney or heart failure without diabetes.
11
, 
12
, 
13
, 
14
, 
15
, 
16
, 
17
, 
18
, 
19
, 
20
 There were also similar findings in observational register studies.
21
, 
22
 It is possible that such beneficial effects also apply to patients with early‐stage T2D without advanced complications, but this has hitherto not been studied.

In Sweden, T2D care is largely provided within primary care, which has been a challenging setting to perform controlled trials. In recent years, however, the register‐based randomised controlled trial (RRCT) design has emerged as a cost‐effective alternative to traditional RCTs and has been previously successfully employed in several fields of medicine, including cardiology, orthopaedic surgery, and gynaecology.
23
, 
24
, 
25
, 
26
 Endpoint data collection from health care registers enables large‐scale clinical trials in real‐world clinical care with limited research resources.
27

The ongoing SMARTEST study (SGLT2 inhibitor or Metformin As standaRd Treatment of Early‐Stage Type 2 diabetes) is the first RRCT within the diabetes field. The study is largely performed in primary care and aims to assess whether the SGLT2 inhibitor dapagliflozin is superior to metformin in preventing diabetes micro‐ and macrovascular complications, as well as premature death in individuals with early‐stage T2D.
28
 Outcomes are captured in Swedish health care registers including the national Swedish Diabetes Register (NDR) and the Swedish National Patient Register (NPR).
29
, 
30
, 
31

In this article, we present the baseline clinical characteristics of the study participants with early‐stage T2D who entered the SMARTEST study. We highlight the benefits of the RRCT in T2D care and also present novel options for remote participant recruitment.

## 方法 / Methods

We have reported the details of the study design in a previous publication.
28
 Briefly, SMARTEST is a prospective randomised open‐label blinded endpoint trial (PROBE) study, mainly performed in a real‐world primary care setting. It is an investigator‐initiated multicentre study with Uppsala University as the sponsor. Thirty‐one out of 36 total study sites were primary care centres located across Sweden. An overview of the study design is shown in Figure 1.

Schematic overview of study design.

We recruited participants via advertisement or contact from their regular health care units. Following pre‐screening by telephone, eligible participants came to a screening visit at a study site. Alternatively, a video visit with remote blood sampling and clinical examination at the local primary health care was performed (see below). Eligibility was assessed according to the following inclusion criteria: age over 18 years, diagnosis of T2D according to WHO criteria, diabetes duration less than 4 years, BMI between 18.5 and 45 kg/m2, and pharmacological treatment with one oral antidiabetic drug only or with no pharmacological treatment at all. Participants and their primary health care centre had to take part in the Swedish National Diabetes Register (NDR) and accept individual data collection from the Swedish national population and health care registers, and medical records. The exclusion criteria were: known or suspected other form of diabetes than type 2; more than 4 weeks of ongoing or previous treatment with insulin, GLP‐1 receptor agonists, SGLT2‐inhibitors, or a combination of any diabetes medications; HbA1c over 70 mmol/mol for patients on pharmacological treatment or over 80 mmol/mol without pharmacological treatment; contraindication to treatment with either metformin or dapagliflozin or unacceptable risk with either treatment as assessed by the investigator; established diagnosis of myocardial infarction, angina pectoris, stroke, peripheral arterial disease, or heart failure; ongoing foot ulcers; any serious disease with life expectancy deemed to be less than 4 years; eGFR <60 mL/min × 1.73 m2 (according to CKD‐EPI 2009; i.e., CKD Stage 3 or worse); a condition indicating that the patient would be non‐compliant or unsuitable for the study medication as judged by the investigator (e.g., serious psychiatric disorders or alcohol or substance abuse); pregnancy, breastfeeding, or women of childbearing potential without adequate anticonception; involvement in the planning and/or in the conduct of the study; ongoing participation in another clinical trial.

Blood samples were allowed with random timing, that is, largely non‐fasting, and analysed according to local clinical routine using validated methods. Body weight and height were measured without shoes in light clothing. Blood pressure was measured to the nearest 2 mmHg after 5 min of resting in the sitting position.

If the participant was judged eligible, a computerised random assignment was initiated, resulting in treatment allocation, which typically took place during a telephone call within 2 weeks after the eligibility assessment. The participant was given oral and written information about the allocated treatment, and an electronic prescription was sent for pharmacy dispensing. Researchers were blinded to the randomised treatment allocation and associated endpoints, but the study participants and local primary health care physicians and staff were not blinded. Study medication was delivered at Apoteket AB, the publicly owned and largest pharmacy organisation in Sweden. When a participant was included in the study, the recruiting study sites contacted the primary health care centre to inform them about study participation and protocol. Study participants continued the usual diabetes follow‐up according to guidelines, while maintaining the randomised treatment.

Participants were divided into two strata, each comprising at least 25% of the whole study cohort.

Stratum A included study participants with no previous or current history of treatment with pharmacological antidiabetic agents for longer than 4 weeks in total (drug‐naïve stratum). Stratum B included participants with current or previous treatment on a single pharmacological antidiabetic medication (monotherapy stratum) for more than 4 weeks. Within each stratum, participants were randomly assigned 1:1 to treatment with either 10 mg dapagliflozin once daily or with metformin at individualised doses.

The general treatment target was HbA1c <53 mmol/mol, but this could be adapted individually. When there was a need to add or change medication over time, metformin and SGLT2 inhibitors were avoided (unless strictly indicated), and other alternatives were recommended. Follow‐up was performed with telephone visits every 12th month, and additional contacts or visits took place when called upon by the participant or their health care providers. The routine follow‐up and clinical and laboratory assessments were performed according to national guidelines, usually twice, but at least once per year. Data were reported to the NDR at least annually. NDR has more than 90% coverage and includes data on microvascular diabetes complications (retina, foot, and kidney examinations), diabetes treatment, laboratory analyses, including HbA1c, lipids, eGFR, urinary albumin/creatinine ratio.
31
 Other treatments besides the study medication for diabetes, such as medications for hypertension, dyslipidaemia, and/or other conditions, were provided according to clinical practice and could be modified as needed. Additionally, health‐related quality‐of‐life questionnaires were distributed at the first‐ and second‐year follow‐up.

All hospitalisations and specialised outpatient care visits are registered in the Swedish Patient Register, hosted by the National Board of Health and Welfare; all deaths in the Swedish Population Register; and all prescribed drugs in the Swedish Prescribed Drug Register. All these registers have a near 100% coverage.
30
, 
32
, 
33
 Data collection for endpoints and adverse events relies primarily on source data from these and the NDR register.

The primary composite outcome aimed to reflect event‐free survival. Therefore, a composite endpoint was chosen, and it was defined as time‐to‐first‐event of one of the following: (1) all‐cause death; (2) non‐fatal myocardial infarction; or stroke (ischemic or haemorrhagic); or heart failure; or appearance or progression (according to established grading) of retinopathy, nephropathy (albuminuria, or CKD stage ≥3 and at least 10% reduction from baseline eGFR), or diabetic foot disease.

Secondary endpoints were (1) any component of the primary endpoint; (2) time to start of daily insulin treatment; (3) change in cardiometabolic risk factors (HbA1c, LDL‐cholesterol, BMI, systolic and diastolic blood pressure); and (4) health care costs and health‐related quality of life. Safety assessment was stipulated only regarding serious adverse events (SAEs) and AEs leading to study drug discontinuation.

Medical history and baseline data were assessed based on information provided by the participants, collected at the inclusion visit, or retrieved from electronic health records (EHR). Data were entered into an electronic case report form (Viedoc version 4, Viedoc Technologies AB, Uppsala, Sweden), and documentation was reported in the EHR.

A novel digital consent system (minforskning.se) was developed at Uppsala University during the recruitment period.
34
 It was used in the trial to make the consent process and management of consents safer, simpler, more sustainable, and more cost‐effective. This model for remote inclusion was initiated during the COVID‐19 pandemic, when the rate of inclusion in the trial decreased. The entry point of the system is a portal where potential study participants can access all relevant information about clinical research studies, consent to studies, access copies of their signed consents, and receive secure communication about their participation in a study. The consent process uses nationally accepted digital identification systems. Co‐signing of a study physician is made using the same nationally accepted digital IDs after the participant has completed their signing. Hence, the system not only collects a digital consent but also identifies the participant, as all nationally accepted digital IDs use the Swedish personal identification number. This facilitates linkage to all national registries and health data sources, as these also use the same personal identification number. Consents can be monitored remotely.

The digital consent procedure also allowed for other non‐traditional ways of enrolment. To collect the baseline data necessary for the trial, mobile teams were sent out. The team could consist of a study physician, a study nurse, or both. Consents were obtained via video by a study physician at a remote site (Uppsala) or on‐site by a mobile team study physician, and physical examination and blood samples were obtained by the mobile team study nurse, study physician, or other on‐site personnel.

At least twice per year, data on the trial population are extracted from the NDR and sent to the National Board of Health and Welfare for data linkage, as described in detail previously.
28
 Upon return, these data are sent to the NDR data manager, who summarises data on outcomes and adverse events, sends data on adverse events to sites for safety assessments, and sends data on outcomes and adverse events to the study statistician. The statistician sends these data to the data safety committee and discloses blinded summary data to the study leadership for observation of outcome rates.

All participants gave their written informed consent, which was signed either by hand or electronically, as described above. The study was conducted according to the principles of the Declaration of Helsinki and was approved by the Swedish Research Ethics Review Authority and the Swedish Medical Product Agency (Dnr: 2019‐01747 and 5.1‐2019‐21 111, respectively). There were amendments for minor changes, and in October 2024, the transfer according to the Clinical Trials Information System (CTIS) procedure of the European Medical Products Agency was completed (EU number 2024‐516228‐33‐00).

In early 2021, an option for remote inclusion and informed consent was approved and launched (see above). Further, several sub‐studies have been approved, which involve selected study sites and will report specific exploratory analyses.

The primary objective is to address the possible superiority of dapagliflozin over metformin. Using the Schoenfeld formula, the total number of events needed for 90% power to detect a hazard ratio of 0.8, at a two‐sided alpha level of 0.05, was calculated to be 844 for the primary composite efficacy endpoint. For the two key secondary composite efficacy endpoints, the power to detect a similar effect is estimated at 90% or above. No adjustment in sample size will be made due to dropouts since endpoints will be collected from registries providing near‐complete coverage of events for an intention‐to‐treat analysis.

Originally, the event rate for the primary composite endpoint was estimated to be 7 per 100 patient‐years, and 4300 patients were planned to be included in the study with a maximum duration of 4 years. However, blinded evaluations disclosed an event rate of the primary composite of approximately 12 per 100 patient‐years as of August 2023. In addition, recruitment was slower than anticipated, mostly because of the Covid‐19 pandemic, leading to a longer follow‐up time than planned, now approximately 24–72 months (average 45 months). Therefore, the final inclusion target was set to at least 2050 participants. The study will continue until 844 primary composite events have occurred. The study is expected to be completed in December 2025.

Randomisation was done using large permuted blocks within each of stratum A (N = 606) and B (N = 1466) and with a 1:1 ratio to dapagliflozin or metformin.

Baseline characteristics were summarised with both median and the interquartile range, and mean and standard deviation for continuous data, and proportions for categorical data (Table 1).

Baseline characteristics of randomised patients in the SMARTEST study.

Note: Data are from the inclusion visit. Stratum A: drug‐naïve participants. Stratum B: participants on monotherapy. Continuous variables are shown as mean (SD) and median (IQR). Categorical variables are presented as percentages (absolute frequency, n). Categorical variables were compared between stratum A and B with Pearson's chi‐square test, while continuous variables were analysed using the Wilcoxon rank‐sum test. Numbers of participants with missing data are shown in Table S1.

Abbreviations: ARB, angiotensin‐receptor blocker; BMI, body mass index; BP, blood pressure; eGFR, estimated glomerular filtration rate.

## 结果 / Results

The cohort of patients prescribed the randomised study medication consists of 2072 study participants. Of these, 606 (29%) drug‐naïve participants belong to stratum A, and 1466 (71%) belong to stratum B of whom 99% were on monotherapy with metformin. The rates of recruitment as well as composite events are shown in Figure 2. Initially, 2176 individuals attended the screening visit, but 104 were excluded, mostly because they did not meet the eligibility criteria.

Cumulative number of randomised participants and primary composite endpoint events over time. Data are from the study start in September 2019 until October 2023, when the recruitment target was reached.

Clinical characteristics of the study population are presented in Table 1. The mean age at inclusion was 61.2 years, and 39% of the study participants were women. More than 50% of participants had obesity (BMI ≥30). Around one‐third of the study participants reported moderate physical activity at least five times per week. Active smokers represented 10% of stratum A and 8% of stratum B.

HbA1c in stratum B was, on average, at optimal levels, with a mean of 45.3 mmol/mol. In participants belonging to stratum A, mainly newly diagnosed, the mean was somewhat higher as expected (49.6 mmol/mol). Pharmacological treatment for hypertension was ongoing in 64.5% and treatment for dyslipidaemia in 57.1% of the participants. The mean blood pressures were slightly above target levels (mean SBP 135 mmHg, mean DBP 82 mmHg). Inhibitors of the renin‐angiotensin‐aldosterone system were prescribed to more than half of the study cohort (angiotensin receptor blockers 33%, ACE inhibitors 20%). The mean LDL‐cholesterol was close to acceptable in stratum B (2.7 mmol/L) but higher in stratum A (3.3 mmol/L).

Renal function was generally normal in both strata. However, around 5% of the participants presented with microalbuminuria (urine creatinine‐to‐albumin ratio ≥3 mg/mmol) at the time of inclusion.

The number of participants with missing data is shown in Table S1.

At the coordinating study site (Uppsala University Hospital), 234 participants, out of 932 in total, were enrolled remotely at a video appointment with a study physician. Written information had been sent in advance, and a signed electronic informed consent was obtained from these participants. Medical history for eligibility assessment was obtained from the patients and their EHRs. Figure 3 illustrates the geographical distribution of the utilisation of this approach. In addition, 114 participants were enrolled by a mobile study physician from the coordinating site, travelling to a health care centre close to the participant's place of residence. A local nurse or a mobile research nurse supported blood sampling or anthropometric assessments. Altogether, a total of 348 participants (36%) at this site utilised either of these options for remote enrolment. The number of participants included over time at the Uppsala University Hospital study site is presented by visit type in Figure 4. Detailed data on remote recruitment are shown in Table S2.

Map of Swedish Regions showing the proportion of participants being included and giving consent remotely via video. The yellow dots represent the study sites (n = 36, listed in Appendix S1). The numbers identify the 21 Swedish Regions that are listed in Table S2.

Mode of participant inclusion at the Uppsala University Hospital study site: On‐site physical visits, video visits and by mobile team physician, respectively. Data show the number of subjects randomised over time until recruitment completion.

In blinded interim analyses, the preliminary event rate of the primary composite endpoint was 11.7/100 patient‐years (py) in the whole study population up to August 2023 (mean follow‐up time 19.0 months), and this was used to determine the final sample size of at least 2050 randomised participants and the time to close recruitment, stipulating randomisation no later than October 2023. The event rate of the primary composite endpoint is depicted in Figure 2 together with the recruitment rate. The combined rate of first microvascular complications, that is, either diabetic foot, retinopathy, micro/macro‐albuminuria or eGFR lowering (>10% together with CKD stage at least 3), was about 11 per 100 py, that is, higher than anticipated.
35
, 
36
 In contrast, the rate of non‐lethal major adverse cardiovascular events and all‐cause death was about 1/100 py (0.6 for cardiovascular events and 0.3 for death). No serious unexpected safety issues have been reported. The data safety monitoring committee (DSMC) performs evaluations twice per year of SAEs (mostly hospitalisations) as well as AEs leading to withdrawal of study medication. So far, there have not been any new safety signals, and the DSMC has recommended continuation of the study according to the study protocol.

## 讨论 / Discussion

We have designed and launched a register‐based decentralised clinical trial (RRCT) largely run in primary care. This is, to the best of our knowledge, the first RRCT conducted in the diabetes field. With the help of digital tools and mobile study staff for remote recruitment, enrolment, and randomisation, we could include patients with early‐stage T2D across the entire Sweden, including participants from scarcely populated areas with long distances to health care facilities. Based on blinded interim data, we found that the overall rates of major cardiovascular events and mortality were lower than previously reported for similar populations.
21
, 
22
, 
37
 In contrast, the incidence of microvascular complications was higher than expected.
35

Overall, our cohort includes participants with a median diabetes duration of around 1 year. Around 60% of the study participants were male, in line with the higher T2D prevalence reported in males.
38
 There was a high prevalence of cardiovascular risk factors, such as obesity, hypertension, and dyslipidaemia. More than half of the study population had a higher systolic blood pressure than the recommended level of <130 mmHg. Also, the LDL‐cholesterol level was over the recommended threshold according to Swedish guidelines (<2.5 mmol/L) in more than 50%, confirming that insufficient lipid‐lowering is a common problem in people with diabetes.
39

From a Swedish perspective, a large proportion were previous smokers (40%), and almost 1 out of 10 study participants was an active smoker by the time of inclusion, a greater proportion than in the general population.
40
 Notably, more than 5% presented with microalbuminuria at the time of inclusion, and more than 10% with retinopathy. Also, more than 5% of the study participants displayed early signs of diabetic foot problems, mainly peripheral sensory neuropathy. Such signs of early microvascular diabetes complications were present in both the monotherapy and, to a lesser extent, in the drug‐naïve stratum.

In line with the study scope and despite the high prevalence of several CV‐risk factors, our study cohort, that is, early T2D without serious complications, had less history of major cardiovascular disease than the general population with T2D.
41
 This distinguishes the SMARTEST study from previous outcome studies on SGLT2 inhibitors.
11
, 
12
, 
13
, 
14
, 
15
, 
16
, 
17
, 
18
, 
19
, 
20

We report a higher incidence rate of the primary composite endpoint than was expected based on available epidemiological data on diabetes complications,
21
, 
22
, 
35
, 
37
 and this might partly be due to underreporting of microvascular complications in previous studies.
42
 Thus, the rate of death and incidence of cardiovascular diseases were lower, whereas the rate of microvascular complications, in particular foot‐at‐risk and nephropathy,
35
, 
36
 was higher than anticipated. In Sweden, guidelines for diabetes care aim for control of modifiable risk factors beyond glycaemia. This involves dietary adjustments, physical activity, weight control, smoking cessation, and treatment of hypertension and dyslipidaemia, all of which may contribute to a reduction of CVD and mortality rates, as also observed in previous work.
42
 On the other hand, the high rates of emerging microvascular complications in our study might partly be explained by the stringent Swedish standardised screening program for early detection of such conditions.

No important safety alerts have so far been communicated by the data and safety monitoring committee. Serious adverse events were listed and reviewed at least twice yearly, and no suspected unexpected serious adverse events have been reported.

This clinical trial represents a joint effort between academia and the health care system, without the direct involvement of a pharmaceutical company. The study is conducted in a decentralised way, with a management team located in Uppsala and a national steering group with members from all medical universities and health care regions. There are in total 36 study sites across the country, of which 31 are primary healthcare centres (PHCs) and 5 are clinical research units at university hospitals (see Appendix S1 for the complete list of study sites). Over 100 PHCs contributed to participant recruitment and follow‐up.

In contrast to classical clinical trials, study drugs were dispensed at pharmacies as usual, everyday treatments upon a routine digital prescription, and not at specific study sites, allowing the trial to represent a real‐world health care scenario.

The RRCT design was possible since the investigational treatments had regulatory approval for long with well‐established efficacy and safety profiles. The collaboration model was based on close interactions between academic researchers and health care professionals, including a large network of collaborating PHCs. We propose that the learnings can be adopted for future large‐scale pragmatic trials in diabetes as well as in other disease areas.

The digital consent procedure allowed for video inclusion in a drug trial for the first time in Sweden, and this enabled continued inclusion during the COVID‐19 pandemic. This also allowed patients living far from trial sites to participate in this study, as exemplified by the remote enrolment of participants from all across the country. Altogether, this increased the inclusion rate at the ‘pilot site’, Uppsala University Hospital, where digital inclusion accounted for 36% of participants. This allowed individuals living in rural areas far away from the nearest study site to take part in the study, since physical enrolment would have probably hampered them from entering the study. This enhanced the study's feasibility and sustainability through reduced travel for study participants and study monitors.

The RRCT design relies on robust register data, and the validity of the Swedish National Diabetes Register has been demonstrated in comparison with EHR data.
29
 On the other hand, although very high, the coverage of register data utilised in the current trial is not complete. The RRCT approach allowed us to perform a nationwide large‐scale RCT, notably reducing the administrative and organisational burden of the study sites.
23
 This approach is highly cost‐effective compared to traditional RCTs. According to preliminary estimates, the total cost of this decentralised RRCT is about 10% of a regular RCT of similar size,
23
 but the patient‐related savings due to digital inclusions are not yet assessed. Also, the RRCT design enabled easier access for participants, partly reducing the risks of selection bias, for example, for individuals living far away from study sites.

On the other hand, there are also potential disadvantages of the RRCT approach. It poses a greater demand on central study coordination with respect to monitoring, data collection and validation. Furthermore, the RRCT is strictly dependent on the registers' reliability, in particular determined by the degree of coverage vis‐à‐vis the intended patient population, frequency and completeness of data entries as well as data validity. Failure to fulfil any of these aspects in a standardised and sustained manner will clearly jeopardise the successful completion and utility of an RRCT.

Moreover, the follow‐up of study participants in their regular health care setting, in this case primary care centres, requires careful planning. Since resources are limited, economic incentives are often needed to stimulate participation of PHCs, for example to allow for extra staffing.

## 结论 / Conclusion

The decentralised procedure for inclusion in the SMARTEST trial enables efficient trials in primary care patients with T2D, allowing study sites of different capacities to participate. The study conduct was simplified, and follow‐up was largely handled in routine primary health care thanks to the collection of study endpoints from national registers.

The SMARTEST study provides positive learnings on nationwide research networks, automated endpoint capture, and digital tools for remote participant recruitment. This facilitated the enrolment of a socioeconomically and geographically representative study population. The study can serve as a model to perform pragmatic and cost‐effective real‐world clinical trials in the diabetes field, as well as in other diseases areas, within the primary care setting.

The important research question on the choice of first‐line glucose‐lowering agent in T2D is currently unresolved, and the main results of the SMARTEST trial will provide important guidance in the near future. They may either reinforce the metformin paradigm or argue for an early introduction of SGLT2 inhibitors for better prevention of organ complications and premature death.
