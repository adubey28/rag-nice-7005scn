# Development Logbook — 7005SCN

This logbook records *what I did and
why* on each day. `EVIDENCE.md` records *what was measured*, with the numbers,
commands and outputs behind every claim. Where an entry below cites a section
number (S12, S21 and so on), that is the corresponding evidence in `EVIDENCE.md`.

---

## Session 1 — Environment, corpus, first ingestion
**Stage & aim:** Stand up the pipeline on a single guideline (NG28) to de-risk the
stack before committing to the full corpus.

**What I did:** Built the Python 3.11 environment and resolved the dependency set.
Downloaded NG28 from nice.org.uk, recorded the download date and the guideline's
"Last updated" date, and ran ingestion with SHA-256 hashing and frequency-based
header/footer removal.

**Result / evidence:** Ingestion clean; residual furniture audit all zero (S3).
Fixed-size chunking produced coherent chunks with 100% offset integrity (S4).

**Decision made and why:** Python 3.11 rather than 3.12/3.13 — `faiss-cpu` and
`torch` wheels are best-tested there and RAGAS's dependency tree is fussier on
newer interpreters. Exact search (FAISS `IndexFlatIP`) rather than approximate
nearest neighbour: the corpus is ~550 chunks, so ANN buys nothing and introduces
a source of non-determinism I would then have to control for.

**Risk noted:** Free-tier quota is the binding constraint on the whole experiment.
Everything that can be done offline should be done offline.

**Next action:** Verify the embedding model on real hardware, then scale to four
guidelines.

---

## Session 2 — Independent reproduction on the target machine
**Stage & aim:** Reproduce the build on the machine that will run the experiment,
rather than assuming it transfers.

**What I did:** Rebuilt from scratch in a clean virtual environment. Ran the
embedding model on real hardware for the first time. Recorded resolved package
versions for the reproducibility appendix.

**Result / evidence:** Ingestion reproduced exactly (S7.1). Embedding sanity check
behaved sensibly — related clinical terms scored higher than unrelated ones
(S7.2). Resolved versions recorded (S7.3).

**Problem hit → how resolved:** Two defects that only appeared under reproduction.
The test suite was **non-deterministic across hash seeds** (S7.4) — it had been
passing by accident, not by correctness. And **test dependencies were missing**
from `requirements.txt` (S7.5), so the suite could not run on a clean install at
all. Both fixed.

**Decision made and why:** Reproduction is not a formality. Two real defects were
invisible on the machine where the code was written. From here, every stage ends
at a gate with a measured pass condition, recorded in `EVIDENCE.md`.

**Risk noted:** Defects that hide in code paths never executed in isolation. This
became the recurring theme of the project.

**Next action:** Verify the generator model is actually callable.

---

## Session 3 — Live API verification; the generator was gone
**Date:** 5 August 2026
**Stage & aim:** Confirm the generator named in the approved proposal is available
before building anything that depends on it.

**What I did:** Listed available models and attempted a live call to
`gemini-2.5-flash`, the model specified in the proposal.

**Result / evidence:** `404 NOT_FOUND — no longer available to new users` (S8.2).
The model **appears in `models.list()` but is not callable.**

**Decision made and why:** Substituted `gemini-3.6-flash`, the current Flash model.
This is a forced substitution, not a preference, and it carries a real
methodological cost: the Gemini 3.x line **deprecates `temperature`** and cannot
fully disable thinking, so generation is no longer bit-reproducible (S8.3). The
mitigation is that every answer is generated **once**, cached, and all scoring runs
against that one fixed set. The experiment is therefore internally consistent and
auditable even though the generator is not deterministic. This must be reported as
a stated limitation, not glossed.

**Problem hit → how resolved:** Learned that catalogue presence is not evidence of
availability. This mattered again later when assessing the fallback model.

**Risk noted:** Further model deprecations mid-project. Everything model-related is
now pinned in `config.py` and verified by live test rather than assumption.

**Next action:** Calibrate semantic chunking against the fixed-size baseline.

---

## Session 4 — Semantic chunking, and the confound it exposed
**Date:** 6 August 2026
**Stage & aim:** Implement semantic chunking and check it is a fair comparator for H1.

**What I did:** Ran semantic chunking at the initial percentile (95) and compared
chunk-length statistics against the fixed-size arm.

