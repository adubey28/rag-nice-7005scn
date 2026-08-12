# EVIDENCE - Stage 1/2 executed against the real NICE corpus

Generated automatically from the ingestion run at 2026-08-04T18:24:53+00:00.
Every figure below is read from the output files, not transcribed by hand.

Reproduce with:

```
python src/ingest.py --docs NG28 NG136 NG238 NG106 --overwrite
python src/chunking.py --chunking fixed --docs NG28 NG136 NG238 NG106 --overwrite
```

## 1. Corpus provenance

| Doc | Format | Pages | NICE published | Last updated | SHA-256 (first 16) |
|---|---|---|---|---|---|
| NG28 | `pdf` | 131 | 2 December 2015 | 18 February 2026 | `1a3be64ff05a3a01` |
| NG136 | `pdf` | 52 | 28 August 2019 | 26 February 2026 | `07f00ff626bb0aa9` |
| NG238 | `pdf` | 52 | 14 December 2023 | - | `ca66058149bff1c4` |
| NG106 | `pdf` | 39 | 12 September 2018 | 3 September 2025 | `6e344e58fe587d67` |

> All four sources are genuine PDF 1.7 documents. Ingestion verifies the `%PDF`
> magic number rather than trusting the file extension and records `source_format`
> per document, so the corpus cannot become heterogeneous without it appearing in
> the provenance record.

## 2. Extraction and cleaning

| Doc | Raw chars | Cleaned chars | Retained | Structural footers removed | Repeated lines removed |
|---|---|---|---|---|---|
| NG28 | 213,388 | 186,888 | 87.6% | 130 | 0 |
| NG136 | 98,391 | 87,136 | 88.6% | 51 | 0 |
| NG238 | 87,435 | 74,603 | 85.3% | 51 | 1 |
| NG106 | 62,578 | 54,038 | 86.4% | 38 | 0 |

Retention is tightly clustered (85.3-88.6%), the expected signature of removing
per-page furniture only. A document far outside that band would indicate either
surviving boilerplate or cleaning that ate real content.

## 3. Residual furniture audit (target: all zero)

| Doc | 'All rights reserved' | 'Page N of' | '(NGxxx)' footer | control chars | numbered recommendations |
|---|---|---|---|---|---|
| NG28 | 0 | 0 | 0 | 0 | 142 |
| NG136 | 0 | 0 | 0 | 0 | 79 |
| NG238 | 0 | 0 | 0 | 0 | 103 |
| NG106 | 0 | 0 | 0 | 0 | 92 |

## 4. Chunking - fixed-size (1000 chars, 150 overlap)

- Total chunks: **553**
- Per document: NG28 257, NG136 118, NG238 106, NG106 72
- Length: min 31 / median 850 / mean 761 / max 999 chars
- Chunks under 100 chars: 5

### Offset integrity (the load-bearing invariant)

**553 / 553 chunks slice back to the source text exactly.**

Every retrieval metric depends on `[start_char, end_char)` locating the chunk in the
source document. If offsets drift, precision@k and recall@k silently measure nothing
while still producing plausible numbers. Verified here on the real corpus.

## 5. Known limitations observed in the real output

- Section headings are sometimes glued to the following sentence
  (e.g. "Healthy eating For advice on healthy eating, see..."). Cosmetic; does not
  affect span integrity, but note it as an extraction limitation.
- The corpus mixes ordinary hyphens with non-breaking hyphens (U+2011), which affects
  BM25 tokenisation of terms such as "mono-unsaturated". Worth a normalisation pass
  before the hybrid retrieval runs.

## 6. What is NOT yet verified

| Component | Status | Blocker |
|---|---|---|
| Ingestion (4 docs) | VERIFIED on real data | - |
| Fixed chunking | VERIFIED on real data | - |
| Semantic chunking | unit-tested only | needs embedding model (huggingface.co blocked) |
| Embedding + FAISS index | unit-tested with stub | needs embedding model |
| Dense retrieval | unit-tested with stub | needs embedding model |
| Hybrid retrieval (BM25+RRF) | unit-tested with stub | needs embedding model |
| Generation (Gemini) | NEVER EXECUTED | needs API key + network |
| RAGAS scoring | NOT YET BUILT | Stage 4 |

Unit tests prove the logic; only execution on the real corpus proves the system.
Everything not marked VERIFIED is Claude Code's job on the local machine.

---

## 7. Independent reproduction on the target machine (Claude Code, Windows)

Executed by Claude Code on Windows, Python 3.11.9, in a clean venv built from
`requirements.txt`.

### 7.1 Ingestion reproduced exactly

All figures in sections 1-3 above reproduced **doc-for-doc with no differences**:
page counts, provenance dates, SHA-256 prefixes, raw/cleaned character counts,
retention percentages, footer and repeat-removal counts, the residual-furniture
audit (all zero), and recommendation counts (142 / 79 / 103 / 92).

Ingestion is therefore reproducible across operating systems and Python builds.

### 7.2 Embedding model verified on real hardware (first time)

```
EMBEDDING MODEL
  OK    BAAI/bge-small-en-v1.5 -> shape (3, 384)
  sanity: cos('hypertension','high blood pressure') = 0.900
          cos('hypertension','diabetes')            = 0.684
```

384 dimensions as configured, and the related pair scores materially higher than
the unrelated pair. This is the first evidence that the embedding model works on
the target machine rather than through a test stub.

### 7.3 Resolved package versions (reproducibility appendix)

| Package | Pinned | Resolved |
|---|---|---|
| Python | 3.11.x | 3.11.9 (Windows AMD64) |
| pypdf | 5.1.0 | 5.1.0 |
| sentence-transformers | 3.3.1 | 3.3.1 |
| torch | 2.5.1 | 2.5.1+cpu |
| faiss-cpu | 1.9.0 | 1.9.0 |
| numpy | 1.26.4 | 1.26.4 |
| google-genai | 0.3.0 | 0.3.0 |
| pandas | 2.2.3 | 2.2.3 |

### 7.4 Defect found by reproduction: non-deterministic test suite

The independent run reported 28/29 rather than 29/29. Investigation showed a
real defect in the test suite, not in the pipeline.

The offline stub embedder hashed tokens with Python's built-in `hash()`, which is
salted with a **per-process random seed** unless `PYTHONHASHSEED` is pinned. The
stub therefore produced different vectors on every run, and the dense-retrieval
assertion passed or failed depending on the seed. Development runs had pinned
`PYTHONHASHSEED=0`, which concealed this and made the suite appear green.

Demonstration before the fix:

```
PYTHONHASHSEED=0 -> 3 passed
PYTHONHASHSEED=1 -> 1 failed, 2 passed
PYTHONHASHSEED=2 -> 1 failed, 2 passed
PYTHONHASHSEED=3 -> 3 passed
PYTHONHASHSEED=4 -> 1 failed, 2 passed
```

Fix: token hashing switched to `zlib.crc32`, which is stable across processes,
machines and Python versions. After the fix:

```
PYTHONHASHSEED=0,1,2,3,7,99 -> 29 passed (every seed)
unset, 3 consecutive runs   -> 29 passed, 29 passed, 29 passed
```

Two points for the report. First, this failure said nothing about the quality of
`bge-small-en-v1.5`; the affected test uses the stub, so the correct reading is a
flaky fixture, not a weak retriever. Second, it is a concrete example of why
independent reproduction on a second machine is a methodological requirement
rather than a courtesy - the defect was invisible on the development machine by
construction.

### 7.5 Second defect: missing test dependencies

`pytest` and `reportlab` were absent from `requirements.txt`, so a clean install
could not run the acceptance gate. Both are now pinned in the default install.

---

## 8. Live API verification (5 August 2026)

Executed by Claude Code on the target machine against the live Gemini Developer
API with a free-tier Google AI Studio key.

### 8.1 SDK

