"""
Tests for the retrieval metrics.

Every expected value here is computed BY HAND in the test name or comment, not
by running the code and recording whatever it produced. A metrics test that
asserts the code agrees with itself proves nothing; these assert the code agrees
with the definition.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from metrics_retrieval import (  # noqa: E402
    aggregate, by_question_type, evaluate_question, precision_at_k,
    recall_at_k, reciprocal_rank,
)


def chunk(doc: str, start: int, end: int) -> dict:
    return {"doc_id": doc, "start_char": start, "end_char": end,
            "chunk_id": f"{doc}:{start}", "text": "x" * (end - start)}


def gold(doc: str, start: int, end: int) -> dict:
    return {"doc_id": doc, "start_char": start, "end_char": end}


# --------------------------------------------------------------------------
# precision@k
# --------------------------------------------------------------------------

def test_precision_all_relevant_is_one():
    retrieved = [chunk("NG28", 0, 500), chunk("NG28", 400, 900)]
    g = [gold("NG28", 100, 800)]
    assert precision_at_k(retrieved, g, k=2) == 1.0


def test_precision_two_of_four_relevant_is_half():
    retrieved = [chunk("NG28", 0, 500), chunk("NG28", 5000, 5500),
                 chunk("NG28", 400, 900), chunk("NG28", 9000, 9500)]
    g = [gold("NG28", 100, 800)]
    assert precision_at_k(retrieved, g, k=4) == 0.5


def test_precision_denominator_is_k_not_length():
    """A retriever returning one lucky hit must not beat one returning five
    with four hits. Denominator is k."""
    retrieved = [chunk("NG28", 0, 500)]
    g = [gold("NG28", 100, 800)]
    assert precision_at_k(retrieved, g, k=5) == pytest.approx(0.2)


def test_precision_ignores_cross_document_overlap():
    """Identical offsets in a DIFFERENT guideline must not count. Without the
    doc_id check, chunks would appear relevant purely by coincidence of
    position, inflating every score."""
    retrieved = [chunk("NG136", 100, 800)]
    g = [gold("NG28", 100, 800)]
    assert precision_at_k(retrieved, g, k=1) == 0.0


def test_precision_rejects_trivial_overlap():
    """A 10-character brush against a gold span is not relevance."""
    retrieved = [chunk("NG28", 790, 1200)]     # overlaps gold by 10 chars
    g = [gold("NG28", 100, 800)]
    assert precision_at_k(retrieved, g, k=1, min_overlap_chars=50) == 0.0


# --------------------------------------------------------------------------
# recall@k  (passage-level, not chunk-level)
# --------------------------------------------------------------------------

def test_recall_one_of_two_gold_passages_is_half():
    retrieved = [chunk("NG28", 0, 500)]
    g = [gold("NG28", 100, 400), gold("NG136", 100, 400)]
    assert recall_at_k(retrieved, g, k=5) == 0.5


def test_recall_both_passages_found_is_one():
    retrieved = [chunk("NG28", 0, 500), chunk("NG136", 0, 500)]
    g = [gold("NG28", 100, 400), gold("NG136", 100, 400)]
    assert recall_at_k(retrieved, g, k=5) == 1.0


def test_recall_is_passage_level_not_chunk_level():
    """Three chunks all covering the SAME single gold passage is recall 1.0,
    not 3.0. If recall counted chunks, smaller chunks would score higher purely
    by being smaller - and chunk size is a variable under test, so that would
    confound H1 directly."""
    retrieved = [chunk("NG28", 100, 300), chunk("NG28", 250, 450),
                 chunk("NG28", 400, 600)]
    g = [gold("NG28", 100, 600)]
    assert recall_at_k(retrieved, g, k=3) == 1.0


def test_recall_respects_k_cutoff():
    """A gold passage found only at rank 6 must not count at k=5."""
    retrieved = [chunk("NG28", 9000 + i * 100, 9100 + i * 100) for i in range(5)]
    retrieved.append(chunk("NG28", 100, 400))
    g = [gold("NG28", 100, 400)]
    assert recall_at_k(retrieved, g, k=5) == 0.0
    assert recall_at_k(retrieved, g, k=6) == 1.0


# --------------------------------------------------------------------------
# reciprocal rank
# --------------------------------------------------------------------------

@pytest.mark.parametrize("position,expected", [(0, 1.0), (1, 0.5), (2, 1 / 3), (3, 0.25)])
def test_reciprocal_rank_by_position(position, expected):
    retrieved = [chunk("NG28", 9000 + i * 100, 9050 + i * 100) for i in range(5)]
    retrieved[position] = chunk("NG28", 100, 400)
    g = [gold("NG28", 100, 400)]
    assert reciprocal_rank(retrieved, g) == pytest.approx(expected)


def test_reciprocal_rank_zero_when_nothing_relevant():
    retrieved = [chunk("NG28", 9000, 9500)]
    g = [gold("NG28", 100, 400)]
    assert reciprocal_rank(retrieved, g) == 0.0


# --------------------------------------------------------------------------
# aggregation
# --------------------------------------------------------------------------

def test_aggregate_means_and_hit_rate():
    per_q = [
        {"precision@5": 0.4, "recall@5": 1.0, "reciprocal_rank": 1.0, "hit": True},
        {"precision@5": 0.2, "recall@5": 0.5, "reciprocal_rank": 0.5, "hit": True},
        {"precision@5": 0.0, "recall@5": 0.0, "reciprocal_rank": 0.0, "hit": False},
    ]
    agg = aggregate(per_q, k=5)
    assert agg["n_questions"] == 3
    assert agg["precision@5"] == pytest.approx(0.2)          # (0.4+0.2+0)/3
    assert agg["recall@5"] == pytest.approx(0.5)             # (1+0.5+0)/3
    assert agg["mrr"] == pytest.approx(0.5)                  # (1+0.5+0)/3
    assert agg["hit_rate"] == pytest.approx(2 / 3)
    assert agg["precision@5_sd"] > 0


def test_aggregate_empty_is_empty_not_crash():
    assert aggregate([], k=5) == {}


def test_by_question_type_splits_correctly():
    per_q = [
        {"precision@5": 1.0, "recall@5": 1.0, "reciprocal_rank": 1.0, "hit": True},
        {"precision@5": 0.0, "recall@5": 0.0, "reciprocal_rank": 0.0, "hit": False},
    ]
    out = by_question_type(per_q, ["factual", "multi_step"], k=5)
    assert set(out) == {"factual", "multi_step"}
    assert out["factual"]["recall@5"] == 1.0
    assert out["multi_step"]["recall@5"] == 0.0


# --------------------------------------------------------------------------
# end-to-end shape
# --------------------------------------------------------------------------

def test_evaluate_question_returns_expected_keys():
    retrieved = [chunk("NG28", 0, 500), chunk("NG28", 9000, 9500)]
    g = [gold("NG28", 100, 400), gold("NG136", 0, 300)]
    out = evaluate_question(retrieved, g, k=5)
    assert out["precision@5"] == pytest.approx(0.2)   # 1 relevant of k=5
    assert out["recall@5"] == 0.5                     # 1 of 2 gold passages
    assert out["reciprocal_rank"] == 1.0              # relevant chunk at rank 1
    assert out["n_gold_passages"] == 2
    assert out["hit"] is True
