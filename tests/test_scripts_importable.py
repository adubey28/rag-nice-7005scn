"""
Every script must be runnable. Regression test for a real shipped bug.

WHY THIS EXISTS
---------------
`src/console.py` was added and its import bulk-patched into ten scripts at once.
Nine of them already put `src/` on `sys.path`; `check_env.py` did not, so it
died with ModuleNotFoundError - and it died at IMPORT time, meaning the very
first pre-flight command a user runs was broken, on a machine where no unit test
would have touched it.

Unit tests import MODULES. They never exercise a script's `__main__` path, so a
broken `sys.path` setup in a CLI entry point is invisible to them. This test
closes that gap by invoking each script as a subprocess exactly as a user would.

`--help` is used because argparse exits 0 after printing usage without executing
anything: no API calls, no quota, no side effects, but the whole import chain
runs first.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

SCRIPTS = sorted(
    [p for p in (ROOT / "scripts").glob("*.py")]
    + [p for p in (ROOT / "src").glob("*.py") if p.name != "__init__.py"]
)


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_script_imports_cleanly(script: Path):
    r = subprocess.run([sys.executable, str(script), "--help"],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, (
        f"{script.name} failed to start:\n"
        f"{r.stderr.strip().splitlines()[-1] if r.stderr.strip() else r.stdout}"
    )


def test_env_is_loaded_without_importing_generate():
    """Regression: `.env` was previously read only as a side effect of importing
    generate.py, so `run_experiment.py --score` (which never imports it) failed
    with 'DEEPINFRA_API_KEY is not set' while the key was present all along.

    Credentials must not depend on unrelated import order."""
    code = (
        "import sys, os; sys.path[:0]=['.','src']; "
        "os.environ.pop('RAGNICE_TEST', None); "
        "import evaluate_ragas; "
        "assert 'generate' not in sys.modules, 'evaluate_ragas pulled in generate'; "
        "import env; assert env._LOADED, '.env was not loaded'; "
        "print('OK')"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                       text=True, cwd=str(ROOT), timeout=120)
    assert r.returncode == 0 and "OK" in r.stdout, (
        f"scoring path does not load .env independently:\n{r.stderr[-800:]}")
