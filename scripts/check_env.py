"""
Pre-flight check. Run this FIRST, before anything else, and paste its output
into your logbook — it is your reproducibility record for the report appendix.

    python scripts/check_env.py
    python scripts/check_env.py --list-models    # confirm the Gemini model name
"""

from __future__ import annotations

import argparse
import importlib
import os
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from console import safe_stdout  # noqa: E402

safe_stdout()

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

PACKAGES = [
    "pypdf", "langchain_text_splitters", "sentence_transformers", "torch",
    "faiss", "numpy", "google.genai", "dotenv", "tenacity", "tqdm", "pandas",
]


def check_packages() -> bool:
    print("PACKAGES")
    ok = True
    for name in PACKAGES:
        try:
            mod = importlib.import_module(name)
            version = getattr(mod, "__version__", None)
            if version is None and "." in name:
                root = importlib.import_module(name.split(".")[0])
                version = getattr(root, "__version__", "?")
            print(f"  OK    {name:<28} {version or '?'}")
        except Exception as exc:  # noqa: BLE001
            ok = False
            print(f"  FAIL  {name:<28} {type(exc).__name__}: {exc}")
    return ok


def check_keys() -> bool:
    print("\nAPI KEYS")
    ok = True
    import config as _cfg
    judge_env = _cfg.JUDGE_API_KEY_ENV[_cfg.JUDGE_PROVIDER]
    for key, needed_at in [("GOOGLE_API_KEY", "generation"),
                           (judge_env, f"RAGAS judge ({_cfg.JUDGE_PROVIDER})")]:
        val = os.getenv(key)
        if val:
            print(f"  OK    {key:<16} set (...{val[-4:]})")
        else:
            print(f"  MISS  {key:<16} not set — needed at {needed_at}")
            if needed_at == "generation":
                ok = False
    return ok


def check_corpus() -> None:
    import config

    print("\nCORPUS FILES")
    for doc_id, meta in config.CORPUS.items():
        path = config.RAW / meta["filename"]
        state = f"OK    {path.stat().st_size/1_000_000:.1f} MB" if path.exists() \
            else "MISS  download from " + meta["url"]
        print(f"  {doc_id:<7} {meta['filename']:<12} {state}")


def check_embedder() -> bool:
    print("\nEMBEDDING MODEL (downloads ~130MB on first run)")
    try:
        import config
        from src.embed_index import encode_passages  # noqa: F401
    except Exception:
        sys.path.insert(0, str(ROOT / "src"))
        import config  # noqa: F811
        from embed_index import encode_passages  # noqa: F811

    try:
        vecs = encode_passages(["hypertension", "high blood pressure", "diabetes"])
        import numpy as np

        sim_related = float(np.dot(vecs[0], vecs[1]))
        sim_unrelated = float(np.dot(vecs[0], vecs[2]))
        print(f"  OK    {config.EMBEDDING_MODEL} -> shape {vecs.shape}")
        print(f"  sanity: cos('hypertension','high blood pressure') = {sim_related:.3f}")
        print(f"          cos('hypertension','diabetes')            = {sim_unrelated:.3f}")
        if sim_related > sim_unrelated:
            print("  OK    related pair scores higher — embeddings behave sensibly")
            return True
        print("  WARN  related pair did NOT score higher — investigate before proceeding")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL  {type(exc).__name__}: {exc}")
        return False


def list_models() -> None:
    print("\nAVAILABLE GEMINI MODELS (confirm the one in config.GEN_MODEL)")
    try:
        from google import genai

        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        for m in client.models.list():
            name = getattr(m, "name", "?")
            if "gemini" in str(name):
                print(f"  {name}")
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL  {type(exc).__name__}: {exc}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--skip-embedder", action="store_true")
    args = ap.parse_args()

    print("=" * 70)
    print("7005SCN RAG pipeline — environment check")
    print(f"  Python   {sys.version.split()[0]}  ({platform.system()} {platform.machine()})")
    print(f"  Root     {ROOT}")
    print("=" * 70 + "\n")

    ok = check_packages()
    ok = check_keys() and ok
    check_corpus()
    if not args.skip_embedder:
        ok = check_embedder() and ok
    if args.list_models:
        list_models()

    print("\n" + "=" * 70)
    print("READY — proceed to src/ingest.py" if ok
          else "NOT READY — resolve the FAIL/MISS lines above")
    print("=" * 70)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
