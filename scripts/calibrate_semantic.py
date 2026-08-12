"""
Calibrate the semantic breakpoint percentile against the fixed-size baseline.

    python scripts/calibrate_semantic.py
    python scripts/calibrate_semantic.py --percentiles 95 90 85 80 75 70

WHY THIS EXISTS - THE CONFOUND IT REMOVES
-----------------------------------------
H1 asks whether SEGMENTATION STRATEGY affects faithfulness. It does not ask
whether more context affects faithfulness - that is a different, already
well-studied question.

The first real run produced a mean semantic chunk of 1,136 characters against
761 for fixed-size: a ratio of 1.49. At a fixed retrieval depth of k=5 the
semantic condition would therefore receive roughly 49% more text per question
than the fixed condition. If semantic then scored higher on faithfulness, the
result would be uninterpretable: better segmentation and more evidence are fully
confounded, and no amount of downstream statistics can separate them afterwards.

The fix is to calibrate the breakpoint percentile so that mean chunk length is
comparable across conditions BEFORE any results are generated. Lowering the
percentile creates more breakpoints and therefore shorter chunks, while leaving
the mechanism untouched - cuts still fall at the largest semantic distances,
there are simply more of them.

This is a nuisance-variable control, not a thumb on the scale. It is decided in
advance, on chunk-length statistics alone, with no reference to faithfulness or
retrieval scores. Report the calibration table in the methodology so the choice
is transparent and auditable.

COST
----
Embedding dominates the runtime, and the distance profile does not depend on the
percentile. `semantic_prepare()` is therefore called once per document and the
distances reused across every candidate, so the whole sweep costs roughly one
semantic chunking run rather than one per candidate.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config  # noqa: E402
from console import safe_stdout  # noqa: E402

safe_stdout()
from chunking import (  # noqa: E402
    chunk_fixed, chunk_semantic, merge_undersized, semantic_prepare,
)
from embed_index import encode_passages  # noqa: E402


def stats(lengths: list[int]) -> dict:
    return {
        "n": len(lengths),
        "min": min(lengths) if lengths else 0,
        "median": statistics.median(lengths) if lengths else 0,
        "mean": statistics.mean(lengths) if lengths else 0,
        "max": max(lengths) if lengths else 0,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", nargs="+", default=list(config.CORPUS))
    ap.add_argument("--percentiles", nargs="+", type=float,
                    default=[95, 90, 85, 80, 75, 70])
    ap.add_argument("--buffer", type=int, default=config.STAGE1.semantic_buffer)
    ap.add_argument("--max-chars", type=int,
                    default=config.STAGE1.semantic_max_chars)
    ap.add_argument("--min-chars", type=int, default=config.STAGE1.min_chunk_chars)
    args = ap.parse_args()

    texts: dict[str, str] = {}
    for d in args.docs:
        p = config.INTERIM / f"{d}.json"
        if not p.exists():
            print(f"{d} not ingested. Run scripts/build_all.py first.")
            sys.exit(1)
        texts[d] = json.loads(p.read_text(encoding="utf-8"))["text"]

    # ---- baseline: fixed-size, with the same minimum-chunk policy ----
    fixed_lengths: list[int] = []
    for d, t in texts.items():
        pieces = chunk_fixed(t, config.STAGE1.chunk_size,
                             config.STAGE1.chunk_overlap)
        pieces = merge_undersized(t, pieces, args.min_chars)
        fixed_lengths += [p["n_chars"] for p in pieces]
    fixed = stats(fixed_lengths)

    print("=" * 74)
    print("SEMANTIC BREAKPOINT CALIBRATION")
    print("=" * 74)
    print(f"\nBaseline - fixed-size ({config.STAGE1.chunk_size}/"
          f"{config.STAGE1.chunk_overlap}, min {args.min_chars}):")
    print(f"  {fixed['n']} chunks | mean {fixed['mean']:.1f} | "
          f"median {fixed['median']:.0f} | min {fixed['min']} | max {fixed['max']}")

    # ---- embed once per document ----
    print(f"\nEmbedding sentences for {len(texts)} documents (once, reused "
          f"across all {len(args.percentiles)} candidates)...")
    prepared = {}
    t0 = time.time()
    for d, t in texts.items():
        prepared[d] = semantic_prepare(t, encode_passages, args.buffer)
        print(f"  {d}: {len(prepared[d][0])} sentences")
    print(f"  embedding wall-clock: {time.time() - t0:.1f}s")

    # ---- sweep ----
    print(f"\n{'percentile':>11} {'chunks':>8} {'mean':>9} {'median':>8} "
          f"{'max':>7} {'ratio':>7}")
    print("-" * 74)

    rows = []
    for pct in args.percentiles:
        lengths: list[int] = []
        for d, t in texts.items():
            pieces = chunk_semantic(t, encode_passages, percentile=pct,
                                    buffer=args.buffer, max_chars=args.max_chars,
                                    _prepared=prepared[d])
            pieces = merge_undersized(t, pieces, args.min_chars)
            lengths += [p["n_chars"] for p in pieces]
        st = stats(lengths)
        ratio = st["mean"] / fixed["mean"] if fixed["mean"] else 0
        rows.append((pct, st, ratio))
        flag = "  <-- closest" if abs(ratio - 1.0) == min(
            abs(r - 1.0) for _, _, r in rows) else ""
        print(f"{pct:>11.0f} {st['n']:>8} {st['mean']:>9.1f} "
              f"{st['median']:>8.0f} {st['max']:>7} {ratio:>7.2f}{flag}")

    best = min(rows, key=lambda r: abs(r[2] - 1.0))
    print("-" * 74)
    print(f"\nRECOMMENDED percentile: {best[0]:.0f}  "
          f"(mean {best[1]['mean']:.1f} vs fixed {fixed['mean']:.1f}, "
          f"ratio {best[2]:.2f})")
    print("\nSet config.RunConfig.semantic_percentile to this value, then rebuild")
    print("the semantic index. Record the whole table above in the methodology -")
    print("it shows the confound was controlled deliberately and in advance,")
    print("rather than discovered afterwards in the results.")

    out = config.OUTPUTS / "semantic_calibration.json"
    out.write_text(json.dumps({
        "fixed_baseline": fixed,
        "candidates": [{"percentile": p, **s, "ratio_to_fixed": r}
                       for p, s, r in rows],
        "recommended_percentile": best[0],
        "min_chunk_chars": args.min_chars,
        "buffer": args.buffer,
        "max_chars": args.max_chars,
    }, indent=2), encoding="utf-8")
    print(f"\nWritten to outputs/{out.name}")


if __name__ == "__main__":
    main()
