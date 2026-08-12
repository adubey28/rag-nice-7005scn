"""
Central configuration for the RAG-over-NICE-guidelines experiment.

Everything that could vary between experimental runs lives here, in one place.
That is deliberate and methodological, not just tidy: the study's validity rests
on the claim that only the independent variables changed between conditions.
A single config module makes that claim inspectable and auditable.

`RunConfig.fingerprint()` produces a short hash of the settings that actually
affect results. Every artefact written to disk carries that fingerprint, so a
result file can always be traced back to the exact configuration that produced
it. Record the fingerprint in your logbook alongside each run.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path

# Load .env HERE, not in a leaf module.
#
# load_dotenv() previously lived only in generate.py. `--all` imports generate
# as a side effect, so the environment happened to be loaded; `--score` alone
# does not, so the judge key was invisible and scoring could not be resumed
# independently. Environment availability must not depend on import order.
# config.py is imported by every entry point, so loading here makes it
# unconditional.
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:  # dotenv absent: real environment variables still work
    pass

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RAW = DATA / "raw"          # PDFs downloaded from NICE (never edited by code)
INTERIM = DATA / "interim"  # extracted text, chunk sets
INDEX = DATA / "index"      # FAISS indexes + chunk stores
OUTPUTS = ROOT / "outputs"  # answers, metrics, figures

for _p in (RAW, INTERIM, INDEX, OUTPUTS):
    _p.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# Corpus registry
# --------------------------------------------------------------------------
# Stage 1 uses NG28 only. The other three are declared now so that scaling up
# is a data task, not a code change.
CORPUS = {
    "NG28": {
        "title": "Type 2 diabetes in adults: management",
        "filename": "ng28.pdf",
        "url": "https://www.nice.org.uk/guidance/ng28",
    },
    "NG136": {
        "title": "Hypertension in adults: diagnosis and management",
        "filename": "ng136.pdf",
        "url": "https://www.nice.org.uk/guidance/ng136",
    },
    "NG238": {
        "title": ("Cardiovascular disease: risk assessment and reduction, "
                  "including lipid modification"),
        "filename": "ng238.pdf",
        "url": "https://www.nice.org.uk/guidance/ng238",
    },
    "NG106": {
        "title": "Chronic heart failure in adults: diagnosis and management",
        "filename": "ng106.pdf",
        "url": "https://www.nice.org.uk/guidance/ng106",
    },
}

# The full experimental corpus. Defaults across the codebase point here so that
# a forgotten --docs flag cannot silently run an experiment over a subset of the
# corpus - a failure mode that produces plausible numbers for the wrong study.
CORPUS_DOCS = ["NG28", "NG136", "NG238", "NG106"]

# Retained for the single-document smoke test only. Do not use for experiments.
STAGE1_DOCS = ["NG28"]


# --------------------------------------------------------------------------
# Models (held CONSTANT across all experimental conditions)
# --------------------------------------------------------------------------
# bge-small-en-v1.5: 384 dimensions, ~33M parameters, CPU-friendly, and strong
# on MTEB retrieval benchmarks for its size. It is an *asymmetric* retrieval
# model: queries must be prefixed with an instruction, passages must not. Get
# this wrong and retrieval quality degrades silently — a real threat to H2.
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# Generator. Verify this string is still served on the free tier by running
# `python scripts/check_env.py --list-models` and record the result.
# Generator. VERIFY against the live model list before the final run.
#
# Two candidates, and the choice is a methodological one, not a convenience:
#
#   gemini-2.5-flash  Accepts temperature=0 and thinking_budget=0. Determinism
#                     is controllable, which the design requires. Legacy: no
#                     shutdown date on the Developer API, but retired on Vertex
#                     from 16 Oct 2026 and some users saw intermittent 404s in
#                     July 2026.
#   gemini-3.6-flash  Current default Flash (July 2026). BUT temperature/top_p/
#                     top_k are deprecated on the 3.x line and thinking cannot
#                     be fully disabled - so exact-repeat determinism is no
#                     longer guaranteed and token spend rises.
#
# RESOLVED 2026-08-05 by live test: gemini-2.5-flash returns
#   404 NOT_FOUND "no longer available to new users"
# It appears in models.list() but is not callable, so it is not an option. The
# experiment therefore runs on gemini-3.6-flash and ACCEPTS the loss of
# temperature control. Consequence for the methodology: generation is not
# bit-reproducible. Mitigation - every raw answer is cached and archived, so all
# scoring runs against one fixed set of generated outputs, and the results are
# internally consistent and auditable even though the generator is not
# deterministic. Report this as a stated limitation.
# GEN_MODEL_FALLBACK is used only if the primary returns 404/NOT_FOUND, and the
# substitution is recorded in every output file.
GEN_MODEL = "gemini-3.6-flash"
GEN_MODEL_FALLBACK = "gemini-3.5-flash"
# NOTE: Gemini 3.x DEPRECATES temperature, so this value is sent but has no
# guaranteed effect. It is retained because it is the documented intent and it
# is recorded in every run fingerprint. Do not describe generation as
# deterministic in the report: it is not. The control that actually holds is
# that every answer is generated ONCE, cached, and all scoring runs against
# that one fixed set - see the GEN_MODEL note above.
GEN_TEMPERATURE = 0.0
GEN_MAX_TOKENS = 1024

# Judge model for Stage 3 (RAGAS). Deliberately a different family from the
# generator so that no model grades its own output.
# JUDGE (RAGAS faithfulness / answer relevancy)
#
# Held constant, and deliberately a DIFFERENT model family from the generator
# (Gemini 3.6 Flash) so that no model grades its own output. This is a
# methodological requirement, not a preference.
#
# Provider history, all forced rather than chosen:
#   llama-3.3-70b-versatile on Groq - deprecated 17 Jun 2026, shutdown ~16 Aug
#   openai/gpt-oss-120b on Groq     - viable, but Groq's free tier caps at
#                                     ~200k tokens/day = 5.2 days for this
#                                     experiment, and paid upgrades are frozen
#                                     ("temporarily unavailable due to high
#                                     demand", reported Apr-May 2026)
#   Llama 3.3 70B on DeepInfra      - current choice. Same model family as the
#                                     original plan, no daily token cap, and the
#                                     whole experiment costs ~$0.15-0.30.
#
# JUDGE_PROVIDER selects the backend; the model is a different family from the
# generator under every option.
# Groq was removed entirely on 7 Aug 2026 (paid tier frozen, free tier too slow).
# Both remaining providers speak the OpenAI-compatible protocol, so no
# provider-specific dependency is required.
JUDGE_PROVIDER = "deepinfra"          # "deepinfra" | "openai"

JUDGE_MODELS = {
    "deepinfra": "meta-llama/Llama-3.3-70B-Instruct",
    "openai": "gpt-4o-mini",
}
JUDGE_BASE_URLS = {
    "deepinfra": "https://api.deepinfra.com/v1/openai",
    "openai": None,
}
JUDGE_API_KEY_ENV = {
    "deepinfra": "DEEPINFRA_API_KEY",
    "openai": "OPENAI_API_KEY",
}
JUDGE_MODEL = JUDGE_MODELS[JUDGE_PROVIDER]


# --------------------------------------------------------------------------
# Experimental variables
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class RunConfig:
    """One experimental condition."""

    # Independent variable 1: chunking strategy
    chunking: str = "fixed"          # "fixed" | "semantic" | "none"
    chunk_size: int = 1000           # characters (fixed-size only)
    chunk_overlap: int = 150         # characters (fixed-size only)

    # Semantic chunking parameters (see src/chunking.py for the algorithm)
    # CALIBRATED 2026-08-06 against the fixed-size baseline, on chunk-length
    # statistics only (scripts/calibrate_semantic.py; table in EVIDENCE.md S10).
    # p85 gave mean 799.0 vs fixed 767.9 = ratio 1.04, against 1.49 at the
    # original p95. Fixed BEFORE any results exist.
    # Those are the CALIBRATION figures, measured on the pre-normalisation
    # text. The final build on normalised text gives 509 semantic chunks,
    # mean 789.6, against 547 fixed, mean 770.8 = ratio 1.02 (EVIDENCE.md S13).
    # Quote 1.02 as the achieved parity; 1.04 is the figure the DECISION was
    # made on. Both appear in the audit trail and they are not in conflict.
    semantic_percentile: float = 85.0   # breakpoint threshold on distance
    semantic_buffer: int = 1            # neighbouring sentences for context
    semantic_max_chars: int = 2000      # hard cap; oversized chunks are split
    min_chunk_chars: int = 100          # applied to BOTH strategies (see
                                        # chunking.merge_undersized)

    # Independent variable 2: retrieval method
    retrieval: str = "dense"         # "dense" | "hybrid" | "none"
    top_k: int = 5

    # Hybrid fusion parameters (reciprocal rank fusion)
    rrf_k: int = 60                  # Cormack et al. (2009) standard constant
    fusion_pool: int = 30            # candidates drawn from each ranker

    # Held constant
    embedding_model: str = EMBEDDING_MODEL
    gen_model: str = GEN_MODEL
    gen_temperature: float = GEN_TEMPERATURE

    # Documents in scope for this run
    doc_ids: tuple[str, ...] = field(
        default_factory=lambda: tuple(CORPUS_DOCS))

    def name(self) -> str:
        """Human-readable condition label, e.g. 'fixed_dense_k5'."""
        if self.retrieval == "none":
            return "baseline_noretrieval"
        return f"{self.chunking}_{self.retrieval}_k{self.top_k}"

    def index_name(self) -> str:
        """Indexes depend only on chunking + embedding, not on retrieval or k.
        Two conditions that share a chunking strategy share an index — which
        is both efficient and a guarantee that they see identical chunks."""
        docs = "-".join(sorted(self.doc_ids))
        if self.chunking == "fixed":
            return f"{docs}__fixed_{self.chunk_size}_{self.chunk_overlap}"
        if self.chunking == "semantic":
            return (f"{docs}__semantic_p{self.semantic_percentile:g}"
                    f"_b{self.semantic_buffer}_m{self.semantic_max_chars}")
        return f"{docs}__{self.chunking}"

    def fingerprint(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:10]

    def as_dict(self) -> dict:
        d = asdict(self)
        d["condition"] = self.name()
        d["fingerprint"] = self.fingerprint()
        return d


# The Stage 1 smoke-test condition.
STAGE1 = RunConfig(chunking="fixed", retrieval="dense", top_k=5, doc_ids=("NG28",))


# --------------------------------------------------------------------------
# Prompting
# --------------------------------------------------------------------------
# The refusal clause matters more than it looks. Faithfulness is the proportion
# of claims in the answer supported by the retrieved context. A model that is
# permitted to say "not stated" when retrieval fails will score as faithful; a
# model forced to answer regardless will hallucinate and score badly. This
# prompt is therefore part of the experimental apparatus and is held constant
# across every condition — it must be quoted verbatim in the methodology.
SYSTEM_PROMPT = (
    "You are a careful research assistant answering questions about UK NICE "
    "clinical guidelines. You answer ONLY from the numbered extracts provided "
    "in the user's message. You must not use prior knowledge, and you must not "
    "infer beyond what the extracts state.\n\n"
    "Rules:\n"
    "1. Base every statement on the provided extracts.\n"
    "2. After each statement, cite the extract number(s) it came from, e.g. [2].\n"
    "3. If the extracts do not contain the information needed, reply exactly: "
    "\"The provided guideline extracts do not state this.\"\n"
    "4. Be concise and factual. Do not add caveats, disclaimers or advice.\n"
    "5. This is a research prototype. Never present output as medical advice."
)

USER_PROMPT_TEMPLATE = (
    "Extracts from NICE guidelines:\n\n"
    "{context}\n\n"
    "---\n"
    "Question: {question}\n\n"
    "Answer using only the extracts above, citing extract numbers."
)


def format_context(chunks: list[dict]) -> str:
    """Render retrieved chunks as numbered extracts for the prompt."""
    parts = []
    for i, c in enumerate(chunks, start=1):
        parts.append(
            f"[{i}] (source: {c['doc_id']}, chunk {c['chunk_id']})\n{c['text'].strip()}"
        )
    return "\n\n".join(parts)
