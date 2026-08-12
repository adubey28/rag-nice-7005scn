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

## Experimental design

Two chunking strategies (fixed-size with overlap; semantic) x two retrieval
methods (dense; hybrid) at fixed retrieval depth = four core configurations,
plus a non-retrieval baseline. One top-k sensitivity check on the best
configuration only. Embedding model and LLMs held constant so that differences
are attributable to the design choices under test.

**Corpus:** NG28 (type 2 diabetes), NG136 (hypertension), NG238 (cardiovascular
risk and lipid modification), NG106 (chronic heart failure).

## Current state

| Component | Status |
|---|---|
| Ingestion (all four guidelines) | Verified, reproduced on two machines |
| Punctuation normalisation | Verified, 6 non-ASCII characters remain corpus-wide |
| Fixed-size chunking | Verified, 547 chunks, 547/547 offsets exact |
| Semantic chunking (p85) | Verified, 509 chunks, 509/509 offsets exact |
| Chunk-length parity (H1 confound control) | Verified, mean ratio 1.02 |
| Dense retrieval | Verified on real corpus |
| Hybrid retrieval (BM25 + RRF) | Verified, reorders on 5/5 probe queries |
| Generation (Gemini 3.6 Flash) | Verified, positive controls cite correctly |
| Refusal behaviour | Verified, 3/3 refusal tests pass |
| Retrieval metrics (P@k, R@k, MRR) | Implemented and tested |
| Evaluation dataset | **60 questions, 60 verified, 0 errors** |
| RAGAS harness (DeepInfra judge) | Built, budget verified (~$0.21) |
| Experiment orchestrator | Built, dry run verified |
| Experiment (5 conditions x 60 questions) | Complete, 300 answers generated and cached |
| Top-k sensitivity sweep (k=3, 10) | Retrieval metrics complete; RAGAS scoring not run |
| RAGAS scoring | Complete, 600/600 scored, 0 missing, 0 NaN |
| Significance testing (Wilcoxon, Holm, rank-biserial) | Complete |
| Report | Not yet started |

Test suite: run `python -m pytest tests/ -q`; all tests must pass, deterministic across hash seeds. The current count is recorded in EVIDENCE.md.

See `EVIDENCE.md` for the measured results behind every "verified" above, and
`PROMPTS.md` for the Claude Code run sheet.

---

## 1. Environment

**Python 3.11.x.** Use 3.11 rather than 3.12/3.13: `faiss-cpu` and `torch` wheels are
best-tested there, and RAGAS's dependency tree (Stage 3) is fussier on newer interpreters.

```bash
# macOS / Linux
python3.11 -m venv .venv && source .venv/bin/activate

# Windows PowerShell
py -3.11 -m venv .venv; .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `faiss-cpu` fails to build, you are almost certainly on the wrong Python version —
check `python --version` before trying anything else.

**API key.** Create a free key at <https://aistudio.google.com/apikey>, then:

```bash
cp .env.example .env      # Windows: copy .env.example .env
# paste the key after GOOGLE_API_KEY=
```

`.env` is gitignored. Never commit it, and never paste a key into a report appendix.

---

## 2. Get the corpus

Go to <https://www.nice.org.uk/guidance/ng28>, use **Download guidance (PDF)**, and save
it as `data/raw/ng28.pdf` (exactly that filename).

Record in your logbook: the download date, the guideline's **"Last updated"** date shown
on the NICE page, and the SHA-256 that `ingest.py` prints. NICE guidelines are revised;
without those three facts the study is not reproducible, and reproducibility is explicitly
assessed.

---

## 3. Run it

`PROMPTS.md` is the authoritative run sheet, executed via Claude Code. The
commands below are the same steps run directly. All defaults now point at the
full four-guideline corpus, so `--docs` is optional.

```bash
# 0. Pre-flight
python scripts/check_env.py --list-models
python -m pytest tests/ -q                    # all must pass

# 1. Build everything: ingest -> chunk (both strategies) -> embed -> index
python scripts/build_all.py --docs NG28 NG136 NG238 NG106

# 2. Retrieval only - no API call, no quota consumed
python src/retrieve.py "What HbA1c target should be agreed with adults with type 2 diabetes managed by diet alone?"

