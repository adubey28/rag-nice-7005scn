"""
Offline tests for the experiment runner: conditions, caching, metrics.

No API key, no network, no quota. The generator and retriever are faked so the
runner's own logic - cache hit/miss, atomic writes, metric wiring, baseline
handling - is exercised deterministically.

Run:  python -m pytest tests/test_experiment.py -v
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config  # noqa: E402
import experiment as exp  # noqa: E402


@pytest.fixture
def workspace(monkeypatch):
    tmp = Path(tempfile.mkdtemp(prefix="ragnice_exp_"))
    monkeypatch.setattr(exp, "CACHE_DIR", tmp / "cache")
    exp.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


ROWS = [
    {"question_id": "Q001", "question": "What is the HbA1c target?",
     "question_type": "factual", "reference_answer": "48 mmol/mol.",
     "gold_passages": [{"doc_id": "NG28", "passage": "x", "locator": "1.5.7",
                        "start_char": 1000, "end_char": 1200}]},
    {"question_id": "Q002", "question": "Compare two targets.",
     "question_type": "multi_step", "reference_answer": "They differ.",
     "gold_passages": [
         {"doc_id": "NG28", "passage": "x", "locator": "a",
          "start_char": 1000, "end_char": 1200},
         {"doc_id": "NG136", "passage": "y", "locator": "b",
          "start_char": 5000, "end_char": 5200}]},
]


class FakeRetriever:
    """Returns one chunk overlapping the first gold span, one that does not."""

    def __init__(self): self.calls = 0

    def search(self, question, top_k):
        self.calls += 1
        return [
            {"chunk_id": "NG28:fixed:00001", "doc_id": "NG28",
             "start_char": 950, "end_char": 1300, "rank": 1, "score": 0.9,
             "text": "relevant text"},
            {"chunk_id": "NG28:fixed:00099", "doc_id": "NG28",
             "start_char": 90000, "end_char": 90500, "rank": 2, "score": 0.4,
             "text": "irrelevant text"},
        ][:top_k]


def _install(monkeypatch, gen_counter):
    def fake_generate(question, chunks=None, no_retrieval=False, **kw):
        gen_counter.append(question)
        ctx = [c["text"] for c in (chunks or [])]
        return {"answer": f"answer to {question}", "contexts": ctx,
                "context_chars": sum(len(c) for c in ctx),
                "latency_seconds": 0.1, "gen_config_variant": "v3_thinking_low",
                "temperature_applied": False}

    monkeypatch.setitem(sys.modules, "generate",
                        type(sys)("generate"))
    sys.modules["generate"].generate_answer = fake_generate
    retriever = FakeRetriever()
    fake_retrieve = type(sys)("retrieve")
    fake_retrieve.get_retriever = lambda *a, **k: retriever
    monkeypatch.setitem(sys.modules, "retrieve", fake_retrieve)
    return retriever


def test_conditions_are_the_five_specified():
    conds = exp.core_conditions(top_k=5)
    names = [c.name() for c in conds]
    assert names == ["fixed_dense_k5", "fixed_hybrid_k5",
                     "semantic_dense_k5", "semantic_hybrid_k5",
                     "baseline_noretrieval"]


def test_topk_sweep_varies_only_k():
    best = config.RunConfig(chunking="semantic", retrieval="hybrid", top_k=5)
    sweep = exp.topk_sweep(best, ks=(3, 5, 10))
    assert [c.top_k for c in sweep] == [3, 5, 10]
    assert {c.chunking for c in sweep} == {"semantic"}
    assert {c.retrieval for c in sweep} == {"hybrid"}


def test_second_run_uses_cache_and_calls_no_api(workspace, monkeypatch):
    """The core guarantee: a resumed run must not regenerate, because Gemini 3.x
    is not deterministic and a regenerated answer would not match the score
    already computed against the previous one."""
    calls = []
    _install(monkeypatch, calls)
    cfg = config.RunConfig(chunking="fixed", retrieval="dense", top_k=2)

    first = exp.run_condition(cfg, ROWS, progress=False)
    assert len(calls) == 2
    assert all(not r.from_cache for r in first)

    second = exp.run_condition(cfg, ROWS, progress=False)
    assert len(calls) == 2, "cache miss: the API was called again"
    assert all(r.from_cache for r in second)
    assert [r.answer for r in first] == [r.answer for r in second]


def test_cache_write_is_atomic(workspace, monkeypatch):
    """No .tmp files may survive; a half-written cache entry read back as JSON
    would silently corrupt a resumed run."""
    calls = []
    _install(monkeypatch, calls)
    cfg = config.RunConfig(chunking="fixed", retrieval="dense", top_k=2)
    exp.run_condition(cfg, ROWS, progress=False)
    assert list(exp.CACHE_DIR.glob("*.tmp")) == []
    assert len(list(exp.CACHE_DIR.glob("*.json"))) == 2


def test_corrupt_cache_entry_is_regenerated(workspace, monkeypatch):
    calls = []
    _install(monkeypatch, calls)
    cfg = config.RunConfig(chunking="fixed", retrieval="dense", top_k=2)
    exp.run_condition(cfg, ROWS, progress=False)
    for p in exp.CACHE_DIR.glob("*.json"):
        p.write_text("{ not valid json", encoding="utf-8")
    exp.run_condition(cfg, ROWS, progress=False)
    assert len(calls) == 4, "corrupt cache should force regeneration"


def test_retrieval_metrics_computed_from_spans(workspace, monkeypatch):
    calls = []
    _install(monkeypatch, calls)
    cfg = config.RunConfig(chunking="fixed", retrieval="dense", top_k=2)
    res = exp.run_condition(cfg, ROWS, progress=False)

    q1 = res[0]
    assert q1.precision_at_k == pytest.approx(0.5), "1 of 2 retrieved overlaps gold"
    assert q1.recall_at_k == pytest.approx(1.0), "its single gold span is covered"
    assert q1.reciprocal_rank == pytest.approx(1.0), "relevant chunk is rank 1"

    q2 = res[1]
    assert q2.recall_at_k == pytest.approx(0.5), "only 1 of 2 gold spans covered"


def test_baseline_has_no_retrieval_metrics(workspace, monkeypatch):
    """Precision/recall/MRR are undefined without retrieval. Reporting 0.0 would
    be a category error - it would read as 'retrieved nothing relevant' rather
    than 'did not retrieve'."""
    calls = []
    _install(monkeypatch, calls)
    cfg = config.RunConfig(chunking="none", retrieval="none", top_k=0)
    res = exp.run_condition(cfg, ROWS, progress=False)

    assert all(r.precision_at_k is None for r in res)
    assert all(r.recall_at_k is None for r in res)
    assert all(r.reciprocal_rank is None for r in res)
    assert all(r.contexts == [] for r in res)


def test_conditions_do_not_share_cache(workspace, monkeypatch):
    """Two conditions asking the same question must not collide, or one would
    silently inherit the other's answers."""
    calls = []
    _install(monkeypatch, calls)
    a = config.RunConfig(chunking="fixed", retrieval="dense", top_k=2)
    b = config.RunConfig(chunking="semantic", retrieval="dense", top_k=2)
    exp.run_condition(a, ROWS, progress=False)
    exp.run_condition(b, ROWS, progress=False)
    assert len(calls) == 4, "different conditions shared a cache key"


