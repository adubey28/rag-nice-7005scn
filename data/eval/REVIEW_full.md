# Evaluation dataset - full review sheet (60 candidates)

**These are drafts, not data.** Nothing counts until you have checked it
against the source and set `verified: true`.

Every passage below is machine-verified to appear VERBATIM in the ingested
text at the character offsets shown, so no time is wasted on quotes that do
not exist. What the machine cannot judge: whether the question is natural,
whether the answer is complete and nothing more, and whether multi-passage
items genuinely need every passage.

Composition: {'factual': 26, 'comparative': 18, 'multi_step': 16}
---

## Q001 - factual

**Q** A patient's type 2 diabetes is being managed with diet and lifestyle changes only. What HbA1c should they be aiming for?

**A** 48 mmol/mol (6.5%).

*Evidence 1: NG28 rec 1.5.7 chars `[21126:21425]`*

> 1.5.7 For adults whose type 2 diabetes is managed either by healthy living and diet, or healthy living and diet combined with an initial medication regimen that is not associated with hypoglycaemia (see the section on initial medicines), support them to aim for an HbA1c level of 48 mmol/mol (6.5%).

☐ accept ☐ edit ☐ reject

---

## Q002 - factual

**Q** How high does HbA1c have to get before treatment needs intensifying in someone already on a single glucose-lowering drug?

**A** 58 mmol/mol (7.5%) or above.

*Evidence 1: NG28 rec 1.5.8 chars `[21566:21725]`*

> 1.5.8 In adults with type 2 diabetes, if HbA1c levels are not adequately controlled by the initial medication regimen and rise to 58 mmol/mol (7.5%) or higher:

☐ accept ☐ edit ☐ reject

---

## Q003 - factual

**Q** A patient is diagnosed with type 2 diabetes in their thirties. What should they be started on?

**A** Modified-release metformin and an SGLT-2 inhibitor.

*Evidence 1: NG28 rec 1.16.1 chars `[78352:78489]`*

> 1.16.1 For adults with early onset type 2 diabetes, offer modified-release metformin and an SGLT-2 inhibitor, and consider adding either:

☐ accept ☐ edit ☐ reject

---

## Q004 - factual

**Q** Is it acceptable to prescribe a GLP-1 receptor agonist alongside a DPP-4 inhibitor?

**A** No - these two should not be given together.

*Evidence 1: NG28 rec 1.24.6 chars `[115038:115166]`*

> 1.24.6 Do not offer both a GLP-1 receptor agonist or tirzepatide and a DPP-4 inhibitor together to treat type 2 diabetes. [2026]

☐ accept ☐ edit ☐ reject

---

## Q005 - comparative

**Q** A patient follows a ketogenic diet and is due to start an SGLT-2 inhibitor. Is there anything to consider first?

**A** Yes. Check whether they are at increased risk of diabetic ketoacidosis before starting. A very low carbohydrate or ketogenic diet is a modifiable risk, and treatment may need to be delayed until the diet has changed.

*Evidence 1: NG28 rec 1.21.1 chars `[103822:103968]`*

> 1.21.1 Before starting an SGLT-2 inhibitor, check whether the person may be at increased risk of diabetic ketoacidosis (DKA), for example if they:

*Evidence 2: NG28 rec 1.21.2 chars `[104179:104405]`*

> 1.21.2 Address modifiable risks of DKA before starting an SGLT-2 inhibitor. For example, people who are following a very low carbohydrate or ketogenic diet may need to delay treatment until they have changed their diet. [2022]

☐ accept ☐ edit ☐ reject

---

## Q006 - multi_step

**Q** A patient is on both an SGLT-2 inhibitor and a GLP-1 receptor agonist but has not reached their HbA1c target. Should either drug be stopped?

**A** The GLP-1 receptor agonist should be stopped if it is not helping reach the target and is not being taken for cardiovascular benefit. The SGLT-2 inhibitor can be continued despite the target not being met, because of its cardiovascular and renal benefits.

*Evidence 1: NG28 rec 1.24.2 chars `[114425:114602]`*

> 1.24.2 Consider continuing SGLT-2 inhibitors for their cardiovascular or renal benefits, even if they do not help the person reach their individualised glycaemic targets. [2026]

*Evidence 2: NG28 rec 1.24.4 chars `[114722:114919]`*

> 1.24.4 Stop GLP-1 receptor agonists or tirzepatide if they do not help the person reach their individualised glycaemic targets and they are not being taken for their cardiovascular benefits. [2026]

*Why multi-passage: Requires both passages: neither alone supports the contrast.*

☐ accept ☐ edit ☐ reject

---

## Q007 - factual

**Q** A patient's clinic blood pressure reads 156/94. What should be done next to establish whether they actually have hypertension?

**A** Offer ambulatory blood pressure monitoring (ABPM) to confirm the diagnosis.

*Evidence 1: NG136 rec 1.2.3 chars `[10340:10618]`*

> 1.2.3 If clinic blood pressure is between 140/90 mmHg and 180/120 mmHg, offer ambulatory blood pressure monitoring (ABPM) to confirm the diagnosis of hypertension. See the section on identifying who to refer for people with a clinic blood pressure 180/120 mmHg or higher. [2019]

☐ accept ☐ edit ☐ reject

---

## Q008 - factual

**Q** A patient cannot tolerate wearing the 24-hour monitor. What is the alternative for confirming diagnosis?

**A** Offer home blood pressure monitoring (HBPM) instead.

*Evidence 1: NG136 rec 1.2.4 chars `[10620:10780]`*

> 1.2.4 If ABPM is unsuitable or the person is unable to tolerate it, offer home blood pressure monitoring (HBPM) to confirm the diagnosis of hypertension. [2019]

☐ accept ☐ edit ☐ reject

---

## Q009 - factual

**Q** How many readings are needed to confirm a diagnosis using 24-hour monitoring, and how often should they be taken?

**A** At least 2 measurements per hour during usual waking hours, and the average of at least 14 measurements taken during waking hours is used to confirm the diagnosis.

