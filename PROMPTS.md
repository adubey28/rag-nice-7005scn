> ## SUPERSEDED IN PART — read this before running anything (added 12 Aug 2026)
>
> This run sheet was written while the experiment was being built. The setup and
> verification steps (R1–R6) remain correct. **Step R7 is now dangerous**, and
> the sheet predates the LLM-judged context metrics entirely. Where this file
> and `EVIDENCE.md` disagree, **`EVIDENCE.md` is authoritative.**
>
> ### R7 — DO NOT RUN `run_experiment.py --all`
>
> R7 instructs you to run `python scripts/run_experiment.py --all`. **Do not.**
> That regenerates every answer. Gemini 3.x deprecated `temperature`, so
> regeneration returns different answers, different faithfulness scores and
> different results — replacing the experiment rather than reproducing it. Every
> figure in `EVIDENCE.md` would cease to describe the artefact.
>
> There is also an integrity dimension: the results are already known and both
> hypotheses are unsupported. Re-running after seeing that, then reporting
> whichever numbers emerged, is not defensible. Report the run that was
> pre-specified, scored once and audited.
>
> **`--score` is safe and idempotent.** It scores cached answers and never
> regenerates. All scoring commands in this project used `--score`.
>
> ### Other corrections
>
> | In this file | Status as of 12 Aug 2026 |
> |---|---|
> | R7 expects 300 generations across 5 conditions | **420** across 7 (the sweep at k=3 and k=10 adds two) |
> | No mention of context metrics | `--include-llm-context-metrics` scores `llm_context_precision` and `llm_context_recall`. Undefined for the baseline, which retrieves nothing, and excluded automatically. See EVIDENCE.md S31. |
> | Setup extracts `rag-nice-final.zip` | The current archive is built by `scripts/make_submission.py`. The warning about never using `-Force` over an existing tree still applies and is still the reason a patch was silently reverted on 11 Aug. |
> | `verify_install.py` marker list | Extended 12 Aug with three markers covering the ragas column mapping, the baseline exclusion and the `**cached` merge. Without them it passed on an unpatched file. See EVIDENCE.md S34. |
>
> R2's expected chunk figures (fixed 547 / mean 770.8; semantic 509 / mean 789.6)
> are still correct and were reproduced on a clean clone on 12 Aug (S36).

# Claude Code run sheet

The clean, linear procedure for building and running this experiment from
scratch. Each step assumes the previous one passed.

This is the **procedure**, not the history. The development history - every
error found, every parameter decision and why - is in `EVIDENCE.md`, which is
the audit trail and the source material for the methodology chapter. Keeping
them separate means this file stays runnable while nothing is lost.

Paste each block into Claude Code in order and run in the FOREGROUND. Claude
Code reads `CLAUDE.md` on startup, so it already knows the project rules.

---

## Setup (once)

```powershell
cd ~\Downloads

# DANGER - DO NOT run `Expand-Archive rag-nice-final.zip -Force` over an
# existing rag-nice folder. On 11 Aug 2026 that command silently reverted
# src/evaluate_ragas.py to a pre-patch version while leaving newer files in
# place, so the project looked correct and scored with known-broken code.
# -Force overwrites; it does not remove files that are not in the archive, so
# the result is a SILENT MIXTURE of old and new. Extract only into an empty
# directory:
if (Test-Path rag-nice) {
    Write-Host "rag-nice already exists - do NOT re-extract. Skip to the venv step." -ForegroundColor Yellow
} else {
    Expand-Archive rag-nice-final.zip -DestinationPath .
}

cd rag-nice
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Create .env ONLY if it does not already exist. `copy` would overwrite your
# keys with the blank template - this has happened once and cost a run.
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env      # add GOOGLE_API_KEY and DEEPINFRA_API_KEY, save, close
python scripts\check_env.py       # confirm BOTH keys show OK before proceeding
python scripts\verify_install.py  # confirm no stale code is present
claude
```

`verify_install.py` is not optional. It checks that the scoring code on disk is
the patched version and that no superseded copy survives anywhere. A patch you
believe is installed but is not is worse than no patch, because it removes the
suspicion that would otherwise make you check.

Confirm `.env` is named `.env` and not `.env.txt` (File Explorer: View ->
File name extensions).

---

## R1 - Verify the environment

```
Read CLAUDE.md and EVIDENCE.md.

1. python scripts/check_env.py --list-models
   Report the output verbatim. If config.GEN_MODEL is not in the available
   model list, tell me which models ARE available and STOP - do not choose a
   substitute. The generator is a held-constant experimental variable.

2. python -m pytest tests/ -q
   Every test must pass. Do not hard-code an expected count here - it
   changes whenever a script or test file is added, and a stale number
   trains you to ignore the real one. Record the count in EVIDENCE.md.

Report both results before continuing.
```

## R2 - Build the corpus and both indexes

Derived artefacts are not shipped, so this step is required, not optional.

