"""
Stage 6 - Statistical analysis: paired tests, effect sizes, figures.

    python scripts/analyse.py
    python scripts/analyse.py --alpha 0.05 --no-figures

WHY PAIRED, NON-PARAMETRIC TESTS
--------------------------------
Every condition answers the SAME 60 questions, so observations are paired:
question 17 under fixed/dense and question 17 under semantic/dense are the same
question, not two independent draws. An unpaired test would discard that
pairing, inflate the standard error, and lose real statistical power.

The tests are non-parametric (Wilcoxon signed-rank) because RAGAS faithfulness
is bounded in [0,1] and typically piles up near 1.0 - strongly non-normal, so a
paired t-test's assumptions do not hold. Recall@k is worse still: with k=5 and
one or two gold spans it takes only a handful of discrete values.

EFFECT SIZE IS REPORTED ALWAYS, NOT ONLY WHEN p < 0.05
------------------------------------------------------
With n=60 a trivial difference can reach significance, and a meaningful one can
miss it. The rank-biserial correlation is reported for every comparison
alongside its confidence interval, so the reader sees the MAGNITUDE rather than
just a verdict. A p-value alone would not support the claims H1 and H2 make.

MULTIPLE COMPARISONS
--------------------
H1 and H2 are each tested twice (once at each level of the other factor), and
several secondary comparisons follow. Holm-Bonferroni correction is applied
within each hypothesis family and reported alongside the uncorrected value, so
the reader can see both. Uncorrected p-values on six comparisons would be an
obvious weakness for a marker to pick up.

WHAT IT DOES NOT DO
-------------------
It does not decide whether a hypothesis is "supported". It reports the test
statistic, both p-values, the effect size and the CI. The interpretation belongs
in the discussion, written by the researcher.
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config  # noqa: E402
from console import safe_stdout  # noqa: E402

safe_stdout()

RUNS = config.OUTPUTS / "runs"
METRICS = ["faithfulness", "answer_relevancy", "precision_at_k",
           "recall_at_k", "reciprocal_rank",
           "llm_context_precision", "llm_context_recall"]

# LLM-judged context metrics exist only for the four core cells. The
# non-retrieval baseline has no retrieved context, so both are UNDEFINED
# there - not zero - and are excluded by src/evaluate_ragas.py. The top-k
# sweep conditions were scored on faithfulness and answer relevancy only.
# load_condition() simply omits what is absent, and compare() pairs on the
# intersection of question ids, so missing metrics reduce no comparison to
# a partial one.
LLM_CONTEXT = ["llm_context_precision", "llm_context_recall"]


def load_condition(name: str) -> dict[str, dict[str, float]]:
    """Return {metric: {question_id: value}} for one condition."""
    out: dict[str, dict[str, float]] = {m: {} for m in METRICS}

    run = RUNS / f"{name}.json"
    if run.exists():
        for r in json.loads(run.read_text(encoding="utf-8"))["results"]:
            for m in ("precision_at_k", "recall_at_k", "reciprocal_rank"):
                if r.get(m) is not None:
                    out[m][r["question_id"]] = float(r[m])

    ragas = RUNS / f"{name}__ragas.json"
    if ragas.exists():
        for r in json.loads(ragas.read_text(encoding="utf-8")):
            for m in ("faithfulness", "answer_relevancy",
                      "llm_context_precision", "llm_context_recall"):
                if r.get(m) is not None:
                    out[m][r["question_id"]] = float(r[m])
    return out


def paired(a: dict[str, float], b: dict[str, float]):
    """Values for questions present in BOTH conditions, in a stable order."""
    ids = sorted(set(a) & set(b))
    return ids, [a[i] for i in ids], [b[i] for i in ids]


def rank_biserial(x: list[float], y: list[float]) -> float:
    """Effect size for a paired design: (favourable - unfavourable) / total,
    over non-zero differences. Ranges -1 to +1; positive favours x."""
    diffs = [xi - yi for xi, yi in zip(x, y) if xi != yi]
    if not diffs:
        return 0.0
    pos = sum(1 for d in diffs if d > 0)
    neg = sum(1 for d in diffs if d < 0)
    return (pos - neg) / len(diffs)


def bootstrap_ci(x: list[float], y: list[float], n_boot: int = 5000,
                 seed: int = 42) -> tuple[float, float]:
    import random
    rng = random.Random(seed)
    n = len(x)
    if n == 0:
        return (0.0, 0.0)
    stats = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        stats.append(rank_biserial([x[i] for i in idx], [y[i] for i in idx]))
    stats.sort()
    return (stats[int(0.025 * n_boot)], stats[int(0.975 * n_boot)])


def compare(name_a: str, name_b: str, metric: str,
            data: dict) -> dict | None:
    from scipy.stats import wilcoxon

    a = data.get(name_a, {}).get(metric, {})
    b = data.get(name_b, {}).get(metric, {})
    ids, xa, xb = paired(a, b)
    if len(ids) < 6:
        return None

    diffs = [p - q for p, q in zip(xa, xb)]
    if all(d == 0 for d in diffs):
        stat, p = 0.0, 1.0
    else:
        try:
            stat, p = wilcoxon(xa, xb, zero_method="wilcox",
                               alternative="two-sided")
        except ValueError:
            return None

    lo, hi = bootstrap_ci(xa, xb)
    return {
        "metric": metric, "a": name_a, "b": name_b, "n": len(ids),
        "mean_a": sum(xa) / len(xa), "mean_b": sum(xb) / len(xb),
        "median_diff": sorted(diffs)[len(diffs) // 2],
        "wilcoxon_W": float(stat), "p_uncorrected": float(p),
        "rank_biserial": rank_biserial(xa, xb),
        "ci_low": lo, "ci_high": hi,
        "n_ties": sum(1 for d in diffs if d == 0),
    }


def holm(results: list[dict]) -> None:
    """Holm-Bonferroni within a family, written back as p_holm."""
    ordered = sorted(results, key=lambda r: r["p_uncorrected"])
    m = len(ordered)
    prev = 0.0
    for i, r in enumerate(ordered):
        adj = min(1.0, (m - i) * r["p_uncorrected"])
        adj = max(adj, prev)          # enforce monotonicity
        r["p_holm"] = adj
        prev = adj


def fmt(r: dict, alpha: float) -> str:
    sig = "*" if r["p_holm"] < alpha else " "
    return (f"  {r['a']:<21}vs {r['b']:<21}n={r['n']:<3} "
            f"{r['mean_a']:.3f} vs {r['mean_b']:.3f}  "
            f"p={r['p_uncorrected']:.4f} p_holm={r['p_holm']:.4f}{sig} "
            f"rb={r['rank_biserial']:+.3f} [{r['ci_low']:+.2f},{r['ci_high']:+.2f}]")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args()

    names = sorted({p.stem.replace("__ragas", "") for p in RUNS.glob("*.json")})
    if not names:
        print(f"No results in {RUNS}. Run scripts/run_experiment.py first.")
        sys.exit(1)
    data = {n: load_condition(n) for n in names}

    print("=" * 96)
    print("ANALYSIS - paired Wilcoxon signed-rank, rank-biserial effect size, "
          "Holm-corrected")
    print("=" * 96)
    print(f"\nConditions found: {', '.join(names)}\n")

    families = {
        "H1  semantic vs fixed chunking (faithfulness)": [
            ("semantic_dense_k5", "fixed_dense_k5", "faithfulness"),
            ("semantic_hybrid_k5", "fixed_hybrid_k5", "faithfulness"),
        ],
        "H2  hybrid vs dense retrieval (retrieval quality)": [
            ("fixed_hybrid_k5", "fixed_dense_k5", "recall_at_k"),
            ("semantic_hybrid_k5", "semantic_dense_k5", "recall_at_k"),
            ("fixed_hybrid_k5", "fixed_dense_k5", "precision_at_k"),
            ("semantic_hybrid_k5", "semantic_dense_k5", "precision_at_k"),
            ("fixed_hybrid_k5", "fixed_dense_k5", "reciprocal_rank"),
            ("semantic_hybrid_k5", "semantic_dense_k5", "reciprocal_rank"),
        ],
        # PRE-SPECIFIED 12 Aug 2026, before any aggregate context result was
        # inspected (see EVIDENCE.md S31). Held as a SEPARATE family so that
        # Holm correction within H2 is unchanged by its addition. Labelled
        # exploratory: these metrics were not named in the original H2
        # statement, which specified precision@k, recall@k and MRR.
        "Context quality  hybrid vs dense (LLM-judged, exploratory)": [
            ("fixed_hybrid_k5", "fixed_dense_k5", "llm_context_precision"),
            ("semantic_hybrid_k5", "semantic_dense_k5", "llm_context_precision"),
            ("fixed_hybrid_k5", "fixed_dense_k5", "llm_context_recall"),
            ("semantic_hybrid_k5", "semantic_dense_k5", "llm_context_recall"),
        ],
        "Context quality  semantic vs fixed (LLM-judged, exploratory)": [
            ("semantic_dense_k5", "fixed_dense_k5", "llm_context_precision"),
            ("semantic_hybrid_k5", "fixed_hybrid_k5", "llm_context_precision"),
            ("semantic_dense_k5", "fixed_dense_k5", "llm_context_recall"),
            ("semantic_hybrid_k5", "fixed_hybrid_k5", "llm_context_recall"),
        ],
        "Retrieval vs non-retrieval baseline (faithfulness)": [
            (c, "baseline_noretrieval", "faithfulness")
            for c in ("fixed_dense_k5", "fixed_hybrid_k5",
                      "semantic_dense_k5", "semantic_hybrid_k5")
        ],
    }

    all_results = {}
    for family, comps in families.items():
        rs = [r for r in (compare(a, b, m, data) for a, b, m in comps) if r]
        if not rs:
            print(f"\n{family}\n  (no paired data yet)")
            continue
        holm(rs)
        all_results[family] = rs
        print(f"\n{family}")
        by_metric: dict[str, list] = {}
        for r in rs:
            by_metric.setdefault(r["metric"], []).append(r)
        for metric, group in by_metric.items():
            print(f"  [{metric}]")
            for r in group:
                print(fmt(r, args.alpha))

    out = config.OUTPUTS / "analysis.json"
    out.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    print(f"\n\nWritten to outputs/{out.name}")
    print("\nrb = rank-biserial correlation, with 95% bootstrap CI. * marks "
          "p_holm < alpha.")
    print("A CI spanning zero means the direction of the effect is not "
          "established, regardless of the p-value.")
    print("\nThese are test results, not conclusions. Interpretation belongs in "
          "the discussion.")

    if not args.no_figures:
        try:
            make_figures(data, names)
        except Exception as exc:  # noqa: BLE001
            print(f"\n[figures] skipped: {type(exc).__name__}: {exc}")


def make_figures(data: dict, names: list[str]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figdir = config.OUTPUTS / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    core = [n for n in names if n.endswith("_k5") or n == "baseline_noretrieval"]

    for metric in METRICS:
        series = [(n, list(data[n][metric].values())) for n in core
                  if data[n][metric]]
        if len(series) < 2:
            continue
        fig, ax = plt.subplots(figsize=(8, 4.5))
        # NOTE: do not pass labels= or tick_labels= here. matplotlib renamed
        # `labels` to `tick_labels` in 3.9 and REMOVED `labels` in 3.11, so
        # either keyword breaks on some version permitted by requirements.txt
        # (matplotlib>=3.8). Setting the ticks explicitly works on all of them.
        ax.boxplot([v for _, v in series], showmeans=True)
        ax.set_xticks(range(1, len(series) + 1))
        ax.set_xticklabels([n for n, _ in series])
        ax.set_ylabel(metric.replace("_", " "))
        ax.set_title(f"{metric.replace('_', ' ')} by condition (n per box shown)")
        for i, (_, v) in enumerate(series, start=1):
            ax.annotate(f"n={len(v)}", (i, ax.get_ylim()[0]),
                        ha="center", va="bottom", fontsize=8, alpha=0.7)
        plt.xticks(rotation=20, ha="right")
        plt.tight_layout()
        fig.savefig(figdir / f"{metric}.png", dpi=200)
        plt.close(fig)

    sweep = sorted([n for n in names if "_k" in n and n.startswith("semantic_hybrid")],
                   key=lambda n: int(n.rsplit("_k", 1)[1]))
    if len(sweep) >= 2:
        fig, ax = plt.subplots(figsize=(7, 4))
        ks = [int(n.rsplit("_k", 1)[1]) for n in sweep]
        for metric in ("recall_at_k", "precision_at_k", "faithfulness"):
            vals = [data[n][metric] for n in sweep]
            if not all(vals):
                continue
            means = [sum(v.values()) / len(v) for v in vals]
            ax.plot(ks, means, marker="o", label=metric.replace("_", " "))
        ax.set_xlabel("retrieval depth k")
        ax.set_ylabel("mean score")
        ax.set_title("Top-k sensitivity (best configuration)")
        ax.legend()
        plt.tight_layout()
        fig.savefig(figdir / "topk_sensitivity.png", dpi=200)
        plt.close(fig)

    print(f"\n[figures] written to outputs/figures/")


if __name__ == "__main__":
    main()
