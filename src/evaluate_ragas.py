"""
Stage 4b - RAGAS scoring harness (DeepInfra judge, local embeddings).

WHY THIS IS A SEPARATE STEP FROM GENERATION
-------------------------------------------
RAGAS is the only part of the pipeline that spends metered external credit, and
it is expensive per sample: faithfulness decomposes an answer into individual
claims and verifies each one separately, so one sample is several LLM calls
rather than one. Roughly 3,500 tokens per sample across faithfulness and answer
relevancy, or about 1.05M tokens for 60 questions across 5 conditions.

Keeping scoring separate from generation means generation can complete in one
sitting while scoring runs independently, resuming from cache after any
interruption, without the two ever falling out of step.

METRIC SELECTION - AND AN HONEST DEVIATION FROM THE PROPOSAL
------------------------------------------------------------
The proposal specified four RAGAS metrics: faithfulness, answer relevance,
context precision and context recall.

Context precision and context recall are computed here by DEFAULT from character
span overlap in experiment.py, not by an LLM judge. Two reasons, one principled
and one practical:

  Principled - relevance must be defined identically across conditions. Chunk
  boundaries differ between the fixed and semantic arms, so an LLM judging
  "is this retrieved chunk relevant" applies a different implicit standard to
  different-sized chunks. Span overlap against the dataset's gold passages is
  the same rule for every condition, and it is deterministic and reproducible.

  Practical - those two metrics carry the largest LLM cost. Excluding them
  brings the evaluation inside the free-tier budget.

Set `--include-llm-context-metrics` to compute them via RAGAS as well, if quota
allows, and report both. That is the stronger result if it is affordable: two
independent operationalisations of the same construct agreeing is convergent
validity evidence.

This deviation must be stated plainly in the methodology, not buried.

API NOTE
--------
In ragas 0.4.3 the metric classes are NOT re-exported at package level; the
documented `from ragas.metrics import Faithfulness` fails. They import from
private modules instead. `_import_metrics()` tries the public path first so this
keeps working if a later release re-exports them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from env import load_env, require  # noqa: E402

load_env()

SCORE_CACHE = config.OUTPUTS / "ragas_cache"
SCORE_CACHE.mkdir(parents=True, exist_ok=True)

# Rough per-sample token cost, measured from prompt+context+answer sizes.
# Used only for budgeting, never for reporting.
TOKENS_PER_SAMPLE_FAITHFULNESS = 2600
TOKENS_PER_SAMPLE_RELEVANCY = 900
TOKENS_PER_SAMPLE_CONTEXT_LLM = 3200
# Reference ceiling for budgeting only. DeepInfra imposes no daily token cap on
# a funded account; this is retained so `--estimate-only` can report how a
# free-tier-style daily limit would constrain the run if a provider is switched.
REFERENCE_TOKENS_PER_DAY = 200_000
# Rough per-million-token cost of the current judge, for reporting only.
JUDGE_COST_PER_MTOK = {"deepinfra": 0.20, "openai": 0.30}

# Judge retry policy. ragas defaults to timeout=180s, max_retries=10,
# max_wait=60s and log_tenacity=False, which means a failing call can occupy
# ~40 minutes while printing nothing at all. Measured behaviour on this setup
# (scripts/probe_judge.py, 10 Aug 2026): a healthy two-metric sample completes
# in ~56s, and individual judge calls return in ~3-10s.
JUDGE_TIMEOUT_S = 120
JUDGE_MAX_RETRIES = 4
JUDGE_MAX_WAIT_S = 20

# The context metrics are far heavier: LLMContextPrecisionWithReference issues
# ONE judge call PER RETRIEVED CHUNK, so at top_k=5 a single sample costs
# roughly five times a faithfulness sample. Measured 11 Aug 2026: ~109s per
# sample when healthy. A 120s bound produced TimeoutError, which then triggered
# the retry ladder and pushed a sample to 277s while still failing - the bound
# intended to prevent stalls was itself causing them. Timeouts must be set from
# the measured cost of the SLOWEST metric in the set, not the typical one.
JUDGE_TIMEOUT_S_CONTEXT = 300
JUDGE_MAX_RETRIES_CONTEXT = 3
JUDGE_MAX_WAIT_S_CONTEXT = 30

# Samples whose score could not be obtained are appended here for inspection
# rather than being silently dropped.
FAILURE_LOG = config.OUTPUTS / "ragas_failures.jsonl"


def _is_nan(v) -> bool:
    return isinstance(v, float) and math.isnan(v)


def _import_metrics():
    """Return (Faithfulness, ResponseRelevancy, LLMContextPrecisionWithReference,
    LLMContextRecall), tolerating the 0.4.3 packaging quirk."""
    try:
        from ragas.metrics import (  # type: ignore
            Faithfulness, LLMContextPrecisionWithReference, LLMContextRecall,
            ResponseRelevancy,
        )
        return Faithfulness, ResponseRelevancy, LLMContextPrecisionWithReference, LLMContextRecall
    except ImportError:
        from ragas.metrics._answer_relevance import ResponseRelevancy
        from ragas.metrics._context_precision import LLMContextPrecisionWithReference
        from ragas.metrics._context_recall import LLMContextRecall
        from ragas.metrics._faithfulness import Faithfulness
        return Faithfulness, ResponseRelevancy, LLMContextPrecisionWithReference, LLMContextRecall


def build_judge(provider: str | None = None):
    """Build the RAGAS judge for the configured provider.

    All providers are reached through a chat-model wrapper that RAGAS can wrap
    in LangchainLLMWrapper. DeepInfra and OpenAI share the OpenAI-compatible
    client, which keeps the dependency surface small and means the provider can
    be switched with one config value rather than a rewrite - useful, given that
    two judge providers have already become unavailable mid-project.

    temperature=0 for score stability: the judge must not be a source of
    variance in the results.
    """
    from ragas.llms import LangchainLLMWrapper

    provider = provider or config.JUDGE_PROVIDER
    model = config.JUDGE_MODELS[provider]
    env_var = config.JUDGE_API_KEY_ENV[provider]
    key = require(env_var, f"config.JUDGE_PROVIDER is currently '{provider}'.")

    from langchain_openai import ChatOpenAI
    kwargs = {"model": model, "api_key": key, "temperature": 0.0}
    base = config.JUDGE_BASE_URLS.get(provider)
    if base:
        kwargs["base_url"] = base
    return LangchainLLMWrapper(ChatOpenAI(**kwargs))


def build_embeddings():
    """Local embeddings for answer relevancy - no API cost, and the same model
    family used for retrieval."""
    from langchain_huggingface import HuggingFaceEmbeddings
    from ragas.embeddings import LangchainEmbeddingsWrapper

    return LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL))


def score_key(condition: str, question_id: str, metric: str) -> str:
    h = hashlib.sha256(f"{condition}|{question_id}|{metric}|"
                       f"{config.JUDGE_MODEL}".encode()).hexdigest()[:16]
    return f"{condition}__{question_id}__{metric}__{h}"


def estimate_budget(n_samples: int, n_conditions: int,
                    include_llm_context: bool) -> dict:
    per = TOKENS_PER_SAMPLE_FAITHFULNESS + TOKENS_PER_SAMPLE_RELEVANCY
    if include_llm_context:
        per += TOKENS_PER_SAMPLE_CONTEXT_LLM
    total = per * n_samples * n_conditions
    return {
        "samples": n_samples,
        "conditions": n_conditions,
        "tokens_per_sample": per,
        "total_tokens_estimated": total,
        "provider": config.JUDGE_PROVIDER,
        "judge_model": config.JUDGE_MODEL,
        "estimated_cost_usd": round(
            total / 1_000_000 * JUDGE_COST_PER_MTOK.get(config.JUDGE_PROVIDER, 0.3), 2),
        "days_if_capped_at_200k_per_day": round(total / REFERENCE_TOKENS_PER_DAY, 1),
    }


def score_condition(rows: list[dict], results: list[dict], condition: str,
                    include_llm_context: bool = False,
                    sleep: float = 2.0, limit: int | None = None) -> list[dict]:
    """Score one condition's answers, caching every (sample, metric) individually.

    Per-sample caching (rather than per-condition) is what makes a daily-batch
    workflow possible: a run that stops on a rate limit resumes exactly where it
    left off, and no already-paid-for score is ever recomputed.

    THREE CORRECTNESS PROPERTIES, each fixing a defect found on 10 Aug 2026:

    1. NaN IS NEVER CACHED AS A SCORE. `evaluate()` runs with
       raise_exceptions=False, so a judge failure returns np.nan rather than
       raising - the previous `except` block was unreachable for judge faults.
       The old code then wrote NaN to cache, because `nan is not None` is True.
       That froze a failure permanently and averaged it into the condition mean.
       NaN is now retried once, then logged and left uncached if it persists.

    2. ONLY MISSING METRICS ARE RE-SCORED. Previously, if faithfulness cached
       and answer_relevancy failed, the next run recomputed BOTH - paying twice
       for the one that had succeeded.

    3. RETRIES ARE BOUNDED AND VISIBLE. An explicit RunConfig replaces ragas's
       silent 10-retry / 180s ladder, and progress prints every sample with a
       timing, so a slow run is distinguishable from a hung one. This mattered:
       at ~56s per sample the old every-fifth-sample print left the console
       silent for nearly five minutes, which reads as a freeze.
    """
    from ragas import EvaluationDataset, SingleTurnSample, evaluate
    from ragas.run_config import RunConfig

    F, RR, CP, CR = _import_metrics()
    judge, embeddings = build_judge(), build_embeddings()

    factories = {"faithfulness": F, "answer_relevancy": RR}
    names = ["faithfulness", "answer_relevancy"]
    if include_llm_context:
        # Context precision and recall score the RETRIEVED CONTEXT. The
        # non-retrieval baseline has none - `retrieved_contexts` is [""] - so
        # both metrics are undefined there, not merely low. Requesting them
        # would spend roughly an hour of judge time to produce NaN, and would
        # fill the failure log with entries that are correct behaviour rather
        # than faults. The baseline is excluded by construction and reported as
        # "not applicable", which is the honest description.
        if condition == "baseline_noretrieval":
            print(f"  {condition}: context metrics are undefined without "
                  f"retrieved context - scoring faithfulness and answer "
                  f"relevancy only")
        else:
            factories.update({"llm_context_precision": CP,
                              "llm_context_recall": CR})
            names += ["llm_context_precision", "llm_context_recall"]

    heavy = "llm_context_precision" in names
    run_config = RunConfig(
        timeout=JUDGE_TIMEOUT_S_CONTEXT if heavy else JUDGE_TIMEOUT_S,
        max_retries=JUDGE_MAX_RETRIES_CONTEXT if heavy else JUDGE_MAX_RETRIES,
        max_wait=JUDGE_MAX_WAIT_S_CONTEXT if heavy else JUDGE_MAX_WAIT_S)

    by_id = {r["question_id"]: r for r in rows}
    out: list[dict] = []
    todo: list[tuple[dict, SingleTurnSample, list[str]]] = []
    cached_by_qid: dict[str, dict] = {}

    missing_rows = [r["question_id"] for r in results
                    if r["question_id"] not in by_id]
    if missing_rows:
        raise KeyError(
            f"{condition}: {len(missing_rows)} generated question_id(s) are not "
            f"in the evaluation dataset: {missing_rows[:5]}. The dataset and the "
            f"cached answers have diverged - do not score against a mismatched "
            f"instrument.")

    for res in results:
        qid = res["question_id"]
        cached: dict[str, float | None] = {}
        for m in names:
            p = SCORE_CACHE / f"{score_key(condition, qid, m)}.json"
            if p.exists():
                cached[m] = json.loads(p.read_text(encoding="utf-8"))["score"]
        if len(cached) == len(names):
            out.append({"question_id": qid, "condition": condition, **cached,
                        "from_cache": True})
            continue

        wanted = [m for m in names if m not in cached]
        cached_by_qid[qid] = dict(cached)
        row = by_id[qid]
        todo.append((res, SingleTurnSample(
            user_input=row["question"],
            response=res["answer"],
            retrieved_contexts=res["contexts"] or [""],
            reference=row["reference_answer"],
        ), wanted))

    if limit is not None:
        # Emit the samples we are NOT scoring this run, carrying whatever is
        # already cached for them. Truncating `todo` alone silently dropped them
        # from the returned records, so `run_experiment.phase_score` then wrote a
        # 3-record file over the 60-record one and the summary table reported
        # pilot means as if they were the full result. A partial run must never
        # be able to narrow the reported result set.
        for res, _sample, _wanted in todo[limit:]:
            qid = res["question_id"]
            rec = {"question_id": qid, "condition": condition,
                   "from_cache": True, **cached_by_qid.get(qid, {})}
            for m in names:
                rec.setdefault(m, None)
            out.append(rec)
        todo = todo[:limit]

    est_min = len(todo) * (56 + sleep) / 60
    print(f"  {condition}: {len(out)} cached, {len(todo)} to score "
          f"(~{est_min:.0f} min at the measured rate)")

    t_start = time.time()
    for i, (res, sample, wanted) in enumerate(todo, start=1):
        qid = res["question_id"]
        metrics = [factories[m]() for m in wanted]

        # Resolve the ragas result column from the metric INSTANCE, never from
        # our own label. Our cache keys are stable names we control
        # ("llm_context_precision"); the column ragas returns is whatever the
        # class declares in `.name`, and the two do not always agree:
        #     LLMContextPrecisionWithReference.name == "llm_context_precision_with_reference"
        #     LLMContextRecall.name                 == "context_recall"
        # A hardcoded lookup silently returned None for both on 11 Aug 2026, so
        # every score was discarded AFTER the judge had been paid to compute it.
        # Reading `.name` makes this self-correcting if ragas renames a metric.
        colmap = {m: inst.name for m, inst in zip(wanted, metrics)}

        scores, err = _evaluate_once(evaluate, EvaluationDataset, sample,
                                     metrics, judge, embeddings, run_config)

        # Retry once if anything came back NaN. A transient judge fault usually
        # clears; a structural NaN (refusal -> no extractable claims) will not,
        # which is exactly how the two are told apart.
        nan_first = [m for m in wanted if _is_nan(scores.get(colmap[m]))]
        if nan_first and err is None:
            time.sleep(sleep)
            retry_metrics = [factories[m]() for m in nan_first]
            retry_scores, err = _evaluate_once(
                evaluate, EvaluationDataset, sample, retry_metrics, judge,
                embeddings, run_config)
            for m, inst in zip(nan_first, retry_metrics):
                if not _is_nan(retry_scores.get(inst.name)):
                    scores[colmap[m]] = retry_scores[inst.name]

        # `**cached` preserves metrics already scored in an earlier run. Without
        # it, adding a metric to `names` wipes the previously cached values from
        # the written record, because only `wanted` is recomputed - which blanked
        # faithfulness and answer_relevancy across every condition on 11 Aug 2026.
        rec = {"question_id": qid, "condition": condition,
               "from_cache": False, **cached_by_qid.get(qid, {})}
        unresolved: list[str] = []
        for m in wanted:
            val = scores.get(colmap[m])
            if val is None or _is_nan(val):
                unresolved.append(m)
                rec[m] = None
                continue                      # NOT cached - will be retried
            (SCORE_CACHE / f"{score_key(condition, qid, m)}.json").write_text(
                json.dumps({"score": float(val)}), encoding="utf-8")
            rec[m] = float(val)
        for m in names:
            rec.setdefault(m, None)

        if unresolved:
            _log_failure(condition, qid, unresolved, res, err)

        out.append(rec)

        elapsed = time.time() - t_start
        eta = (elapsed / i) * (len(todo) - i) / 60
        flag = f"  UNRESOLVED {unresolved}" if unresolved else ""
        print(f"    [{i}/{len(todo)}] {qid} "
              f"{' '.join(f'{m[:5]}={rec[m]:.2f}' for m in wanted if rec[m] is not None)}"
              f"  ({elapsed/i:.0f}s/sample, ETA {eta:.0f} min){flag}",
              flush=True)
        time.sleep(sleep)

    return out


def _evaluate_once(evaluate, EvaluationDataset, sample, metrics, judge,
                   embeddings, run_config) -> tuple[dict, str | None]:
    """One ragas evaluation. Returns (scores, error_string_or_None)."""
    try:
        ev = evaluate(dataset=EvaluationDataset(samples=[sample]),
                      metrics=metrics, llm=judge, embeddings=embeddings,
                      run_config=run_config, show_progress=False)
        return ev.to_pandas().iloc[0].to_dict(), None
    except Exception as exc:                                    # noqa: BLE001
        return {}, f"{type(exc).__name__}: {str(exc)[:200]}"


def _log_failure(condition: str, qid: str, metrics: list[str], res: dict,
                 err: str | None) -> None:
    """Append an unresolved sample to the failure log for later inspection."""
    answer = (res.get("answer") or "").strip()
    with FAILURE_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "condition": condition,
            "question_id": qid,
            "metrics": metrics,
            "exception": err,
            "answer_chars": len(answer),
            "answer_preview": answer[:300],
            "n_contexts": len(res.get("contexts") or []),
        }) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="RAGAS scoring harness.")
    ap.add_argument("--estimate-only", action="store_true",
                    help="Print the token budget and exit without spending quota.")
    ap.add_argument("--conditions", type=int, default=5)
    ap.add_argument("--samples", type=int, default=60)
    ap.add_argument("--include-llm-context-metrics", action="store_true")
    args = ap.parse_args()

    est = estimate_budget(args.samples, args.conditions,
                          args.include_llm_context_metrics)
    print(json.dumps(est, indent=2))
    print(f"\nEstimated cost on {est['provider']} ({est['judge_model']}): "
          f"${est['estimated_cost_usd']}")
    if args.estimate_only:
        return
    print("\nRun scripts/run_experiment.py to execute generation and scoring.")


if __name__ == "__main__":
    main()
