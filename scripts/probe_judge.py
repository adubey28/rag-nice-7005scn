"""
Probe the judge endpoint. Costs a fraction of a cent; takes under a minute.

WHY THIS EXISTS
---------------
When scoring stops advancing, the console gives you nothing to work with:
`ragas.evaluate()` is called with `show_progress=False`, and its internal retry
ladder has `log_tenacity=False`, so a call that is being retried ten times over
half an hour prints not one character.

This probe separates the two layers, in order, so the failure is attributed to
the right one:

    Layer 1  raw OpenAI-compatible POST to DeepInfra
             -> is the endpoint reachable, is the key valid, how slow is it?
    Layer 2  one full ragas faithfulness evaluation on a fixed sample
             -> does the ragas wrapper produce a real number?

If layer 1 passes and layer 2 returns NaN, the fault is in the ragas layer.
If layer 1 is slow or 429s, the fault is the provider and no code change fixes it.

Run:
    python scripts/probe_judge.py
    python scripts/probe_judge.py --timeout 30 --retries 1
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config  # noqa: E402
from console import safe_stdout  # noqa: E402

safe_stdout()

from env import require  # noqa: E402

SAMPLE_CONTEXT = (
    "For adults with type 2 diabetes managed by diet and lifestyle alone, "
    "support them to aim for an HbA1c level of 48 mmol/mol (6.5%)."
)
SAMPLE_QUESTION = ("What HbA1c target should be agreed with adults with type 2 "
                   "diabetes managed by diet and lifestyle alone?")
SAMPLE_ANSWER = "An HbA1c level of 48 mmol/mol (6.5%) should be agreed [1]."
SAMPLE_REFERENCE = "48 mmol/mol (6.5%)."


def layer1_raw(timeout: float) -> bool:
    """Smallest possible chat completion against the configured provider."""
    print("-" * 72)
    print("LAYER 1  raw endpoint")
    print("-" * 72)

    provider = config.JUDGE_PROVIDER
    key = require(config.JUDGE_API_KEY_ENV[provider])
    base = config.JUDGE_BASE_URLS.get(provider)
    print(f"  provider   {provider}")
    print(f"  model      {config.JUDGE_MODEL}")
    print(f"  base_url   {base or '(provider default)'}")
    print(f"  key        ...{key[-4:]} (length {len(key)})")

    from openai import OpenAI
    client = OpenAI(api_key=key, base_url=base, timeout=timeout, max_retries=0)

    t0 = time.time()
    try:
        resp = client.chat.completions.create(
            model=config.JUDGE_MODEL,
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
            max_tokens=5, temperature=0.0)
    except Exception as exc:                                    # noqa: BLE001
        dt = time.time() - t0
        print(f"\n  FAILED after {dt:.1f}s")
        print(f"  {type(exc).__name__}: {str(exc)[:400]}")
        print("\n  The judge endpoint itself is the problem. No change to")
        print("  evaluate_ragas.py can work around this. Check, in order:")
        print("    1. DeepInfra account balance / billing status")
        print("    2. the key is still valid (regenerate if in doubt)")
        print("    3. the model string is still served")
        return False

    dt = time.time() - t0
    text = (resp.choices[0].message.content or "").strip()
    print(f"\n  OK in {dt:.2f}s -> {text!r}")
    usage = getattr(resp, "usage", None)
    if usage:
        print(f"  tokens: prompt={usage.prompt_tokens} "
              f"completion={usage.completion_tokens}")

    if dt > 20:
        print(f"\n  !! {dt:.1f}s for a 5-token reply is very slow. Faithfulness")
        print("     makes several calls per sample, so at this latency a single")
        print("     condition of 60 questions would take hours.")
    return True


def layer2_ragas(timeout: float, retries: int) -> bool:
    """One full ragas faithfulness evaluation, with a bounded retry ladder."""
    print("\n" + "-" * 72)
    print("LAYER 2  ragas faithfulness on one sample")
    print("-" * 72)

    from ragas import EvaluationDataset, SingleTurnSample, evaluate
    from ragas.run_config import RunConfig

    from evaluate_ragas import _import_metrics, build_embeddings, build_judge

    F, RR, _, _ = _import_metrics()

    default = RunConfig()
    print(f"  ragas DEFAULT ladder : timeout={default.timeout}s "
          f"max_retries={default.max_retries} max_wait={default.max_wait}s")
    print(f"  this probe uses      : timeout={timeout:g}s "
          f"max_retries={retries} max_wait=5s")
    print("  (evaluate_ragas.py passes no run_config, so it uses the DEFAULT)")

    rc = RunConfig(timeout=int(timeout), max_retries=retries, max_wait=5)

    print("\n  building judge and embeddings ...")
    t0 = time.time()
    judge, embeddings = build_judge(), build_embeddings()
    print(f"  built in {time.time() - t0:.1f}s")

    sample = SingleTurnSample(
        user_input=SAMPLE_QUESTION, response=SAMPLE_ANSWER,
        retrieved_contexts=[SAMPLE_CONTEXT], reference=SAMPLE_REFERENCE)

    print("  evaluating ...")
    t0 = time.time()
    try:
        ev = evaluate(dataset=EvaluationDataset(samples=[sample]),
                      metrics=[F(), RR()], llm=judge, embeddings=embeddings,
                      run_config=rc, show_progress=False)
        scores = ev.to_pandas().iloc[0].to_dict()
    except Exception as exc:                                    # noqa: BLE001
        print(f"\n  RAISED after {time.time() - t0:.1f}s")
        print(f"  {type(exc).__name__}: {str(exc)[:400]}")
        return False
    dt = time.time() - t0

    print(f"\n  returned in {dt:.1f}s")
    ok = True
    for m in ("faithfulness", "answer_relevancy"):
        val = scores.get(m)
        is_nan = isinstance(val, float) and math.isnan(val)
        flag = "NaN <-- judge failed silently" if is_nan else ""
        print(f"    {m:<20} {val!r} {flag}")
        if val is None or is_nan:
            ok = False

    if ok:
        print(f"\n  Both metrics returned real numbers in {dt:.1f}s.")
        print(f"  At this rate, 300 samples ~= {dt * 300 / 60:.0f} minutes of")
        print("  judge time, plus the 2s inter-sample sleep (10 more minutes).")
    else:
        print("\n  ragas returned NaN while layer 1 succeeded. The endpoint is")
        print("  alive, so the failure is inside the ragas call - most often the")
        print("  judge returning output the metric's parser rejects, which ragas")
        print("  retries and then swallows because raise_exceptions=False.")
    return ok


def main() -> None:
    ap = argparse.ArgumentParser(description="Probe the RAGAS judge endpoint.")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--retries", type=int, default=1)
    ap.add_argument("--skip-ragas", action="store_true",
                    help="Layer 1 only - no ragas import, no model download.")
    args = ap.parse_args()

    print("=" * 72)
    print("JUDGE PROBE")
    print("=" * 72)

    if not layer1_raw(args.timeout):
        sys.exit(1)
    if args.skip_ragas:
        return
    if not layer2_ragas(args.timeout, args.retries):
        sys.exit(2)
    print("\nBoth layers healthy.\n")


if __name__ == "__main__":
    main()
