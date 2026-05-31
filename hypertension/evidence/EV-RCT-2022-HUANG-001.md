---
type: RCT
language: en
status: reviewed
extracted_by: api+llm
authors:
- Huang X
- Cao T
- Chen L
- Li J
- Tan Z
- Xu B
- Xu R
- Song Y
- Zhou Z
- Wang Z
- Wei Y
- Zhang Y
- Li J
- Huo Y
- Qin X
- Wu Y
- Wang X
- Wang H
- Cheng X
- Xu X
- Liu L
tags:
- stroke prediction
- machine learning
- hypertension
- risk modeling
- random forest
- XGBoost
- logistic regression
- CSPPT
- nested case-control
title:
  zh: null
  en: Novel Insights on Establishing Machine Learning-Based Stroke Prediction Models
    Among Hypertensive Adults
year: 2022
journal: Frontiers in cardiovascular medicine
pmid: '35600480'
doi: 10.3389/fcvm.2022.901240
pico:
  population:
    condition: hypertension without prior stroke
    sample_size: 23270
  intervention:
    name: RUS-applied random forest with laboratory variables
  comparison:
    name: null model (sensitivity=0, specificity=100, mean AUC=0.643)
  outcomes:
    primary:
    - name: first stroke (nonfatal/fatal ischemic or hemorrhagic)
      effect_size:
        metric: AUC
        value: 0.624
        ci_low: 0.61
        ci_high: 0.64
        p: 0.001
risk_of_bias:
  tool: RoB2
  overall: some_concerns
grade:
  level: low
id: EV-RCT-2022-HUANG-001
study_type: COHORT
---



## English Abstract

Stroke is a major global health burden, and risk prediction is essential for the primary prevention of stroke. However, uncertainty remains about the optimal prediction model for analyzing stroke risk. In this study, we aim to determine the most effective stroke prediction method in a Chinese hypertensive population using machine learning and establish a general methodological pipeline for future analysis.

The training set included 70% of data (n = 14,491) from the China Stroke Primary Prevention Trial (CSPPT). Internal validation was processed with the rest 30% of CSPPT data (n = 6,211), and external validation was conducted using a nested case–control (NCC) dataset (n = 2,568). The primary outcome was the first stroke. Four received analysis methods were processed and compared: logistic regression (LR), stepwise logistic regression (SLR), extreme gradient boosting (XGBoost), and random forest (RF). Population characteristic data with inclusion and exclusion of laboratory variables were separately analyzed. Accuracy, sensitivity, specificity, kappa, and area under receiver operating characteristic curves (AUCs) were used to make model assessments with AUCs the top concern. Data balancing techniques, including random under-sampling (RUS) and synthetic minority over-sampling technique (SMOTE), were applied to process this unbalanced training set.