*Evidence 1: NG136 rec 1.2.6 chars `[11136:11473]`*

> 1.2.6 When using ABPM to confirm a diagnosis of hypertension, ensure that at least 2 measurements per hour are taken during the person's usual waking hours (for example, between 08:00 and 22:00). Use the average value of at least 14 measurements taken during the person's usual waking hours to confirm a diagnosis of hypertension. [2011]

☐ accept ☐ edit ☐ reject

---

## Q010 - factual

**Q** A 74-year-old has been diagnosed with hypertension. What clinic blood pressure should treatment be aiming to achieve?

**A** Below 140/90 mmHg, and maintained below that level.

*Evidence 1: NG136 rec 1.4.20 chars `[23446:23761]`*

> 1.4.20 For adults with hypertension aged under 80, reduce clinic blood pressure to below 140/90 mmHg and ensure that it is maintained below that level. See also table 1 for guidance on clinic blood pressure targets for people aged under 80 with type 1 diabetes or severe chronic kidney disease. [2019, amended 2022]

☐ accept ☐ edit ☐ reject

---

## Q011 - factual

**Q** A patient of Black African family origin needs starting on treatment for high blood pressure. Does the choice of drug differ?

**A** Yes - consider an angiotensin II receptor blocker (ARB) in preference to an ACE inhibitor.

*Evidence 1: NG136 rec 1.4.30 chars `[28050:28367]`*

> 1.4.30 When choosing antihypertensive drug treatment for adults of Black African or African-Caribbean family origin, consider an angiotensin II receptor blocker (ARB), in preference to an angiotensin-converting enzyme (ACE) inhibitor. [2019] Follow the MHRA safety advice on ACE inhibitors and angiotensin II receptor

☐ accept ☐ edit ☐ reject

---

## Q012 - factual

**Q** A patient has developed a persistent dry cough since starting their blood pressure medication. What should be offered instead?

**A** An ARB.

*Evidence 1: NG136 rec 1.4.33 chars `[30354:30474]`*

> 1.4.33 If an ACE inhibitor is not tolerated, for example because of cough, offer an ARB to treat hypertension. [2019] Fo

☐ accept ☐ edit ☐ reject

---

## Q013 - factual

**Q** A patient has developed ankle swelling on their blood pressure medication and it is not tolerable. What is the alternative?

**A** A thiazide-like diuretic.

*Evidence 1: NG136 rec 1.4.36 chars `[31009:31134]`*

> 1.4.36 If a CCB is not tolerated, for example because of oedema, offer a thiazide-like diuretic to treat hypertension. [2019]

☐ accept ☐ edit ☐ reject

---

## Q014 - factual

**Q** If a diuretic is being started for high blood pressure, which type should be chosen and can you give an example?

**A** A thiazide-like diuretic, such as indapamide, in preference to a conventional thiazide diuretic such as bendroflumethiazide or hydrochlorothiazide.

*Evidence 1: NG136 rec 1.4.38 chars `[31275:31502]`*

> 1.4.38 If starting or changing diuretic treatment for hypertension, offer a thiazide-like diuretic, such as indapamide in preference to a conventional thiazide diuretic such as bendroflumethiazide or hydrochlorothiazide. [2019]

☐ accept ☐ edit ☐ reject

---

## Q015 - comparative

**Q** A patient's blood pressure remains high despite optimal doses of three different drugs. What is this called, and what comes next?

**A** They are regarded as having resistant hypertension. Consider adding a fourth antihypertensive drug as step 4 treatment, or seek specialist advice.

*Evidence 1: NG136 rec 1.4.46 chars `[33764:33973]`*

> 1.4.46 If hypertension is not controlled in adults taking the optimal tolerated doses of an ACE inhibitor or an ARB plus a CCB and a thiazide-like diuretic, regard them as having resistant hypertension. [2019]

*Evidence 2: NG136 rec 1.4.48 chars `[34262:34407]`*

> 1.4.48 For people with confirmed resistant hypertension, consider adding a fourth antihypertensive drug as step 4 treatment or seeking specialist

*Why multi-passage: Needs both: the definition and the subsequent action are in separate recommendations.*

☐ accept ☐ edit ☐ reject

---

## Q016 - comparative

**Q** A patient starting step 4 treatment has a potassium level of 4.2 mmol/l. What further diuretic option is available to them?

**A** Low-dose spironolactone may be considered, since their potassium is 4.5 mmol/l or less. Particular caution is needed in people with a reduced eGFR.

*Evidence 1: NG136 rec 1.4.49 chars `[34604:34894]`*

> 1.4.49 Consider further diuretic therapy with low-dose spironolactone for adults with resistant hypertension starting step 4 treatment who have a blood potassium level of 4.5 mmol/l or less. Use particular caution in people with a reduced estimated glomerular filtration rate because they h

☐ accept ☐ edit ☐ reject

---

## Q017 - multi_step

**Q** Two patients both have stage 1 hypertension - one is 58 with a 10-year cardiovascular risk of 8%, the other is 84 with a clinic reading of 154/88. Should either be offered drug treatment?

**A** Both may be considered for drug treatment alongside lifestyle advice. For the 58-year-old, treatment can be considered despite the 10-year risk being below 10%, bearing in mind that 10-year risk may underestimate lifetime probability. For the 84-year-old, treatment can be considered because clinic blood pressure is over 150/90 mmHg, using clinical judgement if there is frailty or multimorbidity.

*Evidence 1: NG136 rec 1.4.12 chars `[18771:19076]`*

> 1.4.12 Consider antihypertensive drug treatment in addition to lifestyle advice for adults aged under 60 with stage 1 hypertension and an estimated 10-year risk below 10%. Bear in mind that 10-year cardiovascular risk may underestimate the lifetime probability of developing cardiovascular disease. [2019]

*Evidence 2: NG136 rec 1.4.13 chars `[19078:19378]`*