`google-genai` upgraded 0.3.0 -> **2.17.0**. `client.models.list()` succeeded
immediately after the upgrade, returning 42 model IDs. The earlier
501 UNIMPLEMENTED was therefore an artefact of the stale SDK, not an API
restriction and not a free-tier limitation. The REST fallback was not required.

### 8.2 Generator model selection - decided by live test, not assumption

| Model | Listed by `models.list()` | Callable | Outcome |
|---|---|---|---|
| `gemini-2.5-flash` | yes | **no** | `404 NOT_FOUND` - "no longer available to new users" |
| `gemini-3.6-flash` | yes | **yes** | Answers correctly once `thinking_budget` is not sent |

**Listing membership does not imply callability.** `gemini-2.5-flash` is
enumerated by the API but decommissioned for new callers, so it was not an
available option regardless of preference.

`gemini-3.6-flash` initially returned `400 INVALID_ARGUMENT`. The cause was the
request carrying `thinking_config.thinking_budget=0`, which the 3.x line does not
accept. Critically, the config object *constructs* without error and is rejected
only at request time, so a try/except around construction cannot catch it.

**Decision: the experiment runs on `gemini-3.6-flash`.**

### 8.3 Consequence for the methodology - stated limitation

The 3.x line deprecated `temperature`, `top_p` and `top_k`, and thinking cannot
be fully disabled. Generation is therefore **not bit-reproducible**: the same
prompt may yield a different answer on a later run. The original design assumed
`temperature=0`; that assumption no longer holds and must be corrected in the
methodology rather than quietly retained.

Mitigations implemented:

1. Every generated answer is cached and archived, so all scoring runs against one
   fixed set of outputs. Results are internally consistent and fully auditable
   even though the generator is not deterministic.
2. Each output record carries `temperature_applied` and `gen_config_variant`, so
   the report can state exactly what was sent to the API rather than what was
   intended.

### 8.4 Code change: runtime config fallback ladder

`generate.py` now tries an ordered list of config variants per model family and
uses the first the API accepts, recording which one succeeded. Transient errors
(429/5xx) are retried with exponential backoff; rejected arguments (400/404) are
**not** retried, since retrying a rejected payload burns five calls of free-tier
quota and fails anyway.

Verified offline by `tests/test_generation_config.py` (12 tests, faked client, no
quota consumed), including a regression test reproducing the exact 3.6-flash
`thinking_budget` rejection observed live.

**Full suite: 41 tests passing.**

---

## 9. Semantic chunking first real run (C2) and the confound it exposed

Executed by Claude Code on the real four-guideline corpus.

| Strategy | Chunks | NG28 | NG136 | NG238 | NG106 | min | median | mean | max |
|---|---|---|---|---|---|---|---|---|---|
| fixed (1000/150) | 553 | 257 | 118 | 106 | 72 | 31 | 850 | 760.9 | 999 |
| semantic (p95, buffer 1, max 2000) | 354 | 169 | 71 | 66 | 48 | 5 | 1225 | 1136.1 | 1997 |

**Offset integrity: fixed 553/553 exact, semantic 354/354 exact.** The span
invariant holds for both strategies on real data.

**Semantic chunking cost:** 287.2s chunking/embedding plus 80.4s index build =
367.6s, approximately 2.4x the fixed condition. Reportable as a secondary
outcome (the computational price of the semantic strategy).

### 9.1 The confound

Semantic mean 1,136.1 vs fixed 760.9 = **ratio 1.49**, immediately below the 1.5
stop condition. At a fixed retrieval depth of k=5 the semantic condition would
receive roughly 49% more text per question. A faithfulness advantage for
semantic chunking would then be uninterpretable: better segmentation and greater
evidence volume would be fully confounded, and no downstream statistical test
could separate them.

The threshold was not breached, so the run did not halt - but passing at 1.49
against a 1.50 limit is not a clean pass, and proceeding on that basis would have
been a design decision made by a rounding margin.

### 9.2 Degenerate fragments

The semantic minimum chunk length was **5 characters**. A fragment that small
cannot support an answer, yet it still occupies one of the k retrieval slots,
silently reducing the effective context that condition receives.

### 9.3 Remedies implemented

1. **`merge_undersized()`** folds any chunk below `min_chunk_chars` (default 100)
   into its neighbour, re-slicing from source so the span invariant is preserved
   by construction. Applied to **both** strategies: a cleanup applied only to the
   challenger arm would itself be an asymmetry invalidating H1.

   Verified on the real corpus for fixed chunking: 553 -> 548 chunks, minimum
   length 31 -> 109, zero chunks under 100 chars, **548/548 offsets still exact**.

2. **`semantic_prepare()`** separates the expensive embedding step from the
   percentile threshold, so a calibration sweep reuses one distance profile
   instead of re-embedding per candidate.

3. **`scripts/calibrate_semantic.py`** sweeps candidate percentiles and reports
   the resulting chunk-length distribution against the fixed baseline, so the
   percentile is chosen to equalise mean chunk length BEFORE any results exist.
   The calibration reads chunk-length statistics only and never sees
   faithfulness or retrieval scores, so it cannot bias the outcome it protects.

   Sweep logic verified offline with a deterministic stub embedder on NG106:
   mean chunk length falls monotonically (p95 1226.8 -> p75 508.2) with zero
   offset errors and no sub-100-char chunks at any setting.

This is a nuisance-variable control decided in advance, and the calibration table
belongs in the methodology chapter as evidence that the confound was identified
and removed rather than discovered afterwards in the results.

---

## 10. Semantic percentile calibration (C2b) - decision and rationale

Real embeddings, four documents, 2,884 sentences, ~5.5 min wall-clock. One
distance profile computed per document and reused across all six candidates.

Fixed-size baseline (merge applied, min 100 chars): **548 chunks, mean 767.9**.

| Percentile | Chunks | Mean | Median | Max | Ratio to fixed |
|---|---|---|---|---|---|
| 95 | 326 | 1233.8 | 1261 | 2008 | 1.61 |
| 90 | 412 | 975.9 | 1026 | 1985 | 1.27 |
| **85** | **503** | **799.0** | **687** | **2044** | **1.04** |
| 80 | 596 | 674.1 | 506 | 2044 | 0.88 |
| 75 | 703 | 571.2 | 409 | 2044 | 0.74 |
| 70 | 809 | 496.2 | 355 | 2041 | 0.65 |

**Decision: `semantic_percentile = 85`**, fixed in config before any results
exist. Mean chunk length 799.0 against 767.9 - a ratio of 1.04, against 1.49 at
the original p95 setting.

Note the ratio at p95 here (1.61) differs from the 1.49 measured in C2. The
difference is `merge_undersized()`, which is applied in the calibration and
raises the fixed-size mean from 760.9 to 767.9 while also removing semantic
fragments. The two numbers are consistent; the calibrated figure is the
authoritative one because both arms now receive identical treatment.

### 10.1 Distributions are matched on the mean, not on shape

At p85 the means agree closely but the distributions do not:

| | Fixed | Semantic (p85) |
|---|---|---|
| Mean | 767.9 | 799.0 |
| Median | 852 | 687 |
| Max | 1090 | 2044 |

Semantic chunking is right-skewed: more short chunks and a longer tail. **This
was not further corrected, and the choice is deliberate.** Tightening
`semantic_max_chars` toward the fixed maximum would force more cuts at
non-semantic boundaries, progressively converting semantic chunking into
fixed-size chunking and blunting the very difference H1 exists to measure.
Variable chunk length is a property of the strategy under test, not a defect to
be engineered away.

The mean is the correct matching target because the confound concerns **total
context volume delivered at a fixed k**, which aggregates over many retrievals.

### 10.2 The confound is now testable rather than merely controlled

Corpus-level mean parity does not by itself guarantee equal delivered context,
because retrieval is not random sampling - longer chunks may be retrieved at a
different rate than they occur in the corpus.