def test_summarise_splits_by_question_type(workspace, monkeypatch):
    calls = []
    _install(monkeypatch, calls)
    cfg = config.RunConfig(chunking="fixed", retrieval="dense", top_k=2)
    s = exp.summarise(exp.run_condition(cfg, ROWS, progress=False))
    assert s["overall"]["n"] == 2
    assert s["factual"]["n"] == 1
    assert s["multi_step"]["n"] == 1
    assert s["multi_step"]["recall_at_k"] == pytest.approx(0.5)


def test_budget_estimate_scales_and_reports_cost():
    from evaluate_ragas import estimate_budget

    small = estimate_budget(60, 5, include_llm_context=False)
    large = estimate_budget(60, 5, include_llm_context=True)
    assert large["total_tokens_estimated"] > small["total_tokens_estimated"]
    assert large["estimated_cost_usd"] > small["estimated_cost_usd"]
    assert small["provider"] == config.JUDGE_PROVIDER
    assert small["judge_model"] == config.JUDGE_MODEL


def test_no_groq_in_runtime_config():
    """Groq was removed on 7 Aug 2026. A stale reference in live config would
    surface as a confusing missing-key warning or an import error mid-run."""
    assert "groq" not in config.JUDGE_MODELS
    assert "groq" not in config.JUDGE_API_KEY_ENV
    assert config.JUDGE_PROVIDER in config.JUDGE_MODELS
    assert config.JUDGE_MODEL == config.JUDGE_MODELS[config.JUDGE_PROVIDER]