```
python scripts/build_all.py --docs NG28 NG136 NG238 NG106

Report, for BOTH chunking arms: chunk count, per-document counts,
min/median/mean/max length, count of chunks under 100 chars, offset integrity,
and FAISS vector count vs chunk record count.

Expected (from EVIDENCE.md sections 11 and 13):
  fixed     547 chunks, mean 770.8, min >= 100, 547/547 offsets exact
  semantic  509 chunks, mean 789.6, min >= 100, 509/509 offsets exact

Report ANY figure that differs. Offset integrity below 100% on either arm means
chunk spans no longer address the right passages, which silently invalidates
every retrieval metric - stop and tell me rather than proceeding.
```

## R3 - Verify grounding and refusal behaviour

The single most consequential check. If the system answers a question the
corpus cannot support, every faithfulness score collected afterwards is
measuring the wrong thing.

```
Run each and paste the FULL output.

POSITIVE CONTROLS - should answer, citing extracts:

python src/ask.py --show-context "What HbA1c target should be agreed with adults with type 2 diabetes managed by diet and lifestyle alone?"
python src/ask.py "What is recommended as first-line treatment for adults with chronic heart failure with reduced ejection fraction?"

REFUSAL TESTS - must reply exactly:
"The provided guideline extracts do not state this."

python src/ask.py "What is the capital of Peru?"
python src/ask.py --show-context "What is the recommended first-line inhaled therapy for adults with COPD?"
python src/ask.py --show-context "What is the target INR range for an adult taking warfarin for atrial fibrillation?"

BASELINE - same question, no retrieval:

python src/ask.py --baseline "What HbA1c target should be agreed with adults with type 2 diabetes managed by diet and lifestyle alone?"

The COPD and warfarin tests matter most. Both are plausible clinical questions
from adjacent NICE guidelines NOT in this corpus, so retrieval returns
superficially related cardiometabolic text and the model must refuse anyway
rather than answering from its own medical knowledge. That is exactly the
hallucination mode faithfulness is designed to detect.

DO NOT edit config.SYSTEM_PROMPT to make a failing test pass. Report the actual
behaviour.
```

## R4 - Verify retrieval fusion

```
For each of these five questions, run retrieval under BOTH dense and hybrid at
top_k=5 on the fixed arm, and report the retrieved chunk_ids side by side plus
the dense_rank and sparse_rank provenance fields on the hybrid results:

  - "HbA1c target for adults managed by diet alone"
  - "amlodipine calcium channel blocker step 1"
  - "NT-proBNP threshold for urgent referral"
  - "atorvastatin 20 mg primary prevention QRISK3"
  - "eGFR threshold for reviewing metformin dose"

State on how many of the five hybrid returned a different ordering from dense.
If the answer is zero, BM25 is contributing nothing and H2 cannot be tested -
report that rather than adjusting anything.

Note this is a mechanism check, not a result. It shows only that fusion changes
the ranking, not that hybrid retrieves more relevant chunks. That is settled by
the gold-span evaluation, which may find hybrid worse on some question types.
```

## R5 - Validate the evaluation dataset

Run after the 60 question-answer pairs have been manually verified.

```
python scripts/validate_dataset.py

Report the full output. For every error, give the question_id and exactly what
needs changing. Do NOT edit data/eval/eval_dataset.json yourself - it is the
authored measuring instrument and only the researcher may change it.
```

## R6 - Paraphrase robustness (retrieval only, no cost)

Checks whether retrieval depends on the specific wording of the evaluation set.
No generation, no judge, no API spend.

```
python scripts/paraphrase_robustness.py --chunking fixed --retrieval dense
python scripts/paraphrase_robustness.py --chunking fixed --retrieval hybrid
python scripts/paraphrase_robustness.py --chunking semantic --retrieval hybrid

Report the mean recall by phrasing and the mean paraphrase delta for each.
Interpretation thresholds are built into the script and were fixed before any
result was seen.
```

## R7 - Run the experiment

```
python scripts/run_experiment.py --dry-run     # plan and budget, spends nothing
python scripts/run_experiment.py --all

Generation and scoring are both cached per question, so an interrupted run
resumes exactly where it stopped and never repays for work already done.

Report: per-condition completion counts, any API errors, total runtime, and the
final summary table.

Generation and scoring are cached per question, so an interrupted run resumes
exactly where it stopped. If it halts on a rate limit, simply run the same
command again.

Do NOT interpret differences in the summary means as results. Significance
testing and effect sizes come afterwards.
```

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| `MISS GOOGLE_API_KEY` / `MISS DEEPINFRA_API_KEY` | `.env` missing, or saved as `.env.txt` |
| `404 no longer available` on the generator | Model decommissioned; report the model list, do not substitute |
| `400 INVALID_ARGUMENT` on generation | Config ladder in `generate.py` should handle it; report if it does not |
| Offset integrity below 100% | Chunks built against different corpus text; rerun R2 with `--overwrite` |
| `ModuleNotFoundError: langchain_community.chat_models.vertexai` | `langchain-community` newer than 0.3.29; reinstall from `requirements.txt` |
| `UnicodeEncodeError` on Windows console | Should be fixed; report if it recurs |
