"""
Verify the chunk offset invariant on the REAL built artefacts. OFFLINE, instant.

WHY THIS EXISTS
---------------
Every chunk records `start_char`/`end_char` into its source document. Gold
evidence in the evaluation dataset is stored as character spans, and retrieval
relevance is span overlap. That is what makes retrieval metrics comparable
between the fixed and semantic arms, whose chunk boundaries differ. CLAUDE.md
states it plainly: any change that breaks span fidelity breaks the experiment.

`build_all.py` reports chunk counts and length statistics but does NOT verify
offsets, so a build can look entirely healthy while the spans address the wrong
passages. That failure has already occurred once on this project: a stale chunk
file showed 162 of 548 offsets valid after punctuation normalisation, while
every count and mean looked correct.

The unit tests guard the invariant on synthetic text. This script checks the
actual files on disk, which is the only thing the experiment was run against.

    python scripts/verify_offsets.py

Pass condition: 100% exact on BOTH arms. Anything less invalidates every
retrieval metric and must stop the pipeline.
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


def check(chunk_path: Path) -> tuple[int, int, list[str]]:
    """Return (exact, total, sample_failures) for one chunk file."""
    chunks = json.loads(chunk_path.read_text(encoding="utf-8"))
    sources: dict[str, str] = {}
    exact = 0
    failures: list[str] = []

    for c in chunks:
        doc_id = c["doc_id"]
        if doc_id not in sources:
            p = config.INTERIM / f"{doc_id}.txt"
            if not p.exists():
                failures.append(f"missing source text: {p.name}")
                sources[doc_id] = ""
                continue
            sources[doc_id] = p.read_text(encoding="utf-8")

        src = sources[doc_id]
        s, e = c["start_char"], c["end_char"]
        if 0 <= s < e <= len(src) and src[s:e] == c["text"]:
            exact += 1
        elif len(failures) < 5:
            got = src[s:e][:60] if 0 <= s < e <= len(src) else "<out of range>"
            failures.append(
                f"{c['chunk_id']} [{s}:{e}]\n"
                f"        stored : {c['text'][:60]!r}\n"
                f"        source : {got!r}")
    return exact, len(chunks), failures


def main() -> None:
    argparse.ArgumentParser(
        description="Verify chunk offsets against source text. Offline."
    ).parse_args()

    print("=" * 74)
    print("CHUNK OFFSET INTEGRITY")
    print("=" * 74)

    files = sorted(config.INTERIM.glob("chunks__*.json"))
    if not files:
        print("\n  No chunk files found in data/interim/.")
        print("  Run: python scripts/build_all.py --docs NG28 NG136 NG238 NG106")
        sys.exit(1)

    total_bad = 0
    for f in files:
        arm = "semantic" if "semantic" in f.name else "fixed"
        exact, total, failures = check(f)
        pct = (exact / total * 100) if total else 0.0
        status = "EXACT" if exact == total else "*** BROKEN ***"
        print(f"\n  {arm:9} {f.name}")
        print(f"    {exact}/{total} exact ({pct:.1f}%)  {status}")
        for msg in failures:
            print(f"      {msg}")
        if exact != total:
            total_bad += 1

    print("\n" + "=" * 74)
    if total_bad:
        print(f"  {total_bad} chunk file(s) FAILED. Retrieval metrics computed")
        print("  against these are meaningless: the spans address the wrong")
        print("  passages. Rebuild with --overwrite and re-check before")
        print("  trusting any downstream number.")
        print("=" * 74)
        sys.exit(1)
    print("  ALL CHUNK OFFSETS EXACT - span-overlap relevance is sound.")
    print("=" * 74)


if __name__ == "__main__":
    main()