`generate.py` therefore records `context_chars` and `n_contexts` on every
generated answer. Mean delivered context per condition can then be reported
directly, and if the conditions differ materially it can be entered as a
covariate rather than assumed away. The confound is converted from an
assumption into a measured quantity.

---

## 11. Rebuild at the calibrated setting (C2c) - both arms locked

| | fixed_1000_150 | semantic_p85_b1_m2000 |
|---|---|---|
| Chunks | 548 | 503 |
| NG28 / NG136 / NG238 / NG106 | 254 / 118 / 105 / 71 | 218 / 107 / 99 / 79 |
| min / median / mean / max | 109 / 852 / 767.9 / 1090 | 102 / 687 / 799.0 / 2044 |
| Chunks under 100 chars | 0 | 0 |
| Offset integrity | **548/548 exact** | **503/503 exact** |
| FAISS vectors vs chunk records | 548 = 548 | 503 = 503 |
| Build wall-clock | 203.2s | 538.4s |

**Mean chunk length ratio: 799.0 / 767.9 = 1.04** (was 1.49 at p95). The
context-volume confound identified in section 9 is controlled, and the setting
was fixed before any experimental results existed.

The realised figures reproduce the calibration sweep exactly (503 chunks, mean
799.0, median 687, max 2044), confirming that the sweep's reuse of a single
distance profile per document is equivalent to a full rebuild.

**Computational cost of the semantic condition: 538.4s vs 203.2s, a factor of
2.65.** Reportable as a secondary outcome - the semantic strategy is not free,
and that trade-off belongs in the discussion alongside any faithfulness benefit.

Both arms now carry zero undersized chunks and a fully exact character-span
round-trip, so relevance labels derived from gold passage spans are valid under
either segmentation. The experimental apparatus is complete.

---

## 12. Refusal and grounding tests (C3) - PASSED, plus a significant find

### 12.1 Results

| Test | Question | Expected | Result |
|---|---|---|---|
| Positive 1 | HbA1c target, diet-managed T2DM | Answer with citations | **PASS** |
| Positive 2 | First-line therapy, HFrEF | Answer, citing NG106 | **PASS** |
| Refusal 1 | Capital of Peru | Refuse | **PASS** (exact wording) |
| Refusal 2 | First-line inhaled therapy for COPD | Refuse | **PASS** |
| Refusal 3 | Target INR, warfarin in AF | Refuse | Crashed before generation (see 12.2) |
| Baseline | Same as Positive 1, no retrieval | Answers unguided | Run |

**Refusal 2 is the load-bearing result.** COPD is a plausible clinical question
from an adjacent NICE guideline that is not in the corpus, so retrieval returned
superficially related cardiometabolic extracts. The model refused anyway rather
than answering from parametric medical knowledge dressed as grounded output.
That is precisely the hallucination mode faithfulness is designed to detect, and
the grounding prompt held against it.

### 12.2 The crash, and the larger defect it exposed

Refusal 3 aborted with `UnicodeEncodeError` while printing retrieved context to a
Windows cp1252 console - a display-layer fault, not a pipeline or model failure.
Fixed by reconfiguring stdout to UTF-8 with replacement fallback, so console
encoding can never determine an experimental result.

Investigating the offending character revealed a **substantive defect in the
corpus**, not merely a printing problem. An audit found 87 non-ASCII characters:

| Char | Codepoint | Count | Appears in |
|---|---|---|---|
| `－` | U+FF0D fullwidth hyphen | 38 | NICE's second-level bullet marker |
| `‑` | U+2011 non-breaking hyphen | 25 | SGLT-2, DPP-4, GLP-1, 10-year, mono-unsaturated |
| `–` | U+2013 en dash | 18 | sodium-glucose, African-Caribbean |

**Why this threatened H2.** BM25 matches literal tokens. A query containing
"SGLT-2" with an ordinary hyphen would not match a corpus containing "SGLT‑2",
so the sparse half of hybrid retrieval would fail on exactly the rare clinical
terms where it is expected to outperform dense retrieval. The hypothesis would
have been tested against a corpus quietly rigged against it.

It also threatened the evaluation dataset: a gold passage copied from source and
retyped with an ordinary hyphen would fail verbatim location during validation.

**Fix.** `normalise_punctuation()` maps these to ASCII during ingestion. Every
mapping is strictly 1:1, so document length and character offsets are unchanged
and the span invariant is preserved by construction. The fullwidth hyphen
additionally now resolves to a list marker, so NICE sub-bullets become separate
blocks instead of running together in prose.

After the fix: remaining non-ASCII is 5 pound signs and one stray cedilla, and
"SGLT-2" resolves to 193 uniform occurrences across the corpus.

This was found only because a refusal test crashed on a Windows console. It
would not have surfaced through unit tests, and would have depressed H2 silently.

---

## 13. Post-normalisation recalibration and C4 fusion check

### 13.1 Calibration re-run after punctuation normalisation

| Percentile | Chunks | Mean | Median | Ratio to fixed |
|---|---|---|---|---|
| 95 | 327 | 1230.2 | 1262 | 1.60 |
| 90 | 415 | 968.9 | 1015 | 1.26 |
| **85** | **509** | **789.6** | **645** | **1.02** |
| 80 | 600 | 669.6 | 492 | 0.87 |
| 75 | 702 | 572.1 | 410 | 0.74 |
| 70 | 806 | 498.1 | 357 | 0.65 |

Fixed baseline after normalisation: 547 chunks, mean 770.8.

**Percentile 85 confirmed, unchanged.** Selected independently on the
pre-normalisation text (ratio 1.04) and again on the normalised text (ratio
1.02), with the ratio moving slightly toward parity. The setting therefore
tracks a stable property of the segmentation rather than fitting noise in one
particular version of the corpus - a robustness result worth stating in the
methodology.

### 13.2 C4 - dense vs hybrid, fixed arm, top_k=5

Hybrid returned a different ordering from dense on **5 of 5 queries**.

| Query | Reordered | Notable |
|---|---|---|
| HbA1c target, diet-managed | yes | rank 1/2 swap |
| amlodipine, CCB step 1 | yes | sparse#1 promoted from dense#3 |
| NT-proBNP urgent referral | yes | two chunks entering top-5 from dense#11 and dense#9 |
| atorvastatin 20 mg QRISK3 | yes | NG238:00077 promoted from dense#7 on sparse#3 |
| eGFR review of metformin | yes | promotions from dense#9, #13 and #18 |

Reciprocal rank fusion is demonstrably combining two distinct rankings rather
than passing the dense ordering through. **H2 is testable.**

### 13.3 What C4 does NOT establish

C4 is a mechanism check, not a result. It shows only that the sparse component
contributes and that fusion changes the ranking. It says nothing about whether
hybrid retrieves MORE RELEVANT chunks - that is what the gold-span evaluation
measures, and it may well find hybrid worse on some question types.

Query 3 illustrates the risk directly. For an NT-proBNP question - NG106
territory - hybrid promoted chunks from NG136 and NG238 into the top 5 on
lexical strength. That may be useful cross-guideline evidence, or it may be
lexical false-positives displacing correct NG106 content and depressing
precision@k. The distinction cannot be settled by inspection, only against
labelled gold passages.

This caution belongs in the write-up. Reporting "hybrid reordered every query"
as though it supported H2 would be an overclaim.

### 13.4 Both outstanding items now closed

**Semantic arm rebuilt on normalised text:** 509 chunks, mean ~790, matching the
calibration sweep. Offset integrity **509/509 exact**; fixed arm **547/547
exact**. FAISS vector counts match chunk record counts for both arms.

**C3 refusal test completed.** The warfarin/atrial-fibrillation query returns the
exact required string, "The provided guideline extracts do not state this.", and
the top-5 retrieved extracts contain no anticoagulation content. This closes the
refusal gate: all three refusal tests pass, including the two designed to be
plausible clinical questions from adjacent NICE guidelines outside the corpus.

