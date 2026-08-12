"""
Stage 1f — End-to-end: question in, grounded answer out.

This is the file you run to verify the whole stack. It also writes a JSON
transcript of every question to outputs/, tagged with the run fingerprint, so
that Stage 1 already produces the kind of auditable record the full experiment
will depend on.

    python src/ask.py "What HbA1c target is recommended for adults with type 2 diabetes managed by lifestyle and diet?"
    python src/ask.py --baseline "..."      # non-retrieval condition
    python src/ask.py --show-context "..."  # print the retrieved extracts
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402

# Windows consoles default to cp1252, which cannot encode characters that appear
# in guideline text. Printing a retrieved extract would raise UnicodeEncodeError
# and abort the run before the model was ever called - a display-layer fault
# masquerading as a pipeline failure. Reconfigure stdout to UTF-8 with a safe
# fallback so console encoding can never determine an experimental result.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
from generate import generate_answer  # noqa: E402
from retrieve import get_retriever  # noqa: E402


def answer_question(question: str, cfg: config.RunConfig,
                    baseline: bool = False) -> dict:
    if baseline:
        result = generate_answer(question, no_retrieval=True,
                                 model=cfg.gen_model,
                                 temperature=cfg.gen_temperature)
        result["retrieved"] = []
        result["condition"] = "baseline_noretrieval"
    else:
        retriever = get_retriever(cfg.index_name(), cfg.retrieval,
                                  cfg.embedding_model)
        hits = retriever.search(question, cfg.top_k)
        result = generate_answer(question, chunks=hits,
                                 model=cfg.gen_model,
                                 temperature=cfg.gen_temperature)
        result["retrieved"] = [
            {
                "rank": h["rank"],
                "score": h["score"],
                "chunk_id": h["chunk_id"],
                "doc_id": h["doc_id"],
                "start_char": h["start_char"],
                "end_char": h["end_char"],
            }
            for h in hits
        ]
        result["condition"] = cfg.name()

    result["config"] = cfg.as_dict()
    result["timestamp_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="Ask the RAG pipeline a question.")
    ap.add_argument("question")
    ap.add_argument("--baseline", action="store_true",
                    help="Non-retrieval baseline condition.")
    ap.add_argument("--top-k", type=int, default=config.STAGE1.top_k)
    ap.add_argument("--chunking", default="fixed")
    ap.add_argument("--retrieval", default="dense")
    ap.add_argument("--docs", nargs="+", default=config.CORPUS_DOCS)
    ap.add_argument("--show-context", action="store_true")
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args()

    cfg = config.RunConfig(
        chunking=args.chunking,
        retrieval=args.retrieval,
        top_k=args.top_k,
        doc_ids=tuple(args.docs),
    )

    result = answer_question(args.question, cfg, baseline=args.baseline)

    print("\n" + "=" * 78)
    print(f"CONDITION : {result['condition']}   (fingerprint {cfg.fingerprint()})")
    print(f"QUESTION  : {result['question']}")
    print("=" * 78)

    if args.show_context and result["retrieved"]:
        print("\nRETRIEVED EXTRACTS")
        for r, ctx in zip(result["retrieved"], result["contexts"]):
            print(f"\n[{r['rank']}] score={r['score']:.4f}  {r['chunk_id']}")
            print(ctx[:500].replace("\n", " ") + ("..." if len(ctx) > 500 else ""))
        print("\n" + "-" * 78)

    print(f"\nANSWER\n{result['answer']}\n")

    if result["retrieved"]:
        top = result["retrieved"][0]
        print(f"[top-1 similarity {top['score']:.4f} | {len(result['retrieved'])} "
              f"chunks used | {result['latency_seconds']}s]")
    else:
        print(f"[no retrieval | {result['latency_seconds']}s]")

    if not args.no_save:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = config.OUTPUTS / f"ask__{result['condition']}__{stamp}.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        print(f"[saved transcript -> outputs/{out.name}]")


if __name__ == "__main__":
    main()
