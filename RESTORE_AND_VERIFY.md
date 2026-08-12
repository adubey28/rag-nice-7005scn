# FRESH START — restore and verify

Run sheet for moving to `rag-nice-v2-2026-08-11.zip` without losing results.
Every step has a pass condition. If a step fails its condition, STOP and report
it rather than continuing — each gate exists because something once passed
silently while being wrong.

---

## The principle behind this procedure

The pipeline splits into two halves with different reproducibility properties,
and they must be treated differently.

**Deterministic** — ingestion, cleaning, chunking, embedding, indexing,
retrieval and all retrieval metrics. Given the same PDFs and the same embedding
model these reproduce exactly, and the expected values are already recorded in
`EVIDENCE.md`. Rebuilding them from scratch is therefore not a risk: it is a
reproducibility check with a known answer.

**Not deterministic** — generation. `config.py` records that Gemini 3.x
deprecates `temperature` and cannot fully disable thinking, so the same prompt
does not reliably return the same answer. The 420 cached answers **cannot be
regenerated identically.** Re-generating would produce a different experiment,
not a repeat of this one. The committed mitigation is that every answer is
generated once, cached, and all scoring runs against that one fixed set.

So: rebuild the deterministic half, preserve the other half, and verify both.

---

## Step 0 — Back up. Not optional.

```powershell
cd ~\Downloads
Copy-Item rag-nice -Destination rag-nice-BACKUP-2026-08-11 -Recurse
```

Pass condition: the backup folder exists and contains `outputs\ragas_cache`
with 600 files.

```powershell
(Get-ChildItem rag-nice-BACKUP-2026-08-11\outputs\ragas_cache -Filter *.json).Count
```

Expect **600**. If this is not 600, stop — do not proceed until you know why.

---

## Step 1 — Move the old tree aside

```powershell
Rename-Item rag-nice rag-nice-old
```

Do not delete it. It stays until the new tree is fully verified.

---

## Step 2 — Extract the new tree

```powershell
Expand-Archive rag-nice-v2-2026-08-11.zip -DestinationPath .
```

Extract into an EMPTY location. Never use `-Force` over an existing tree: it
overwrites files but does not remove files absent from the archive, producing a
silent mixture of old and new. That is precisely how a reverted patch went
unnoticed on 11 Aug 2026.

---

## Step 3 — Restore the two things the archive cannot contain

```powershell
Copy-Item rag-nice-old\.env        -Destination rag-nice\
Copy-Item rag-nice-old\outputs\*   -Destination rag-nice\outputs\ -Recurse -Force
```

That is all. `data\index\` is deliberately NOT copied — it is derived, and
Step 6 rebuilds it. Restoring less means less to go wrong.

---

## Step 4 — Environment

```powershell
cd rag-nice
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\check_env.py
```

Pass condition: every package OK, **both** API keys OK, all four PDFs found,
and the embedding sanity check reports that the related pair scores higher.

If `.env` shows as missing, check it is named `.env` and not `.env.txt`
(File Explorer → View → File name extensions).

---

## Step 5 — Prove no stale code is present

```powershell
python scripts\verify_install.py
python -m pytest tests\ -q
```

Pass conditions:

* `ALL CHECKS PASSED`
* **0 failed.** Record the passing count in `EVIDENCE.md` section 29, which
  carries a `TO CONFIRM` marker. Do not copy a number you have not seen.

`verify_install.py` also fails if any module exists in both `src\` and
`scripts\`, which is the import-shadowing defect from EVIDENCE section 27.

---

## Step 6 — Rebuild the deterministic half from scratch

This is the reproducibility demonstration. It calls no API and spends nothing.

```powershell
python scripts\build_all.py --docs NG28 NG136 NG238 NG106
```

Pass conditions, from `EVIDENCE.md` sections 11 and 13:

| Arm | Chunks | Mean length | Offset integrity | FAISS vectors |
|---|---|---|---|---|
| fixed | **547** | **770.8** | **547/547 exact** | 547 = 547 |
| semantic (p85) | **509** | **789.6** | **509/509 exact** | 509 = 509 |

Any deviation matters. Offset integrity below 100% means chunk spans no longer
address the right passages, which silently invalidates every retrieval metric.
A stale chunk file once showed 162/548 valid while looking entirely normal.

Report any figure that differs and stop.

---

## Step 7 — Verify the preserved half

```powershell
python scripts\diagnose_scoring.py
```

Pass condition:

```
TOTAL    600 scored    0 missing    0 NaN    0 bad
```

and no orphaned-cache warning. The cache key is
`sha256(condition|question_id|metric|judge_model)`, so a file that was wrong,
truncated, or produced under a different judge model cannot pass this check
silently — it appears as missing, bad, or orphaned.

An independent corroboration is available for free: `run_experiment.py` filters
scores with `is not None`, which admits NaN, and one NaN in 60 makes the printed
mean NaN. If Step 8 prints ten finite means, the cache contains no NaN.

---

## Step 8 — Re-derive the results

```powershell
python scripts\run_experiment.py --score
```

Every condition must report `60 cached, 0 to score`. **Nothing should be sent to
the judge.** If any condition wants to score, the restore is incomplete — stop
and re-check Step 3.

Then:

```powershell
python scripts\analyse.py
```

Pass conditions:

* the summary table matches the values recorded on 11 Aug 2026
* `outputs\figures\` contains **6** PNG files
* no `[figures] skipped` line

```powershell
(Get-ChildItem outputs\figures -Filter *.png).Count
```

---

## Step 9 — Confirm, then keep the old tree anyway

Once Steps 5–8 all pass, `rag-nice-old` and the backup are redundant. Keep both
until the dissertation is submitted. They cost disk space and nothing else.

---

## What must NOT be re-run, and why

`python scripts\run_experiment.py --all` regenerates answers. Do not run it.

Gemini 3.x ignores `temperature`, so regeneration produces different answers,
different faithfulness scores, and different results. The experiment would be
replaced rather than reproduced, and every number already recorded in
`EVIDENCE.md` would cease to describe the artefact.

There is also an integrity dimension. The results are already known: H1 and H2
were not supported. Re-running after seeing that, and then reporting whichever
set of numbers came out, is not a defensible position — and an examiner is
entitled to ask which run was reported and why. Report the run that was
pre-specified, scored once, and audited. That is this one.

---

## Open decisions to settle before the Results chapter is drafted

**Refusal handling.** Refusals produce undefined (NaN) faithfulness because
there are no claims to verify. Refusal rate differs by condition, so silently
dropping them biases the H1 comparison in favour of whichever condition refuses
more. Recommended rule, to be fixed in writing before drafting:

> Faithfulness is reported as the mean over scoreable questions, accompanied by
> an explicit count of unscoreable (refused) questions per condition.

**Top-k sweep scoring.** `semantic_hybrid_k3` and `semantic_hybrid_k10` have
retrieval metrics but no RAGAS scores, so the sensitivity figure plots two of
three lines. Scoring them costs roughly two unattended hours and would test
whether retrieval depth affects faithfulness — potentially the most interesting
positive finding available, given both hypotheses are null. Decide before
drafting, not after.

**Precision@k ceiling.** With approximately one gold chunk per question and
k=5, the maximum attainable P@5 is about 0.2. Observed values are 0.183–0.203,
i.e. at the ceiling, so P@k cannot discriminate between retrieval methods here.
State this explicitly or report a normalised figure; presenting the four values
as a comparison without the ceiling would be a genuine weakness.