### 13.5 Pipeline status: complete and verified

| Component | Verified on real corpus |
|---|---|
| Ingestion, four guidelines | Yes, reproduced across two machines |
| Punctuation normalisation | Yes, non-ASCII reduced to 5 pound signs + 1 cedilla |
| Fixed-size chunking | Yes, 547 chunks, 547/547 offsets exact |
| Semantic chunking (p85) | Yes, 509 chunks, 509/509 offsets exact |
| Chunk-length parity (H1 control) | Yes, ratio 1.02 |
| FAISS index integrity | Yes, vector counts match records, both arms |
| Dense retrieval | Yes |
| Hybrid retrieval (BM25 + RRF) | Yes, reorders on 5/5 queries |
| Generation, grounded | Yes, positive controls cite correctly |
| Refusal behaviour | Yes, 3/3 refusal tests pass |

Every remaining task depends on the evaluation dataset.

---

## 14. Evaluation harness built (Stage 4)

### 14.1 A dependency break found before it cost anything

`ragas==0.4.3` fails at import against current `langchain-community`:

```
ModuleNotFoundError: No module named 'langchain_community.chat_models.vertexai'
```

The module was removed in langchain-community 0.4.x. Versions were bisected;
**0.3.29 is the newest that still works** and is now pinned. Older versions
(0.3.20, 0.3.10, 0.2.19) fail differently, against langchain-core.

Separately, the documented import `from ragas.metrics import Faithfulness` does
NOT work in 0.4.3 - the metric classes are not re-exported at package level.
They import from private modules instead. `_import_metrics()` tries the public
path first and falls back, so the harness keeps working if a later release
re-exports them.

Both issues were found by installing and importing rather than by reading
documentation.

### 14.2 Quota budget - measured, and it constrains the schedule

| Configuration | Tokens/sample | Total (60 x 5) | Days at Groq free tier |
|---|---|---|---|
| Faithfulness + answer relevancy | 3,500 | 1,050,000 | **5.2** |
| Plus LLM context precision/recall | 6,700 | 2,010,000 | **10.1** |

Groq free tier is approximately 200,000 tokens/day on `openai/gpt-oss-120b`.

**Consequence:** LLM-judged context precision and recall are excluded by default.
Those constructs are instead measured deterministically by character-span overlap
against the dataset's gold passages, which is free, reproducible, and applies an
identical relevance rule to both chunking arms - an advantage over LLM judging,
since chunk sizes differ between arms and an LLM would apply a different implicit
standard to each. This is a deviation from the proposal's metric list and must be
stated plainly in the methodology.

### 14.3 Caching is a correctness requirement, not an optimisation

Because Gemini 3.x does not honour `temperature`, re-running a question can
produce a different answer. Without caching, a faithfulness score and the answer
it describes could diverge, and a rate-limit crash mid-run would leave the
experiment internally inconsistent.

Every generated answer is cached by (condition, question, model) with atomic
writes; every RAGAS score is cached per (condition, question, metric). A run that
stops on a rate limit resumes exactly where it left off and never repays for a
score already obtained.

### 14.4 Tests

10 new offline tests (`tests/test_experiment.py`), no API key or network
required, covering: the five conditions, top-k sweep isolation, cache hit/miss,
atomic writes, corrupt-cache regeneration, span-derived retrieval metrics,
baseline returning None rather than 0.0 for undefined metrics, cache key
collision between conditions, and by-question-type aggregation.

**Full suite: 69 tests passing.**

---

## 15. Judge provider change (7 August 2026)

The third forced substitution of an external dependency in this project.

| Judge | Status | Reason |
|---|---|---|
| `llama-3.3-70b-versatile` (Groq) | abandoned | Deprecated 17 Jun 2026, shutdown ~16 Aug - one day before submission |
| `openai/gpt-oss-120b` (Groq) | abandoned | Free tier caps at ~200k tokens/day (5.2 days for this experiment); paid Developer tier upgrades frozen, "temporarily unavailable due to high demand" |
| **`meta-llama/Llama-3.3-70B-Instruct` (DeepInfra)** | **current** | No daily token cap; ~$0.15-0.30 for the full experiment; still a different model family from the generator |

The methodological requirement is unchanged and satisfied: the judge is not from
the Gemini family, so no model grades its own output.

**Code impact: none beyond configuration.** `config.JUDGE_PROVIDER` now selects
between DeepInfra, Groq and OpenAI; DeepInfra and OpenAI share the
OpenAI-compatible client. No ingestion, chunking, indexing, retrieval or dataset
artefact is affected, and nothing already verified needs re-running.

This is the fourth external dependency to shift under the project (Gemini SDK,
generator model, judge model twice). The pattern itself is a reportable finding:
research systems built on third-party model APIs carry a maintenance burden that
does not appear in the published method, and a study whose judge model is
withdrawn mid-experiment is not reproducible in the way the field assumes. The
provider abstraction added here is the mitigation.

---

## 16. Integrity audit (7 August 2026) - one real defect found

A full state audit was run rather than assumed. It checked corpus provenance,
residual furniture, non-ASCII characters, the chunk offset invariant, dataset
validity, config coherence and file inventory.

**Defect found:** the packaged `chunks__*.json` reported **162/548 offsets exact**
instead of 548/548. The file had been built before punctuation normalisation, so
its character offsets no longer addressed the correct passages in the re-ingested
text. A rebuild from the current text gives **547/547 exact**, confirming the
pipeline itself was sound - only the stale packaged artefact was wrong.

**Why it mattered.** The file looked valid. Nothing about it announced staleness.
Had it been extracted over a correct local build, every retrieval metric computed
afterwards would have been wrong while still producing plausible numbers.

**Root-cause fix.** Derived artefacts (`chunks__*.json`, `data/index/*`) are no
longer shipped at all. Only the ingested corpus text travels with the package,
because the dataset's gold passages are character offsets into those exact files
and must stay synchronised with them. Everything derived is rebuilt locally with
`scripts/build_all.py`. This removes the failure mode rather than correcting one
instance of it.

**Audit result after the fix:**

| Check | Result |
|---|---|
| Residual furniture, all four documents | 0 |
| Non-ASCII characters remaining | 6 total (5 pound signs, 1 cedilla) |
| Chunk offset invariant (fresh build) | 547/547 exact |
| Evaluation dataset structural errors | 0 |
| Dataset composition | 26 factual / 18 comparative / 16 multi_step |
| Judge model family differs from generator | yes |
| Groq references in runtime code | none (regression test added) |
| Test suite | 70 passing |

---

## 17. Instrument validity: lexical leakage and paraphrase robustness

Raised by the researcher on review: the drafted questions read as though
reverse-engineered from the source sentences. Rather than resolve this by
impression, it was measured.

### 17.1 Lexical leakage measured

For each question, the fraction of its content words (stopwords removed) that
also appear in its own gold passage:

| | Before rewrite | After rewrite |
|---|---|---|
| Mean | 0.43 | **0.39** |
| Median | 0.44 | 0.40 |
| Questions above 0.6 | 11 | **5** |

**Why this matters.** A question that reuses its gold passage's vocabulary makes
retrieval artificially easy. That inflates every condition AND can compress the
differences between them - producing a ceiling effect that reads as "no
significant difference between chunking strategies" when the true finding is
"the test items could not discriminate".

### 17.2 Which questions were rewritten, and which were not

Inspection separated two causes of high overlap:

- **Unavoidable clinical vocabulary.** Q021 (0.85) shares "albumin",
  "creatinine", "chronic kidney disease" - the terminology of the scenario, for
  which no natural paraphrase exists. Left unchanged; forcing synonyms would
  make the question less realistic, not more.
- **Borrowed sentence structure.** Q040 reproduced the passage's own comparison
  framing; Q016 and Q041 lifted its verbs. These were rewritten.