# 3. Full pipeline
python src/ask.py --show-context "What HbA1c target should be agreed with adults with type 2 diabetes managed by diet alone?"

# 4. Non-retrieval baseline, same question
python src/ask.py --baseline "What HbA1c target should be agreed with adults with type 2 diabetes managed by diet alone?"
```

Steps 0-2 cost nothing and hit no API. Only 3-4 consume free-tier quota.

To recalibrate semantic chunking (already done; percentile locked at 85):

```bash
python scripts/calibrate_semantic.py
```

---

## 4. Verification gates

Every stage ends at a gate with a measured pass condition, recorded in
`EVIDENCE.md`. The gates already passed:

| Gate | Condition | Result |
|---|---|---|
| Ingestion | Zero residual furniture; reproduces across machines | Passed |
| Chunk offsets | `source[start:end] == text` for every chunk, both strategies | 547/547 and 509/509 |
| Chunk-length parity | Semantic/fixed mean ratio near 1.0 | 1.02 |
| Index integrity | FAISS vector count == chunk record count | 547=547, 509=509 |
| **Refusal (C3)** | A plausible clinical question outside the corpus returns "The provided guideline extracts do not state this." | Passed, 3/3 |
| **Fusion (C4)** | Hybrid reorders results relative to dense on exact-term queries | Passed, 5/5 |
| Scoring integrity | Every (condition, question, metric) scored, no NaN, no orphaned cache entries | 600/600, 0 NaN |

All build and measurement gates have passed. The experiment is complete; the
remaining work is the written report.

Verify the scoring gate at any time, offline and free:

```bash
python scripts/verify_install.py     # no stale code on disk
python scripts/diagnose_scoring.py   # 600 scored, 0 missing, 0 NaN
```

The refusal gate is the most consequential remaining check. If the model answers
a question the corpus cannot support, every faithfulness score collected
afterwards measures the wrong thing.

---

## 5. Project structure

```
rag-nice/
├── config.py                    # single source of truth for every experimental variable
├── requirements.txt
├── .env.example
├── EVIDENCE.md                  # measured results behind every verified claim
├── PROMPTS.md                   # Claude Code run sheet
├── CLAUDE.md                    # project rules for Claude Code
├── LOGBOOK.md
├── src/
│   ├── ingest.py                # source -> cleaned text (+ SHA-256, furniture removal)
│   ├── chunking.py              # fixed-size + semantic (p85) + merge_undersized
│   ├── embed_index.py           # sentence-transformers -> FAISS IndexFlatIP
│   ├── retrieve.py              # dense + hybrid (BM25 + reciprocal rank fusion)
│   ├── generate.py              # Gemini call, config ladder, non-retrieval baseline
│   ├── spans.py                 # character-span overlap -> relevance labels
│   ├── metrics_retrieval.py     # precision@k, recall@k, MRR
│   ├── dataset.py               # evaluation dataset schema + validator
│   └── ask.py                   # end-to-end CLI, saves a JSON transcript
├── scripts/
│   ├── check_env.py
│   ├── build_all.py             # ingest + chunk + index, all strategies
│   ├── calibrate_semantic.py    # percentile sweep against the fixed baseline
│   ├── validate_dataset.py      # dataset schema + verbatim span validator
│   ├── paraphrase_robustness.py # does retrieval survive rewording?
│   ├── run_experiment.py        # orchestrator: generate, sweep, score
│   ├── analyse.py               # Wilcoxon, Holm correction, effect sizes, figures
│   ├── verify_install.py        # no stale or duplicated code on disk (offline)
│   ├── diagnose_scoring.py      # score-cache state per condition (offline)
│   ├── inspect_nan_scores.py    # NaN triage: refusal vs judge failure (offline)
│   └── probe_judge.py           # two-layer judge connectivity check
├── tests/                       # offline, no API key required
├── data/{raw,interim,index,eval}/
└── outputs/                     # transcripts, metrics, figures
```

---

## 6. Version control

Initialise a repository now, before the first run:

```bash
git init && git add . && git commit -m "RAG pipeline over four NICE guidelines"
```

The assignment brief states that evidence of how your thinking developed — version-
controlled documents, journals — may be requested. A commit history that starts on day one
and runs to submission is the cheapest possible insurance, and it feeds directly into the
Project Management band (10%).
