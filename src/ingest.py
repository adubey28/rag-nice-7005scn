"""
Stage 1a - Ingestion: NICE guideline -> cleaned plain text -> JSON record.

WHY THIS MODULE MATTERS MOST
----------------------------
Every downstream measurement inherits the quality of this step. If extraction
leaves running headers, page numbers and copyright boilerplate scattered through
the text then fixed-size chunks are polluted at unpredictable positions, and
semantic chunking - which detects meaning shifts between adjacent sentences - is
actively misled by that noise. The H1 comparison would then be confounded by an
artefact of extraction rather than driven by the chunking strategies. So the
cleaning here is conservative, auditable, and writes a .txt for human review.

INPUT FORMAT VERIFICATION
-------------------------
All four corpus documents are PDF 1.7. `load_pages()` nonetheless verifies the
%PDF magic number rather than trusting the file extension, and records the
detected format in `source_format`. This is a defensive guard, not a workaround:
a corpus file replaced by a different format would otherwise either fail deep in
the pipeline with an opaque error, or - worse - be parsed incorrectly without
failing at all, silently corrupting every downstream measurement. Recording the
format per document means the corpus cannot become heterogeneous without it
appearing in the provenance record.

THREE-LAYER CLEANING
--------------------
1. Normalisation. Line endings unified; U+0002 is stripped. That control
   character appears in some PDF text layers where the source had a soft hyphen
   ("terms-and<0x02>conditions"), and left in place it corrupts tokenisation
   for BM25.

2. Structural furniture removal by pattern. Every NICE page ends with the same
   block:

       <Guideline title> (NG28)
       (c) NICE 2026. All rights reserved. Subject to Notice of rights (...).
       Page 16 of
       131

   Frequency-based detection alone cannot remove this, because the page number
   differs on every page, so the lines are not exact repeats. _NICE_FOOTER
   matches the whole block including the varying number.

3. Frequency-based furniture removal for whatever remains. Any short line
   appearing on more than repeat_threshold of pages is treated as furniture.
   This generalises across all four guidelines with no per-document rules,
   which is less brittle and easier to justify than hard-coded strings.

Provenance (publication date, last-updated date, SHA-256) is captured
automatically. NICE guidelines are revised; without those facts the study is not
reproducible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from console import safe_stdout  # noqa: E402

safe_stdout()


# --------------------------------------------------------------------------
# Loading - format detection
# --------------------------------------------------------------------------

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def load_pages(path: Path) -> tuple[list[str], str]:
    """Return (pages, source_format).

    Sniffs the file rather than trusting the extension: one of the four corpus
    files is plain text despite being named .pdf.
    """
    with open(path, "rb") as f:
        magic = f.read(5)

    if magic == b"%PDF-":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return [(p.extract_text() or "") for p in reader.pages], "pdf"

    # Fallback for a plain-text source: recover page structure by splitting on
    # blank lines, which the frequency-based furniture detector requires.
    raw = path.read_bytes().decode("utf-8", errors="replace")
    pages = [p for p in raw.split("\n\n") if p.strip()]
    return pages, "plain_text"


# --------------------------------------------------------------------------
# Layer 1: normalisation
# --------------------------------------------------------------------------

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# Unicode punctuation observed in the real NICE PDFs, mapped to ASCII.
#
# WHY THIS MATTERS MORE THAN IT LOOKS
# -----------------------------------
# These characters are visually indistinguishable from an ordinary hyphen but
# are different codepoints, and they sit inside exactly the terms that matter:
#   U+2011 NON-BREAKING HYPHEN   SGLT-2, DPP-4, GLP-1, 10-year, mono-unsaturated
#   U+2013 EN DASH               sodium-glucose, African-Caribbean
#   U+FF0D FULLWIDTH HYPHEN      NICE's second-level bullet marker
#
# BM25 matches literal tokens. A query containing "SGLT-2" with an ordinary
# hyphen will NOT match a corpus containing "SGLT\u20112", so the sparse half of
# hybrid retrieval fails on precisely the rare clinical terms where it should
# outperform dense retrieval. Left unfixed this would silently depress H2.
#
# It also protects the evaluation dataset: a gold passage copied from the source
# and retyped with an ordinary hyphen would fail verbatim location, producing
# confusing validation errors during authoring.
#
# Every mapping is 1:1, so character offsets and document length are unchanged
# and the [start_char, end_char) invariant is preserved by construction.
_PUNCT_MAP = {
    "\u2011": "-",   # non-breaking hyphen
    "\u2012": "-",   # figure dash
    "\u2013": "-",   # en dash
    "\u2014": "-",   # em dash
    "\u2212": "-",   # minus sign
    "\uff0d": "-",   # fullwidth hyphen-minus (NICE sub-bullet)
    "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"',
    "\u00a0": " ",   # non-breaking space
}
_PUNCT_RE = re.compile("[" + "".join(_PUNCT_MAP) + "]")


def normalise_punctuation(text: str) -> str:
    """Map Unicode punctuation to ASCII. Strictly 1:1 - offsets are preserved."""
    return _PUNCT_RE.sub(lambda m: _PUNCT_MAP[m.group()], text)


def normalise(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u0002", "").replace("\u00ad", "")
    text = normalise_punctuation(text)
    return _CTRL.sub("", text)


# --------------------------------------------------------------------------
# Layer 2: structural furniture (NICE-specific, pattern-based)
# --------------------------------------------------------------------------

_NICE_FOOTER = re.compile(
    r"[^\n]*\(NG\d+\)\s*\n"
    r"\u00a9?\s*NICE\s+\d{4}\.\s*All rights reserved\..*?"
    r"Page\s+\d+\s+of\s*\n?\s*\d+",
    re.DOTALL | re.IGNORECASE,
)

_NICE_COPYRIGHT = re.compile(
    r"\u00a9?\s*NICE\s+\d{4}\.\s*All rights reserved\.\s*"
    r"Subject to Notice of rights[^\n]*"
    r"(\n[^\n]*conditions#notice-of-rights\)\.)?",
    re.IGNORECASE,
)

_PAGE_OF = re.compile(r"\bPage\s+\d+\s+of\s*\n?\s*\d+", re.IGNORECASE)


def strip_structural_furniture(text: str) -> tuple[str, int]:
    n = len(_NICE_FOOTER.findall(text))
    text = _NICE_FOOTER.sub("\n", text)
    text = _NICE_COPYRIGHT.sub("", text)
    text = _PAGE_OF.sub("", text)
    return text, n


# --------------------------------------------------------------------------
# Layer 3: frequency-based furniture
# --------------------------------------------------------------------------

def find_furniture(pages: list[str], repeat_threshold: float = 0.5,
                   max_len: int = 120) -> set[str]:
    counts: Counter[str] = Counter()
    for page in pages:
        seen = set()
        for line in page.splitlines():
            s = line.strip()
            if s and len(s) <= max_len:
                seen.add(s)
        counts.update(seen)
    cutoff = max(2, int(len(pages) * repeat_threshold))
    return {line for line, n in counts.items() if n >= cutoff}


_PAGE_NUM = re.compile(r"^(page\s+)?\d+(\s+of\s+\d+)?$", re.I)
_BULLET = re.compile(r"^[\u2022\u25AA\u25E6\u00b7]\s*")


def clean_page(text: str, furniture: set[str]) -> str:
    kept = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            kept.append("")
            continue
        if s in furniture or _PAGE_NUM.match(s):
            continue
        kept.append(_BULLET.sub("- ", s))
    return "\n".join(kept)


# --------------------------------------------------------------------------
# Reflow
# --------------------------------------------------------------------------

_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
_MULTI_BLANK = re.compile(r"\n{3,}")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")


def reflow(text: str) -> str:
    """Rejoin lines broken mid-sentence, preserving block structure.

    NICE recommendations are numbered (1.6.10) and those identifiers are the
    anchors used to trace reference answers back to source, so a line beginning
    a numbered recommendation, a list item, or a short heading starts a new
    block rather than being glued to the previous sentence.
    """
    text = _HYPHEN_BREAK.sub(r"\1\2", text)

    out: list[str] = []
    buffer = ""

    def flush() -> None:
        nonlocal buffer
        if buffer.strip():
            out.append(_MULTI_SPACE.sub(" ", buffer.strip()))
        buffer = ""

    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            flush()
            continue
        starts_block = bool(
            re.match(r"^\d+(\.\d+)+\b", line)
            or re.match(r"^-\s", line)
            or re.match(r"^[A-Z][A-Za-z ,\u0027&/()-]{2,60}$", line)
        )
        if starts_block and buffer:
            flush()
        buffer = f"{buffer} {line}".strip() if buffer else line

    flush()
    return _MULTI_BLANK.sub("\n\n", "\n\n".join(out))


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------

_PUBLISHED = re.compile(r"Published:\s*([0-9]{1,2}\s+\w+\s+[0-9]{4})", re.I)
_UPDATED = re.compile(r"Last updated:\s*([0-9]{1,2}\s+\w+\s+[0-9]{4})", re.I)


def extract_provenance(head: str) -> dict:
    pub = _PUBLISHED.search(head)
    upd = _UPDATED.search(head)
    return {
        "nice_published": pub.group(1) if pub else None,
        "nice_last_updated": upd.group(1) if upd else None,
    }


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def ingest(doc_id: str, overwrite: bool = False, quiet: bool = False) -> dict:
    meta = config.CORPUS[doc_id]
    pdf_path = config.RAW / meta["filename"]
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"Expected {pdf_path}. Download from {meta['url']} using the "
            f"'Download guidance (PDF)' link and save with that exact filename."
        )

    out_json = config.INTERIM / f"{doc_id}.json"
    out_txt = config.INTERIM / f"{doc_id}.txt"
    if out_json.exists() and not overwrite:
        if not quiet:
            print(f"[ingest] {doc_id}: already ingested (--overwrite to redo)")
        return json.loads(out_json.read_text(encoding="utf-8"))

    raw_pages, source_format = load_pages(pdf_path)
    n_chars_raw = sum(len(p) for p in raw_pages)

    pages = [normalise(p) for p in raw_pages]
    provenance = extract_provenance("\n".join(pages[:2]))

    stripped, n_footers = [], 0
    for p in pages:
        cleaned, n = strip_structural_furniture(p)
        stripped.append(cleaned)
        n_footers += n

    furniture = find_furniture(stripped)
    cleaned_pages = [clean_page(p, furniture) for p in stripped]
    text = reflow("\n\n".join(cleaned_pages))

    record = {
        "doc_id": doc_id,
        "title": meta["title"],
        "url": meta["url"],
        "source_file": meta["filename"],
        "source_format": source_format,
        "sha256": sha256_of(pdf_path),
        "n_pages": len(raw_pages),
        "n_chars_raw": n_chars_raw,
        "n_chars_clean": len(text),
        "pct_retained": round(100 * len(text) / max(1, n_chars_raw), 1),
        "n_structural_footers_removed": n_footers,
        "n_furniture_lines_removed": len(furniture),
        **provenance,
        "ingested_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "text": text,
    }

    out_json.write_text(json.dumps(record, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    out_txt.write_text(text, encoding="utf-8")

    if not quiet:
        print(f"[ingest] {doc_id} ({source_format}): {record['n_pages']} pages, "
              f"{n_chars_raw:,} -> {len(text):,} chars "
              f"({record['pct_retained']}% retained)")
        print(f"[ingest]   structural footers removed: {n_footers} | "
              f"repeated lines removed: {len(furniture)}")
        print(f"[ingest]   NICE published {provenance['nice_published']} | "
              f"last updated {provenance['nice_last_updated']}")
        print(f"[ingest]   sha256 {record['sha256'][:16]}...")
    return record


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest NICE guidelines.")
    ap.add_argument("--docs", nargs="+", default=config.STAGE1_DOCS)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    for doc_id in args.docs:
        ingest(doc_id, overwrite=args.overwrite)
        print()


if __name__ == "__main__":
    main()
