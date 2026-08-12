"""
Report the EFFECTIVE sample size behind every Wilcoxon test. OFFLINE, instant.

WHY THIS EXISTS
---------------
The Wilcoxon signed-rank test discards pairs whose difference is exactly zero.
`analyse.py` prints `n=60`, which is the number of paired questions available -
not the number the test actually used.

This matters here specifically. Faithfulness is a ratio of supported claims to
total claims, so it piles up on a few values, 1.0 above all. When both
conditions answer a question identically well, the difference is 0 and the pair
is dropped. If 40 of 60 pairs are tied, the test ran on 20, and a limitations
section claiming "n=60" would overstate the study's power.

That is not a defect in the analysis - it is standard Wilcoxon behaviour - but
it must be reported, because "no significant difference at n=60" and "no
significant difference at n=17" are very different statements about how much
this study could ever have detected.

    python scripts/effective_n.py
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from console import safe_stdout  # noqa: E402

safe_stdout()

# Reuse analyse.py's own loaders so this reports on exactly the same data.
_spec = importlib.util.spec_from_file_location(
    "_an", ROOT / "scripts" / "analyse.py")
_an = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_an)

COMPARISONS = [
    ("H1", "semantic_dense_k5", "fixed_dense_k5", "faithfulness"),
    ("H1", "semantic_hybrid_k5", "fixed_hybrid_k5", "faithfulness"),
    ("H2", "fixed_hybrid_k5", "fixed_dense_k5", "recall_at_k"),
    ("H2", "semantic_hybrid_k5", "semantic_dense_k5", "recall_at_k"),
    ("H2", "fixed_hybrid_k5", "fixed_dense_k5", "precision_at_k"),
    ("H2", "semantic_hybrid_k5", "semantic_dense_k5", "precision_at_k"),
    ("H2", "fixed_hybrid_k5", "fixed_dense_k5", "reciprocal_rank"),
    ("H2", "semantic_hybrid_k5", "semantic_dense_k5", "reciprocal_rank"),
    ("BASE", "fixed_dense_k5", "baseline_noretrieval", "faithfulness"),
    ("BASE", "semantic_hybrid_k5", "baseline_noretrieval", "faithfulness"),
]


def main() -> None:
    argparse.ArgumentParser(
        description="Effective n after tied pairs are dropped. Offline."
    ).parse_args()

    print("=" * 84)
    print("EFFECTIVE SAMPLE SIZE  (Wilcoxon discards zero-difference pairs)")
    print("=" * 84)
    print(f"  {'':5}{'comparison':46}{'pairs':>7}{'tied':>7}"
          f"{'used':>7}{'% used':>8}")
    print("-" * 84)

    cache: dict[str, dict] = {}
    worst = 100.0
    for tag, a, b, metric in COMPARISONS:
        for n in (a, b):
            if n not in cache:
                cache[n] = _an.load_condition(n)
        da, db = cache[a].get(metric, {}), cache[b].get(metric, {})
        ids, xa, xb = _an.paired(da, db)
        if not ids:
            continue
        diffs = [p - q for p, q in zip(xa, xb)]
        tied = sum(1 for d in diffs if d == 0)
        used = len(diffs) - tied
        pct = used / len(diffs) * 100 if diffs else 0.0
        worst = min(worst, pct)
        flag = "  <-- low" if pct < 50 else ""
        label = f"{a} vs {b} [{metric}]"
        if len(label) > 46:
            label = label[:43] + "..."
        print(f"  {tag:5}{label:46}"
              f"{len(diffs):>7}{tied:>7}{used:>7}{pct:>7.0f}%{flag}")

    print("-" * 84)
    print("\nHOW TO REPORT THIS")
    print("  Quote the USED column as the test's n, not the pairs column.")
    print("  A high tie count is itself a finding: it means the two conditions")
    print("  returned identically scored answers on those questions, i.e. the")
    print("  design choice made no difference there at all.")
    if worst < 50:
        print("\n  At least one comparison used under half its pairs. Say so in")
        print("  the limitations section, and avoid describing the study as")
        print("  powered at n=60.")
    print()


if __name__ == "__main__":
    main()
