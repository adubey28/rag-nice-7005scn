"""
Compute the attainable ceiling for precision@k. OFFLINE, instant, no API.

WHY THIS EXISTS
---------------
precision@k is bounded above by how many chunks in the corpus are relevant at
all. If a question has only one relevant chunk and k is 5, the highest
attainable precision@5 is 0.2 - a perfect retriever scores 0.2, not 1.0.

Reporting raw precision@k without that ceiling invites the reader to conclude
retrieval is poor when it may be near-optimal, and it makes the four conditions
look closer together than the underlying differences warrant. This script
computes the ceiling exactly, from the real chunk files and the real gold spans,
using the same `spans.is_relevant` rule the experiment itself uses.

Two figures are produced per chunking arm:

  ceiling      mean over questions of min(relevant_chunks, k) / k
  attainment   observed precision@k / ceiling, i.e. how much of the
               achievable precision the retriever actually captured

Attainment is the number worth reporting: it is comparable across k, and it
answers "how good is this retriever?" rather than "what number came out?".

    python scripts/precision_ceiling.py
    python scripts/precision_ceiling.py --k 3 --k 10
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
import experiment as exp  # noqa: E402
import spans  # noqa: E402


def chunk_file_for(chunking: str) -> Path | None:
    cfg = config.RunConfig(chunking=chunking, retrieval="dense",
                           doc_ids=tuple(config.CORPUS_DOCS))
    p = config.INTERIM / f"chunks__{cfg.index_name()}.json"
    return p if p.exists() else None


def observed_precision(condition: str) -> float | None:
    """Mean precision@k actually achieved, from the generation run file."""
    p = exp.RUNS_DIR / f"{condition}.json"
    if not p.exists():
        return None
    vals = [r["precision_at_k"]
            for r in json.loads(p.read_text(encoding="utf-8"))["results"]
            if r.get("precision_at_k") is not None]
    return statistics.fmean(vals) if vals else None


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Compute the attainable precision@k ceiling. Offline.")
    ap.add_argument("--k", type=int, action="append",
                    help="Retrieval depth; repeatable. Default 5.")
    args = ap.parse_args()
    ks = args.k or [5]

    rows = ds.load_dataset()
    print("=" * 78)
    print("PRECISION@K CEILING")
    print("=" * 78)
    print(f"  questions {len(rows)}")

    gold_counts = [len(r["gold_passages"]) for r in rows]
    print(f"  gold passages per question: min {min(gold_counts)} "
          f"mean {statistics.fmean(gold_counts):.2f} max {max(gold_counts)}")

    for chunking in ("fixed", "semantic"):
        cf = chunk_file_for(chunking)
        if cf is None:
            print(f"\n  {chunking}: chunk file not built - run build_all.py")
            continue
        chunks = json.loads(cf.read_text(encoding="utf-8"))

        # How many chunks does each question have that count as relevant?
        rel_counts = []
        for row in rows:
            gold = ds.gold_spans_for(row)
            rel_counts.append(sum(1 for c in chunks
                                  if spans.is_relevant(c, gold)))

        print(f"\n  --- {chunking} ({len(chunks)} chunks) ---")
        print(f"  relevant chunks per question: min {min(rel_counts)} "
              f"mean {statistics.fmean(rel_counts):.2f} max {max(rel_counts)}")
        zero = sum(1 for n in rel_counts if n == 0)
        if zero:
            print(f"  !! {zero} question(s) have NO relevant chunk. Their "
                  f"precision and recall are 0 by construction, not by "
                  f"retrieval failure.")

        for k in ks:
            ceiling = statistics.fmean(min(n, k) / k for n in rel_counts)
            print(f"\n  k={k}: ceiling {ceiling:.3f}   "
                  f"(a perfect retriever cannot exceed this)")
            for retrieval in ("dense", "hybrid"):
                cond = f"{chunking}_{retrieval}_k{k}"
                obs = observed_precision(cond)
                if obs is None:
                    continue
                att = obs / ceiling if ceiling else float("nan")
                print(f"      {cond:24} observed {obs:.3f}   "
                      f"attainment {att:6.1%} of ceiling")

    print("\n" + "=" * 78)
    print("Report precision@k WITH its ceiling, or report attainment instead.")
    print("A raw precision@5 of 0.20 against a ceiling of 0.29 is a retriever")
    print("capturing two thirds of what is achievable - not a failing one.")
    print("=" * 78)


if __name__ == "__main__":
    main()