Six questions were rewritten (Q016, Q024, Q038, Q040, Q041, Q049), with large
individual reductions: Q049 0.75 -> 0.15, Q038 0.70 -> 0.21, Q041 0.62 -> 0.30.
Reference answers and gold passages were unchanged; only phrasing moved.

The five remaining above 0.6 are all cases where the overlap is the clinical
terminology itself.

### 17.3 Paraphrase robustness check

27 probe questions, each paired with two independently worded paraphrases - one
lay/patient register, one terse clinical register - preserving the scenario
while changing the wording. 54 alternative phrasings in total, spanning all
three question types and all four guidelines.

`scripts/paraphrase_robustness.py` runs retrieval on the original and on each
paraphrase and compares gold-passage recall. It uses retrieval only: no
generation, no judge, no API cost.

**Interpretation is prespecified**, so the result cannot be read favourably after
the fact:

- recall roughly unchanged -> retrieval generalises beyond the author's phrasing
- recall drops sharply -> the evaluation set's phrasing was doing hidden work and
  the headline retrieval figures are optimistic

Both outcomes are reportable. The second is a genuine limitation that most RAG
evaluations never test for, and stating it is stronger than leaving the
assumption unexamined.

---

## 18. Dataset finalised and orchestrator built

### 18.1 Final dataset composition - matches the proposal exactly

| | Proposal | Final |
|---|---|---|
| factual | 24 | **24** |
| comparative | 18 | **18** |
| multi_step | 18 | **18** |

**Validation: 60 rows, 60 verified, 0 errors, 0 warnings.**

Evidence spread improved substantially during rebalancing:

| Guideline | Before | After |
|---|---|---|
| NG28 | 12.8% | **21.6%** |
| NG136 | 37.2% | 34.1% |
| NG238 | 25.6% | 22.7% |
| NG106 | 24.4% | 21.6% |

Rebalancing served three purposes at once. Retired: two factual items that
duplicated a comparison already covered by a multi-step item, and the two
highest-leakage comparative items drawn from the over-represented guidelines.
Added: four NG28 items (two multi-step, two factual). Composition, corpus
balance and instrument quality all improved together.

Final lexical leakage: **mean 0.36, with 2 items above 0.6** (originally 0.43
with 11 above 0.6). 28 items require multiple gold passages; 4 span two
guidelines.

### 18.2 Dead code removed

`scripts/draft_questions.py` was written to have candidate questions drafted on
the local machine, but that workflow was not used - the questions were drafted
directly from the ingested corpus text and then verified by the researcher.
Leaving the script in place would imply a method that was not followed, so it
was removed. The actual procedure is what belongs in the methodology.

### 18.3 Orchestrator

`scripts/run_experiment.py` drives generation, the top-k sweep and RAGAS scoring
as separately resumable phases. Verified by dry run:

```
questions      60
conditions     5: fixed_dense_k5, fixed_hybrid_k5, semantic_dense_k5,
                  semantic_hybrid_k5, baseline_noretrieval
generator      gemini-3.6-flash
judge          meta-llama/Llama-3.3-70B-Instruct (deepinfra)
generations    300
judge tokens   ~1,050,000 (~$0.21)
```

Separating generation from scoring means an interruption in one phase cannot
corrupt the other, and the metered phase can be rerun without regenerating
answers - which matters because regeneration under Gemini 3.x can produce a
different answer and silently decouple a score from the text it describes.

---

## 19. Dependency resolution failure and fix (7 August 2026)

A clean install on the target machine failed outright:

```
ERROR: Cannot install -r requirements.txt (line 42) and datasets==3.2.0
because these package versions have conflicting dependencies.
    The user requested datasets==3.2.0
    ragas 0.4.3 depends on datasets>=4.0.0
```

**Cause.** `datasets==3.2.0` was pinned from a version listing rather than from
ragas's declared requirement. Inspecting the installed package confirms
`ragas 0.4.3` requires `datasets>=4.0.0`, making the file unsatisfiable. A
second latent conflict existed: `langchain-core==0.3.28` was pinned while ragas
0.4.3 pulls the langchain 1.x line.

**Fix, established empirically rather than by inference.** A clean virtual
environment and `pip install --dry-run` were used to find a version set that
actually resolves. The experimentally significant versions were held fixed and
confirmed compatible:

| Package | Held at | Why |
|---|---|---|
| numpy | 1.26.4 | faiss-cpu 1.9.0 is built against numpy 1.x |
| torch | 2.5.1 | verified embedding stack |
| faiss-cpu | 1.9.0 | verified index behaviour |
| sentence-transformers | 3.3.1 | verified embedding model |
| pandas | 2.2.3 | verified |
| langchain-community | 0.3.29 | newest version ragas 0.4.3 can import |

`langchain-core`, `langchain-openai` and `datasets` are now left to ragas to
constrain; over-pinning them is what caused the failure.

**One version had to move: `langchain-text-splitters` 0.3.4 -> 1.1.2**, a major
release, because the 0.3.x line requires langchain-core <0.4. Since the splitter
determines chunk boundaries, and chunk boundaries determine every retrieval
metric, this was verified rather than assumed:

```
547 chunks | mean 770.8 | min 109 | offsets 547/547 exact
IDENTICAL to verified build: True
```

Chunking output is byte-identical to the previously verified build, and the full
suite passes (70 tests). The upgrade therefore does not affect any result.

**Process note.** This is the second time a pin taken from documentation rather
than from a resolved environment has failed on the target machine. Pins are now
established by clean-environment resolution and confirmed by re-running the test
suite and reproducing a known-good build.

---

## 20. R2 - build reproduced on the target machine after the dependency fix

Executed on Windows, Python 3.11.9, in a clean venv built from the resolved
`requirements.txt` (section 19), including the forced
`langchain-text-splitters` 0.3.4 -> 1.1.2 upgrade.

| | fixed_1000_150 | semantic_p85_b1_m2000 |
|---|---|---|
| Chunks | **547** | **509** |
| Per document (NG28/NG136/NG238/NG106) | 255 / 116 / 105 / 71 | 221 / 107 / 100 / 81 |
| min / median / mean / max | 109 / 853 / **770.8** / 1090 | 102 / 645 / **789.6** / 2044 |
| Chunks under 100 chars | 0 | 0 |
| Offset integrity | **547/547 exact** | **509/509 exact** |
| FAISS vectors = chunk records = meta | 547 = 547 = 547 | 509 = 509 = 509 |
| Build wall-clock | 149.2s | 455.6s (349.7 chunk + 105.8 index) |

Chunk counts, means and offset integrity reproduce the reference build exactly.
This is the independent confirmation that the text-splitter major-version upgrade
did not move chunk boundaries - important because chunk boundaries determine
every retrieval metric, and the upgrade was forced by dependency resolution
rather than chosen.

**Per-document counts differ from section 11** (fixed was 254/118/105/71). This
is expected and not a discrepancy: section 11 predates the Unicode punctuation
normalisation of section 12.2, which altered block boundaries and therefore how
chunks distribute across documents. The post-normalisation per-document split
was not previously recorded, so the figures above establish it. Corpus-level
totals and means are unaffected.

**Semantic/fixed build-time ratio: 3.05x** (455.6s vs 149.2s), against 2.65x in
section 11. Both are machine- and load-dependent wall-clock measurements; the
consistent finding is that the semantic condition costs roughly 3x the fixed
condition to build. Report as a range, not a point estimate.

---

## 21. R3-R6 results, and a substantive finding on paraphrase sensitivity

### 21.1 R3 - grounding and refusal: 3/3 refusal tests passed

| Test | Result |
|---|---|
| HbA1c target, diet-managed T2DM | PASS, cited, top-1 similarity 0.8322 |
| HFrEF first-line therapy | PASS, cited, top-1 similarity 0.7874 |
| Capital of Peru | PASS, exact refusal wording, top-1 only 0.4056 |
| COPD inhaled therapy | PASS, exact wording, retrieved only cardiometabolic extracts |
| Warfarin/AF INR target | PASS, exact wording, no anticoagulation content retrieved |
| Baseline, no retrieval | Answered correctly from parametric knowledge |

