"""
No module may exist in both `src/` and `scripts/`.

WHY THIS EXISTS
---------------
On 11 Aug 2026 a stray copy of `evaluate_ragas.py` appeared in `scripts/`
alongside the real one in `src/`, most likely from a patch file copied into the
wrong folder. It surfaced only as an odd `test_script_imports_cleanly
[evaluate_ragas.py0]` failure - the `0` suffix pytest appends to duplicate
parametrise ids.

The visible symptom was trivial. The invisible risk was not. Python resolves
`import evaluate_ragas` by scanning `sys.path` in order, and every script in
`scripts/` gets its own directory prepended as `sys.path[0]` before its body
runs. A module present in both folders therefore resolves differently depending
on which file does the importing and when it manipulates `sys.path`. A stale
duplicate can shadow the real module and be used silently, with no error.

That is the same failure class as the three defects already in EVIDENCE.md: the
stale chunk file, the NaN cached as a real score, and the metric that failed by
returning rather than raising. Each looked correct and produced wrong results
without complaint. This test makes the condition impossible to reintroduce.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_module_in_both_src_and_scripts():
    src = {p.name for p in (ROOT / "src").glob("*.py")} - {"__init__.py"}
    scripts = {p.name for p in (ROOT / "scripts").glob("*.py")}
    clash = sorted(src & scripts)
    assert not clash, (
        "These modules exist in BOTH src/ and scripts/, so `import <name>` is "
        f"ambiguous and may silently resolve to the wrong copy: {clash}. "
        "Library modules belong in src/; command-line entry points belong in "
        "scripts/. Delete the stray copy - do not rename it."
    )


def test_every_script_declares_its_import_root():
    """Each script must put the repo root and src/ on sys.path before importing.

    Without this a script runs only from one working directory, which is how
    `check_env.py` originally shipped broken.
    """
    offenders = []
    for p in sorted((ROOT / "scripts").glob("*.py")):
        text = p.read_text(encoding="utf-8", errors="replace")
        if "sys.path.insert" not in text:
            offenders.append(p.name)
    assert not offenders, (
        f"scripts without an explicit sys.path setup: {offenders}. "
        "They will fail when invoked from another working directory."
    )
