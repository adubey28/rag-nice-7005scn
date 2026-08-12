# CLAUDE.md — 7005SCN RAG over NICE Clinical Guidelines

## Context
MSc dissertation artefact (Coventry University, 7005SCN). Anuj Dubey, 16180226.
Controlled experiment measuring how chunking and retrieval strategy affect the
faithfulness and retrieval quality of a RAG QA system over four NICE guidelines.
Ethics approved: P194982. Due 17 August 2026.

- **H1** semantic chunking > fixed-size chunking on faithfulness
- **H2** hybrid retrieval > dense retrieval on retrieval quality

## Rules — these are not negotiable
1. **Never invent, estimate, simulate or placeholder an experimental result.**
   Metrics come only from real runs. If a run fails, report the failure.
2. **Never change an experimental parameter to make a result look better.**
   Parameters are fixed in `config.py` before running and stay fixed.
3. **Do not silently modify `config.py`.** If a value must change, say so
   explicitly and explain why; it affects the validity of the comparison.
4. **The embedding model and both LLMs are held constant across all
   conditions.** This is the study's core control. Nothing may vary it.
5. Never commit `.env`, API keys, or the NICE PDFs.
6. If something is ambiguous, ask rather than guess. A wrong assumption baked
   into the pipeline invalidates results downstream.

## Architecture
- `config.py` — single source of truth for every experimental variable
- `src/ingest.py` — PDF -> cleaned text (frequency-based header/footer removal)
- `src/chunking.py` — `fixed` (RecursiveCharacterTextSplitter) and `semantic`
  (percentile-breakpoint, reimplemented to preserve character offsets)
- `src/embed_index.py` — sentence-transformers -> FAISS IndexFlatIP (exact)
- `src/retrieve.py` — `DenseRetriever`, `HybridRetriever` (BM25 + RRF, k=60)
- `src/spans.py` — character-span overlap -> binary relevance labels
- `src/generate.py` — Gemini call + non-retrieval baseline
- `src/ask.py` — end-to-end CLI, saves JSON transcripts
- `scripts/build_all.py` — ingest + chunk + index everything
- `tests/test_components.py` — logic tests with a stubbed embedder (no network)

## Critical invariant
Every chunk carries `start_char`/`end_char` into the source document. Gold
evidence in the evaluation dataset is stored as character spans, and relevance
is span overlap. This is what makes retrieval metrics comparable between the
fixed and semantic conditions, whose chunk boundaries differ. **Any change that
breaks span fidelity breaks the experiment.** `tests/test_components.py` guards it —
run the tests after touching `chunking.py`.

## Environment
Python 3.11, venv at `.venv`. Keys in `.env` (`GOOGLE_API_KEY`, `DEEPINFRA_API_KEY`).
Windows: paths via `pathlib`, never hard-coded separators.
Free-tier rate limits are the binding constraint — batch and cache; never
brute-force retry in a tight loop.

## Style
Standard library and the pinned packages only; no new dependencies without
asking. Explain design decisions in module docstrings — they become
methodology-chapter material.