The grounding gate holds. Note the baseline answered this particular question
correctly unaided, so it is a weak discriminator between grounded and ungrounded
output - relevant when interpreting baseline faithfulness later.

### 21.2 R4 - fusion: 5/5 queries reordered. R5 - dataset: 60/60, 0 errors.

### 21.3 R6 - paraphrase robustness: retrieval degrades severely

27 probes, 3 conditions, retrieval only.

| Condition | original | paraphrase_1 | paraphrase_2 | delta |
|---|---|---|---|---|
| fixed / dense | 0.759 | 0.093 | 0.056 | **-0.685** |
| fixed / hybrid | 0.704 | 0.056 | 0.093 | **-0.630** |
| semantic / hybrid | 0.741 | 0.093 | 0.093 | **-0.648** |

**Two competing explanations were tested and one was eliminated.**

*Was it query length?* No. Pooled across conditions, the lay full-sentence
paraphrases and the terse clinical-shorthand paraphrases give **identical mean
recall (0.081 vs 0.081)** and near-identical correct-document rates (0.803 vs
0.778), with the terse form actually ahead in two of three conditions. Terseness
is not the driver.

*Was it a near miss rejected by the span threshold?* No. Among zero-recall
instances, **75-80% still retrieved the correct guideline**, but the median gap
from the nearest retrieved chunk to the gold span was **6,000-9,900 characters** -
roughly 8-13 chunks away. The system reaches the right document and then the
wrong section of it. That is a genuine retrieval failure, not a metric artefact.

### 21.4 What this means, stated carefully

The evaluation questions were authored from the source text and share its
clinical vocabulary. A paraphrase that a patient would plausibly use - "what
blood sugar number should I be aiming for" where the guideline says "HbA1c" -
loses that overlap, and retrieval degrades from ~0.75 recall to ~0.08.

**Internal validity is preserved.** Every condition faces identical questions, so
the H1 and H2 comparisons remain valid: the inflation applies equally to all
arms. What is limited is **external validity** - the absolute retrieval figures
describe performance on vocabulary-matched queries and should not be read as
performance on arbitrary user phrasings.

