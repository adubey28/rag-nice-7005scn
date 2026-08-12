"""
Build the full experimental substrate: ingest all four guidelines, then build
both chunk sets and both FAISS indexes.

    python scripts/build_all.py                 # all four guidelines
    python scripts/build_all.py --docs NG28     # smaller smoke run
    python scripts/build_all.py --overwrite     # rebuild from scratch

Costs nothing: no LLM calls. The only network use is the one-off download of
the embedding model from Hugging Face on first run.

Note that only TWO indexes are built for FOUR experimental conditions. Dense and
hybrid retrieval share an index — hybrid adds BM25 on top of the same chunk set
at query time. That is deliberate: it makes it structurally impossible for the
dense and hybrid conditions to be reading different chunks, which is exactly the
kind of confound a controlled comparison has to rule out.
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
from ingest import ingest  # noqa: E402
from embed_index import build_index  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", nargs="+", default=list(config.CORPUS.keys()))
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    docs = tuple(args.docs)
    summary: dict[str, dict] = {}

    print("\n" + "=" * 78)
    print("STEP 1/2  INGEST")
    print("=" * 78)
    for doc_id in docs:
        rec = ingest(doc_id, overwrite=args.overwrite)
        summary[doc_id] = {
            "pages": rec["n_pages"],
            "chars_clean": rec["n_chars_clean"],
            "retained_pct": round(100 * rec["n_chars_clean"] / max(1, rec["n_chars_raw"]), 1),
            "sha256": rec["sha256"],
        }
        print()

    print("=" * 78)
    print("STEP 2/2  CHUNK + INDEX  (semantic chunking embeds every sentence:")
    print("          expect it to take several minutes on CPU)")
    print("=" * 78)
    index_stats = {}
    for chunking in ("fixed", "semantic"):
        cfg = config.RunConfig(chunking=chunking, doc_ids=docs)
        print(f"\n--- {chunking} ---")
        t0 = time.time()
        name, n_chunks = build_index(cfg, overwrite=args.overwrite)
        index_stats[chunking] = {
            "index_name": name,
            "n_chunks": n_chunks,
            "build_seconds": round(time.time() - t0, 1),
        }

    report = {"documents": summary, "indexes": index_stats,
              "docs": list(docs)}
    out = config.OUTPUTS / "build_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("BUILD COMPLETE — copy this table into your logbook")
    print("=" * 78)
    print(f"{'Doc':<8}{'Pages':>7}{'Chars':>10}{'Retained':>10}  SHA-256")
    for doc_id, s in summary.items():
        print(f"{doc_id:<8}{s['pages']:>7}{s['chars_clean']:>10,}"
              f"{s['retained_pct']:>9}%  {s['sha256'][:16]}...")
    print()
    print(f"{'Strategy':<12}{'Chunks':>9}{'Build (s)':>12}")
    for k, s in index_stats.items():
        print(f"{k:<12}{s['n_chunks']:>9}{s['build_seconds']:>12}")
    print(f"\nwrote outputs/{out.name}")

    fx, se = index_stats["fixed"]["n_chunks"], index_stats["semantic"]["n_chunks"]
    print(f"\nSanity: fixed={fx} chunks, semantic={se} chunks. These SHOULD differ.")
    if abs(fx - se) / max(fx, se) < 0.05:
        print("WARNING: the two strategies produced near-identical chunk counts.")
        print("         Check that semantic chunking actually ran (see the sample).")


if __name__ == "__main__":
    main()
