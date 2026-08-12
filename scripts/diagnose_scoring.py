"""
Diagnose the state of RAGAS scoring. OFFLINE - no API calls, no spend.

WHY THIS EXISTS
---------------
`score_condition()` reports only a running count. When scoring stops advancing
that count cannot distinguish between:

    (a) the judge is failing and every sample is returning NaN
    (b) the judge is hanging inside ragas's internal retry ladder
    (c) the cache keys changed, so previously paid-for scores are invisible
    (d) scoring genuinely finished for the conditions it was given

This script reconstructs the full (condition x question x metric) matrix from
disk and reports which of those is true, plus the exact question the run
stopped on.

It reads:
    outputs/runs/<condition>.json       the generated answers (scoring input)
    outputs/ragas_cache/*.json          one file per scored (cond, qid, metric)

It writes nothing and calls nothing. Safe to run at any time, including while a
scoring run is still in progress.
"""

from __future__ import annotations

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
LLM_CONTEXT_METRICS = ["llm_context_precision", "llm_context_recall"]


def _read_score(path: Path):
    """Return (ok, value). ok=False means the file is unreadable/corrupt."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"unreadable: {exc}"
    try:
        return True, json.loads(raw)["score"]
    except (ValueError, KeyError) as exc:
        # json.loads accepts bare NaN, so this catches genuinely malformed files
        # and truncated writes - e.g. a process killed mid-write.
        return False, f"malformed ({type(exc).__name__}): {raw[:60]!r}"


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(
        description="Report the state of the RAGAS score cache. Offline.")
    ap.add_argument("--include-llm-context-metrics", action="store_true",
                    help="Expect 4 metrics per sample rather than 2.")
    ap.add_argument("--top-k", type=int, default=5,
                    help="Retrieval depth used for the core conditions.")
    args = ap.parse_args()

    include_llm_context = args.include_llm_context_metrics
    names = METRICS + (LLM_CONTEXT_METRICS if include_llm_context else [])

    print("=" * 78)
    print("RAGAS SCORING DIAGNOSTIC")
    print("=" * 78)
    print(f"  judge model      {config.JUDGE_MODEL}")
    print(f"  judge provider   {config.JUDGE_PROVIDER}")
    print(f"  metrics expected {names}")
    print(f"  cache directory  {SCORE_CACHE}")

    all_files = sorted(SCORE_CACHE.glob("*.json"))
    print(f"  cache files      {len(all_files)}")

    conditions = exp.core_conditions(top_k=args.top_k)
    run_files = {c.name(): exp.RUNS_DIR / f"{c.name()}.json" for c in conditions}

    missing_runs = [n for n, p in run_files.items() if not p.exists()]
    if missing_runs:
        print(f"\n  !! no generation output for: {missing_runs}")
        print("     phase_score SKIPS these conditions entirely.")

    # ---------------------------------------------------------------- matrix
    expected_keys: set[str] = set()
    print("\n" + "-" * 78)
    print(f"{'condition':<24}{'answers':>9}{'scored':>9}{'missing':>9}"
          f"{'NaN':>7}{'bad':>6}")
    print("-" * 78)

    stalled_at = None
    nan_records: list[tuple[str, str, str]] = []
    bad_records: list[tuple[str, str, str, str]] = []
    total_scored = total_expected = 0

    for cfg in conditions:
        cond = cfg.name()
        path = run_files[cond]
        if not path.exists():
            print(f"{cond:<24}{'-':>9}{'-':>9}{'-':>9}{'-':>7}{'-':>6}")
            continue

        results = json.loads(path.read_text(encoding="utf-8"))["results"]
        qids = [r["question_id"] for r in results]

        # The non-retrieval baseline has NO retrieved context, so the two
        # LLM-judged context metrics are undefined there - not zero - and
        # src/evaluate_ragas.py excludes it. Expecting them here reported 120
        # phantom "missing" scores and triggered a spurious judge-failure
        # verdict. Mirror the exclusion instead. (Fixed 12 Aug 2026.)
        cond_names = [m for m in names
                      if not (cond == "baseline_noretrieval"
                              and m in LLM_CONTEXT_METRICS)]

        scored = missing = n_nan = n_bad = 0
        first_missing = None

        for qid in qids:
            for m in cond_names:
                key = score_key(cond, qid, m)
                expected_keys.add(key)
                total_expected += 1
                p = SCORE_CACHE / f"{key}.json"
                if not p.exists():
                    missing += 1
                    if first_missing is None:
                        first_missing = (qid, m)
                    continue
                scored += 1
                total_scored += 1
                ok, val = _read_score(p)
                if not ok:
                    n_bad += 1
                    bad_records.append((cond, qid, m, str(val)))
                elif isinstance(val, float) and math.isnan(val):
                    n_nan += 1
                    nan_records.append((cond, qid, m))

        print(f"{cond:<24}{len(qids):>9}{scored:>9}{missing:>9}"
              f"{n_nan:>7}{n_bad:>6}")

        if first_missing and stalled_at is None:
            stalled_at = (cond, *first_missing,
                          qids.index(first_missing[0]) + 1, len(qids))

    print("-" * 78)
    print(f"{'TOTAL':<24}{'':>9}{total_scored:>9}"
          f"{total_expected - total_scored:>9}"
          f"{len(nan_records):>7}{len(bad_records):>6}")

    # ------------------------------------------------------------- orphans
    orphans = [f for f in all_files if f.stem not in expected_keys]
    if orphans:
        print(f"\n!! {len(orphans)} cache files do NOT match any expected key.")
        print("   The cache key is sha256(condition|question_id|metric|JUDGE_MODEL),")
        print("   so this means the judge model, a condition name, or a question_id")
        print("   changed since those scores were paid for. They are now invisible")
        print("   to score_condition() and will be recomputed at full cost.")
        for f in orphans[:5]:
            print(f"     {f.name}")
        if len(orphans) > 5:
            print(f"     ... and {len(orphans) - 5} more")

    # -------------------------------------------------------------- verdict
    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)

    if total_expected and total_scored == total_expected:
        print("  Scoring is COMPLETE for all conditions with generation output.")
    elif stalled_at:
        cond, qid, metric, pos, n = stalled_at
        print(f"  First unscored sample: {cond} / {qid} / {metric}")
        print(f"  That is question {pos} of {n} in that condition.")
        print("  Scoring resumes from here; earlier work is not repaid.")

    if nan_records:
        print(f"\n  !! {len(nan_records)} cached scores are NaN.")
        print("     ragas.evaluate() is called with raise_exceptions=False, so a")
        print("     judge failure returns NaN instead of raising. NaN passes the")
        print("     `if val is not None` gate in evaluate_ragas.py and is written")
        print("     to cache as a real score - so it is never retried, and it")
        print("     silently contaminates the condition mean.")
        for cond, qid, m in nan_records[:8]:
            print(f"       {cond:<22} {qid:<10} {m}")
        if len(nan_records) > 8:
            print(f"       ... and {len(nan_records) - 8} more")

    if bad_records:
        print(f"\n  !! {len(bad_records)} cache files are malformed "
              "(likely killed mid-write):")
        for cond, qid, m, why in bad_records[:8]:
            print(f"       {cond:<22} {qid:<10} {m}  {why}")

    if not nan_records and not bad_records and stalled_at:
        print("\n  No NaN and no corruption in what HAS been scored. Every cached")
        print("  score is a real number. That rules out failure mode (a) and")
        print("  points at the judge call itself - run scripts/probe_judge.py.")

    print()


if __name__ == "__main__":
    main()
