# Evaluation dataset - review sheet, batch 2 (NG136 hypertension)

14 candidates. Every passage machine-verified verbatim in `data/interim/NG136.txt`
at the offsets shown. Your job is judgement: is the question natural, is the
answer complete, and do the multi-passage items genuinely need every passage?
---

## Q007 - factual

**Q** A patient's clinic blood pressure reads 156/94. What should be done next to establish whether they actually have hypertension?

**A** Offer ambulatory blood pressure monitoring (ABPM) to confirm the diagnosis.

*Evidence 1: `rec 1.2.3` chars `[10340:10618]`*

> 1.2.3 If clinic blood pressure is between 140/90 mmHg and 180/120 mmHg, offer ambulatory blood pressure monitoring (ABPM) to confirm the diagnosis of hypertension. See the section on identifying who to refer for people with a clinic blood pressure 180/120 mmHg or higher. [2019]

☐ accept ☐ edit ☐ reject

---

## Q008 - factual

**Q** A patient cannot tolerate wearing the 24-hour monitor. What is the alternative for confirming diagnosis?

**A** Offer home blood pressure monitoring (HBPM) instead.

*Evidence 1: `rec 1.2.4` chars `[10620:10780]`*

> 1.2.4 If ABPM is unsuitable or the person is unable to tolerate it, offer home blood pressure monitoring (HBPM) to confirm the diagnosis of hypertension. [2019]

☐ accept ☐ edit ☐ reject

---

## Q009 - factual

**Q** How many readings are needed to confirm a diagnosis using 24-hour monitoring, and how often should they be taken?

**A** At least 2 measurements per hour during usual waking hours, and the average of at least 14 measurements taken during waking hours is used to confirm the diagnosis.

*Evidence 1: `rec 1.2.6` chars `[11136:11473]`*

> 1.2.6 When using ABPM to confirm a diagnosis of hypertension, ensure that at least 2 measurements per hour are taken during the person's usual waking hours (for example, between 08:00 and 22:00). Use the average value of at least 14 measurements taken during the person's usual waking hours to confirm a diagnosis of hypertension. [2011]

☐ accept ☐ edit ☐ reject

---

## Q010 - factual

**Q** A 74-year-old has been diagnosed with hypertension. What clinic blood pressure should treatment be aiming to achieve?

**A** Below 140/90 mmHg, and maintained below that level.

*Evidence 1: `rec 1.4.20` chars `[23446:23761]`*

> 1.4.20 For adults with hypertension aged under 80, reduce clinic blood pressure to below 140/90 mmHg and ensure that it is maintained below that level. See also table 1 for guidance on clinic blood pressure targets for people aged under 80 with type 1 diabetes or severe chronic kidney disease. [2019, amended 2022]

☐ accept ☐ edit ☐ reject

---

## Q011 - factual

**Q** A patient of Black African family origin needs starting on treatment for high blood pressure. Does the choice of drug differ?

**A** Yes - consider an angiotensin II receptor blocker (ARB) in preference to an ACE inhibitor.

*Evidence 1: `rec 1.4.30` chars `[28050:28367]`*

> 1.4.30 When choosing antihypertensive drug treatment for adults of Black African or African-Caribbean family origin, consider an angiotensin II receptor blocker (ARB), in preference to an angiotensin-converting enzyme (ACE) inhibitor. [2019] Follow the MHRA safety advice on ACE inhibitors and angiotensin II receptor

☐ accept ☐ edit ☐ reject

---

## Q012 - factual

**Q** A patient has developed a persistent dry cough since starting their blood pressure medication. What should be offered instead?

**A** An ARB.

*Evidence 1: `rec 1.4.33` chars `[30354:30474]`*

> 1.4.33 If an ACE inhibitor is not tolerated, for example because of cough, offer an ARB to treat hypertension. [2019] Fo

☐ accept ☐ edit ☐ reject

---

## Q013 - factual

**Q** A patient has developed ankle swelling on their blood pressure medication and it is not tolerable. What is the alternative?

**A** A thiazide-like diuretic.

*Evidence 1: `rec 1.4.36` chars `[31009:31134]`*

> 1.4.36 If a CCB is not tolerated, for example because of oedema, offer a thiazide-like diuretic to treat hypertension. [2019]

☐ accept ☐ edit ☐ reject

---

## Q014 - factual

**Q** If a diuretic is being started for high blood pressure, which type should be chosen and can you give an example?

**A** A thiazide-like diuretic, such as indapamide, in preference to a conventional thiazide diuretic such as bendroflumethiazide or hydrochlorothiazide.

*Evidence 1: `rec 1.4.38` chars `[31275:31502]`*

> 1.4.38 If starting or changing diuretic treatment for hypertension, offer a thiazide-like diuretic, such as indapamide in preference to a conventional thiazide diuretic such as bendroflumethiazide or hydrochlorothiazide. [2019]

☐ accept ☐ edit ☐ reject

---

## Q015 - comparative

**Q** A patient's blood pressure remains high despite optimal doses of three different drugs. What is this called, and what comes next?