**Result / evidence:** At p95 the semantic arm produced chunks averaging **1.49×**
the fixed-size mean (S9.1). It also produced degenerate fragments — very short
chunks carrying no usable content (S9.2).

**Decision made and why:** This is a confound, not a detail. If semantic chunks are
half again as long, then at the same top-k the semantic conditions see
substantially more context, and any faithfulness difference could be explained by
context volume rather than by chunking strategy. **H1 would be untestable.**

Two remedies, both applied *before any result existed* (S9.3, S10):
1. Calibrated the breakpoint percentile against chunk-length statistics only.
   p85 gave a mean ratio of 1.04 against 1.49 at p95.
2. Applied `merge_undersized()` symmetrically to **both** arms at a 100-character
   minimum, so neither arm is advantaged by the fix.

**Risk noted, and it stands:** the arms are matched on the **mean**, not on the
distribution (S10.1, and later S38). Chunk-length variance remains an uncontrolled
difference between the H1 conditions. This is a limitation to state, not one to
hide — matching distributions would mean abandoning the percentile-breakpoint
algorithm, which is the strategy under test.

**Next action:** Lock both arms and verify offset integrity.

---

## Session 5 — Judge provider forced to change; integrity audit
**Date:** 7 August 2026
**Stage & aim:** Secure a judge model and audit what had been built so far.

**What I did:** Attempted to secure the planned judge (Llama 3.3 70B on Groq).
Then ran an integrity audit across the codebase.

