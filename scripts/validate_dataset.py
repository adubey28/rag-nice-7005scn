"""
Validate the evaluation dataset. Run this after every editing session.

    python scripts/validate_dataset.py
    python scripts/validate_dataset.py --strict   # exit non-zero on warnings too

It reports three things:
  1. Structural errors that would invalidate the experiment (must be zero)
  2. Warnings worth a second look
  3. Coverage: question types, and how evidence is spread across the four
     guidelines — a dataset that draws 80% of its evidence from NG28 does not
     support claims about "NICE guidelines" in general, and a marker will
     notice.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config  # noqa: E402
from console import safe_stdout  # noqa: E402

safe_stdout()
from dataset import (  # noqa: E402
    DATASET_PATH, TARGET_COMPOSITION, TARGET_TOTAL,
    load_dataset, load_source_texts, validate_dataset,
)


def bar(n: int, target: int, width: int = 24) -> str:
    filled = 0 if target == 0 else min(width, int(width * n / target))
    return "█" * filled + "·" * (width - filled)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", type=Path, default=DATASET_PATH)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--write-spans", action="store_true",
                    help="Write resolved character spans back into the file.")
    args = ap.parse_args()

    rows = load_dataset(args.path)
    sources = load_source_texts()

    if not sources:
        print("No ingested documents found. Run scripts/build_all.py first.")
        sys.exit(1)

    issues, summary = validate_dataset(rows, sources)

    print("=" * 72)
    print(f"EVALUATION DATASET VALIDATION  —  {args.path.name}")
    print("=" * 72)

    print(f"\nRows: {summary['n_rows']}  |  verified by you: "
          f"{summary['n_verified']}  |  errors: {summary['n_errors']}  |  "
          f"warnings: {summary['n_warnings']}")

    print("\nQUESTION TYPE COVERAGE (target in brackets)")
    for qtype, target in TARGET_COMPOSITION.items():
        n = summary["by_type"].get(qtype, 0)
        print(f"  {qtype:<12} {bar(n, target)} {n:>3} / {target}")
    total = summary["n_rows"]
    print(f"  {'TOTAL':<12} {bar(total, TARGET_TOTAL)} {total:>3} / {TARGET_TOTAL}")

    print("\nEVIDENCE SPREAD ACROSS THE CORPUS")
    all_gold = sum(summary["by_doc"].values()) or 1
    for doc_id in config.CORPUS:
        n = summary["by_doc"].get(doc_id, 0)
        pct = 100 * n / all_gold
        flag = "  <-- thin" if pct < 12 and total > 10 else ""
        print(f"  {doc_id:<7} {n:>3} passages  ({pct:4.1f}%){flag}")

    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    if errors:
        print(f"\nERRORS ({len(errors)}) — these block evaluation")
        for i in errors:
            print(i)
    if warnings:
        print(f"\nWARNINGS ({len(warnings)})")
        for i in warnings[:40]:
            print(i)
        if len(warnings) > 40:
            print(f"  ... and {len(warnings) - 40} more")

    if args.write_spans and not errors:
        args.path.write_text(json.dumps(rows, ensure_ascii=False, indent=2),
                             encoding="utf-8")
        print(f"\nResolved character spans written back into {args.path.name}")

    print("\n" + "=" * 72)
    if errors:
        print("NOT READY — fix the errors above before running any experiment.")
    elif summary["n_verified"] < summary["n_rows"]:
        print(f"STRUCTURALLY VALID — but {summary['n_rows'] - summary['n_verified']} "
              f"rows are not yet marked verified.")
    else:
        print("READY — dataset is structurally valid and fully verified.")
    print("=" * 72)

    sys.exit(1 if errors or (args.strict and warnings) else 0)


if __name__ == "__main__":
    main()
