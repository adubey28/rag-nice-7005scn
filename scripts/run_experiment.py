"""
Stage 5 - Experiment orchestrator.

Drives the full experiment end to end:

    python scripts/run_experiment.py --generate         # all 5 conditions
    python scripts/run_experiment.py --score            # RAGAS on the answers
    python scripts/run_experiment.py --sweep            # top-k sensitivity
    python scripts/run_experiment.py --all              # everything, in order
    python scripts/run_experiment.py --dry-run          # plan + budget, no calls

DESIGN
------
Generation and scoring are separate phases that can be run independently and
resumed. Generation spends the Gemini free tier; scoring spends metered judge
credit. Keeping them apart means an interruption in one never corrupts the
other, and the expensive phase can be repeated without regenerating answers.

Everything is cached per question. A run that stops at question 47 resumes at
question 47 - it does not restart, and it does not re-pay for work already done.
This matters beyond convenience: because Gemini 3.x does not honour temperature,
regenerating an answer can produce a DIFFERENT answer, which would silently
decouple a faithfulness score from the text it was computed on.

WHAT IT WRITES
--------------
    outputs/cache/            one JSON per (condition, question) - raw answers
    outputs/ragas_cache/      one JSON per (condition, question, metric)
    outputs/runs/<name>.json  per-condition results with retrieval metrics
    outputs/summary.json      aggregated table across all conditions

Nothing is overwritten in place; a failed run leaves the previous state intact.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config  # noqa: E402
from console import safe_stdout  # noqa: E402

safe_stdout()
import dataset as ds  # noqa: E402
import experiment as exp  # noqa: E402
from env import load_env  # noqa: E402

load_env()


def load_rows() -> list[dict]:
    rows = ds.load_dataset()
    sources = ds.load_source_texts()
    ds.resolve_spans(rows, sources)          # raises if the instrument is invalid
    unverified = [r["question_id"] for r in rows if not r.get("verified")]
    if unverified:
        print(f"WARNING: {len(unverified)} questions are not marked verified: "
              f"{unverified[:5]}{'...' if len(unverified) > 5 else ''}")
    return rows


def phase_generate(rows: list[dict], conditions: list, sleep: float) -> dict:
    summaries = {}
    for cfg in conditions:
        print(f"\n[generate] {cfg.name()}  (fingerprint {cfg.fingerprint()})")
        t0 = time.time()
        results = exp.run_condition(cfg, rows, sleep=sleep)
        summary = exp.summarise(results)
        summary["config"] = cfg.as_dict()
        summary["wall_clock_seconds"] = round(time.time() - t0, 1)
        summary["n_generated_this_run"] = sum(1 for r in results if not r.from_cache)

        out = exp.RUNS_DIR / f"{cfg.name()}.json"
        out.write_text(json.dumps(
            {"summary": summary, "results": [r.as_dict() for r in results]},
            ensure_ascii=False, indent=2), encoding="utf-8")

        o = summary["overall"]
        print(f"[generate] {cfg.name()}: n={o['n']} "
              f"P@k={_f(o['precision_at_k'])} R@k={_f(o['recall_at_k'])} "
              f"MRR={_f(o['mrr'])} ctx={o['mean_context_chars']:.0f} chars "
              f"({summary['wall_clock_seconds']}s, "
              f"{summary['n_generated_this_run']} new)")
        summaries[cfg.name()] = summary
    return summaries


def phase_score(rows: list[dict], conditions: list, include_llm_context: bool,
                sleep: float, limit: int | None) -> dict:
    from evaluate_ragas import score_condition

    scores = {}
    for cfg in conditions:
        run_file = exp.RUNS_DIR / f"{cfg.name()}.json"
        if not run_file.exists():
            print(f"[score] {cfg.name()}: no generation output, skipping")
            continue
        results = json.loads(run_file.read_text(encoding="utf-8"))["results"]
        print(f"\n[score] {cfg.name()}")
        rec = score_condition(rows, results, cfg.name(),
                              include_llm_context=include_llm_context,
                              sleep=sleep, limit=limit)
        scores[cfg.name()] = rec

        for metric in ("faithfulness", "answer_relevancy"):
            vals = [r[metric] for r in rec if r.get(metric) is not None]
            if vals:
                print(f"[score] {cfg.name()} {metric}: "
                      f"mean {sum(vals)/len(vals):.3f} (n={len(vals)})")

        out = exp.RUNS_DIR / f"{cfg.name()}__ragas.json"
        out.write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return scores


def _f(v) -> str:
    return "n/a" if v is None else f"{v:.3f}"


def write_summary() -> None:
    """Collate every condition into one table for the results chapter."""
    table = []
    for run in sorted(exp.RUNS_DIR.glob("*.json")):
        if run.name.endswith("__ragas.json"):
            continue
        data = json.loads(run.read_text(encoding="utf-8"))
        s = data["summary"]
        row = {"condition": run.stem, **{k: v for k, v in s["overall"].items()}}

        ragas_file = exp.RUNS_DIR / f"{run.stem}__ragas.json"
        if ragas_file.exists():
            rec = json.loads(ragas_file.read_text(encoding="utf-8"))
            for metric in ("faithfulness", "answer_relevancy"):
                vals = [r[metric] for r in rec if r.get(metric) is not None]
                row[metric] = sum(vals) / len(vals) if vals else None
                row[f"{metric}_n"] = len(vals)
        table.append(row)

    out = config.OUTPUTS / "summary.json"
    out.write_text(json.dumps(table, indent=2), encoding="utf-8")

    print("\n" + "=" * 96)
    print(f"{'condition':<24}{'n':>4}{'P@k':>8}{'R@k':>8}{'MRR':>8}"
          f"{'faith':>9}{'relev':>9}{'ctx chars':>11}")
    print("-" * 96)
    for r in table:
        print(f"{r['condition']:<24}{r['n']:>4}{_f(r.get('precision_at_k')):>8}"
              f"{_f(r.get('recall_at_k')):>8}{_f(r.get('mrr')):>8}"
              f"{_f(r.get('faithfulness')):>9}{_f(r.get('answer_relevancy')):>9}"
              f"{r.get('mean_context_chars', 0):>11.0f}")
    print("=" * 96)
    print(f"\nWritten to outputs/{out.name}")
    print("\nThese are raw aggregates only. Significance testing (Wilcoxon "
          "signed-rank on paired questions) and effect sizes come next - do not "
          "read a difference in these means as a result on its own.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the full experiment.")
    ap.add_argument("--generate", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--sweep", action="store_true",
                    help="top-k sensitivity on the best retrieval configuration")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the plan and budget without spending anything.")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--sleep", type=float, default=4.0,
                    help="Seconds between generation calls (free-tier pacing).")
    ap.add_argument("--score-sleep", type=float, default=2.0)
    ap.add_argument("--limit", type=int, default=None,
                    help="Score at most N samples per condition (for a pilot).")
    ap.add_argument("--include-llm-context-metrics", action="store_true")
    ap.add_argument("--best", default="semantic_hybrid",
                    help="Configuration for the top-k sweep, e.g. fixed_dense.")
    args = ap.parse_args()

    if not any([args.generate, args.score, args.sweep, args.all, args.dry_run]):
        ap.error("choose at least one of --generate --score --sweep --all --dry-run")

    rows = load_rows()
    conditions = exp.core_conditions(top_k=args.top_k)

    from evaluate_ragas import estimate_budget
    est = estimate_budget(len(rows), len(conditions),
                          args.include_llm_context_metrics)

    print("=" * 72)
    print("EXPERIMENT PLAN")
    print("=" * 72)
    print(f"  questions      {len(rows)}")
    print(f"  conditions     {len(conditions)}: "
          f"{', '.join(c.name() for c in conditions)}")
    print(f"  generator      {config.GEN_MODEL}")
    print(f"  judge          {config.JUDGE_MODEL} ({config.JUDGE_PROVIDER})")
    print(f"  generations    {len(rows) * len(conditions)} "
          f"(cached, so only uncached ones are billed)")
    print(f"  judge tokens   ~{est['total_tokens_estimated']:,} "
          f"(~${est['estimated_cost_usd']})")
    if args.dry_run:
        print("\nDry run - nothing executed.")
        return

    if args.generate or args.all:
        phase_generate(rows, conditions, args.sleep)

    if args.sweep or args.all:
        chunking, retrieval = args.best.rsplit("_", 1)
        best = config.RunConfig(chunking=chunking, retrieval=retrieval,
                                top_k=args.top_k)
        sweep = [c for c in exp.topk_sweep(best) if c.top_k != args.top_k]
        print(f"\n[sweep] top-k sensitivity on {args.best}: "
              f"{[c.top_k for c in sweep]}")
        phase_generate(rows, sweep, args.sleep)

    if args.score or args.all:
        phase_score(rows, conditions, args.include_llm_context_metrics,
                    args.score_sleep, args.limit)

    write_summary()


if __name__ == "__main__":
    main()