**A** They are regarded as having resistant hypertension. Consider adding a fourth antihypertensive drug as step 4 treatment, or seek specialist advice.

*Evidence 1: `rec 1.4.46` chars `[33764:33973]`*

> 1.4.46 If hypertension is not controlled in adults taking the optimal tolerated doses of an ACE inhibitor or an ARB plus a CCB and a thiazide-like diuretic, regard them as having resistant hypertension. [2019]

*Evidence 2: `rec 1.4.48` chars `[34262:34407]`*

> 1.4.48 For people with confirmed resistant hypertension, consider adding a fourth antihypertensive drug as step 4 treatment or seeking specialist

*Why multi-passage: Needs both: the definition and the subsequent action are in separate recommendations.*

☐ accept ☐ edit ☐ reject

---

## Q016 - comparative

**Q** A patient starting step 4 treatment has a potassium level of 4.2 mmol/l. What further diuretic option is available to them?

**A** Low-dose spironolactone may be considered, since their potassium is 4.5 mmol/l or less. Particular caution is needed in people with a reduced eGFR.

*Evidence 1: `rec 1.4.49` chars `[34604:34894]`*

> 1.4.49 Consider further diuretic therapy with low-dose spironolactone for adults with resistant hypertension starting step 4 treatment who have a blood potassium level of 4.5 mmol/l or less. Use particular caution in people with a reduced estimated glomerular filtration rate because they h

☐ accept ☐ edit ☐ reject

---

## Q017 - multi_step

**Q** Two patients both have stage 1 hypertension - one is 58 with a 10-year cardiovascular risk of 8%, the other is 84 with a clinic reading of 154/88. Should either be offered drug treatment?

**A** Both may be considered for drug treatment alongside lifestyle advice. For the 58-year-old, treatment can be considered despite the 10-year risk being below 10%, bearing in mind that 10-year risk may underestimate lifetime probability. For the 84-year-old, treatment can be considered because clinic blood pressure is over 150/90 mmHg, using clinical judgement if there is frailty or multimorbidity.

*Evidence 1: `rec 1.4.12` chars `[18771:19076]`*

> 1.4.12 Consider antihypertensive drug treatment in addition to lifestyle advice for adults aged under 60 with stage 1 hypertension and an estimated 10-year risk below 10%. Bear in mind that 10-year cardiovascular risk may underestimate the lifetime probability of developing cardiovascular disease. [2019]

*Evidence 2: `rec 1.4.13` chars `[19078:19378]`*

> 1.4.13 Consider antihypertensive drug treatment in addition to lifestyle advice for people aged over 80 with stage 1 hypertension if their clinic blood pressure is over 150/90 mmHg. Use clinical judgement for people with frailty or multimorbidity (see also NICE's guideline on multimorbidity). [2019]

*Why multi-passage: Two distinct age-based criteria; neither passage covers both patients.*

☐ accept ☐ edit ☐ reject

---

## Q018 - multi_step

**Q** A patient aged 83 and a patient aged 62 are both being treated for hypertension. Do they have the same clinic blood pressure target?

**A** No. The 62-year-old should be reduced to below 140/90 mmHg, while the 83-year-old should be reduced to below 150/90 mmHg, with clinical judgement used if there is frailty or multimorbidity.

*Evidence 1: `rec 1.4.20` chars `[23446:23646]`*

> 1.4.20 For adults with hypertension aged under 80, reduce clinic blood pressure to below 140/90 mmHg and ensure that it is maintained below that level. See also table 1 for guidance on clinic blood pr

*Evidence 2: `rec 1.4.21` chars `[23763:24013]`*

> 1.4.21 For adults with hypertension aged 80 and over, reduce clinic blood pressure to below 150/90 mmHg and ensure that it is maintained below that level. Use clinical judgement for people with frailty or multimorbidity (see NICE's guideline on multi

*Why multi-passage: Requires both age-band targets.*

☐ accept ☐ edit ☐ reject

---

## Q019 - comparative

**Q** A patient's clinic reading is 184/122 but they have no symptoms suggesting they need to be seen the same day. What should happen?

**A** Carry out investigations for target organ damage as soon as possible.

*Evidence 1: `rec 1.5.1` chars `[35973:36244]`*

> 1.5.1 If a person has severe hypertension (clinic blood pressure of 180/120 mmHg or higher), but no symptoms or signs indicating same-day referral (see recommendation 1.5.2), carry out investigations for target organ damage (see recommendation 1.3.3) as soon as possible:

☐ accept ☐ edit ☐ reject

---

## Q020 - factual

**Q** On standing, a patient's systolic blood pressure drops by 24 mmHg. Is this significant enough to act on?

**A** Yes - a fall of 20 mmHg or more in systolic blood pressure after standing for at least 1 minute meets the threshold for further action.

*Evidence 1: `rec 1.1.6` chars `[8565:8754]`*

> 1.1.6 If the person's systolic blood pressure falls by 20 mmHg or more, or their diastolic blood pressure falls by 10 mmHg or more, after the person has been standing for at least 1 minute:

☐ accept ☐ edit ☐ reject

---
