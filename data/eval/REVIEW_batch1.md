# Evaluation dataset - review sheet, batch 1 (NG28)

Six drafted candidates for your verification. **These are drafts, not data.**
Nothing here counts until you have checked it against the source and set
`verified: true`.

Every passage below has been machine-checked to appear VERBATIM in
`data/interim/NG28.txt` at the character offsets shown, so you will not waste
time on quotes that do not exist. What the machine cannot check is whether the
question is sensible, whether the answer is complete, and whether a multi-step
question genuinely needs all its passages. That is your judgement.

---

## Q001 - factual

**Question**  
What HbA1c target should be supported for an adult whose type 2 diabetes is managed by healthy living and diet alone?

**Reference answer**  
An HbA1c level of 48 mmol/mol (6.5%).

**Evidence (1 passage(s))**

1. `rec 1.5.7` - chars `[21126:21425]` in NG28

> 1.5.7 For adults whose type 2 diabetes is managed either by healthy living and diet, or healthy living and diet combined with an initial medication regimen that is not associated with hypoglycaemia (see the section on initial medicines), support them to aim for an HbA1c level of 48 mmol/mol (6.5%).

**Your verdict:** ☐ accept  ☐ accept with edits  ☐ reject

---

## Q002 - factual

**Question**  
At what HbA1c level does NICE indicate that treatment is not adequately controlled by the initial medication regimen in adults with type 2 diabetes?

**Reference answer**  
58 mmol/mol (7.5%) or higher.

**Evidence (1 passage(s))**

1. `rec 1.5.8` - chars `[21566:21725]` in NG28

> 1.5.8 In adults with type 2 diabetes, if HbA1c levels are not adequately controlled by the initial medication regimen and rise to 58 mmol/mol (7.5%) or higher:

**Your verdict:** ☐ accept  ☐ accept with edits  ☐ reject

---

## Q003 - factual

**Question**  
Which two medicines should be offered to adults with early onset type 2 diabetes?

**Reference answer**  
Modified-release metformin and an SGLT-2 inhibitor.

**Evidence (1 passage(s))**

1. `rec 1.16.1` - chars `[78352:78489]` in NG28

> 1.16.1 For adults with early onset type 2 diabetes, offer modified-release metformin and an SGLT-2 inhibitor, and consider adding either:

**Your verdict:** ☐ accept  ☐ accept with edits  ☐ reject

---

## Q004 - factual

**Question**  
Can a GLP-1 receptor agonist and a DPP-4 inhibitor be prescribed together for type 2 diabetes?

**Reference answer**  
No. NICE states that both should not be offered together.

**Evidence (1 passage(s))**

1. `rec 1.24.6` - chars `[115038:115166]` in NG28

> 1.24.6 Do not offer both a GLP-1 receptor agonist or tirzepatide and a DPP-4 inhibitor together to treat type 2 diabetes. [2026]

**Your verdict:** ☐ accept  ☐ accept with edits  ☐ reject

---

## Q005 - comparative

**Question**  
What should be checked before starting an SGLT-2 inhibitor, and what dietary pattern may require delaying treatment?

**Reference answer**  
Whether the person is at increased risk of diabetic ketoacidosis; a very low carbohydrate or ketogenic diet may require delaying treatment until the diet has changed.

**Evidence (2 passage(s))**

1. `rec 1.21.1` - chars `[103822:103968]` in NG28

> 1.21.1 Before starting an SGLT-2 inhibitor, check whether the person may be at increased risk of diabetic ketoacidosis (DKA), for example if they:

2. `rec 1.21.2` - chars `[104179:104405]` in NG28

> 1.21.2 Address modifiable risks of DKA before starting an SGLT-2 inhibitor. For example, people who are following a very low carbohydrate or ketogenic diet may need to delay treatment until they have changed their diet. [2022]

**Your verdict:** ☐ accept  ☐ accept with edits  ☐ reject

---

## Q006 - multi_step

**Question**  
How does NICE's advice on continuing SGLT-2 inhibitors differ from its advice on stopping GLP-1 receptor agonists when glycaemic targets are not met?

**Reference answer**  
SGLT-2 inhibitors may be continued for cardiovascular or renal benefits even if glycaemic targets are not reached, whereas GLP-1 receptor agonists or tirzepatide should be stopped if they do not help reach targets and are not being taken for cardiovascular benefits.

**Evidence (2 passage(s))**

1. `rec 1.24.2` - chars `[114425:114602]` in NG28

> 1.24.2 Consider continuing SGLT-2 inhibitors for their cardiovascular or renal benefits, even if they do not help the person reach their individualised glycaemic targets. [2026]

2. `rec 1.24.4` - chars `[114722:114919]` in NG28

> 1.24.4 Stop GLP-1 receptor agonists or tirzepatide if they do not help the person reach their individualised glycaemic targets and they are not being taken for their cardiovascular benefits. [2026]

*Note: Requires both passages: neither alone supports the contrast.*

**Your verdict:** ☐ accept  ☐ accept with edits  ☐ reject

---

## What to check on each one

1. **Is the question one someone would actually ask?** If it reads like it was
   reverse-engineered from a sentence, it is a weak test item.
2. **Is the reference answer fully supported and complete?** Nothing added that
   is not in the passage; nothing important from the passage left out.
3. **For comparative and multi-step: are all the passages genuinely needed?**
   If one passage alone could answer it, it is a factual question wearing a
   costume - and multi-step items are where hybrid retrieval is expected to
   show its advantage, so mislabelling them weakens H2.
4. **Is the answer traceable?** Open `data/interim/NG28.txt`, jump to the
   character offset, and confirm the passage is really the evidence.

## Target composition for the full set

| Type | Target | This batch |
|---|---|---|
| factual | 24 | 4 |
| comparative | 18 | 1 |
| multi_step | 18 | 1 |
| **total** | **60** | **6** |

Evidence must also be spread across all four guidelines - the validator flags
any guideline contributing under 12% of gold passages.
