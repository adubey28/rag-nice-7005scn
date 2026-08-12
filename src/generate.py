"""
Stage 1e — Generation: retrieved context + question -> grounded answer.

Rate limits on the free tier are the practical constraint for the whole
project, so retry-with-backoff is built in from the start rather than bolted on
when the full experiment starts failing at 2am.

The `no_retrieval=True` path is the non-retrieval baseline condition: the same
model, the same temperature, the same question, but answering from parametric
memory alone. Implementing it here — inside the same module, sharing the same
call machinery — is what makes the baseline a fair comparison rather than a
different experiment.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tenacity import (  # noqa: E402
    retry, retry_if_exception, stop_after_attempt, wait_exponential,
)

import config  # noqa: E402
from env import load_env, require  # noqa: E402

load_env()

_CLIENT = None

BASELINE_SYSTEM_PROMPT = (
    "You are a careful research assistant answering questions about UK NICE "
    "clinical guidelines from your own knowledge. Be concise and factual. "
    "If you do not know, say so. This is a research prototype; never present "
    "output as medical advice."
)


def get_client():
    global _CLIENT
    if _CLIENT is None:
        from google import genai

        key = require("GOOGLE_API_KEY",
                      "Get one at https://aistudio.google.com/apikey")
        _CLIENT = genai.Client(api_key=key)
    return _CLIENT


def _config_variants(system_prompt: str, temperature: float, max_tokens: int,
                     model: str) -> list[tuple[str, dict]]:
    """Ordered list of (label, kwargs) generation configs to try.

    WHY A LADDER RATHER THAN A SINGLE CONFIG
    ----------------------------------------
    The Gemini API rejects some field combinations at REQUEST time with
    400 INVALID_ARGUMENT, not at object-construction time. A try/except around
    building the config object therefore cannot catch them - the object builds
    fine and the server refuses it. Each variant below is attempted in order and
    the first accepted one is used; the label of whichever succeeded is recorded
    in the output so the report can state exactly what was sent.

    Field support by model family:
      2.x  temperature accepted; thinking disabled via thinking_budget=0
      3.x  temperature/top_p/top_k deprecated; thinking_budget replaced by
           thinking_level; thinking cannot be fully disabled

    Because 3.x does not honour temperature, generation under 3.x is NOT
    bit-reproducible. That is a stated limitation, not an oversight - see
    generate_answer(), which records `temperature_applied` per call.
    """
    base = {"system_instruction": system_prompt, "max_output_tokens": max_tokens}
    is_v3_plus = any(model.startswith(f"gemini-{n}") for n in (3, 4, 5))

    if is_v3_plus:
        return [
            ("v3_thinking_low", {**base, "_thinking": {"thinking_level": "LOW"}}),
            ("v3_no_thinking", dict(base)),
            ("minimal", {"max_output_tokens": max_tokens}),
        ]
    return [
        ("v2_temp0_nothinking",
         {**base, "temperature": temperature, "_thinking": {"thinking_budget": 0}}),
        ("v2_temp0", {**base, "temperature": temperature}),
        ("v2_plain", dict(base)),
        ("minimal", {"max_output_tokens": max_tokens}),
    ]


def _materialise(kwargs: dict):
    """Turn a variant spec into a GenerateContentConfig, dropping any field the
    installed SDK does not expose."""
    from google.genai import types

    kwargs = dict(kwargs)
    thinking = kwargs.pop("_thinking", None)
    if thinking:
        try:
            kwargs["thinking_config"] = types.ThinkingConfig(**thinking)
        except (TypeError, AttributeError, ValueError):
            pass
    return types.GenerateContentConfig(**kwargs)


def _is_transient(exc: BaseException) -> bool:
    """Retry rate limits and server faults; never retry a rejected argument.

    Retrying a 400 or 404 just burns quota five times before failing anyway, and
    on a free tier that is quota the experiment cannot spare.
    """
    s = str(exc)
    if any(code in s for code in ("400", "404", "INVALID_ARGUMENT", "NOT_FOUND",
                                  "PERMISSION_DENIED")):
        return False
    return any(tok in s for tok in ("429", "500", "502", "503", "504",
                                    "RESOURCE_EXHAUSTED", "UNAVAILABLE",
                                    "DEADLINE_EXCEEDED", "timeout", "Timeout"))


@retry(
    retry=retry_if_exception(_is_transient),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _call_model(prompt: str, system_prompt: str, model: str,
                temperature: float, max_tokens: int) -> tuple[str, str]:
    """Return (answer_text, config_variant_label)."""
    client = get_client()
    errors: list[str] = []

    for label, kwargs in _config_variants(system_prompt, temperature,
                                          max_tokens, model):
        try:
            resp = client.models.generate_content(
                model=model, contents=prompt, config=_materialise(kwargs),
            )
        except Exception as exc:  # noqa: BLE001
            if _is_transient(exc):
                raise                      # let tenacity back off and retry
            errors.append(f"{label}: {type(exc).__name__}: {str(exc)[:160]}")
            continue                       # rejected argument -> try next variant

        text = getattr(resp, "text", None)
        if text:
            return text.strip(), label
        errors.append(f"{label}: empty response ({getattr(resp, 'candidates', None)})")

    raise RuntimeError(
        f"All generation config variants failed for {model}:\n  "
        + "\n  ".join(errors)
    )


def generate_answer(question: str, chunks: list[dict] | None = None,
                    no_retrieval: bool = False,
                    model: str = config.GEN_MODEL,
                    temperature: float = config.GEN_TEMPERATURE,
                    max_tokens: int = config.GEN_MAX_TOKENS) -> dict:
    t0 = time.time()

    if no_retrieval:
        system_prompt = BASELINE_SYSTEM_PROMPT
        prompt = f"Question: {question}\n\nAnswer concisely."
        context = ""
    else:
        if not chunks:
            raise ValueError("chunks required unless no_retrieval=True")
        context = config.format_context(chunks)
        system_prompt = config.SYSTEM_PROMPT
        prompt = config.USER_PROMPT_TEMPLATE.format(context=context,
                                                    question=question)

    answer, variant = _call_model(prompt, system_prompt, model, temperature,
                                  max_tokens)
    temperature_applied = variant.startswith("v2")

    return {
        "question": question,
        "answer": answer,
        "contexts": [c["text"] for c in (chunks or [])],
        # Delivered context volume. Corpus-level mean chunk length is matched by
        # calibration, but retrieval is not random sampling - longer chunks may
        # be retrieved at a different rate than they occur. Recording the actual
        # characters delivered per query lets the volume confound be TESTED
        # against data rather than assumed away, and used as a covariate if the
        # conditions turn out to differ.
        "context_chars": sum(len(c["text"]) for c in (chunks or [])),
        "n_contexts": len(chunks or []),
        "context_chunk_ids": [c["chunk_id"] for c in (chunks or [])],
        "no_retrieval": no_retrieval,
        "model": model,
        "temperature": temperature,
        "temperature_applied": temperature_applied,
        "gen_config_variant": variant,
        "latency_seconds": round(time.time() - t0, 2),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate an answer (baseline mode).")
    ap.add_argument("question")
    ap.add_argument("--no-retrieval", action="store_true",
                    help="Baseline condition: answer without any context.")
    args = ap.parse_args()

    if not args.no_retrieval:
        print("Tip: use src/ask.py for the full retrieval pipeline. "
              "This entry point runs the baseline only.")
    result = generate_answer(args.question, no_retrieval=True)
    print(f"\n{result['answer']}\n")
    print(f"[{result['latency_seconds']}s | {result['model']}]")


if __name__ == "__main__":
    main()