> 1.4.13 Consider antihypertensive drug treatment in addition to lifestyle advice for people aged over 80 with stage 1 hypertension if their clinic blood pressure is over 150/90 mmHg. Use clinical judgement for people with frailty or multimorbidity (see also NICE's guideline on multimorbidity). [2019]

*Why multi-passage: Two distinct age-based criteria; neither passage covers both patients.*

☐ accept ☐ edit ☐ reject

---

## Q018 - multi_step

**Q** A patient aged 83 and a patient aged 62 are both being treated for hypertension. Do they have the same clinic blood pressure target?

**A** No. The 62-year-old should be reduced to below 140/90 mmHg, while the 83-year-old should be reduced to below 150/90 mmHg, with clinical judgement used if there is frailty or multimorbidity.

*Evidence 1: NG136 rec 1.4.20 chars `[23446:23646]`*

> 1.4.20 For adults with hypertension aged under 80, reduce clinic blood pressure to below 140/90 mmHg and ensure that it is maintained below that level. See also table 1 for guidance on clinic blood pr

*Evidence 2: NG136 rec 1.4.21 chars `[23763:24013]`*

> 1.4.21 For adults with hypertension aged 80 and over, reduce clinic blood pressure to below 150/90 mmHg and ensure that it is maintained below that level. Use clinical judgement for people with frailty or multimorbidity (see NICE's guideline on multi

*Why multi-passage: Requires both age-band targets.*

☐ accept ☐ edit ☐ reject

---

## Q019 - comparative

**Q** A patient's clinic reading is 184/122 but they have no symptoms suggesting they need to be seen the same day. What should happen?

**A** Carry out investigations for target organ damage as soon as possible.

*Evidence 1: NG136 rec 1.5.1 chars `[35973:36244]`*

> 1.5.1 If a person has severe hypertension (clinic blood pressure of 180/120 mmHg or higher), but no symptoms or signs indicating same-day referral (see recommendation 1.5.2), carry out investigations for target organ damage (see recommendation 1.3.3) as soon as possible:

☐ accept ☐ edit ☐ reject

---

## Q020 - factual

**Q** On standing, a patient's systolic blood pressure drops by 24 mmHg. Is this significant enough to act on?

**A** Yes - a fall of 20 mmHg or more in systolic blood pressure after standing for at least 1 minute meets the threshold for further action.

*Evidence 1: NG136 rec 1.1.6 chars `[8565:8754]`*

> 1.1.6 If the person's systolic blood pressure falls by 20 mmHg or more, or their diastolic blood pressure falls by 10 mmHg or more, after the person has been standing for at least 1 minute:

☐ accept ☐ edit ☐ reject

---

## Q021 - multi_step

**Q** A 68-year-old with hypertension also has chronic kidney disease and an albumin to creatinine ratio of 85 mg/mmol. What clinic blood pressure should they be treated to?

**A** Below 130/80 mmHg. The general target for someone under 80 with hypertension is below 140/90, but for a person under 80 with chronic kidney disease and an albumin to creatinine ratio of 70 mg/mmol or more the target is below 130/80.

*Evidence 1: NG136 rec 1.4.20 chars `[23446:23646]`*

> 1.4.20 For adults with hypertension aged under 80, reduce clinic blood pressure to below 140/90 mmHg and ensure that it is maintained below that level. See also table 1 for guidance on clinic blood pr

*Evidence 2: NG136 table 1 chars `[20957:21257]`*

> - type 1 diabetes plus albumin to creatinine ratio of 70 mg/mmol or more or  - chronic kidney disease plus albumin to creatinine ratio of 70 mg/mmol or more  Below 130/80 NICE's guideline on type 1 diabetes in adults (recommendation 1.13.8)  NICE's guideline on chronic kidney disease (recommendation

*Why multi-passage: Requires the recommendation AND table 1. The recommendation alone gives the wrong answer for this patient - a good discriminator between conditions that retrieve the table and those that do not.*

☐ accept ☐ edit ☐ reject

---

## Q022 - multi_step

**Q** An 84-year-old with hypertension and chronic kidney disease has an albumin to creatinine ratio of 45 mg/mmol. What blood pressure target applies?

**A** Below 140/90 mmHg. The usual target for someone aged 80 and over is below 150/90, but for a person aged 80 and over with chronic kidney disease and an albumin to creatinine ratio below 70 mg/mmol the target is below 140/90.

*Evidence 1: NG136 rec 1.4.21 chars `[23763:24013]`*

> 1.4.21 For adults with hypertension aged 80 and over, reduce clinic blood pressure to below 150/90 mmHg and ensure that it is maintained below that level. Use clinical judgement for people with frailty or multimorbidity (see NICE's guideline on multi

*Evidence 2: NG136 table 2 chars `[21265:21685]`*

> Table 2: Clinic blood pressure targets for people aged 80 and over Person aged 80 and over with:  Clinic blood pressure target  Source  - hypertension (with or without type 2 diabetes) or  - type 1 diabetes (regardless of albumin to creatinine ratio)  Below 150/90 Recommendation 1.4.21 NICE's guideline on type 1 diabetes in adults (recommendation 1.13.8)  - chronic kidney disease plus albumin to creatinine ratio less

*Why multi-passage: Age band and comorbidity interact; both passages needed.*

☐ accept ☐ edit ☐ reject

---

## Q023 - comparative

**Q** Which tool should be used to estimate someone's 10-year cardiovascular risk, and does it apply to people with type 2 diabetes?

**A** QRISK3, for people aged between 25 and 84 without CVD, and it should also be used for people with type 2 diabetes aged between 25 and 84.

*Evidence 1: NG238 rec 1.1.7 chars `[6309:6453]`*

> 1.1.7 Use the QRISK3 tool to calculate the estimated CVD risk within the next 10 years for people aged between 25 and 84 without CVD. [May 2023]

*Evidence 2: NG238 rec 1.1.8 chars `[6455:6535]`*

> 1.1.8 Use the QRISK3 tool for people with type 2 diabetes aged between 25 and 84

☐ accept ☐ edit ☐ reject

---

## Q024 - factual

**Q** A patient's total cholesterol comes back at 9.4 mmol/litre. There is no family history of early heart disease. Does that matter?

**A** No - specialist assessment should be arranged for a total cholesterol above 9.0 mmol/litre even without a first-degree family history of premature coronary heart disease.

*Evidence 1: NG238 rec 1.4.5 chars `[23873:24151]`*

> 1.4.5 Arrange for specialist assessment of people with a total blood cholesterol level of more than 9.0 mmol per litre or a non-HDL cholesterol level of more than 7.5 mmol per litre even in the absence of a first-degree family history of premature coronary heart disease. [2014]

☐ accept ☐ edit ☐ reject

---

## Q025 - factual

**Q** A patient has a triglyceride level of 24 mmol/litre and drinks very little alcohol. What should happen?

**A** Refer for urgent specialist review.

*Evidence 1: NG238 rec 1.4.6 chars `[24153:24341]`*

> 1.4.6 Refer for urgent specialist review if a person has a triglyceride level of more than 20 mmol per litre that is not a result of excess alcohol intake or poor glycaemic control. [2014]

☐ accept ☐ edit ☐ reject

---

## Q026 - factual

**Q** How much should non-HDL cholesterol be reduced by when treating someone to prevent a first cardiovascular event?

**A** Aim for a greater than 40% reduction in non-HDL cholesterol.

*Evidence 1: NG238 rec 1.6.1 chars `[30291:30398]`*

> 1.6.1 For primary prevention of CVD aim for a greater than 40% reduction in non-HDL cholesterol. [May 2023]

☐ accept ☐ edit ☐ reject

---

## Q027 - factual

**Q** A patient's liver transaminases are raised at twice the upper limit of normal. Does this rule out starting a statin?

**A** No - people with transaminase levels that are raised but less than 3 times the upper limit of normal should not routinely be excluded from statin treatment.

*Evidence 1: NG238 rec 1.5.6 chars `[26940:27114]`*

> 1.5.6 Do not routinely exclude from statin treatment people who have liver transaminase levels that are raised but are less than 3 times the upper limit of normal. [May 2023]

☐ accept ☐ edit ☐ reject

---

## Q028 - factual

**Q** What proportion of energy intake should come from fat, and specifically from saturated fat, in someone at high cardiovascular risk?

**A** Total fat intake should be 30% or less of total energy intake and saturated fats 7% or less, with saturated fats replaced where possible by mono-unsaturated and polyunsaturated fats.

*Evidence 1: NG238 rec 1.3.2 chars `[19522:19806]`*

> 1.3.2 Advise people at high risk of or with CVD to eat a diet in which total fat intake is 30% or less of total energy intake, saturated fats are 7% or less of total energy intake, and where possible saturated fats are replaced by mono-unsaturated and polyunsaturated fats. [May 2023]

☐ accept ☐ edit ☐ reject

---

## Q029 - comparative

**Q** A patient reports longstanding unexplained muscle aching and is about to be started on a statin. What should be done first?

**A** Ask about persistent generalised unexplained muscle symptoms and, if present, measure creatine kinase levels before offering the statin.

*Evidence 1: NG238 rec 1.5.7 chars `[27116:27405]`*

> 1.5.7 Before offering a statin, ask the person if they have had persistent generalised unexplained muscle symptoms (pain, tenderness or weakness), whether associated or not with previous lipid-lowering treatment. If they have, measure creatine kinase levels. If creatine kinase levels are:

☐ accept ☐ edit ☐ reject

---

## Q030 - factual

**Q** A woman of childbearing age is being considered for a statin. Is there anything that would prevent this?

**A** Yes - statins are contraindicated in pregnancy because of the risk to the unborn child.

*Evidence 1: NG238 rec 1.5.9 chars `[29535:29684]`*

> 1.5.9 Be aware that statins are contraindicated in pregnancy because of the risk to the unborn child of exposure to statins. [2014, amended May 2023]

☐ accept ☐ edit ☐ reject

---

## Q031 - comparative

**Q** A patient's cholesterol is raised and they also have untreated hypothyroidism. What should be addressed before considering a referral or starting treatment?

**A** Exclude common secondary causes of dyslipidaemia such as excess alcohol, uncontrolled diabetes, hypothyroidism, liver disease and nephrotic syndrome before referring for specialist review, and treat comorbidities and secondary causes before starting statins.

*Evidence 1: NG238 rec 1.4.3 chars `[23459:23678]`*

> 1.4.3 Exclude possible common secondary causes of dyslipidaemia (such as excess alcohol intake, uncontrolled diabetes, hypothyroidism, liver disease and nephrotic syndrome) before referring for specialist review. [2014]

*Evidence 2: NG238 rec 1.6.6 chars `[31270:31359]`*

> 1.6.6 Before starting statins, treat comorbidities and secondary causes of dyslipidaemia.

*Why multi-passage: Two separate recommendations cover exclusion before referral and treatment before statins.*

☐ accept ☐ edit ☐ reject

---

## Q032 - comparative

**Q** A 37-year-old has several cardiovascular risk factors but a 10-year QRISK3 score of only 6%. Is there anything else that could inform the discussion?

**A** Consider using a lifetime risk tool such as QRISK3-lifetime, which is particularly suggested for people with a 10-year QRISK3 score below 10% and people under 40 who have CVD risk factors.

*Evidence 1: NG238 rec 1.1.16 chars `[14909:15169]`*

> 1.1.16 Consider using a lifetime risk tool such as QRISK3-lifetime to inform discussions on CVD risk and to motivate lifestyle changes, particularly for people with a 10-year QRISK3 score less than 10%, and people under 40 who have CVD risk factors. [May 2023]

☐ accept ☐ edit ☐ reject

---

## Q033 - factual

**Q** A patient with suspected heart failure has an NT-proBNP of 2,400 ng/litre. How quickly should they be seen?

**A** Refer urgently for specialist assessment and transthoracic echocardiography within 2 weeks.

*Evidence 1: NG106 rec 1.2.3 chars `[11393:11683]`*

> 1.2.3 Because very high levels of NT-proBNP carry a poor prognosis, refer people with suspected heart failure and an NT-proBNP level more than 2,000 nanogram per litre (236 picomole per litre) urgently, to have specialist assessment and transthoracic echocardiography within 2 weeks. [2018]

☐ accept ☐ edit ☐ reject

---

## Q034 - factual

**Q** A patient with suspected heart failure has an NT-proBNP of 900 ng/litre. What is the referral timeframe?

**A** Specialist assessment and transthoracic echocardiography within 6 weeks.

*Evidence 1: NG106 rec 1.2.4 chars `[11685:11911]`*

> 1.2.4 Refer people with suspected heart failure and an NT-proBNP level between 400 and 2,000 nanogram per litre (47 to 236 pmol per litre) to have specialist assessment and transthoracic echocardiography within 6 weeks. [2018]

☐ accept ☐ edit ☐ reject

---

## Q035 - multi_step

**Q** Two patients present with suspected heart failure - one has an NT-proBNP of 2,400 ng/litre and the other 900 ng/litre. Should they be managed with the same urgency?

**A** No. The patient with a level above 2,000 ng/litre should be referred urgently for specialist assessment and echocardiography within 2 weeks, while the patient with a level between 400 and 2,000 ng/litre should be seen within 6 weeks.

*Evidence 1: NG106 rec 1.2.3 chars `[11393:11683]`*

> 1.2.3 Because very high levels of NT-proBNP carry a poor prognosis, refer people with suspected heart failure and an NT-proBNP level more than 2,000 nanogram per litre (236 picomole per litre) urgently, to have specialist assessment and transthoracic echocardiography within 2 weeks. [2018]

*Evidence 2: NG106 rec 1.2.4 chars `[11685:11911]`*

> 1.2.4 Refer people with suspected heart failure and an NT-proBNP level between 400 and 2,000 nanogram per litre (47 to 236 pmol per litre) to have specialist assessment and transthoracic echocardiography within 6 weeks. [2018]

*Why multi-passage: Two thresholds in separate recommendations; neither alone answers the comparison.*

☐ accept ☐ edit ☐ reject

---

## Q036 - factual

**Q** What four medicines should someone with heart failure and a reduced ejection fraction be started on?

**A** An ACE inhibitor, a beta-blocker, a mineralocorticoid receptor antagonist (MRA) and an SGLT2 inhibitor.

*Evidence 1: NG106 rec 1.4.1 chars `[16618:16864]`*

> 1.4.1 Offer an angiotensin-converting enzyme (ACE) inhibitor, a beta-blocker, a mineralocorticoid receptor antagonist (MRA) and a sodium-glucose cotransporter-2 (SGLT2) inhibitor to people with heart failure with reduced ejection fraction. [2025]

☐ accept ☐ edit ☐ reject

---

## Q037 - comparative

**Q** A patient with reduced ejection fraction is on maximum tolerated doses of all four recommended medicines but still has symptoms. What can be considered?

**A** Consider switching the ACE inhibitor to an angiotensin receptor-neprilysin inhibitor (ARNI).

*Evidence 1: NG106 rec 1.4.2 chars `[16866:17076]`*

> 1.4.2 For people on the maximum tolerated dose of each of the 4 medicines who continue to have symptoms of heart failure, consider switching the ACE inhibitor to an angiotensin receptor-neprilysin inhibitor (AR

☐ accept ☐ edit ☐ reject

---

## Q038 - factual

**Q** A patient with reduced ejection fraction develops an intolerance to ACE inhibitors, but not angioedema. What should they be offered instead?

**A** An ARNI, beta-blocker, MRA and SGLT2 inhibitor.

*Evidence 1: NG106 rec 1.4.3 chars `[17163:17365]`*

> 1.4.3 For people with heart failure with reduced ejection fraction who have symptoms of intolerance to ACE inhibitors (other than angioedema), offer an ARNI, betablocker, MRA and SGLT2 inhibitor. [2025]

☐ accept ☐ edit ☐ reject

---

## Q039 - multi_step

**Q** Does the recommended drug combination differ between heart failure with reduced ejection fraction and heart failure with preserved ejection fraction?

**A** Yes. For reduced ejection fraction, an ACE inhibitor, beta-blocker, MRA and SGLT2 inhibitor should be offered. For preserved ejection fraction, an MRA and an SGLT2 inhibitor should be considered.

*Evidence 1: NG106 rec 1.4.1 chars `[16618:16864]`*

> 1.4.1 Offer an angiotensin-converting enzyme (ACE) inhibitor, a beta-blocker, a mineralocorticoid receptor antagonist (MRA) and a sodium-glucose cotransporter-2 (SGLT2) inhibitor to people with heart failure with reduced ejection fraction. [2025]

*Evidence 2: NG106 rec 1.5.4 chars `[22037:22187]`*

> 1.5.4 Consider an MRA and an sodium-glucose cotransporter-2 (SGLT2) inhibitor for treating heart failure with preserved ejection fraction. See also re

*Why multi-passage: Requires both ejection-fraction categories.*

☐ accept ☐ edit ☐ reject

---

## Q040 - multi_step

**Q** How does treatment for mildly reduced ejection fraction compare with treatment for reduced ejection fraction?

**A** Both involve an ACE inhibitor, a beta-blocker, an MRA and an SGLT2 inhibitor, but for reduced ejection fraction these should be offered, whereas for mildly reduced ejection fraction they should be considered.

*Evidence 1: NG106 rec 1.4.1 chars `[16618:16864]`*

> 1.4.1 Offer an angiotensin-converting enzyme (ACE) inhibitor, a beta-blocker, a mineralocorticoid receptor antagonist (MRA) and a sodium-glucose cotransporter-2 (SGLT2) inhibitor to people with heart failure with reduced ejection fraction. [2025]

*Evidence 2: NG106 rec 1.5.1 chars `[20686:20971]`*

> 1.5.1 Consider an angiotensin-converting enzyme (ACE) inhibitor, a beta-blocker, a mineralocorticoid receptor antagonist (MRA) and a sodium-glucose cotransporter-2 (SGLT2) inhibitor for treating heart failure with mildly reduced ejection fraction. See also recommendation 1.5.3. [2025]

*Why multi-passage: The distinction is offer vs consider; both passages needed.*

☐ accept ☐ edit ☐ reject

---

## Q041 - factual

**Q** What should be measured before prescribing an ACE inhibitor or an MRA for heart failure?

**A** The person's renal function and electrolyte levels.

*Evidence 1: NG106 rec 1.7.3 chars `[24455:24732]`*

> 1.7.3 Before prescribing an angiotensin-converting enzyme (ACE) inhibitor, angiotensin receptor-neprilysin inhibitor (ARNI), angiotensin II receptor blocker (ARB) or mineralocorticoid receptor antagonist (MRA), measure the person's renal function and electrolyte levels. [2025]

☐ accept ☐ edit ☐ reject

---

## Q042 - factual

**Q** A patient on an ACE inhibitor for heart failure has a potassium of 5.8 mmol/litre. Is that a level requiring action?

**A** Yes - if potassium rises above 5.5 mmol per litre (or serum creatinine increases by more than 50%), local guidelines should be followed.

*Evidence 1: NG106 rec 1.7.5 chars `[25067:25246]`*

> 1.7.5 If the person's serum creatinine level increases by more than 50% or their potassium concentration increases to more than 5.5 mmol per litre, follow local guidelines. [2025]

☐ accept ☐ edit ☐ reject

---

## Q043 - comparative

**Q** A 79-year-old with heart failure also has COPD and peripheral vascular disease. Should a beta-blocker be avoided?

**A** No - treatment with a beta-blocker should not be withheld solely because of age or the presence of peripheral vascular disease, erectile dysfunction, diabetes, interstitial pulmonary disease or COPD. A 12-lead ECG should be used to assess heart rhythm, rate and conduction abnormalities before deciding whether to prescribe one.

*Evidence 1: NG106 rec 1.7.9 chars `[26262:26495]`*

> 1.7.9 Do not withhold treatment with a beta-blocker solely because of age or the presence of peripheral vascular disease, erectile dysfunction, diabetes, interstitial pulmonary disease or chronic obstructive pulmonary disease. [2010]

*Evidence 2: NG106 rec 1.7.10 chars `[26497:26648]`*

> 1.7.10 Assess for heart rhythm, heart rate and conduction abnormalities using a 12-lead ECG before deciding whether to prescribe a beta-blocker. [2025]

*Why multi-passage: Contraindication myth plus the required pre-check.*

☐ accept ☐ edit ☐ reject

---

## Q044 - factual

**Q** The echocardiogram image quality is poor in a patient being assessed for heart failure. What are the alternatives?

**A** Alternative imaging methods such as radionuclide angiography (multigated acquisition scanning), cardiac MRI or transoesophageal echocardiography.

*Evidence 1: NG106 rec 1.2.11 chars `[13846:14113]`*

> 1.2.11 Think about alternative methods of imaging the heart (for example, radionuclide angiography [multigated acquisition scanning], cardiac MRI or transoesophageal echocardiography) if a poor image is produced by transthoracic echocardiography. [2003, amended 2018]

☐ accept ☐ edit ☐ reject

---

## Q045 - multi_step

**Q** A 62-year-old has both type 2 diabetes managed on diet alone and newly diagnosed hypertension. What HbA1c and clinic blood pressure should they be aiming for?

**A** An HbA1c of 48 mmol/mol (6.5%) and a clinic blood pressure below 140/90 mmHg, maintained below that level.

*Evidence 1: NG28 NG28 rec 1.5.7 chars `[21126:21425]`*

> 1.5.7 For adults whose type 2 diabetes is managed either by healthy living and diet, or healthy living and diet combined with an initial medication regimen that is not associated with hypoglycaemia (see the section on initial medicines), support them to aim for an HbA1c level of 48 mmol/mol (6.5%).

*Evidence 2: NG136 NG136 rec 1.4.20 chars `[23446:23646]`*

> 1.4.20 For adults with hypertension aged under 80, reduce clinic blood pressure to below 140/90 mmHg and ensure that it is maintained below that level. See also table 1 for guidance on clinic blood pr

*Why multi-passage: Targets live in two different guidelines; neither alone answers both halves.*

☐ accept ☐ edit ☐ reject

---

## Q046 - multi_step

**Q** A patient with type 2 diabetes needs their cardiovascular risk estimated. Which tool applies, and does having diabetes change the answer?

**A** QRISK3 should be used for people aged between 25 and 84 without CVD, and it should also be used for people with type 2 diabetes aged between 25 and 84 - so having type 2 diabetes does not change the tool used.

*Evidence 1: NG238 NG238 rec 1.1.7 chars `[6309:6453]`*

> 1.1.7 Use the QRISK3 tool to calculate the estimated CVD risk within the next 10 years for people aged between 25 and 84 without CVD. [May 2023]

*Evidence 2: NG238 NG238 rec 1.1.8 chars `[6455:6535]`*

> 1.1.8 Use the QRISK3 tool for people with type 2 diabetes aged between 25 and 84

☐ accept ☐ edit ☐ reject

---

## Q047 - multi_step

**Q** A patient has both hypertension and heart failure. Which class of diuretic is indicated, and what else should their heart failure treatment include?

**A** If there is evidence of heart failure, a thiazide-like diuretic should be offered. Heart failure with reduced ejection fraction should also be treated with an ACE inhibitor, a beta-blocker, an MRA and an SGLT2 inhibitor.

*Evidence 1: NG136 NG136 rec 1.4.37 chars `[31136:31273]`*

> 1.4.37 If there is evidence of heart failure, offer a thiazide-like diuretic and follow NICE's guideline on chronic heart failure. [2019]

*Evidence 2: NG106 NG106 rec 1.4.1 chars `[16618:16864]`*

> 1.4.1 Offer an angiotensin-converting enzyme (ACE) inhibitor, a beta-blocker, a mineralocorticoid receptor antagonist (MRA) and a sodium-glucose cotransporter-2 (SGLT2) inhibitor to people with heart failure with reduced ejection fraction. [2025]

*Why multi-passage: Spans hypertension and heart failure guidelines.*

☐ accept ☐ edit ☐ reject

---

## Q048 - multi_step

**Q** A patient with early onset type 2 diabetes is also being assessed for cardiovascular risk. What medicines should they start, and what reduction in non-HDL cholesterol should treatment aim for?

**A** They should be offered modified-release metformin and an SGLT-2 inhibitor. For primary prevention of CVD, treatment should aim for a greater than 40% reduction in non-HDL cholesterol.

*Evidence 1: NG28 NG28 rec 1.16.1 chars `[78352:78489]`*

> 1.16.1 For adults with early onset type 2 diabetes, offer modified-release metformin and an SGLT-2 inhibitor, and consider adding either:

*Evidence 2: NG238 NG238 rec 1.6.1 chars `[30291:30398]`*

> 1.6.1 For primary prevention of CVD aim for a greater than 40% reduction in non-HDL cholesterol. [May 2023]

*Why multi-passage: Cross-guideline: diabetes management plus lipid target.*

☐ accept ☐ edit ☐ reject

---

## Q049 - multi_step

**Q** A patient of African-Caribbean family origin with hypertension is not controlled on step 1 treatment and does not have type 2 diabetes. What should be added, and would the choice have been different at step 1?

**A** At step 1 an ARB should be considered in preference to an ACE inhibitor. If hypertension is not controlled on step 1 treatment, an ARB should again be considered in preference to an ACE inhibitor in addition to step 1 treatment.

*Evidence 1: NG136 rec 1.4.30 chars `[28050:28367]`*

> 1.4.30 When choosing antihypertensive drug treatment for adults of Black African or African-Caribbean family origin, consider an angiotensin II receptor blocker (ARB), in preference to an angiotensin-converting enzyme (ACE) inhibitor. [2019] Follow the MHRA safety advice on ACE inhibitors and angiotensin II receptor

*Evidence 2: NG136 rec 1.4.43 chars `[32685:32936]`*

> 1.4.43 If hypertension is not controlled in adults of Black African or African-Caribbean family origin who do not have type 2 diabetes taking step 1 treatment, consider an ARB, in preference to an ACE inhibitor, in addition to step 1 treatment. [2019]

☐ accept ☐ edit ☐ reject

---

## Q050 - multi_step

**Q** A patient on treatment for hypertension is monitoring at home rather than in clinic. What reading should they be aiming for if they are 72, and what if they were 84?

**A** Using ABPM or HBPM, blood pressure should be reduced to below 135/85 mmHg for adults aged under 80 and below 145/85 mmHg for adults aged 80 and over, using clinical judgement for people with frailty or multimorbidity.

*Evidence 1: NG136 rec 1.4.22 chars `[24193:24466]`*

> 1.4.22 When using ABPM or HBPM to monitor the response to treatment in adults with hypertension, use the average blood pressure level taken during the person's usual waking hours (see recommendations 1.2.6 and 1.2.7). Reduce blood pressure and ensure that it is maintained:

*Evidence 2: NG136 rec 1.4.22 targets chars `[24468:24598]`*

> - below 135/85 mmHg for adults aged under 80  - below 145/85 mmHg for adults aged 80 and over. Use clinical judgement for people w

☐ accept ☐ edit ☐ reject

---

## Q051 - multi_step

**Q** A patient with heart failure develops angioedema on an ACE inhibitor and later cannot tolerate an ARNI either. What options remain?

**A** If ACE inhibitors, ARNIs and ARBs are all not tolerated, seek specialist advice and consider hydralazine in combination with nitrate.

*Evidence 1: NG106 rec 1.4.4 chars `[17367:17476]`*

> 1.4.4 For people with angioedema after taking an ACE inhibitor, or who have symptoms of intolerance to ARNIs:

*Evidence 2: NG106 rec 1.4.9 chars `[19274:19430]`*

> 1.4.9 If ACE inhibitors, ARNIs and ARBs are not tolerated, seek specialist advice and consider hydralazine in combination with nitrate. [2010, amended 2025]

☐ accept ☐ edit ☐ reject

---

## Q052 - multi_step

**Q** A patient with type 2 diabetes on a ketogenic diet is also due to start a statin for primary prevention. What should be checked before each treatment?

**A** Before starting an SGLT-2 inhibitor, check whether they are at increased risk of diabetic ketoacidosis, since a very low carbohydrate or ketogenic diet is a modifiable risk. Before starting a statin, perform baseline blood tests and clinical assessment, and treat comorbidities and secondary causes of dyslipidaemia.

*Evidence 1: NG28 NG28 rec 1.21.1 chars `[103822:103968]`*

> 1.21.1 Before starting an SGLT-2 inhibitor, check whether the person may be at increased risk of diabetic ketoacidosis (DKA), for example if they:

*Evidence 2: NG238 NG238 rec 1.6.6 chars `[31270:31359]`*

> 1.6.6 Before starting statins, treat comorbidities and secondary causes of dyslipidaemia.

*Why multi-passage: Cross-guideline pre-treatment checks.*

☐ accept ☐ edit ☐ reject

---

## Q053 - comparative

**Q** What is the difference between how ABPM and HBPM are used when confirming a diagnosis of hypertension?

**A** ABPM is offered first to confirm the diagnosis when clinic blood pressure is between 140/90 and 180/120 mmHg. HBPM is offered instead if ABPM is unsuitable or the person cannot tolerate it.

*Evidence 1: NG136 rec 1.2.3 chars `[10340:10618]`*

> 1.2.3 If clinic blood pressure is between 140/90 mmHg and 180/120 mmHg, offer ambulatory blood pressure monitoring (ABPM) to confirm the diagnosis of hypertension. See the section on identifying who to refer for people with a clinic blood pressure 180/120 mmHg or higher. [2019]

*Evidence 2: NG136 rec 1.2.4 chars `[10620:10780]`*

> 1.2.4 If ABPM is unsuitable or the person is unable to tolerate it, offer home blood pressure monitoring (HBPM) to confirm the diagnosis of hypertension. [2019]

☐ accept ☐ edit ☐ reject

---

## Q054 - comparative

**Q** How does the advice on statin muscle side effects compare with the advice on checking for muscle symptoms beforehand?

**A** People being offered a statin should be advised that the risk of muscle pain, tenderness or weakness is small and that severe muscle adverse effects such as rhabdomyolysis are extremely rare. Separately, before offering a statin the person should be asked about persistent generalised unexplained muscle symptoms, and creatine kinase measured if present.

*Evidence 1: NG238 rec 1.5.3 chars `[25618:25868]`*

> 1.5.3 Advise people who are being offered a statin that the risk of muscle pain, tenderness or weakness associated with statin use is small and the rate of severe muscle adverse effects (rhabdomyolysis) because of statins is extremely low. [May 2023]

*Evidence 2: NG238 rec 1.5.7 chars `[27116:27405]`*

> 1.5.7 Before offering a statin, ask the person if they have had persistent generalised unexplained muscle symptoms (pain, tenderness or weakness), whether associated or not with previous lipid-lowering treatment. If they have, measure creatine kinase levels. If creatine kinase levels are:

☐ accept ☐ edit ☐ reject

---

## Q055 - comparative

**Q** When should a lifetime cardiovascular risk tool be used rather than relying on the 10-year score alone?

**A** A lifetime risk tool such as QRISK3-lifetime can be considered to inform discussions and motivate lifestyle change, particularly for people with a 10-year QRISK3 score below 10% and people under 40 with CVD risk factors. A full formal risk assessment is prioritised for those with an estimated 10-year risk of 10% or more.

*Evidence 1: NG238 rec 1.1.16 chars `[14909:15169]`*

> 1.1.16 Consider using a lifetime risk tool such as QRISK3-lifetime to inform discussions on CVD risk and to motivate lifestyle changes, particularly for people with a 10-year QRISK3 score less than 10%, and people under 40 who have CVD risk factors. [May 2023]

*Evidence 2: NG238 rec 1.1.4 chars `[5855:5988]`*

> 1.1.4 Prioritise people for a full formal risk assessment if their estimated 10-year risk of CVD is 10% or more. [2008, amended 2014]

☐ accept ☐ edit ☐ reject

---

## Q056 - comparative

**Q** How does monitoring of renal function differ before starting an ACE inhibitor for heart failure compared with during treatment?

**A** Renal function and electrolytes should be measured before prescribing an ACE inhibitor, ARNI, ARB or MRA, and measured again during treatment for people taking any of these medicines.

*Evidence 1: NG106 rec 1.7.3 chars `[24455:24732]`*

> 1.7.3 Before prescribing an angiotensin-converting enzyme (ACE) inhibitor, angiotensin receptor-neprilysin inhibitor (ARNI), angiotensin II receptor blocker (ARB) or mineralocorticoid receptor antagonist (MRA), measure the person's renal function and electrolyte levels. [2025]

*Evidence 2: NG106 rec 1.7.4 chars `[24734:24852]`*

> 1.7.4 If the person is taking an ACE inhibitor, ARNI, ARB or MRA, measure their renal function and electrolyte levels:

☐ accept ☐ edit ☐ reject

---

## Q057 - comparative

**Q** A patient's blood pressure is not controlled on an ACE inhibitor alone. What are the options for adding a second drug?

**A** If hypertension is not controlled on step 1 treatment with an ACE inhibitor or ARB, offer the choice of one of the listed drugs in addition to step 1 treatment.

*Evidence 1: NG136 rec 1.4.41 chars `[32219:32399]`*

> 1.4.41 If hypertension is not controlled in adults taking step 1 treatment of an ACE inhibitor or ARB, offer the choice of 1 of the following drugs in addition to step 1 treatment:

☐ accept ☐ edit ☐ reject

---

## Q058 - comparative

**Q** What should be done if hypertension is not diagnosed after investigation?

**A** Measure clinic blood pressure at least every 5 years afterwards, and consider measuring more frequently if the reading is below 140/90 mmHg but still raised.

*Evidence 1: NG136 rec 1.2.10 chars `[12476:12726]`*

> 1.2.10 If hypertension is not diagnosed, measure the person's clinic blood pressure at least every 5 years subsequently, and consider measuring it more frequently if the person's clinic blood pressure is less than 140/90 mmHg but still raised. [2011]

☐ accept ☐ edit ☐ reject

---

## Q059 - comparative

**Q** A patient has isolated systolic hypertension with a systolic reading of 168 mmHg. Should they be treated differently from someone with both systolic and diastolic elevation?

**A** No - people with isolated systolic hypertension of 160 mmHg or more should be offered the same treatment as people with both raised systolic and diastolic blood pressure.

*Evidence 1: NG136 rec 1.4.28 chars `[27395:27585]`*

> 1.4.28 Offer people with isolated systolic hypertension (systolic blood pressure 160 mmHg or more) the same treatment as people with both raised systolic and diastolic blood pressure. [2004]

☐ accept ☐ edit ☐ reject

---

## Q060 - comparative

**Q** Before starting a statin, what baseline work is needed, and what does the decision itself depend on?

**A** Baseline blood tests and clinical assessment should be performed before starting statins, and the decision to start should be made after an informed discussion between the clinician and the person about the risks and benefits of statins.

*Evidence 1: NG238 rec 1.5.5 chars `[26333:26464]`*

> 1.5.5 Before starting statins perform baseline blood tests and clinical assessment. Include all of the following in the assessment:

*Evidence 2: NG238 rec 1.5.1 chars `[25121:25314]`*

> 1.5.1 Make decisions about starting statin treatment after an informed discussion between the clinician and the person about the risks and benefits of statins. [May 2023, amended December 2023]

☐ accept ☐ edit ☐ reject

---