**Result / evidence:** The judge model was **deprecated on Groq** with shutdown
around 16 Aug; the viable alternative was capped at ~200k tokens/day, roughly 5.2
days for this experiment; and **paid upgrades were frozen** ("temporarily
unavailable due to high demand"). Moved to Llama 3.3 70B on DeepInfra — same model
family as planned, no daily cap, whole experiment ~$0.15–0.30 (S15).

**Decision made and why:** The property that matters methodologically is that the
judge is a **different model family from the generator**, so no model grades its
own output. That property holds under every option considered, so the provider
change does not affect validity. Recorded as a forced substitution.

**Problem hit → how resolved:** The integrity audit found a real defect (S16), and
dependency resolution failed outright — `datasets==3.2.0` was pinned but `ragas
0.4.3` requires `>=4.0.0`, making the requirements file unsatisfiable (S19). Fixed
and verified by clean `pip install --dry-run` plus a full test run.

**Risk noted:** Free-tier providers are unstable infrastructure to build a
dissertation on. Every model and provider decision is now dated and evidenced.

**Next action:** Author the evaluation dataset.

---

## Session 6 — Evaluation dataset, and testing my own instrument
**Stage & aim:** Build and validate the 60-question evaluation set — the measuring
instrument the whole study depends on.

**What I did:** Authored 60 questions from the source guidelines (24 factual, 18
comparative, 18 multi-step), traced each reference answer to specific passages, and
stored gold evidence as **character spans** rather than as quoted text. Then tested
the instrument against itself.

**Result / evidence:** 60/60 verified, 0 errors, 88 gold passages, every span
resolving verbatim (S18.1). Composition matches the proposal exactly.

**Decision made and why:** Gold evidence as character spans, with relevance defined
as span overlap, is what makes retrieval metrics **comparable between the fixed and
semantic arms** despite their different chunk boundaries. Without it there is no
fair cross-arm comparison. This is the project's central invariant and is guarded
by tests.

**Problem hit → how resolved:** I measured **lexical leakage** — the degree to
which my questions share vocabulary with the source text (S17.1) — and rewrote the
worst offenders. Then ran a paraphrase robustness check: 27 probes × 2 independent
rewordings, retrieval only, with the interpretation thresholds **fixed before
seeing any result** (S17.3).

**Risk noted, and it turned out to matter:** if the questions' phrasing is doing
hidden work, the headline retrieval figures are optimistic. I wanted that known
either way.

**Next action:** Run the full experiment.

---

## Session 7 — Paraphrase robustness: the most interesting thing I found
**Stage & aim:** Run R3–R6 verification gates before spending quota on the
experiment.

**What I did:** Grounding and refusal tests, fusion check and  dataset validation.

**Result / evidence:**
- **Refusal 3/3 passed** (S21.1). The COPD and warfarin probes matter most: both
  are plausible clinical questions from guidelines *not* in the corpus, so
  retrieval returns superficially related cardiometabolic text and the model must
  refuse anyway. It did.
- **Fusion 5/5 reordered** (S21.2) — BM25 is contributing, so H2 is testable.
- **Paraphrase robustness: recall collapses from ~0.75 to ~0.08** across all three
  conditions tested (S21.3).

**Decision made and why:** I tested two competing explanations and eliminated both.
It was not query length — lay full-sentence and terse clinical paraphrases give
**identical mean recall (0.081 vs 0.081)**. It was not a near miss rejected by the
span threshold — among zero-recall cases, **75–80% still retrieved the correct
guideline**, but the median gap to the gold span was **6,000–9,900 characters**,
roughly 8–13 chunks away. The system reaches the right document and then the wrong
section of it.

**What this means, stated carefully (S21.4):** internal validity is preserved —
every condition faces identical questions, so H1 and H2 remain valid. What is
limited is **external validity**: the absolute retrieval figures describe
vocabulary-matched queries. **No condition was robust** — hybrid did not protect
against it, nor did semantic chunking.

**Risk noted:** 27 probes is small, paraphrases were authored by one person, and no
inter-rater check was done. Report as secondary and exploratory, not as a headline.

**Next action:** Generate.

---

## Session 8 — Generation run; a defect that cached failure as success
**Date:** 10 August 2026
**Stage & aim:** Generate answers for all conditions and begin scoring.

**What I did:** Ran generation across seven conditions (five core plus the k=3 and
k=10 sweep), 60 questions each. Began RAGAS scoring.

**Result / evidence:** 420 answers generated and cached.

**Problem hit → how resolved:** Found that **a failed metric was being cached as a
real score** (S25). RAGAS returns `np.nan` on failure rather than raising, so the
exception handler never fired and the NaN was written to cache as if valid — where
it would be trusted forever, because cached scores are never recomputed. Three
related defects fixed: dead exception-handler code, NaN caching, and the absence of
an explicit `RunConfig` causing silent long retries.

**Decision made and why:** Ran the corrected scoring in plain PowerShell rather
than through an agent — long unattended runs against irreplaceable cached data
should have the smallest possible number of moving parts.

**Risk noted:** `outputs/` is gitignored and exists only on this machine. Backing it
up is safety-critical. Took a full backup.

**Next action:** Complete scoring, then analyse.

---

## Session 9 — Four defects in one day, three of them in my own tooling
**Date:** 11 August 2026
**Stage & aim:** Complete scoring and produce the analysis.

**What I did:** Diagnosed an apparent stall, ran the integrity checks, produced
figures.

**Result / evidence:** Scoring completed, 0 missing, 0 NaN (S29). Deterministic half
rebuilt from scratch and reproduced exactly (S30).

**Problem hit → how resolved:** Four separate defects:
1. **The "stall" was a measurement artefact** (S26). The run was progressing
   silently; I was measuring it wrongly.
2. **A duplicated module enabled silent import shadowing** (S27) — the same module
   name in both `src/` and `scripts/`, so which one loaded depended on import order.
   Added a test that fails if any module name is duplicated.
3. **Figure generation broken by a matplotlib API removal** (S28).
4. **A patch I believed was installed had been silently reverted** — extracting an
   archive with `-Force` over an existing tree overwrites files but does not remove
   files absent from the archive, producing a silent mixture of old and new. The
   project looked correct and was scoring with known-broken code.

**Decision made and why:** Number 4 is the one that changed how I work. A patch you
believe is installed but is not is **worse than no patch**, because it removes the
suspicion that would otherwise make you check. Wrote `verify_install.py` to test
for specific code markers on disk, and stopped extracting archives over existing
trees.

**Risk noted:** My verification tooling is itself unverified. This proved warranted.

**Next action:** Score the top-k sweep; settle the open analysis decisions.

---

## Session 10 — Context metrics, three retracted claims, clean-clone reproduction
**Date:** 12 August 2026
**Stage & aim:** Complete the evaluation on all four RAGAS metrics and finalise the
analysis.

**What I did:** Scored LLM-judged context precision and recall for the four core
conditions, then for the k=3 and k=10 sweep. Ran the full analysis, effective-n and
precision-ceiling checks. Reproduced everything on a clean clone.

**Result / evidence:** 1,560 cached scores, 0 missing, 0 NaN, 0 corrupt.
- **H1 not supported** — effect reverses sign with retrieval method, p(Holm)=1.000.
- **H2 not supported** — all six comparisons p(Holm)=1.000. Hybrid is negative on
  both coverage metrics and positive on both ranking metrics.
- **Top-k sweep, both instruments** (S35): deterministic P@k falls **58%** from k=3
  to k=10 while LLM-judged context precision falls only **9.7%**. P@k × k gives
  0.80, 0.92, 1.12 relevant chunks retrieved — *rising* with depth. The apparent
  collapse is dominated by the denominator, not by degrading retrieval.
- **Clean-clone reproduction** (S36): fresh clone, fresh venv, every value identical
  to three decimal places including bootstrap confidence intervals.

**Decision made and why:** Analysed the two LLM context metrics in **separate
Holm-corrected families** rather than folding them into H2 (S31). H2 was
pre-specified as precision@k, recall@k and MRR; enlarging that family from 6 to 10
comparisons would tighten the correction applied to results I had already seen.
Adjusting a correction after observing results is not defensible. Recorded the
decision *before* computing any aggregate over the context scores.

**Problem hit → how resolved:** Three claims retracted, all mine:
1. **The P@k ceiling estimate was wrong** (S32). I had estimated ~0.2 by dividing
   gold *passages* by k and concluded P@k was saturated and could not discriminate.
   Measured properly, the ceilings are **0.273** and **0.263** with **~70%
   attainment** — not saturated. The error came from reasoning about the ceiling
   instead of measuring it.
2. **`diagnose_scoring.py` reported 120 phantom missing scores** (S33) by expecting
   context metrics for the baseline, which has no retrieved context.
3. **`verify_install.py` passed on an unpatched file** (S34) — it checked seven
   markers, none of which tested the three most recent fixes.

**Reflection:** all three of today's defects were in **verification tooling** — the
code whose only job is to tell me whether something is right. A tool that reports
confidently and wrongly is worse than no tool, because it removes the doubt that
would prompt a manual check. Three instances in one project is a pattern worth
stating in the write-up.

**Risk noted:** `EVIDENCE.md` §32 corrects a claim still repeated in an earlier run
sheet. Drafting Results from the run sheet rather than the evidence log would put a
false statement into the dissertation. Corrected at source.

**Next action:** Draft the report. Methodology and Artefact are the largest
remaining blocks.

---

## Submission builds

Package identity is recorded here for each build. The digest changes on every
rebuild because this logbook and the packaging script are themselves inside the
package — a recorded hash can never describe the build containing that record. The
definitive digest will be taken once on 17 Aug 2026, when the files stop changing.

| Date | Files | SHA-256 (zip) |
|---|---|---|
| 12 Aug 2026 rev 1 | 1645 | *(truncated value recorded in error — see note)* |
| 12 Aug 2026 rev 2 | 1642 | d06ff2668ac21be437f69817e71e278caabc175c6dbd7ccaf689f0bd6d63eea3 |
| 12 Aug 2026 rev 3 | 1642 | b523cd84d064c922fb7f48879d716889228095f429100274e5f3c1f567716319 |
| 12 Aug 2026 rev 4 | 1639 | e7c813bc418ce25952088d51490c621b4ec4a3c46ccf1ff786e1ea2f53fdafd7 |

**Note on rev 1.** The value first recorded was 32 hex characters, labelled
SHA-256. A SHA-256 digest is 64 characters. `make_submission.py` was printing the
first 32 characters followed by an ellipsis while instructing the operator to
record it, so following the tool's own instruction produced a half-digest that
verifies nothing. Fixed: the script now prints all 64 characters across two lines
and states that the full value is also stored as `zip_sha256` in `MANIFEST.json`.
A fourth verification-tooling defect, and the same class as the other three.

---

## Repository

`github.com/adubey28/rag-nice-7005scn` (private). Version control was introduced
late, when the artefact was already complete, so the commit history is short and is
**not** offered as evidence of how the work developed. That evidence is
`EVIDENCE.md` (38 dated sections) and this logbook.