**No condition was robust.** Hybrid retrieval did not protect against it
(fixed/hybrid 0.056 on paraphrase_1, below fixed/dense's 0.093), nor did semantic
chunking. Whatever advantage either strategy shows on the main experiment does
not extend to reworded queries.

This is a genuine contribution rather than a defect. Sohn et al. (2024) report
that medical retrievers are sensitive to how queries are posed; this provides
direct quantitative evidence of that effect on clinical guideline text, using a
prespecified threshold fixed before any result was seen.

**Caveat for the write-up:** 27 probes is a small sample, the paraphrases were
authored by one person, and no inter-rater check was performed on whether each
paraphrase faithfully preserves its question. Report as a secondary, exploratory
analysis with those limits stated - not as a headline claim.

---

## 22. Shipped defect: broken script entry point

`scripts/check_env.py` failed at import with
`ModuleNotFoundError: No module named 'console'`.

**Cause.** `src/console.py` was introduced to centralise the Windows console
encoding fix, and its import was bulk-applied to ten scripts. Nine of those
already placed `src/` on `sys.path`; `check_env.py` placed only the project root.
The patch was applied uniformly to files that were not uniform.

**Why the test suite missed it.** Unit tests import modules. They never execute a
script's `__main__` entry point, so a broken `sys.path` setup in a CLI script is
structurally invisible to them - and this was the FIRST command in the run sheet,
meaning the pre-flight check itself was broken.

**Fix.** The path insert was corrected, and `tests/test_scripts_importable.py`
now invokes every script in `scripts/` and `src/` as a subprocess with `--help`.
argparse exits 0 after printing usage without executing anything, so the full
import chain is exercised with no API calls, no quota and no side effects.

An audit confirmed only `check_env.py` was affected; the other nine start
cleanly. **Suite now 88 tests.**

**Pattern worth noting in the report.** Three defects in this project were
introduced by changes applied uniformly across files that were not uniform
(the stale SDK pin, the hash-seeded stub embedder, this path insert). Each was
caught by execution rather than review. The counter-measure adopted is that any
change touching multiple files is followed by an automated check that every
entry point still starts.

---

## 23. Latent defect: credentials loaded by import side effect

`python scripts/run_experiment.py --score` failed immediately with
`RuntimeError: DEEPINFRA_API_KEY is not set`, while the key was present in
`.env` throughout and 192 scores had already been produced successfully against
the same provider.

**Cause.** `.env` was read only as a side effect of importing `src/generate.py`.
Running `--all` imports that module during the generation phase, so scoring
inherited the environment and worked. Running `--score` alone never imports it,
so `.env` was never read and the credential appeared absent.

The error therefore pointed at the wrong thing entirely: it named a missing key
that was not missing, and would plausibly have led to the key being regenerated
or the judge provider being changed, neither of which was the fault.

**Fix.** `src/env.py` centralises loading with an idempotent `load_env()` and a
`require()` helper that fails with an actionable message. Every module that reads
a credential now loads explicitly rather than relying on import order.
A regression test asserts that `evaluate_ragas` loads `.env` WITHOUT importing
`generate`.

Also corrected: `CLAUDE.md` still named `GROQ_API_KEY` after the judge provider
changed to DeepInfra. That stale reference did not cause the failure but made the
diagnosis harder, since it suggested the key was never expected.

**Suite now 90 tests.**

**Pattern.** This is the fourth defect arising from behaviour that held only
under one execution order (stale packaged chunks, hash-seeded stub embedder,
bulk-patched import path, and now environment loading). Each worked in the path
that was exercised during development and failed in a path that was not. The
harness now has an entry-point test for every script precisely because
module-level unit tests cannot see this class of fault.

---

## 24. Scoring could not be resumed independently - environment loading defect

The scoring phase failed with `DEEPINFRA_API_KEY is not set` while the key was
correctly present in `.env`.

**Cause.** `load_dotenv()` was called only in `src/generate.py`. Running
`run_experiment.py --all` imports the generation module as a side effect, so the
environment was loaded incidentally. Running `--score` alone never imports it, so
the judge key was never read. Environment availability depended on import order.

**Why this mattered more than it looks.** The whole point of separating
generation from scoring was that a long run could be interrupted and resumed. The
scoring phase had never actually been run standalone - only ever after
generation in the same process - so the defect was invisible until the run was
interrupted, which is exactly when resumability is needed. It also presents as a
missing credential, sending the user to check `.env`, which looks correct.

**Fix.** `.env` is now loaded in `config.py`, which every entry point imports, so
availability is unconditional. `tests/test_env_loading.py` asserts that importing
config alone makes the judge key visible and that `generate` is not in
`sys.modules` when it does so. **Suite now 93 tests.**

**Related failure, same session: the `.env` file was wiped.** Both keys were
found blank. The setup instructions contained `copy .env.example .env` as a step
repeated after every archive extraction, which silently overwrites a populated
`.env` with the blank template. Changed to a guarded form that only creates the
file if absent, followed by an explicit `check_env.py` verification step.

**Pattern.** Both defects here are the same shape as sections 19 and 22: a code
path that was never exercised in isolation, and a destructive instruction that
was safe the first time and harmful on repetition. Neither is visible to unit
tests or to review; both required real interrupted execution to surface.

---

## 25. Defect: a failed metric was cached as a real score (10 Aug 2026)

**Symptom.** Scoring appeared to stall at 192 of 600 cached scores.

**Root cause, verified by execution rather than reading.** `ragas.evaluate()`
defaults to `raise_exceptions=False`. A judge failure therefore does not raise;
it returns `np.nan`. Reproduced with a stub judge that always raises `429`:

```
exception reached score_condition's except block? NO - evaluate() returned normally
returned value      nan
`val is not None`   True        <-- the caching gate
WOULD WRITE TO CACHE: {"score": NaN}
re-read as           nan        -> permanently cached, never retried
```

Two consequences, both silent:

1. The `except Exception` block in `score_condition` was **unreachable** for
   judge faults. No error was ever printed.
2. `nan is not None` evaluates `True`, so the failure was written to the cache
   as though it had succeeded, was never retried, and was averaged into the
   condition mean.

**Why ragas's own retries did not save it.** In `ragas/metrics/_faithfulness.py`:

```python
statements = await self._create_statements(row, callbacks)
if statements == []:
    return np.nan          # RETURNS - does not raise
```

and the executor retries only on exceptions. Despite `max_retries=10`, these
samples received **exactly one attempt**. A metric that fails by *returning* is
invisible to the framework's own error handling.

**Fix.** NaN is retried once explicitly; if it persists it is written to
`outputs/ragas_failures.jsonl` and **left uncached**. Only missing metrics are
re-sent to the judge, so a partial failure no longer re-bills the metric that
succeeded. Verified three ways with a stubbed judge: NaN wrote 0 cache files;
recovery on retry wrote 2; a re-score after deleting one metric sent only that
metric to the judge.

---

## 26. The stall was a measurement artefact, not a hang (11 Aug 2026)

The cache advanced from 192 to 256 while the run was believed frozen.
`scripts/probe_judge.py` measured the true rate:

| Layer | Result |
|---|---|
| Raw DeepInfra POST | OK in 3.49s |
| One full ragas sample (2 metrics) | 55.9s, both metrics real numbers |

At ~58s per sample the old code's every-fifth-sample print emitted **one line
every 4.8 minutes**, with `show_progress=False` and `log_tenacity=False`
suppressing everything else. Nothing was broken; the instrument was mute.

ragas's unstated defaults compound this: `timeout=180s, max_retries=10,
max_wait=60s`, so a genuinely failing call can occupy ~40 minutes in silence.
Replaced with an explicit `RunConfig(timeout=120, max_retries=4, max_wait=20)`
and a per-sample progress line carrying a live ETA.

**Lesson for the methodology chapter.** An absence of output is not evidence of
an absence of progress. Any long-running measurement needs a heartbeat whose
period is shorter than a human's patience.

---

## 27. Defect: a duplicated module enabled silent import shadowing (11 Aug 2026)

`pytest` reported a failure with the id `test_script_imports_cleanly
[evaluate_ragas.py0]`. The `0` suffix is what pytest appends to *duplicate*
parametrise ids: `evaluate_ragas.py` existed in **both** `src/` and `scripts/`,
because a patch file had been copied to the wrong folder.

The visible symptom was trivial - `ModuleNotFoundError: No module named 'env'`,
because `src/evaluate_ragas.py` resolves `env` only when `src/` is `sys.path[0]`.
The hidden risk was not. Python resolves imports by scanning `sys.path` in
order, and every script in `scripts/` has its own directory prepended as
`sys.path[0]` before its body runs. The correct copy won only because each
script then inserts `src/` ahead of it. A stale duplicate one ordering change
away from shadowing the real module, silently.

**Fix.** Stray deleted, and `tests/test_no_duplicate_modules.py` added to make
the condition impossible to reintroduce. Verified both ways: passes on a clean
tree, fails with the exact observed error when the stray is recreated.

---

## 28. Defect: figure generation broken by a matplotlib API removal (11 Aug 2026)

`scripts/analyse.py` produced all statistics correctly and then died:

```
[figures] skipped: TypeError: Axes.boxplot() got an unexpected keyword argument 'labels'
```

Confirmed against the installed version:

```
matplotlib 3.11.1
has 'labels'      : False
has 'tick_labels' : True
```

`labels` was renamed `tick_labels` in matplotlib 3.9 and **removed** in 3.11.
Substituting `tick_labels` would break on 3.8, which `requirements.txt` still
permits, so the fix uses `set_xticks` + `set_xticklabels`, valid on every
permitted version. Verified by running the real `make_figures` on 3.11.1: six
PNGs produced with correct axis labels.

---

## 29. Scoring integrity - final state (11 Aug 2026)

```
python scripts/diagnose_scoring.py
```

| condition | answers | scored | missing | NaN | bad |
|---|---|---|---|---|---|
| fixed_dense_k5 | 60 | 120 | 0 | 0 | 0 |
| fixed_hybrid_k5 | 60 | 120 | 0 | 0 | 0 |
| semantic_dense_k5 | 60 | 120 | 0 | 0 | 0 |
| semantic_hybrid_k5 | 60 | 120 | 0 | 0 | 0 |
| baseline_noretrieval | 60 | 120 | 0 | 0 | 0 |
| **TOTAL** | | **600** | **0** | **0** | **0** |

No orphaned cache entries, so no score was paid for under a superseded judge
model string. Independently corroborated: `run_experiment.py` filters scores
with `is not None`, which admits NaN, and a single NaN in 60 makes the printed
mean NaN. All ten condition means printed as finite numbers, which is possible
only if the cache contains no NaN at all.

**Test suite: 99 passing** (`python -m pytest tests\ -q`, 58.57s, 11 Aug 2026),
on the restored v2 tree. This is 97 after removing the duplicated module of
section 27, plus 2 from the new `tests/test_no_duplicate_modules.py` guard.

---

## 30. Reproducibility check: deterministic half rebuilt from scratch (11 Aug 2026)

The pipeline splits into a deterministic half and a non-deterministic half, and
only the first can be re-run without changing the experiment. Generation is not
bit-reproducible (Gemini 3.x deprecates `temperature`, section 6), so the 300
cached answers were preserved while everything upstream of them was rebuilt on a
clean tree from `rag-nice-v2-2026-08-11.zip`.

`python scripts/build_all.py --docs NG28 NG136 NG238 NG106`

| Measure | Rebuild | Recorded (S11/S13) | |
|---|---|---|---|
| fixed chunks | 547 | 547 | match |
| fixed mean chars | 771 | 770.8 | match |
| fixed min chars | 109 | >= 100 | match |
| semantic chunks | 509 | 509 | match |
| semantic mean chars | 790 | 789.6 | match |
| semantic min chars | 102 | >= 100 | match |
| FAISS vectors, fixed | 547 = 547 | equal | match |
| FAISS vectors, semantic | 509 = 509 | equal | match |
| chunk-length parity ratio | 1.025 | 1.02 | match |

Build cost, a reportable secondary outcome: fixed 143.1s, semantic 393.1s. The
semantic arm is **2.7x** more expensive to build because it embeds every
sentence to locate breakpoints, against a single pass for fixed-size splitting.
That cost is incurred once at index time, not per query.

Corpus SHA-256 prefixes unchanged: NG28 `1a3be64f`, NG136 `07f00ff6`,
NG238 `ca660581`, NG106 `6e344e58`.

**Gap found in the procedure, not the artefact.** `build_all.py` reports chunk
counts and length statistics but never verifies the offset invariant, so the
documented pass condition "547/547 offsets exact" could not actually be produced
by the command the run sheet gave. Counts and means are exactly the statistics
that stayed correct during the stale-chunk-file defect of section 19.

Closed by `scripts/verify_offsets.py`, which checks `source[start:end] ==
chunk_text` for every chunk in every built file against the interim text.
Verified both ways: passes on correct offsets, and fails with a diff when 30 of
40 chunk offsets are shifted by 3 characters - a corruption that leaves every
count, mean, minimum and maximum identical.

**Ingestion was skipped** in this rebuild (`already ingested`), so the PDF-to-text
stage was reused rather than reproduced. Re-run with `--overwrite` to close that
last link, then re-run `verify_offsets.py`, because re-ingestion is the one
operation that can move the character offsets the gold spans depend on.


## 31. Analysis plan for the LLM-judged context metrics — pre-specified 12 Aug 2026

**Status when written.** Scoring of `llm_context_precision` and
`llm_context_recall` completed 03:44 on 12 Aug 2026 for the four core
conditions (60/60 per condition per metric, 0 NaN, 0 corrupt, verified by
`scripts/diagnose_scoring.py --include-llm-context-metrics`). **No aggregate
over those values had been computed or inspected when this section was
written.** The only context values seen beforehand were four single-sample
pilot readings from `--limit 1`, which carry no information about the aggregate.

**Decision.** The two LLM-judged context metrics are analysed in two SEPARATE
Holm-corrected families rather than folded into H2:

    "Context quality  hybrid vs dense (LLM-judged, exploratory)"     4 comparisons
    "Context quality  semantic vs fixed (LLM-judged, exploratory)"   4 comparisons

**Rationale.** H2 was pre-specified in the approved proposal as retrieval
quality measured by precision@k, recall@k and MRR. Adding four comparisons to
the H2 family would enlarge it from 6 to 10 and tighten the Holm adjustment
applied to comparisons whose results were already known. Adjusting a correction
after observing results is not defensible. Separate families leave H1 and H2
corrections exactly as originally computed while still subjecting the new
metrics to full inferential treatment. They are labelled *exploratory* because
they were not named in the original hypothesis statement.

**Alternatives rejected.** (a) Descriptive reporting only — discards
inferential information for no gain in rigour. (b) Folding into H2 —
retrospective enlargement of a family after its results were seen.

**Coverage.**
- Four core conditions: complete, 60/60 on all four RAGAS metrics.
- `semantic_hybrid_k3` and `k10`: context metrics added 12 Aug 2026, 60/60 each.
  Faithfulness and answer relevancy means were UNCHANGED by this addition
  (k3 0.873/0.651; k10 0.897/0.790), confirming the additive scoring path does
  not perturb existing cached scores.
- `baseline_noretrieval`: context metrics UNDEFINED by construction — the
  condition retrieves nothing, so precision and recall over an empty context
  set have no value. Excluded in `src/evaluate_ragas.py`. Six files returning
  0.0, written before that exclusion was installed, were deleted 12 Aug 2026
  (verified: exactly 6, 14 bytes each, all `{"score": 0.0}`).

Final cache state: 1560 files, 0 NaN, 0 corrupt.

## 32. CORRECTION — the precision@k ceiling was overstated in earlier notes

An earlier note in `RESTORE_AND_VERIFY.md` estimated attainable P@5 at "about
0.2" by dividing gold passages per question by k, and concluded that observed
values of 0.183–0.203 were "at the ceiling" and therefore unable to
discriminate between retrieval methods. **That estimate was wrong**, and the
conclusion drawn from it was wrong.

Gold *passages* are not gold *chunks*. A two-passage question can overlap three
chunks; measured distributions are 1.37 relevant chunks per question on the
fixed arm (max 3) and 1.32 on the semantic arm (max 3). Measured by
`scripts/precision_ceiling.py`, which walks the actual span overlap:

    fixed arm      ceiling at k=5  0.273
      fixed_dense_k5    observed 0.203   attainment 74.4%
      fixed_hybrid_k5   observed 0.190   attainment 69.5%
    semantic arm   ceiling at k=5  0.263
      semantic_dense_k5   observed 0.187  attainment 70.9%
      semantic_hybrid_k5  observed 0.183  attainment 69.6%

Attainment is ~70%, not saturation. There was headroom the retrievers did not
use, so P@k was NOT prevented from discriminating between methods; it simply
found no difference. The error arose from reasoning about the ceiling instead of
measuring it — the same failure mode as every other defect in this project, and
the reason `CLAUDE.md` requires verification by execution.

Two consequences for reporting:
1. The arms have DIFFERENT ceilings (0.273 vs 0.263), so raw P@k is not
   comparable across chunking strategies. Report attainment, or report P@k
   with its ceiling stated.
2. The justification for adding LLM-judged context metrics is that they provide
   an INDEPENDENT instrument, not that they rescue a saturated measure.

## 33. Two false alarms in `diagnose_scoring.py` — fixed 12 Aug 2026

With `--include-llm-context-metrics` the diagnostic reported
`baseline_noretrieval  120 missing` plus `240 cache files do NOT match any
expected key`, and printed a verdict pointing at judge failure. Both were
defects in the diagnostic:

1. The expectation loop applied all four metric names to every condition,
   including the baseline whose context metrics are deliberately excluded.
   60 questions x 2 metrics = 120 phantom "missing" scores, which triggered the
   spurious judge-failure verdict.
2. The expected-key set was built from `core_conditions(top_k=5)`, so sweep
   conditions were out of scope. 2 conditions x 60 x 2 = 240 "orphaned" files,
   which were in fact completed sweep scores.

Reconciliation at the time: 1080 scored + 240 sweep = 1320 files, 0 NaN, 0 bad.
Fix: mirror the baseline exclusion in the expectation loop. Recorded because a
verification tool that cries wolf trains its operator to ignore it.

## 34. `verify_install.py` marker gap — fixed 12 Aug 2026

`verify_install.py` checked seven markers, none testing for the three fixes
applied on 11 Aug (ragas column resolution, baseline exclusion, `**cached`
merge on partial runs). Run against the superseded 15,737-byte
`evaluate_ragas.py`, it printed ALL CHECKS PASSED. The check intended to prove
the patch was installed could not detect its absence — worse than no check,
because a green light removes the suspicion that would prompt a manual look.
Three markers added; all nine required markers verified present in the real
files and the forbidden marker verified absent.

## 35. Top-k sweep, both instruments — measured 12 Aug 2026

                deterministic          LLM-judged
    k     P@k     R@k     MRR     ctx_prec   ctx_recall   faith   relev
    3    0.267   0.667   0.611     0.832       0.797      0.873   0.651
    5    0.183   0.733   0.627     0.787       0.863      0.845   0.676
   10    0.112   0.867   0.640     0.751       0.921      0.897   0.790

Condition: `semantic_hybrid` at each depth; all other variables held constant.

**Precision–recall trade-off, monotonic on all four retrieval measures.** Both
precision measures fall with depth and both recall measures rise.

**The instruments disagree in magnitude, and that is the finding.** From k=3 to
k=10, deterministic P@k falls 58% while LLM context precision falls 9.7%.
P@k x k gives 0.80, 0.92, 1.12 relevant chunks retrieved — RISING with depth.
The apparent collapse in P@k is therefore dominated by its denominator, not by
degrading retrieval. LLM-judged context precision, which is not bounded by gold
chunk count, shows quality degrading only mildly. This quantifies how much of
the deterministic decline is measurement artefact.

**Evaluation cost scales linearly with k.** Measured judge time per sample:
23s at k=3, 80s at k=10 (3.5x) against a 3.3x increase in retrieved chunks.
Context precision issues one judge call per retrieved chunk.

**Retrieval quality did not predict faithfulness.** Among the k=5 cells,
`fixed_dense_k5` has the LOWEST context precision (0.771) and the HIGHEST
faithfulness (0.918); `semantic_dense_k5` has the highest context precision
(0.807) and faithfulness 0.887; `fixed_hybrid_k5` sits at 0.798 / 0.835. The
ranking inverts. `semantic_hybrid_k3` attains the highest context precision of
any condition (0.832) with mid-table faithfulness (0.873). At this scale the
link between retrieved-context quality and answer faithfulness is weak, which
bears directly on why H1 and H2 are null.

**Questions failing at every depth.** Q001, Q010, Q024, Q047 and Q060 score at
or near 0.00 on context precision at both k=3 and k=10 — a subset where
retrieval fails regardless of depth, consistent with the paraphrase-robustness
finding. Candidates for qualitative error analysis.
