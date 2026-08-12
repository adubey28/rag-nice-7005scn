"""
Environment loading, in one place.

WHY THIS EXISTS
---------------
`.env` was previously loaded as a SIDE EFFECT of importing `generate.py`. That
worked by accident whenever generation ran first, and failed the moment scoring
was run on its own:

    python scripts/run_experiment.py --score
    RuntimeError: DEEPINFRA_API_KEY is not set

The key was present in `.env` the whole time. Nothing imported the module that
happened to read it. Credentials arriving as a side effect of an unrelated
import is a latent fault: it works until the call order changes, then produces
an error that points at the wrong thing entirely.

Every module that reads a credential now calls `load_env()` explicitly. It is
idempotent, so repeated calls cost nothing.
"""

from __future__ import annotations

from pathlib import Path

_LOADED = False


def load_env() -> None:
    global _LOADED
    if _LOADED:
        return
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    _LOADED = True


def require(name: str, hint: str = "") -> str:
    """Fetch a credential, failing with a message that says what to do."""
    import os
    load_env()
    val = os.getenv(name)
    if not val:
        raise RuntimeError(
            f"{name} is not set. Add it to .env in the project root. "
            f"Check the file is named exactly '.env' and not '.env.txt'."
            + (f" {hint}" if hint else "")
        )
    return val
