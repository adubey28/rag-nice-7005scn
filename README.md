# RAG over NICE Clinical Guidelines

**A Retrieval-Augmented Generation Question-Answering System over NICE Clinical
Guidelines: Evaluating the Effect of Chunking and Retrieval Strategies on
Faithfulness and Retrieval Quality**

7005SCN Individual Research Project | Anuj Dubey (16180226)
Supervisor: Seyran Naghdi | Module leader: Dr Rochelle Sassman
Ethics: CU Ethics Online P194982 (approved, low risk)

## Research question

To what extent do different chunking and retrieval strategies affect the
faithfulness and retrieval quality of a RAG question-answering system built over
NICE clinical guidelines, compared with a non-retrieval baseline?

- **H1** Semantic chunking produces higher faithfulness scores than fixed-size chunking.
- **H2** Hybrid retrieval achieves higher retrieval quality than dense retrieval alone.

**Both hypotheses were not supported.** See "Results" below.

---

## Reviewing this repository in five minutes

Every number reported here can be re-derived offline, with no API key and at no
cost, from the data in this repository:

```bash
py -3.11 -m venv .venv && .\.venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt

python scripts/verify_install.py                          # no stale code on disk
python -m pytest tests/ -q                                # 103 tests
python scripts/diagnose_scoring.py --include-llm-context-metrics
python scripts/analyse.py                                 # every hypothesis test
python scripts/effective_n.py                             # how many pairs each test used
```

Expected: `ALL CHECKS PASSED`, 103 passed, `1080 scored / 0 missing / 0 NaN / 0 bad`,
and the full analysis table. This was verified on a clean clone with a fresh
virtual environment on 12 Aug 2026 and reproduced identically, including bootstrap
confidence intervals (EVIDENCE.md S36).

Scripts that need the source corpus — `build_all.py`, `verify_offsets.py`,
`precision_ceiling.py` — require the four NICE PDFs, which are **not** included
for copyright reasons. See "Get the corpus" below.

---

## Results

Raw means, 60 questions per condition. P@k / R@k / MRR are deterministic
(character-span overlap, no LLM). ctx prec / ctx rec / faith / relev are RAGAS
metrics judged by Llama-3.3-70B.

| Condition | P@k | R@k | MRR | ctx prec | ctx rec | faith | relev |
|---|---|---|---|---|---|---|---|
| baseline_noretrieval | n/a | n/a | n/a | n/a | n/a | 0.008 | 0.822 |
| fixed_dense_k5 | 0.203 | 0.775 | 0.597 | 0.771 | 0.868 | **0.918** | 0.712 |
| fixed_hybrid_k5 | 0.190 | 0.733 | 0.598 | 0.798 | 0.835 | 0.835 | 0.683 |
| semantic_dense_k5 | 0.187 | 0.750 | 0.608 | 0.807 | 0.890 | 0.887 | 0.700 |
| semantic_hybrid_k5 | 0.183 | 0.733 | 0.627 | 0.787 | 0.863 | 0.845 | 0.676 |
| semantic_hybrid_k3 | 0.267 | 0.667 | 0.611 | 0.832 | 0.797 | 0.873 | 0.651 |
| semantic_hybrid_k10 | 0.112 | 0.867 | 0.640 | 0.751 | 0.921 | 0.897 | 0.790 |

**H1 not supported.** The effect reverses sign with retrieval method
(rank-biserial -0.176 dense, +0.100 hybrid), both p(Holm) = 1.000.

**H2 not supported.** All six comparisons p(Holm) = 1.000. Hybrid is negative on
both coverage metrics and positive on both ranking metrics — RRF lifts ranking
slightly while displacing dense hits and losing coverage.

**Only significant result:** all four retrieval conditions beat the baseline on
faithfulness, p(Holm) < 0.001. This is partly definitional — faithfulness measures
support *by retrieved context*, and the baseline has none. The finding worth
reporting is the pairing: the baseline scores the **highest** answer relevancy of
any condition (0.822) with the **lowest** faithfulness (0.008). Fluent, on-topic,
ungrounded.

**Effective sample size matters here.** Wilcoxon discards tied pairs. H2 used
10-12 of 60 pairs, H1 used 17-20. On roughly 80% of questions hybrid and dense
retrieved identically — a measurement, not an inference. Run
`scripts/effective_n.py`. Do not read these as tests powered at n=60.

Full statistics, effect sizes and confidence intervals: `outputs/analysis.json`
and `scripts/analyse.py`. Figures: `outputs/figures/` (8 PNGs).

