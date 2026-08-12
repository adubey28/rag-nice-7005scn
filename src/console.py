"""
Console encoding safety.

Windows consoles default to cp1252, which cannot encode characters that occur in
NICE guideline text or in box-drawing output. Printing then raises
UnicodeEncodeError and aborts the run - a display-layer fault that looks like a
pipeline failure and, worse, can abort a script AFTER the real work succeeded.

This bit us twice: once in ask.py (fixed) and again in validate_dataset.py,
which crashed while printing a coverage bar despite the validation itself having
passed. Centralising the fix means it cannot recur script by script.

Call `safe_stdout()` at the top of any script that prints.
"""

from __future__ import annotations

import sys


def safe_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, ValueError):
                pass
