"""
Regression test: .env must load regardless of which entry point runs.

THE BUG THIS PREVENTS
---------------------
`load_dotenv()` originally lived only in `src/generate.py`. Running
`run_experiment.py --all` imports generate as a side effect, so the environment
was loaded by accident. Running `--score` alone never imports it, so the judge
API key was invisible and the scoring phase could not be resumed independently -
despite the key being correctly set on disk.

The failure mode is nasty: it presents as a missing credential, sending you to
check .env, which looks fine. It only appears when scoring is resumed on its
own, which is exactly what a long interrupted run requires.

Fixed by loading .env in config.py, which every entry point imports.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(code: str, env_body: str) -> subprocess.CompletedProcess:
    """Run `code` in a subprocess against a temporary .env, without importing
    the generation module."""
    with tempfile.TemporaryDirectory() as td:
        envfile = Path(td) / ".env"
        envfile.write_text(env_body, encoding="utf-8")
        real = ROOT / ".env"
        backup = real.read_text(encoding="utf-8") if real.exists() else None
        real.write_text(env_body, encoding="utf-8")
        try:
            return subprocess.run(
                [sys.executable, "-c", code], capture_output=True, text=True,
                cwd=str(ROOT), timeout=120)
        finally:
            if backup is None:
                real.unlink(missing_ok=True)
            else:
                real.write_text(backup, encoding="utf-8")


def test_env_loads_from_config_alone():
    """Importing config must be sufficient - no generate.py import required."""
    r = _run(
        "import sys, os; sys.path[:0]=['.','src']\n"
        "import config\n"
        "assert 'generate' not in sys.modules, 'generate.py was imported'\n"
        "print(os.getenv('SENTINEL_KEY'))",
        "SENTINEL_KEY=sentinel-value-9f3a\n")
    assert r.returncode == 0, r.stderr
    assert "sentinel-value-9f3a" in r.stdout, (
        "config.py did not load .env; environment availability still depends on "
        f"import order. stdout={r.stdout!r} stderr={r.stderr[-300:]!r}")


def test_judge_key_visible_to_scoring_path():
    """The scoring entry point must see the judge key without generation."""
    r = _run(
        "import sys, os; sys.path[:0]=['.','src']\n"
        "import config\n"
        "var = config.JUDGE_API_KEY_ENV[config.JUDGE_PROVIDER]\n"
        "print(var, bool(os.getenv(var)))",
        "DEEPINFRA_API_KEY=test-key\nOPENAI_API_KEY=test-key\n")
    assert r.returncode == 0, r.stderr
    assert "True" in r.stdout, (
        f"judge key not visible to the scoring path: {r.stdout!r}")