---

## Experimental design

Two chunking strategies (fixed-size with overlap; semantic) x two retrieval
methods (dense; hybrid BM25 + reciprocal rank fusion) at fixed retrieval depth =
four core configurations, plus a non-retrieval baseline, plus a top-k sensitivity
sweep at k=3 and k=10 on the best configuration. Embedding model and both LLMs
held constant so that differences are attributable to the design choices under
test. The judge is a different model family from the generator, so no model
grades its own output.

**Corpus:** NG28 (type 2 diabetes), NG136 (hypertension), NG238 (cardiovascular
risk and lipid modification), NG106 (chronic heart failure).

## Current state

| Component | Status |
|---|---|
| Ingestion (all four guidelines) | Verified, reproduced on two machines and one clean clone |
| Punctuation normalisation | Verified, 6 non-ASCII characters remain corpus-wide |
| Fixed-size chunking | Verified, 547 chunks, 547/547 offsets exact |
| Semantic chunking (p85) | Verified, 509 chunks, 509/509 offsets exact |
| Chunk-length parity (H1 confound control) | Mean ratio 1.02. Distribution NOT matched — see EVIDENCE.md S38 |
| Dense retrieval | Verified on real corpus |
| Hybrid retrieval (BM25 + RRF) | Verified, reorders on 5/5 probe queries |
| Generation (Gemini 3.6 Flash) | Verified, positive controls cite correctly |
| Refusal behaviour | Verified, 3/3 refusal tests pass |
| Retrieval metrics (P@k, R@k, MRR) | Implemented and tested |
| Evaluation dataset | **60 questions, 60 verified, 88 gold passages, all spans exact** |
| RAGAS harness (DeepInfra judge) | Built and run |
| Experiment (7 conditions x 60 questions) | Complete, **420 answers** generated and cached |
| Top-k sensitivity sweep (k=3, 10) | **Complete on all four RAGAS metrics** |
| RAGAS scoring | **Complete. 1,560 cached scores, 0 missing, 0 NaN, 0 corrupt** |
| Significance testing (Wilcoxon, Holm, rank-biserial) | Complete, 5 families, 20 comparisons |
| Clean-clone reproduction | Verified 12 Aug 2026, identical to 3 d.p. |
| Report | Literature Review drafted (~2,150 words); other chapters in progress |

Test suite: `python -m pytest tests/ -q`. 103 passing as of 12 Aug 2026.

See `EVIDENCE.md` (38 sections) for the measured result behind every "verified"
above, including corrections to claims this project later retracted.

---

## 1. Environment

**Python 3.11.x.** Not 3.12/3.13: `faiss-cpu` and `torch` wheels are best-tested
there, and RAGAS's dependency tree is fussier on newer interpreters.

```bash
# macOS / Linux
python3.11 -m venv .venv && source .venv/bin/activate

# Windows PowerShell
py -3.11 -m venv .venv; .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `faiss-cpu` fails to build, check `python --version` before anything else.

**API keys** are needed only to generate or score. Re-deriving the analysis from
cached results needs none. To run the live pipeline, copy `.env.example` to
`.env` and add `GOOGLE_API_KEY` and `DEEPINFRA_API_KEY`. `.env` is gitignored.

## 2. Get the corpus

The NICE PDFs are not distributed here. Download each from nice.org.uk and save
to `data/raw/` as `ng28.pdf`, `ng136.pdf`, `ng238.pdf`, `ng106.pdf`.

Provenance recorded at build (guidelines are revised; without these the study is
not reproducible):

| Doc | Pages | Chars | Published | Last updated | SHA-256 |
|---|---|---|---|---|---|
| NG28 | 131 | 186,906 | 2 Dec 2015 | 18 Feb 2026 | 1a3be64ff05a3a01... |
| NG136 | 52 | 87,144 | 28 Aug 2019 | 26 Feb 2026 | 07f00ff626bb0aa9... |
| NG238 | 52 | 74,603 | 14 Dec 2023 | (none) | ca66058149bff1c4... |
| NG106 | 39 | 54,049 | 12 Sep 2018 | 3 Sep 2025 | 6e344e58fe587d67... |

## 3. Run it

```bash
python scripts/check_env.py --list-models
python -m pytest tests/ -q

# Build: ingest -> chunk (both strategies) -> embed -> index. No API calls.
python scripts/build_all.py --docs NG28 NG136 NG238 NG106
python scripts/verify_offsets.py

