# RAG over NICE Clinical Guidelines - submission package

**A Retrieval-Augmented Generation Question-Answering System over NICE Clinical
Guidelines: Evaluating the Effect of Chunking and Retrieval Strategies on
Faithfulness and Retrieval Quality**

Anuj Dubey (16180226) | 7005SCN Individual Research Project
Coventry University | Supervisor: Seyran Naghdi
Ethics: CU Ethics Online P194982 (approved, low risk)

Package built 2026-08-13.

---

## What this is

A complete retrieval-augmented generation pipeline over four NICE clinical
guidelines, and a controlled experiment measuring whether the design choices
behind it reduce ungrounded generation.

Two chunking strategies (fixed-size, semantic) crossed with two retrieval
methods (dense, hybrid) at a fixed depth, plus a non-retrieval baseline, over
60 human-verified questions. Faithfulness and answer relevancy are scored by an
independent LLM judge; retrieval quality is measured deterministically against
character-level gold evidence, with no LLM involved.

- **H1** semantic chunking produces higher faithfulness than fixed-size chunking
- **H2** hybrid retrieval achieves higher retrieval quality than dense alone

---

## What is included, and what is not

| Included | Why |
|---|---|
| `src/`, `scripts/`, `tests/` | The full pipeline and its test suite |
| `config.py`, `requirements.txt` | Every experimental variable, and pinned versions |
| `data/eval/` | The 60-question evaluation dataset with character-span gold evidence |
| `outputs/summary.json`, `analysis.json` | Aggregate results, significance tests, effect sizes |
| `outputs/figures/` | Generated figures |
| `outputs/runs/` | Per-question answers, retrieved contexts and metrics |
| `outputs/ragas_cache/` | Every individual judge score |
| `EVIDENCE.md` | The audit trail: every verified result and the command that produced it |

| Excluded | Why |
|---|---|
| `data/raw/*.pdf` | NICE guidelines are copyrighted. URLs and hashes are below. |
| `.env` | API keys. Never distributed. `.env.example` shows the format. |
| `.venv/`, `__pycache__/` | Environment-specific, rebuildable |
| `data/index/*.faiss`, chunk files | Derived; `build_all.py` regenerates them deterministically |

`outputs/ragas_cache/` is the important inclusion. **With it, every reported
number can be re-derived with no API key and no cost** - see step 3 below.

---

## Corpus provenance

The four guidelines are public and free to download from NICE. They are not
redistributed here.

| Guideline | Title | URL | SHA-256 (source PDF) |
|---|---|---|---|
| NG28 | Type 2 diabetes in adults: management | https://www.nice.org.uk/guidance/ng28 | `see outputs/build_report.json` |
| NG136 | Hypertension in adults: diagnosis and management | https://www.nice.org.uk/guidance/ng136 | `see outputs/build_report.json` |
| NG238 | Cardiovascular disease: risk assessment and reduction, including lipid modification | https://www.nice.org.uk/guidance/ng238 | `see outputs/build_report.json` |
| NG106 | Chronic heart failure in adults: diagnosis and management | https://www.nice.org.uk/guidance/ng106 | `see outputs/build_report.json` |

Download each as PDF into `data/raw/` using the exact filenames in
`config.CORPUS`, then run `scripts/build_all.py`. NICE revises its guidelines,
so verify the SHA-256 above if you need to reproduce the published results
exactly.

---

## Running it

### 1. Environment (Python 3.11)

Use 3.11, not 3.12 or 3.13: `faiss-cpu` and `torch` wheels are best-tested there.

```bash
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. What runs with no API key and no cost

```bash
python -m pytest tests/ -q          # full test suite, offline
python scripts/verify_install.py    # no stale or duplicated code
python scripts/diagnose_scoring.py  # score-cache integrity
python scripts/effective_n.py       # effective sample size after tied pairs
python scripts/analyse.py           # significance tests, effect sizes, figures
```

`analyse.py` regenerates every statistic and figure from the shipped results.
This is the fastest way to confirm the reported findings are real.

### 3. Reproducing the scores without paying for them

```bash
python scripts/run_experiment.py --score
```

Every condition should report `60 cached, 0 to score`. No judge call is made;
the numbers come from `outputs/ragas_cache/`. This is how the results are
verified without an API key.

### 4. Rebuilding the pipeline from the source PDFs

Requires the four PDFs in `data/raw/` (see provenance above). No API key.

```bash
python scripts/build_all.py --docs NG28 NG136 NG238 NG106
python scripts/verify_offsets.py
python scripts/precision_ceiling.py
```

Expected: 547 fixed chunks and 509 semantic chunks, offsets 100% exact on both
arms. Offset integrity below 100% means chunk spans no longer address the right
passages, which silently invalidates every retrieval metric - stop if you see it.

### 5. Regenerating answers (needs API keys, and will NOT reproduce exactly)

```bash
cp .env.example .env    # add GOOGLE_API_KEY and DEEPINFRA_API_KEY
python scripts/run_experiment.py --all
```

**This overwrites cached answers.** Gemini 3.x deprecates `temperature` and
cannot fully disable thinking, so regeneration produces different answers,
different faithfulness scores, and different results. The published findings
rest on one fixed, archived set of generated answers. Run this only if you
intend a new experiment rather than a replication.

---

## Reading the code

| Path | Role |
|---|---|
| `config.py` | Single source of truth for every experimental variable |
| `src/ingest.py` | PDF to cleaned text, with frequency-based furniture removal |
| `src/chunking.py` | Fixed-size and semantic chunking, preserving character offsets |
| `src/embed_index.py` | sentence-transformers to FAISS IndexFlatIP (exact search) |
| `src/retrieve.py` | Dense and hybrid retrieval (BM25 + reciprocal rank fusion) |
| `src/spans.py` | Character-span overlap to binary relevance labels |
| `src/generate.py` | Grounded generation with an enforced refusal clause |
| `src/evaluate_ragas.py` | RAGAS harness with per-sample score caching |
| `scripts/analyse.py` | Wilcoxon signed-rank, Holm correction, rank-biserial effect sizes |

**The critical invariant:** every chunk carries `start_char`/`end_char` into its
source document, and gold evidence is stored as character spans. That is what
makes retrieval metrics comparable between chunking strategies whose boundaries
differ. `scripts/verify_offsets.py` checks it; `tests/` guards it.

---

## Scope and limitations

- Generation is **not** bit-reproducible (see step 5). Mitigated by generating
  once, caching, and scoring against that fixed set.
- `precision@k` is bounded by the number of relevant chunks per question.
  Report it against the ceiling computed by `scripts/precision_ceiling.py`, or
  report attainment; raw values understate retrieval quality.
- Wilcoxon discards tied pairs, so the effective sample size is below 60 on
  several comparisons. `scripts/effective_n.py` reports the real figure.
- This is a **research prototype**. It gives no medical advice and is not a
  clinical tool. The system prompt forbids answering beyond the retrieved
  extracts and requires an explicit refusal when they are insufficient.

---

## Ethics

Secondary analysis of public, non-personal data. No human participants, no
personal or special-category data. Approved via CU Ethics Online, project
P194982.
