# Development Logbook — 7005SCN

One entry per working session. Keep it factual and contemporaneous; this is assessed
evidence for the Project Management band (10%) and the audit trail the assignment brief
says may be requested.

---

## Session template

**Date / hours:**
**Stage & aim:**
**What I did:**
**Result / evidence (file paths, fingerprints, figures):**
**Decision made and why (alternatives rejected):**
**Problem hit → how resolved:**
**Risk noted:**
**Next action:**

---

## Stage 1 — record these specifically

### Environment (reproducibility appendix)
- [ ] Python version, OS, machine (CPU/RAM)
- [ ] Full `pip freeze` output, dated
- [ ] Resolved versions of: pypdf, langchain-text-splitters, sentence-transformers, torch, faiss-cpu, google-genai
- [ ] Confirmed Gemini model string from `--list-models` (config.GEN_MODEL may need updating)

### Corpus provenance
- [ ] NG28 download date
- [ ] NICE "Last updated" date shown on the guidance page
- [ ] SHA-256 printed by ingest.py
- [ ] Page count; raw → cleaned character counts; % retained
- [ ] Number of furniture lines removed

### Extraction quality (validity evidence)
- [ ] Read NG28.txt end to end — note any sections that extracted badly (tables? figures?)
- [ ] Screenshot or excerpt of a well-extracted recommendation, and of any failure
- [ ] Decision recorded: accept extraction as-is, or add targeted cleaning (and why)

### Chunking
- [ ] Chunk count, min/median/max/mean length
- [ ] Judgement on the sampled chunk: coherent or mid-idea?
- [ ] chunk_size / chunk_overlap chosen, and the reasoning

### Retrieval + generation
- [ ] Three test questions used, and whether the correct passage was in the top 3
- [ ] Top-1 cosine similarity for each
- [ ] Answer quality: cited extracts? any unsupported statement?
- [ ] **Refusal test result** (out-of-corpus question) — pass/fail
- [ ] Generation latency; any rate-limit errors and the retry behaviour observed

### Decisions to carry into the methodology chapter
- [ ] Exact search (IndexFlatIP) over ANN — why
- [ ] bge-small-en-v1.5 and the asymmetric query prefix — why
- [ ] temperature = 0 — why
- [ ] The grounding prompt, quoted verbatim, and why the refusal clause matters

### Risks logged this stage
- [ ] Free-tier quota consumption per run (measure it — it sets the ceiling on the experiment)
- [ ] Any package that failed to install and the workaround
