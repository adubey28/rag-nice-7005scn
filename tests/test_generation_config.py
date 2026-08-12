"""
Offline tests for the generation config fallback ladder.

CONTEXT
-------
A live test on 5 Aug 2026 established two facts about the Gemini API:

  * `gemini-2.5-flash` is listed by `models.list()` but returns
    404 NOT_FOUND "no longer available to new users" when called. Listing
    membership does not imply callability.
  * `gemini-3.6-flash` rejects `thinking_budget=0` at REQUEST time with
    400 INVALID_ARGUMENT. The config object constructs without error, so a
    try/except around construction cannot catch it.

The second point is why `generate.py` uses a ladder of config variants tried in
order at call time rather than a single config chosen up front. These tests fake
the client so the ladder's behaviour is verified without spending free-tier
quota or requiring an API key.

Run:  python -m pytest tests/test_generation_config.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config  # noqa: E402
import generate  # noqa: E402


class FakeResponse:
    def __init__(self, text): self.text = text
    candidates = None


class FakeModels:
    """Rejects any config whose label is in `reject`, by inspecting the payload."""

    def __init__(self, reject_thinking=False, reject_temperature=False,
                 not_found=False):
        self.reject_thinking = reject_thinking
        self.reject_temperature = reject_temperature
        self.not_found = not_found
        self.calls: list[dict] = []

    def generate_content(self, model, contents, config):  # noqa: A002
        has_thinking = getattr(config, "thinking_config", None) is not None
        has_temp = getattr(config, "temperature", None) is not None
        self.calls.append({"model": model, "thinking": has_thinking,
                           "temperature": has_temp})

        if self.not_found:
            raise RuntimeError("404 NOT_FOUND: no longer available to new users")
        if self.reject_thinking and has_thinking:
            raise RuntimeError("400 INVALID_ARGUMENT: Request contains an "
                               "invalid argument.")
        if self.reject_temperature and has_temp:
            raise RuntimeError("400 INVALID_ARGUMENT: temperature not supported")
        return FakeResponse("Metformin.")


class FakeClient:
    def __init__(self, models): self.models = models


@pytest.fixture(autouse=True)
def _no_real_client(monkeypatch):
    """Guarantee no test can reach the network."""
    monkeypatch.setattr(generate, "_CLIENT", None, raising=False)


def _install(monkeypatch, fake_models):
    monkeypatch.setattr(generate, "get_client",
                        lambda: FakeClient(fake_models))


# --------------------------------------------------------------------------

def test_ladder_falls_through_when_thinking_rejected(monkeypatch):
    """The exact failure seen live on gemini-3.6-flash."""
    models = FakeModels(reject_thinking=True)
    _install(monkeypatch, models)

    text, variant = generate._call_model(
        "q", "sys", "gemini-3.6-flash", 0.0, 256)

    assert text == "Metformin."
    assert variant == "v3_no_thinking", "should have advanced past the rejected variant"
    assert models.calls[0]["thinking"] is True, "first attempt should try thinking_level"
    assert models.calls[1]["thinking"] is False, "second attempt should drop it"


def test_first_variant_used_when_accepted(monkeypatch):
    """No unnecessary extra calls: quota is the binding constraint."""
    models = FakeModels()
    _install(monkeypatch, models)

    _, variant = generate._call_model("q", "sys", "gemini-3.6-flash", 0.0, 256)
    assert variant == "v3_thinking_low"
    assert len(models.calls) == 1


def test_v3_never_sends_temperature(monkeypatch):
    """3.x deprecated temperature. Sending it anyway would imply a determinism
    guarantee the API does not honour."""
    models = FakeModels()
    _install(monkeypatch, models)

    generate._call_model("q", "sys", "gemini-3.6-flash", 0.0, 256)
    assert all(c["temperature"] is False for c in models.calls)


def test_v2_model_sends_temperature(monkeypatch):
    """A 2.x model must still receive temperature=0 if one is ever reinstated."""
    models = FakeModels()
    _install(monkeypatch, models)

    _, variant = generate._call_model("q", "sys", "gemini-2.5-flash", 0.0, 256)
    assert variant == "v2_temp0_nothinking"
    assert models.calls[0]["temperature"] is True


def test_404_is_not_retried_and_surfaces_clearly(monkeypatch):
    """Retrying a decommissioned model wastes five calls of free-tier quota and
    then fails anyway."""
    models = FakeModels(not_found=True)
    _install(monkeypatch, models)

    with pytest.raises(RuntimeError) as exc:
        generate._call_model("q", "sys", "gemini-2.5-flash", 0.0, 256)

    assert "All generation config variants failed" in str(exc.value)
    assert len(models.calls) <= 4, "404 must not trigger tenacity retries"


@pytest.mark.parametrize("message,expected", [
    ("429 RESOURCE_EXHAUSTED", True),
    ("503 UNAVAILABLE", True),
    ("504 DEADLINE_EXCEEDED", True),
    ("400 INVALID_ARGUMENT", False),
    ("404 NOT_FOUND", False),
    ("PERMISSION_DENIED", False),
])
def test_transient_classification(message, expected):
    assert generate._is_transient(RuntimeError(message)) is expected


def test_temperature_applied_flag_is_honest(monkeypatch):
    """The output record must not claim temperature was applied when the model
    silently ignored it - that would misrepresent reproducibility in the report."""
    models = FakeModels()
    _install(monkeypatch, models)
    monkeypatch.setattr(config, "GEN_MODEL", "gemini-3.6-flash")

    result = generate.generate_answer("q", no_retrieval=True,
                                      model="gemini-3.6-flash")
    assert result["temperature_applied"] is False
    assert result["gen_config_variant"] == "v3_thinking_low"
