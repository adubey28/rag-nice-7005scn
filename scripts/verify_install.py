"""
Confirm the RAGAS scoring patch is actually installed. OFFLINE, instant.

WHY THIS EXISTS
---------------
On 11 Aug 2026 a scoring run was started believing the patch was in place. It
was not - the file had never reached src/. The run looked normal, because the
old code prints a plausible progress line, and it silently cached NaN as a real
score for the third time. The cost was an hour and a contaminated cache.

A patch you believe is installed but is not is worse than no patch, because it
removes the suspicion that would otherwise make you check. Run this before any
scoring run. It calls nothing and changes nothing.

    python scripts/verify_install.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from console import safe_stdout  # noqa: E402

safe_stdout()

# (path, marker that must appear, what that marker proves)
CHECKS: list[tuple[str, str, str]] = [
    ("src/evaluate_ragas.py", "def _is_nan",
     "NaN detection helper"),
    ("src/evaluate_ragas.py", "JUDGE_MAX_RETRIES",
     "bounded retry policy (replaces ragas's silent 10x180s ladder)"),
    ("src/evaluate_ragas.py", "def _evaluate_once",
     "single-evaluation wrapper used by the NaN retry"),
    ("src/evaluate_ragas.py", "def _log_failure",
     "unresolved samples logged instead of silently dropped"),
    ("src/evaluate_ragas.py", "at the measured rate",
     "per-sample progress with live ETA"),
    ("src/evaluate_ragas.py", "wanted = [m for m in names if m not in cached]",
     "only missing metrics re-scored (no double billing)"),
    # Added 12 Aug 2026. Without these three, verify_install PASSED on the
    # pre-11-Aug evaluate_ragas.py, so the check meant to prove the patch was
    # installed could not detect its absence - the worst kind of green light.
    ("src/evaluate_ragas.py", "colmap = {m: inst.name for m, inst in zip(wanted, metrics)}",
     "ragas result columns resolved from the metric instance, not our label"),
    ("src/evaluate_ragas.py", "baseline_noretrieval",
     "context metrics excluded for the non-retrieval baseline"),
    ("src/evaluate_ragas.py", "**cached",
     "partial (--limit) runs merge with, not overwrite, cached scores"),
    ("scripts/diagnose_scoring.py", "RAGAS SCORING DIAGNOSTIC",
     "cache-state diagnostic"),
    ("scripts/inspect_nan_scores.py", "STRUCTURAL - refusal",
     "NaN inspector, refusal vs judge-failure"),
    ("scripts/probe_judge.py", "LAYER 1  raw endpoint",
     "judge connectivity probe"),
]

# Text that must NOT survive anywhere - the old NaN-caching gate.
FORBIDDEN: list[tuple[str, str, str]] = [
    ("src/evaluate_ragas.py", "if i % 5 == 0:",
     "old every-fifth-sample print - the patch did NOT overwrite the file"),
]


def main() -> None:
    argparse.ArgumentParser(
        description="Verify the scoring patch is installed. Offline."
    ).parse_args()

    print("=" * 74)
    print("INSTALL VERIFICATION")
    print("=" * 74)
    print(f"  project root  {ROOT}\n")

    failures = 0

    for rel, marker, why in CHECKS:
        path = ROOT / rel
        if not path.exists():
            print(f"  MISSING FILE  {rel}")
            failures += 1
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if marker in text:
            print(f"  OK    {rel:<32} {why}")
        else:
            print(f"  FAIL  {rel:<32} {why}")
            print(f"        expected to find: {marker!r}")
            failures += 1

    print()
    for rel, marker, why in FORBIDDEN:
        path = ROOT / rel
        if path.exists() and marker in path.read_text(encoding="utf-8",
                                                      errors="replace"):
            print(f"  FAIL  {rel:<32} still contains OLD code")
            print(f"        {why}")
            failures += 1
        else:
            print(f"  OK    {rel:<32} old code is gone")

    print("\n" + "=" * 74)
    if failures:
        print(f"  {failures} CHECK(S) FAILED - do NOT start a scoring run.")
        print("  Re-extract the patch archive over the project root, keeping")
        print("  its src/ and scripts/ folder structure, then run this again.")
        print("=" * 74)
        sys.exit(1)

    print("  ALL CHECKS PASSED - safe to score.")
    print("=" * 74)


if __name__ == "__main__":
    main()
