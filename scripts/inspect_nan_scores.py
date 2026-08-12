"""
Inspect the answers behind NaN faithfulness scores. OFFLINE - no API calls.

WHY THIS MATTERS METHODOLOGICALLY
---------------------------------
ragas returns NaN for faithfulness in two very different situations, and they
must not be treated alike:

  STRUCTURAL   `_faithfulness.py` returns np.nan when statement extraction
               yields an empty list ("No statements were generated from the
               answer"). A refusal - "The provided guideline extracts do not
               state this." - contains no verifiable claims, so there is
               nothing to be faithful or unfaithful about. The metric is
               undefined, not failed. This is deterministic: it will recur on
               every re-score.

  TRANSIENT    the judge errored or returned unparseable output and ragas
               swallowed it, because evaluate() runs with
               raise_exceptions=False. Re-scoring usually succeeds.

Conflating them corrupts the headline result. Faithfulness is the metric H1 is
tested on, so a condition that refuses more often would silently have those
questions dropped from its mean - inflating it relative to a condition that
answers and hallucinates. Which of the two you have determines whether these
samples are re-scored or reported as a separate "unscoreable" count.

    python scripts/inspect_nan_scores.py
    python scripts/inspect_nan_scores.py --purge     # delete for re-scoring
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config  # noqa: E402
from console import safe_stdout  # noqa: E402

safe_stdout()

import experiment as exp  # noqa: E402
from evaluate_ragas import SCORE_CACHE, score_key  # noqa: E402

METRICS = ["faithfulness", "answer_relevancy"]

# The exact refusal string mandated by config.SYSTEM_PROMPT rule 3.
REFUSAL = "The provided guideline extracts do not state this."


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Show the answers behind NaN scores. Offline.")
    ap.add_argument("--purge", action="store_true",
                    help="Delete NaN cache files so they are re-scored.")
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    print("=" * 78)
    print("NaN SCORE INSPECTION")
    print("=" * 78)

    conditions = exp.core_conditions(top_k=args.top_k)
    found: list[tuple[str, str, str, Path, dict]] = []

    for cfg in conditions:
        cond = cfg.name()
        run_file = exp.RUNS_DIR / f"{cond}.json"
        if not run_file.exists():
            continue
        results = json.loads(run_file.read_text(encoding="utf-8"))["results"]
        by_id = {r["question_id"]: r for r in results}

        for qid, res in by_id.items():
            for m in METRICS:
                p = SCORE_CACHE / f"{score_key(cond, qid, m)}.json"
                if not p.exists():
                    continue
                try:
                    val = json.loads(p.read_text(encoding="utf-8")).get("score")
                except ValueError:
                    continue
                if isinstance(val, float) and math.isnan(val):
                    found.append((cond, qid, m, p, res))

    if not found:
        print("\n  No NaN scores in the cache.\n")
        return

    print(f"\n  {len(found)} NaN score(s).\n")

    n_refusal = n_other = 0
    for cond, qid, metric, path, res in found:
        answer = (res.get("answer") or "").strip()
        contexts = res.get("contexts") or []
        is_refusal = REFUSAL.lower() in answer.lower()
        verdict = ("STRUCTURAL - refusal, no claims to verify" if is_refusal
                   else "UNCLEAR - not a refusal; likely a judge failure")
        if is_refusal:
            n_refusal += 1
        else:
            n_other += 1

        print("-" * 78)
        print(f"  {cond} / {qid} / {metric}")
        print(f"  verdict     {verdict}")
        print(f"  contexts    {len(contexts)} retrieved, "
              f"{sum(len(c) for c in contexts)} chars")
        print(f"  answer      ({len(answer)} chars)")
        for line in (answer[:600] or "(empty)").splitlines() or ["(empty)"]:
            print(f"      {line}")
        if len(answer) > 600:
            print("      ...")

    print("-" * 78)
    print(f"\n  refusals (structural, will recur)  {n_refusal}")
    print(f"  not refusals (likely transient)   {n_other}")

    print("\n" + "=" * 78)
    print("WHAT TO DO")
    print("=" * 78)
    if n_other:
        print(f"  {n_other} look like judge failures. Purge and re-score them:")
        print("      python scripts/inspect_nan_scores.py --purge")
    if n_refusal:
        print(f"  {n_refusal} are refusals. Faithfulness is UNDEFINED for these,")
        print("  not zero and not missing at random. Re-scoring will return NaN")
        print("  again. They must be reported as an explicit 'unscoreable'")
        print("  count per condition alongside the mean, because refusal rate")
        print("  differs by condition and silently dropping them biases the")
        print("  H1 comparison. Decide and document this BEFORE seeing results.")

    if args.purge:
        for _, _, _, path, _ in found:
            path.unlink()
        print(f"\n  PURGED {len(found)} cache file(s). They will be re-scored.")
    else:
        print("\n  Nothing deleted. Re-run with --purge to remove these.")
    print()


if __name__ == "__main__":
    main()