# Retrieval only - no API call, no quota consumed
python src/retrieve.py "What HbA1c target should be agreed with adults with type 2 diabetes managed by diet alone?"

# Full pipeline (consumes quota)
python src/ask.py --show-context "What HbA1c target should be agreed with adults with type 2 diabetes managed by diet alone?"
python src/ask.py --baseline "What HbA1c target should be agreed with adults with type 2 diabetes managed by diet alone?"
```

### Do NOT run `run_experiment.py --all`

It regenerates answers. Gemini 3.x deprecated `temperature`, so regeneration
produces different answers, different faithfulness scores and different results —
replacing the experiment rather than reproducing it, and invalidating every number
recorded in `EVIDENCE.md`. `--score` is safe and idempotent; `--all` is not.

## 4. Verification gates

| Gate | Condition | Result |
|---|---|---|
| Ingestion | Zero residual furniture; reproduces across machines | Passed |
| Chunk offsets | `source[start:end] == text` for every chunk, both strategies | 547/547 and 509/509 |
| Chunk-length parity | Semantic/fixed mean ratio near 1.0 | 1.02 (mean only — see S38) |
| Index integrity | FAISS vector count == chunk record count | 547=547, 509=509 |
| Gold spans | Every gold passage resolves verbatim by character offset | 88/88 |
| **Refusal** | Out-of-corpus clinical question returns the refusal string | Passed, 3/3 |
| **Fusion** | Hybrid reorders results relative to dense on exact-term queries | Passed, 5/5 |
| Scoring integrity | Every (condition, question, metric) scored, no NaN, no orphans | 1,080 scored, 0 NaN |
| Clean-clone reproduction | Fresh clone + fresh venv reproduces all reported values | Passed, identical to 3 d.p. |

```bash
python scripts/verify_install.py     # no stale code on disk
python scripts/diagnose_scoring.py --include-llm-context-metrics
```

The diagnostic will report ~480 cache files as unmatched. Those are the two sweep
conditions, out of scope for a k=5 diagnostic. Expected, not an error — EVIDENCE.md S33.

---

## 5. Project structure

```
rag-nice/
├── config.py                    # single source of truth for every experimental variable
├── EVIDENCE.md                  # 38 sections: measured results, decisions, corrections
├── LOGBOOK.md                   # development journal
├── src/
│   ├── ingest.py                # source -> cleaned text (+ SHA-256, furniture removal)
│   ├── chunking.py              # fixed-size + semantic (p85) + merge_undersized
│   ├── embed_index.py           # sentence-transformers -> FAISS IndexFlatIP
│   ├── retrieve.py              # dense + hybrid (BM25 + reciprocal rank fusion)
│   ├── generate.py              # Gemini call, config ladder, non-retrieval baseline
│   ├── evaluate_ragas.py        # RAGAS harness, judge retry policy, score cache
│   ├── experiment.py            # condition definitions
│   ├── spans.py                 # character-span overlap -> relevance labels
│   ├── metrics_retrieval.py     # precision@k, recall@k, MRR
│   ├── dataset.py               # evaluation dataset schema + validator
│   └── ask.py                   # end-to-end CLI, saves a JSON transcript
├── scripts/
│   ├── check_env.py             # packages, keys, corpus, embedding sanity
│   ├── build_all.py             # ingest + chunk + index, all strategies
│   ├── calibrate_semantic.py    # percentile sweep against the fixed baseline
│   ├── validate_dataset.py      # dataset schema + verbatim span validator
│   ├── paraphrase_robustness.py # does retrieval survive rewording?
│   ├── run_experiment.py        # orchestrator: generate, sweep, score
│   ├── analyse.py               # Wilcoxon, Holm correction, effect sizes, figures
│   ├── effective_n.py           # tied pairs discarded by Wilcoxon
│   ├── precision_ceiling.py     # attainable P@k given gold-chunk density
│   ├── verify_offsets.py        # chunk span integrity (offline)
│   ├── verify_install.py        # no stale or duplicated code on disk (offline)
│   ├── diagnose_scoring.py      # score-cache state per condition (offline)
│   ├── inspect_nan_scores.py    # NaN triage: refusal vs judge failure (offline)
│   ├── probe_judge.py           # two-layer judge connectivity check
│   └── make_submission.py       # build + verify the submission package
├── tests/                       # offline, no API key required
├── data/{raw,interim,index,eval}/
└── outputs/                     # runs, score cache, figures, analysis
```