The best model performance was observed in RUS-applied RF model with laboratory variables. Compared with null models (sensitivity = 0, specificity = 100, and mean AUCs = 0.643), data balancing techniques improved overall performance with RUS, demonstrating a more satisfactory effect in the current study (RUS: sensitivity = 63.9; specificity = 53.7; and mean AUCs = 0.624. Adding laboratory variables improved the performance of analysis methods. All results were reconfirmed in validation sets. The top 10 important variables were determined by the analysis method with the best performance.

Among the tested methods, the most effective stroke prediction model in targeted population is RUS-applied RF. From the insights, the current study revealed, we provided general frameworks for building machine learning-based prediction models.

## 背景 / Background

Stroke is the leading cause of death in China (1). Stroke management and prevention methods are urgently needed, especially in Chinese rural areas, which bear the heaviest stroke burden (2). Primary prevention of stroke is the top priority, and more than 85% of strokes are preventable (3). The key is to develop effective stroke prediction methods and identify important stroke risk factors.

Machine learning has been validated as an effective data analyzing method and has seen growing usage in epidemiological studies and the field of medicine (4, 5). Its strengths include ease of analysis and the ability to simultaneously consider a huge number of variables and capture complex interactions between variables. For these reasons, machine learning has garnered favor as an analysis method in some research over traditional regression models (6, 7). However, some important methodological questions remain unanswered. Across different studies, the optimal model often differs, and the appropriate balance of variables to include in the model differs as well.

The current study aimed to explore the optimal stroke prediction method by using two classic logistic regression methods and two currently admitted machine learning models. The main data were obtained from a large-scale RCT study and a nested case–control study, which shared similar data characteristics. The targeted population is Chinese rural area hypertensive adults without a prior history of stroke. With the large sample size and thorough data processing process, we also try to establish general framework for future analysis that builds prediction method using machine learning.

## 方法 / Methods

Two datasets with similar baseline characteristics investigated by the same team were selected and analyzed in our study: the China Stroke Primary Prevention Trial (CSPPT) dataset and the nested case–control (NCC) dataset which is a subset from the H-type Hypertension and Stroke Prevention and Control Project (HSPCP).

In brief, CSPPT is a multicenter, double-blinded, randomized control trial conducted in 32 communities in Jiangsu (20 communities) and Anhui (12 communities) provinces from May 19, 2008, to August 24, 2013, in China. This study has been thoroughly described before (8). Eligible participants of the CSPPT study included hypertensive men and women aged 45–75 years, with hypertension defined as seated resting SBP (systolic blood pressure) of 140 mmHg and higher; or DBP (diastolic blood pressure) of 90 mmHg and higher during screening and follow-up visits; or using antihypertensive medication. HSPCP, which has also been thoroughly described previously (9), is an ongoing community-based, multicenter, non-interventional, prospective, observational, real-world registry study. Eligible subjects for the HSPCP study were men and women aged 18 years or older with essential hypertension, defined as seated resting SBP more than or equal to 140 mmHg or DBP more than or equal to 90 at baseline. Both studies were approved by the Ethics Committee of the Institute of Biomedicine, Anhui Medical University, Hefei, China, and all participants from both studies provided written informed consent.

Baseline data, including demographic characteristics, traditional risk factors, medication usage, questionnaire information, physical examinations, and laboratory tests, were collected by trained employees. After careful selection, important variables that presented the most in both the training and validating datasets (intersection) were entered into the final analysis, such as blood pressure, laboratory data, cardiovascular risk factors, and medication use. Furthermore, to explore the additive value on model performance, laboratory variables were excluded in one subgroup analysis and included in another (with or without laboratory test data).

The primary outcome was new nonfatal and fatal stroke (ischemic or hemorrhagic) occurring between baseline and follow-up (a median of 4.2 years). Silent stroke and subarachnoid hemorrhage were excluded. All source data of suspected stroke cases, including imaging data, event reports, and medical records, were collected and further validated by the event adjudication committee (8).

Four data analysis methods were tested which included two logistic regression methods: logistic regression (LR) and stepwise logistic regression (SLR) and two machine learning methods: random forest (RF) and XGBoost.

Two logistic regression analysis methods:

Logistic regression (LR) analyzed the relationship between multiple independent influencing factors and a categorical or binary outcome. By controlling confounding influencing factors and seizing important factors, logistic regression is able to make probabilistic predictions toward the selected outcome (10).

Stepwise logistic regression (SLR) is a semi-automated analysis method that continuously adds or removes variables from the model at each step. It is useful in a database with a large number of independent variables (11).

Two machine learning methods:

Extreme gradient boosting (XGBoost) can generate a collection of classification trees and assign each variable with a predictive risk score (12), which is an improved algorithm based on the GDBT (gradient boosting decision tree). XGBoost performs the second-order Taylor expansion of the cost function and adds a regularization item to achieve better performance. It adds predictions from weak regression trees sequentially to maximize model performance and minimize model complexity while avoiding over-fitting. XGBoost has become one of the most accepted models for risk identification and event prediction.

Random forest (RF) is a widely used learning method that produces an ensemble of decision trees with random variables as branches. By using the majority principle from all of the trees and branches, RF is able to make predictions with high accuracy with less over-fitting and strong anti-noise ability (13). It is a combined classifier algorithm based on the cart decision tree. Following the principle that a minority is subordinate to the majority, RF votes decision trees in the forest and the category with higher votes can be determined.

Two data balancing techniques:

The stroke-to-non-stroke ratio was approximately 1:31, which suggested an imbalance. Random under-sampling (RUS) and synthetic minority over-sampling technique (SMOTE) were used as data balancing techniques in the training dataset. RUS is a commonly used data balancing technique that randomly removes samples from the majority dataset until it reaches a size equivalent to the minority dataset (14). The synthetic minority over-sampling technique (SMOTE) randomly generates synthetic data to increase the minority instances based on similarities between the nearest data neighbors (15).

As mentioned in the study population section (Figure 1), the total CSPPT dataset was divided into a training set (70%, n = 14,491) an internal validation set (30%, n = 6,211); and the NCC dataset, which possesses similar data characteristics with the CSPPT set, was treated as external validation. In brief, a stroke predictive model was trained on the training set. Then, data from the internal and external validation sets were used to treat the aforementioned predictive model to get predictive results. These predictive results were compared with the actual observed results, respectively, from which the processed AUCs can be obtained. At last, AUCs for both validation sets were compared to assess the accuracy and universality of the trained predictive model. In addition, 10-fold cross-validation was applied to each analysis model for derivation and validation. In computational-heavy analyses, a 10-fold CV can improve the accuracy and efficiency of the prediction model by reducing the MSE, bias, and variance (16). Moreover, a 10-fold CV can avoid type III errors (arbitrarily split data suggested testing hypotheses). Ten-fold CV randomly divides data into 10 equal folds, and then, each fold in turn is used as the validation set, while the nine other folds are used as the training set.

Analysis flow for the development and evaluation of models.

Continuous variables are presented as mean with standard deviation (SD, normal distribution) and as medians with inter-quartile range (IQR, skewed distribution). Categorical variables are presented as percentages. The t-test, Wilcoxon rank-sum test, and the Chi-square test were used for statistical comparison between stroke and non-stroke populations. Sensitivity, specificity, accuracy, kappa, and areas under the receiver operating characteristic curve (AUCs) were used to make the model assessment with AUCs the top concerns for model performance evaluation. Data balancing techniques, including RUS and SMOTE, were applied to process the imbalanced dataset (stroke-to-non-stroke incidence was 1:31) meanwhile separately compared with each other and the null model (regression coefficients equal to 0). Box plots were generated to explore the efficacy of the inclusion of laboratory data. Receiver operating characteristics curves were generated to examine and compare the performance of four analysis methods in both the CSPPT and NCC datasets.

Two-tailed P < 0.05 was considered significant in all analyses. All statistical analyses were performed using R software, version 3.5.2 (http://www.R-project.org/, accessed 20 December 2018).

## 结果 / Results

CSPPT dataset (training and internal validation dataset): A total of 20,702 rural Chinese hypertensive participants without a prior history of stroke at baseline were included. In the targeted population, 41% were male (n = 8,497) and had a mean age of 60.0 (SD: 7.5) and a mean SBP of 165.8 (SD 18.3) mmHg at baseline. During a median follow-up period of 4.5 years, 637 new stroke cases occurred (3.1% of the total population). The stroke incidence rate was approximately 3,225.81/100,000. Statistical significances (P < 0.05) were observed regarding age, BMI, DBP, SBP, ALB, AST, GGT, CHOL, GLU, CREA, sex, diabetes, smoking, fruit intake, and antihypertensive drugs usage (P < 0.05).

NCC (external validation set): A total of 2,568 hypertensive patients with a mean age of 70.6 (SD 8.2), 51.1 % being male (n = 1,311), and having a 153.1 (SD 22.8) mmHg mean SBP level were entered into the final analysis. The stroke cases-to-non-stroke cases ratio was 1:1 with number equal to 1,284. With identical variables to the CSPPT dataset, differences were observed in hip, BMI, DBP, SBP, pulse, calcium, triglycerides, glucose, diabetes, antihypertensive drugs usage, and hypoglycemic drugs usage (P < 0.05; Table 1).

Baseline and follow-up characteristics of the study participants.

Data are mean (SD) or n (%).

BMI, body mass index; AST, aspartate aminotransferase; γ-GT, gamma glutamyltranspeptidase; TC, total cholesterol.

The following result description will mainly focus on the training set.

Before data balancing techniques were applied, we observed high AUCs (mean 0.643), very high accuracy (97%), very high specificity (100%), and mean kappa value of 0.97, but very low sensitivity (0), in all four analysis methods. After including laboratory data, similar patterns were found with mean AUCs, accuracy, specificity, kappa, and sensitivity of 0.647, 97%, 100%, 0.97, and 0, respectively.

After data balancing techniques were applied, we can observe improvements in sensitivity and decreases in specificity and AUCs. Higher AUCs were obtained from the analysis method applied with RUS than SMOTE in general (mean 0.623 vs. 0.512). In addition, in RUS-applied models, higher sensitivity (mean 63.9% vs. 14.4%), higher kappa (mean 0.022 vs. −0.004), lower specificity (53.7% vs. 84.4%), and lower accuracy (54.0% vs. 83.3%) were observed compared with SMOTE-applied methods. Moreover, extreme values were found in SMOTE-applied models, but not RUS (e.g., SMOTE-applied RF has 4.80 sensitivity, 95.2% specificity, and 92.7% accuracy).

Although adding the laboratory variables elevated overall model performance, no significant improvement was observed (Table 2). Reductions were only observed regarding specificity and accuracy in SMOTE-applied LR and SL and AUCs for RUS-applied XGBoost, but also with a limited range.

Performance of machine learning methods in different datasets with different data balancing methods.

RF, random forest; XG, XGBoost; LR, logistic regression; SLR, stepwise logistic regression; RUS, random under-sampling; SMOTE, synthetic minority over-sampling technique; and AUC, area under the receiver operating characteristic curve.

With data balancing techniques, the inclusion of laboratory data improved AUCs (mean 0.58 vs. 0.57), sensitivity (42.2% vs. 39.1%), specificity (69.3% vs. 69%), accuracy (68.5% vs. 68.2%), and kappa (0.016 vs. 0.008) compared with the exclusion of laboratory data.

Overall, the RF method appeared to have the highest mean AUCs (Null + RUS + SMOTE/3) of 0.601, and SLR showed the lowest average AUCs of 0.587 before adding laboratory variables. After the inclusion of laboratory data, highest and lowest mean AUC values were found in SLR and XGBoost with values of 0.612 and 0.589, respectively.

In RUS-applied methods, both with and without laboratory data, the highest mean AUC of 0.642 was found in RF, which was also displaced with the highest average sensitivity of 70.7%. Under the same circumstances, the lowest AUC was found in XGBoost with a mean value of 0.622. The lowest sensitivity (59.7%) was observed in the LR model. A similar result was found in SMOTE-applied models as well, with RF having the highest mean AUC (0.528) and XGBoost having the lowest value (0.520) both before and after the inclusion of laboratory data.

Before adding laboratory variables, in the methods processed with both RUS and SMOTE, the RF model showed the highest mean AUC of 0.577, whereas SLR had the lowest AUC value of 0.561. In the analysis method, including laboratory variables and applying RUS and SMOTE, SLR was observed to have the highest mean AUC of 0.589, while XGBoost appeared to have the lowest AUC of 0.573.

In general, similar findings to that of the training set were observed in the NCC dataset as well. The best model performance was obtained in the RUS-applied RF with the highest AUC value of 0.584, which outperformed other tested methods (Table 2). Receiver operating characteristic (ROC) curves were generated to examine and compare the performance of four RUS-applied analysis methods in both the CSPPT and NCC datasets with the inclusion of laboratory data (Figure 2). Results with the exclusion of laboratory data are presented in Supplement Figure 1.

Receiver operating characteristic (ROC) curves for data analysis methods with laboratory data in (A) CSPPT dataset (training set) and (B) NCC dataset (external validation set).

Important variables were selected according to the following techniques: Standardized regression coefficients were used to evaluate the importance of variables in the LR and SLR models; the Gini coefficient (average contribution) was calculated for each variable across all branches in the RF model; the relative numbers of times of a single variable in the full data distribution; and the Gini coefficient was identified for the XGBoost model. The top 25 variables were selected from the most optimal stroke prediction model, being RUS-applied RF with the inclusion of laboratory data, as stroke risk predictors. Figure 3 highlights the most important variables in the RUS-applied RF model with and without laboratory variables. Supplement Figure 2 presents the most important variables from RUS-applied XGBoost method with the inclusion and exclusion of laboratory variables. We can observe different orders and more diversity when more variables were added, but SBP, age, creatinine, triglycerides, and DBP were most commonly identified as the top five important variables.

Most important variables from RUS-applied RF with both inclusion (A) and exclusion (B) of laboratory variables.

## 讨论 / Discussion

The optimal stroke prediction model was not well established and often varies across different studies. Our study not only developed an effective stroke prediction model using machine learning analysis, but also revealed important insights into machine learning-based prediction models in general. To our knowledge, this study is by far the first and largest study that builds machine learning-based stroke prediction model using hypertensive population data.

Heo et al.'s (17) study, which focused on acute ischemic stroke, reported DNN (deep neural network) as the optimal prediction method. Wu et al.'s (18) study found that SMOTE-applied RLR outperformed other tested models in an older Chinese population for predicting the risk of stroke. Ambale-Venkatesh et al. (4) identified RF to be the most effective cardiovascular risk (including stroke) prediction model among nine tested methods in a multiracial population. Moreover, despite showing poor performance in the current study, XGBoost has been previously suggested to be the most effective prediction model for various populations and outcomes (19, 20). The current study found RUS-applied RF method with the inclusion of laboratory variables to be the most effective stroke prediction model in Chinese hypertensive adults. Ascribing to the large sample size and comprehensive study design, we believe the current study is representative in the field of machine learning-based prediction method development. Moreover, with displayed best performance in both training and validation set, the developed stroke prediction method in the present study showed robust universality and accuracy.

Analysis methods, including logistic regression and machine learning, can be disrupted by imbalanced data (21). Data balancing techniques are necessary when pre-processing an imbalanced database (22). The current study had a 1:31 stroke-to-non-stroke ratio, which indicated an imbalance. Before data balancing techniques were applied, the sensitivity of all models was 0, which suggested poor performance regardless of high AUCs. It would thus be inappropriate to directly utilize the raw data. Previous studies have demonstrated the patterns with low sensitivity in the raw model and an overall improvement after applying data balancing techniques (22, 23), which is concomitant with the current study. However, the enhancement effectiveness of applying data balancing technique varied significantly between individual models. In the current study, compared with null model, the sensitivity in the RUS-applied RF with laboratory data model increased from 0 to 72 but was only brought up to 4.8 when the same model was treated by SMOTE. In addition, different AUCs were observed when the same analysis model was applied with different data balancing techniques (18, 24).

To examine the effectiveness of the increment variables on the overall performance of the analysis model, laboratory variables included and excluded were analyzed, which is another unique feature of the present study. To our knowledge, some previous studies have included laboratory variables as a part of stroke prediction (4, 25, 26), but few studies have conducted separate analyses. As given in Table 2, when laboratory results were included, the overall performance of the analysis method was improved both before and after data balancing techniques were applied. Consistent results were reported in An Dinh et al.'s (19) study, which used machine learning methods to predict diabetes and cardiovascular disease, and all AUCs had an average increase of 0.7% after laboratory tests were included.

The targeted participants in our study consisted of population with a higher risk of stroke compared with previous studies (Table 1). Ascribing to the nature of strictly processed RCT, endpoint events were accurately collected, and all variables were presented with veracity and reliability. Compared with Gu D et al.'s study, which aimed to develop a 10-year stroke predicting equation in a Chinese population, our study had a higher baseline age (48 vs. 60), higher baseline SBP (123.6 mmHg vs. 165.8 mmHg), a more rural population, higher antihypertensive drug usage, and less current smokers (25). On the contrary, in contrast to Bharath A et al.'s study, which focused on cardiovascular event prediction by machine learning, our study solely focused on the first stroke and had more current smokers, higher usage of antihypertensive drugs, higher baseline SBP (165.8 mmHg vs. 126.6 mmHg), and lower BMI (24.8 kg/m2 vs. 28.34 kg/m2) (4).

Our study underlines the importance of validation. To demonstrate a trained model is effective, merely succeeding on the original data is not sufficient. It is essential to adduce evidence that such a developed model can perform well in other datasets. However, many review articles have pointed out the general lack of validation or insufficient validation (27, 28). Internal validation enables researchers to quantify and estimate positives from data processing, while verifying results from the training set (29). Furthermore, the trained model should be conducted in the external validation set which contains different data from the training set to examine and evaluate the developed model's performance (28). Studies that lack a thorough validation are relatively less power enough to be convincible of the developed models.

Our study findings have provided important clinical and public health implications. The selection of stroke risk predictors often differs according to various studies (4), even when targeting the same race. The current study focused on Chinese rural hypertensive adults and suggested that SBP, age, creatinine, triglycerides, and DBP are the top five stroke risk predictors. Nevertheless, the top 5 important variables from Wu's (18) study were sex, LDLC, GLU, hypertension, and UA. This difference could be caused by the fact that Yafei Wu et al. focused on an elderly population with a median age of 83 years, while our study has a mean age of 60 years. In addition, Dongfeng GU et al.'s study, with a mean baseline SBP 123.6 mmHg (SD 19.9), reported age, SBP, current smoking, diabetes mellitus, and total cholesterol as the most important variables (25). In comparison, our study has a mean baseline SBP of 165.8 mmHg (SD 18.3).

## 结论 / Conclusion

Among the tested methods, the most effective stroke prediction model in Chinese rural hypertensive adults without a history of stroke is RUS-applied RF with the inclusion of laboratory variables. From the insights, the current study revealed, we provided general frameworks for building machine learning-based prediction models.

Some limitations are a worth concern. Our analysis was focused on a targeted population, and thus, despite the high representation (large sample size, wide age range, and higher morbidity region), further validation is needed to apply the model to larger and more diverse data. In addition, this study only used two currently popular data balancing techniques and two classic analysis methods to develop the stroke prediction models. As improvements and novel methodologies are developed in future, they should be applied and evaluated as well.
