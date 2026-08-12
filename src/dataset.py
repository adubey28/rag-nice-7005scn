"""
Stage 3 — The evaluation dataset: schema, loading, and validation.

THIS IS THE MEASURING INSTRUMENT
--------------------------------
Every number in the Results chapter is produced by comparing system output
against this dataset. If the dataset is weak, no amount of downstream rigour
recovers the study: a faithfulness score computed against a wrong reference
answer is not a weak measurement, it is a meaningless one. The literature
review already commits you to treating instrument validity as a first-class
methodological concern; this module is where that commitment is cashed out.

The validator below enforces the properties that make the instrument sound, and
refuses to pass a dataset that violates them. It is deliberately strict. Every
error it raises is a defect you would otherwise discover *after* burning your
free-tier quota on an invalid run.

SCHEMA (one JSON object per row, stored as a JSON array in
data/eval/eval_dataset.json)
---------------------------------------------------------------------------
  question_id      str    stable identifier, e.g. "Q001"
  question         str    the question as posed to the system
  question_type    str    "factual" | "comparative" | "multi_step"
  reference_answer str    the correct answer, written from the source text
  gold_passages    list   >=1 evidence passages, each:
                            doc_id     str  e.g. "NG28"
                            passage    str  VERBATIM text from the ingested doc
                            locator    str  human anchor, e.g. "rec 1.6.10"
  notes            str    optional; ambiguities, judgement calls, caveats
  author           str    who wrote it (you)
  verified         bool   set true only after YOU have checked it against source

WHY `passage` MUST BE VERBATIM
------------------------------
The validator locates each passage in `data/interim/<DOC>.json` and converts it
to character spans. Those spans are what `spans.py` turns into the relevance
labels behind precision@k, recall@k and MRR. A paraphrased passage cannot be
located, so it cannot be scored — and a passage that *almost* matches is worse,
because it may resolve to the wrong region and produce confidently wrong
metrics. Copy and paste from `data/interim/<DOC>.txt`; never retype.

WHY MULTI-STEP QUESTIONS NEED MULTIPLE GOLD PASSAGES
----------------------------------------------------
Recall@k's denominator is the number of gold passages a question requires. A
multi-step question with only one recorded passage is silently downgraded to a
factual one, which weakens exactly the condition your design intends to stress.
The validator enforces >= 2 passages for `multi_step`.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from spans import locate_span  # noqa: E402

QUESTION_TYPES = ("factual", "comparative", "multi_step")

EVAL_DIR = config.DATA / "eval"
EVAL_DIR.mkdir(parents=True, exist_ok=True)
DATASET_PATH = EVAL_DIR / "eval_dataset.json"

# Target composition. Not arbitrary: factual questions establish the floor,
# comparative questions stress synthesis within a passage, and multi-step
# questions stress retrieval recall across passages — which is where hybrid
# retrieval (H2) should show an advantage if it has one.
TARGET_COMPOSITION = {"factual": 24, "comparative": 18, "multi_step": 18}
TARGET_TOTAL = 60
MIN_PASSAGE_CHARS = 40


@dataclass
class ValidationIssue:
    question_id: str
    severity: str      # "error" blocks the run; "warning" is advisory
    message: str

    def __str__(self) -> str:
        tag = "ERROR" if self.severity == "error" else "warn "
        return f"  [{tag}] {self.question_id}: {self.message}"


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def load_dataset(path: Path = DATASET_PATH) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"No dataset at {path}. The authored dataset ships in "
            f"data/eval/eval_dataset.json; if it is missing, restore it from the "
            f"project archive rather than regenerating it - it is the measuring "
            f"instrument and cannot be reconstructed automatically."
        )
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Dataset must be a JSON array of question objects.")
    return rows


def load_source_texts(doc_ids: list[str] | None = None) -> dict[str, str]:
    """Load the ingested text for each document, keyed by doc_id."""
    texts: dict[str, str] = {}
    for doc_id in (doc_ids or list(config.CORPUS)):
        p = config.INTERIM / f"{doc_id}.json"
        if p.exists():
            texts[doc_id] = json.loads(p.read_text(encoding="utf-8"))["text"]
    return texts


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def validate_row(row: dict, sources: dict[str, str]) -> list[ValidationIssue]:
    qid = row.get("question_id", "<missing id>")
    issues: list[ValidationIssue] = []

    def err(msg: str) -> None:
        issues.append(ValidationIssue(qid, "error", msg))

    def warn(msg: str) -> None:
        issues.append(ValidationIssue(qid, "warning", msg))

    # --- required fields ---
    for field in ("question_id", "question", "question_type",
                  "reference_answer", "gold_passages"):
        if not row.get(field):
            err(f"missing required field '{field}'")
    if issues:
        return issues

    qtype = row["question_type"]
    if qtype not in QUESTION_TYPES:
        err(f"question_type '{qtype}' not one of {QUESTION_TYPES}")

    # --- question sanity ---
    q = row["question"].strip()
    if len(q) < 15:
        warn("question is very short — likely underspecified")
    if not q.endswith("?"):
        warn("question does not end with '?'")

    ans = row["reference_answer"].strip()
    if len(ans) < 10:
        err("reference_answer is too short to be a real answer")

    # --- gold passages ---
    passages = row["gold_passages"]
    if not isinstance(passages, list) or not passages:
        err("gold_passages must be a non-empty list")
        return issues

    if qtype == "multi_step" and len(passages) < 2:
        err("multi_step questions require >= 2 gold passages (recall@k's "
            "denominator depends on it)")

    for i, g in enumerate(passages):
        tag = f"gold_passages[{i}]"
        doc_id = g.get("doc_id")
        passage = (g.get("passage") or "").strip()

        if doc_id not in config.CORPUS:
            err(f"{tag}: unknown doc_id '{doc_id}'")
            continue
        if doc_id not in sources:
            err(f"{tag}: {doc_id} has not been ingested — run src/ingest.py")
            continue
        if len(passage) < MIN_PASSAGE_CHARS:
            err(f"{tag}: passage under {MIN_PASSAGE_CHARS} chars; too short to "
                f"anchor relevance reliably")
            continue

        # The load-bearing check: can this passage be located verbatim?
        try:
            start, end = locate_span(sources[doc_id], passage)
            g["start_char"], g["end_char"] = start, end
        except ValueError as exc:
            err(f"{tag}: passage NOT FOUND verbatim in {doc_id}. "
                f"Copy-paste from data/interim/{doc_id}.txt rather than "
                f"retyping or paraphrasing. ({exc})")

    # --- verification flag ---
    if not row.get("verified"):
        warn("not yet marked verified — you must check this row against source")

    return issues


def validate_dataset(rows: list[dict],
                     sources: dict[str, str]) -> tuple[list[ValidationIssue], dict]:
    issues: list[ValidationIssue] = []

    ids = [r.get("question_id") for r in rows]
    for qid, n in Counter(ids).items():
        if n > 1:
            issues.append(ValidationIssue(str(qid), "error",
                                          f"duplicate question_id ({n} rows)"))

    seen_questions: dict[str, str] = {}
    for r in rows:
        norm = " ".join((r.get("question") or "").lower().split())
        if norm in seen_questions:
            issues.append(ValidationIssue(
                r.get("question_id", "?"), "warning",
                f"near-duplicate of {seen_questions[norm]} — inflates apparent n"))
        else:
            seen_questions[norm] = r.get("question_id", "?")
        issues.extend(validate_row(r, sources))

    type_counts = Counter(r.get("question_type") for r in rows)
    doc_counts: Counter[str] = Counter()
    for r in rows:
        for g in r.get("gold_passages", []) or []:
            if isinstance(g, dict) and g.get("doc_id"):
                doc_counts[g["doc_id"]] += 1

    summary = {
        "n_rows": len(rows),
        "n_verified": sum(1 for r in rows if r.get("verified")),
        "by_type": dict(type_counts),
        "by_doc": dict(doc_counts),
        "n_errors": sum(1 for i in issues if i.severity == "error"),
        "n_warnings": sum(1 for i in issues if i.severity == "warning"),
    }
    return issues, summary


def resolve_spans(rows: list[dict], sources: dict[str, str]) -> list[dict]:
    """Attach start_char/end_char to every gold passage. Call before evaluation.

    Returns the rows with spans populated; raises if any passage cannot be
    located, because proceeding would produce metrics computed against
    unresolvable evidence.
    """
    issues, _ = validate_dataset(rows, sources)
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        raise ValueError(
            f"{len(errors)} dataset errors — refusing to evaluate against an "
            f"invalid instrument. Run scripts/validate_dataset.py for detail."
        )
    return rows


def gold_spans_for(row: dict) -> list[dict]:
    """Extract the span dicts that spans.py consumes."""
    return [
        {"doc_id": g["doc_id"], "start_char": g["start_char"],
         "end_char": g["end_char"], "locator": g.get("locator", "")}
        for g in row["gold_passages"]
    ]
