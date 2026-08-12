"""
Paraphrase robustness check - does retrieval survive rewording?

THE THREAT THIS ADDRESSES
-------------------------
The 60 evaluation questions were drafted by one author working from the source
text. Two risks follow, and neither is visible in the headline metrics:

  1. House style. If every question shares one phrasing register, the experiment
     measures how well the system handles THAT register, not how well it handles
     the queries a real user would type. Every condition is then evaluated on an
     unrepresentative slice of the input space.

  2. Lexical leakage. If a question reuses the vocabulary of its own gold
     passage, retrieval is artificially easy. That inflates every condition and
     can COMPRESS the differences between them - which is fatal, because the
     differences are the entire result. A ceiling effect looks like "no
     significant difference between chunking strategies" when the real finding
     is "the test items were too easy to discriminate".

This script measures both directly. Each probe question is paired with two
independently worded paraphrases that preserve the clinical scenario but change
the register - typically one lay/patient phrasing and one terse clinical one.
Retrieval is then run on the original and on each paraphrase, and gold-passage
recall is compared.

WHY IT COSTS NOTHING
--------------------
Retrieval only. No generation, no judge, no API calls, no quota. It runs in
seconds and can be repeated for every condition.

HOW TO READ THE RESULT
----------------------
  Recall roughly unchanged  -> retrieval generalises beyond the author's
                               phrasing; the instrument is not measuring style.
  Recall drops sharply      -> the evaluation set's phrasing was doing hidden
                               work, and the headline numbers are optimistic.

Either outcome is reportable and worth reporting. The second is a genuine
limitation that most evaluations never test for, and stating it is stronger than
leaving the assumption unexamined.

    python scripts/paraphrase_robustness.py
    python scripts/paraphrase_robustness.py --chunking semantic --retrieval hybrid
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config  # noqa: E402
from console import safe_stdout  # noqa: E402

safe_stdout()
import dataset as ds  # noqa: E402
from metrics_retrieval import recall_at_k  # noqa: E402

PARAPHRASE_PATH = config.DATA / "eval" / "paraphrases.json"


def diagnose(hits: list[dict], gold: list[dict]) -> dict:
    """Distinguish DEGREES of retrieval failure.

    recall@k is binary per gold span: a chunk overlapping by fewer than
    `min_overlap` characters scores exactly the same as a chunk from an
    unrelated guideline. That conflates two very different outcomes:

      near miss  - correct guideline, correct topic, adjacent chunk. The system
                   located the right region and the metric's span threshold
                   rejected it.
      true miss  - wrong guideline entirely. The system did not find the topic.

    For a robustness claim these must be reported separately. "Recall collapsed"
    is a fair description of the first only if the reader also learns that the
    right document was still retrieved.
    """
    gold_docs = {g["doc_id"] for g in gold}
    hit_docs = {h["doc_id"] for h in hits}

    # Distance from the nearest retrieved chunk to the nearest gold span, in
    # characters, within the correct document. 0 means overlapping.
    best = None
    for h in hits:
        for g in gold:
            if h["doc_id"] != g["doc_id"]:
                continue
            if h["start_char"] < g["end_char"] and g["start_char"] < h["end_char"]:
                best = 0
                break
            gap = (g["start_char"] - h["end_char"] if h["end_char"] <= g["start_char"]
                   else h["start_char"] - g["end_char"])
            best = gap if best is None else min(best, gap)
        if best == 0:
            break

    return {
        "correct_doc_retrieved": bool(gold_docs & hit_docs),
        "chars_to_nearest_gold": best,          # None = correct doc never retrieved
        "top1_score": hits[0]["score"] if hits else None,
    }


def evaluate_phrasings(cfg: config.RunConfig, probes: list[dict],
                       rows_by_id: dict, min_overlap: int = 40) -> dict:
    from retrieve import get_retriever

    retriever = get_retriever(cfg.index_name(), cfg.retrieval, cfg.embedding_model)
    per_question = []

    for probe in probes:
        row = rows_by_id.get(probe["question_id"])
        if row is None:
            continue
        gold = ds.gold_spans_for(row)

        variants = {"original": row["question"]}
        for i, alt in enumerate(probe["paraphrases"], start=1):
            variants[f"paraphrase_{i}"] = alt

        recalls, diag = {}, {}
        for label, q in variants.items():
            hits = retriever.search(q, cfg.top_k)
            recalls[label] = recall_at_k(hits, gold, cfg.top_k, min_overlap)
            diag[label] = diagnose(hits, gold)

        per_question.append({
            "question_id": probe["question_id"],
            "question_type": row["question_type"],
            "recalls": recalls,
            "diagnostics": diag,
            "delta": statistics.mean(
                [v for k, v in recalls.items() if k != "original"]
            ) - recalls["original"],
        })

    def mean_for(label: str) -> float:
        vals = [q["recalls"][label] for q in per_question if label in q["recalls"]]
        return statistics.mean(vals) if vals else 0.0

    def doc_hit_rate(label: str) -> float:
        vals = [q["diagnostics"][label]["correct_doc_retrieved"]
                for q in per_question if label in q["diagnostics"]]
        return sum(vals) / len(vals) if vals else 0.0

    def median_gap(label: str):
        vals = [q["diagnostics"][label]["chars_to_nearest_gold"]
                for q in per_question
                if q["diagnostics"].get(label, {}).get("chars_to_nearest_gold") is not None]
        return statistics.median(vals) if vals else None

    labels = sorted({k for q in per_question for k in q["recalls"]})
    return {
        "condition": cfg.name(),
        "n_probes": len(per_question),
        "mean_recall_by_phrasing": {lb: round(mean_for(lb), 3) for lb in labels},
        "correct_doc_rate_by_phrasing": {lb: round(doc_hit_rate(lb), 3) for lb in labels},
        "median_chars_to_gold_by_phrasing": {lb: median_gap(lb) for lb in labels},
        "mean_paraphrase_delta": round(
            statistics.mean([q["delta"] for q in per_question]), 3
        ) if per_question else 0.0,
        "per_question": per_question,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunking", default="fixed", choices=["fixed", "semantic"])
    ap.add_argument("--retrieval", default="dense", choices=["dense", "hybrid"])
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    if not PARAPHRASE_PATH.exists():
        print(f"No paraphrase set at {PARAPHRASE_PATH}.")
        sys.exit(1)

    probes = json.loads(PARAPHRASE_PATH.read_text(encoding="utf-8"))
    rows = ds.load_dataset()
    sources = ds.load_source_texts()
    ds.resolve_spans(rows, sources)
    rows_by_id = {r["question_id"]: r for r in rows}

    cfg = config.RunConfig(chunking=args.chunking, retrieval=args.retrieval,
                           top_k=args.top_k)
    result = evaluate_phrasings(cfg, probes, rows_by_id)

    print("=" * 72)
    print(f"PARAPHRASE ROBUSTNESS - {result['condition']}")
    print("=" * 72)
    print(f"\nProbe questions: {result['n_probes']}  (each with 2 paraphrases)\n")
    print(f"{'phrasing':<16}{'recall@k':>11}{'correct doc':>13}{'median gap':>13}")
    print("-" * 53)
    for label in result["mean_recall_by_phrasing"]:
        gap = result["median_chars_to_gold_by_phrasing"].get(label)
        gap_s = "n/a" if gap is None else f"{gap:.0f} ch"
        print(f"{label:<16}{result['mean_recall_by_phrasing'][label]:>11.3f}"
              f"{result['correct_doc_rate_by_phrasing'][label]:>13.3f}{gap_s:>13}")

    print("\nHow to read this. 'correct doc' is the share of probes where the")
    print("right guideline appeared in the top-k at all; 'median gap' is the")
    print("character distance from the nearest retrieved chunk to the gold span")
    print("within that guideline (0 = overlapping). High doc rate with a small")
    print("gap means the system located the right region and recall@k's span")
    print("threshold rejected it - a near miss. A low doc rate means the topic")
    print("was genuinely not found. These require different claims in the report.")
    delta = result["mean_paraphrase_delta"]
    print(f"\nMean change under paraphrase: {delta:+.3f}")

    if delta < -0.15:
        print("\nSubstantial drop. The evaluation set's phrasing is doing hidden")
        print("work and the headline retrieval numbers are optimistic. Report")
        print("this as a limitation - it is a real finding, not a failure.")
    elif delta < -0.05:
        print("\nModest drop, as expected. Retrieval largely generalises beyond")
        print("the author's phrasing. Report the magnitude.")
    else:
        print("\nNo meaningful degradation. Retrieval is not dependent on the")
        print("specific wording used in the evaluation set.")

    print("\nBiggest individual drops:")
    worst = sorted(result["per_question"], key=lambda q: q["delta"])[:5]
    for q in worst:
        rec = " ".join(f"{k.split('_')[-1]}={v:.2f}" for k, v in q["recalls"].items())
        print(f"  {q['question_id']} [{q['question_type'][:4]}] delta {q['delta']:+.2f}  {rec}")

    out = config.OUTPUTS / f"paraphrase_robustness__{result['condition']}.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nWritten to outputs/{out.name}")


if __name__ == "__main__":
    main()
