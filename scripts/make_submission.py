"""
Assemble a clean, verified submission package. OFFLINE - no API calls, no cost.

WHAT IT PRODUCES
----------------
    outputs/submission/rag-nice-submission/   the package tree
    outputs/submission/rag-nice-submission.zip

The package is what a marker, a supervisor, or a GitHub visitor should receive:
the code, the tests, the documentation, the evaluation dataset, and the results
- and nothing else. It is safe to publish.

DESIGN RULES
------------
1. NOTHING SENSITIVE. `.env` is never copied, and every file that IS copied is
   scanned for the literal key values found in your local `.env`. If a key
   appears anywhere, the build ABORTS. Scanning for the real values catches a
   key pasted into a notebook, a log, or a docstring - which a filename-based
   exclusion would miss entirely.

2. NO COPYRIGHTED CORPUS. The four NICE PDFs are not redistributed. Their URLs
   and SHA-256 hashes are recorded instead, which is both lawful and better
   reproducibility practice. `--include-corpus-text` can add the extracted text
   if you have satisfied yourself about NICE's reuse terms; it is off by
   default and deliberately awkward.

3. RESULTS ARE EVIDENCE, SO THEY SHIP. The default `.gitignore` excludes
   `outputs/`, which is right for a normal repository and wrong for assessed
   work: a marker cloning it would find no results. Summary, analysis, figures,
   per-question runs and the RAGAS score cache are all included. The score
   cache matters most - with it, a third party can re-derive every reported
   number by running `--score` with NO API key and NO cost.

4. DERIVED ARTEFACTS ARE REBUILT, NOT SHIPPED. FAISS indexes and chunk files
   are regenerated deterministically by `build_all.py`, so shipping them adds
   megabytes and a chance of staleness. A stale chunk file has already caused
   one silent failure on this project (EVIDENCE.md section 19).

5. IT VERIFIES ITSELF. The package is checked after assembly: required files
   present, every Python file parses, no secret present, no module duplicated
   between src/ and scripts/. A manifest with sizes and a SHA-256 of the zip is
   written so the submitted artefact can be identified later.

USAGE
-----
    python scripts/make_submission.py                 # build it
    python scripts/make_submission.py --dry-run       # show what would happen
    python scripts/make_submission.py --include-corpus-text
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config  # noqa: E402
from console import safe_stdout  # noqa: E402

safe_stdout()

STAGE = config.OUTPUTS / "submission"
PKG_NAME = "rag-nice-submission"

# (source, destination, required) - directories are copied wholesale.
CODE_DIRS = [("src", "src"), ("scripts", "scripts"), ("tests", "tests")]

DOCS = ["README.md", "EVIDENCE.md", "LOGBOOK.md",
        "requirements.txt", "config.py", ".env.example"]

RESULT_FILES = ["summary.json", "analysis.json", "build_report.json"]

EXCLUDE_NAMES = {"__pycache__", ".pytest_cache", ".venv", "venv", ".git",
                 ".env", ".DS_Store", "submission"}
EXCLUDE_SUFFIX = {".pyc", ".pyo", ".faiss", ".zip"}


def _skip(p: Path) -> bool:
    if any(part in EXCLUDE_NAMES for part in p.parts):
        return True
    return p.suffix in EXCLUDE_SUFFIX


def load_secrets() -> list[str]:
    """Literal key VALUES from .env, so we can prove none of them ship."""
    env = ROOT / ".env"
    secrets: list[str] = []
    if not env.exists():
        return secrets
    for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        value = line.split("=", 1)[1].strip().strip('"').strip("'")
        if len(value) >= 12:          # ignore blanks and trivial placeholders
            secrets.append(value)
    return secrets


def scan_for_secrets(tree: Path, secrets: list[str]) -> list[str]:
    """Return a list of 'path: reason' for any file containing a live key."""
    hits: list[str] = []
    if not secrets:
        return hits
    for p in sorted(tree.rglob("*")):
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for s in secrets:
            if s in text:
                hits.append(f"{p.relative_to(tree)}: contains a live API key "
                            f"(...{s[-4:]})")
    return hits


def copy_tree(src: Path, dst: Path, counter: dict) -> None:
    for p in sorted(src.rglob("*")):
        if p.is_dir() or _skip(p.relative_to(ROOT)):
            continue
        target = dst / p.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
        counter["files"] += 1
        counter["bytes"] += p.stat().st_size


def corpus_provenance() -> str:
    """Record what the corpus was, without redistributing it."""
    lines = ["| Guideline | Title | URL | SHA-256 (source PDF) |",
             "|---|---|---|---|"]
    report = config.OUTPUTS / "build_report.json"
    hashes: dict[str, str] = {}
    if report.exists():
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
            for d in (data.get("documents") or data.get("docs") or []):
                if isinstance(d, dict) and d.get("doc_id"):
                    hashes[d["doc_id"]] = str(d.get("sha256", ""))[:16]
        except (ValueError, TypeError):
            pass
    for doc_id, meta in config.CORPUS.items():
        h = hashes.get(doc_id, "see outputs/build_report.json")
        lines.append(f"| {doc_id} | {meta['title']} | {meta['url']} | `{h}` |")
    return "\n".join(lines)


SUBMISSION_MD = """# RAG over NICE Clinical Guidelines - submission package

**A Retrieval-Augmented Generation Question-Answering System over NICE Clinical
Guidelines: Evaluating the Effect of Chunking and Retrieval Strategies on
Faithfulness and Retrieval Quality**

Anuj Dubey (16180226) | 7005SCN Individual Research Project
Coventry University | Supervisor: Seyran Naghdi
Ethics: CU Ethics Online P194982 (approved, low risk)

Package built {built}.

---

## What this is

A complete retrieval-augmented generation pipeline over four NICE clinical
guidelines, and a controlled experiment measuring whether the design choices
behind it reduce ungrounded generation.

Two chunking strategies (fixed-size, semantic) crossed with two retrieval
methods (dense, hybrid) at a fixed depth, plus a non-retrieval baseline, over
60 human-verified questions. Faithfulness and answer relevancy are scored by an
independent LLM judge; retrieval quality is measured deterministically against
character-level gold evidence, with no LLM involved.

- **H1** semantic chunking produces higher faithfulness than fixed-size chunking
- **H2** hybrid retrieval achieves higher retrieval quality than dense alone

---

## What is included, and what is not

| Included | Why |
|---|---|
| `src/`, `scripts/`, `tests/` | The full pipeline and its test suite |
| `config.py`, `requirements.txt` | Every experimental variable, and pinned versions |
| `data/eval/` | The 60-question evaluation dataset with character-span gold evidence |
| `outputs/summary.json`, `analysis.json` | Aggregate results, significance tests, effect sizes |
| `outputs/figures/` | Generated figures |
| `outputs/runs/` | Per-question answers, retrieved contexts and metrics |
| `outputs/ragas_cache/` | Every individual judge score |
| `EVIDENCE.md` | The audit trail: every verified result and the command that produced it |

| Excluded | Why |
|---|---|
| `data/raw/*.pdf` | NICE guidelines are copyrighted. URLs and hashes are below. |
| `.env` | API keys. Never distributed. `.env.example` shows the format. |
| `.venv/`, `__pycache__/` | Environment-specific, rebuildable |
| `data/index/*.faiss`, chunk files | Derived; `build_all.py` regenerates them deterministically |

`outputs/ragas_cache/` is the important inclusion. **With it, every reported
number can be re-derived with no API key and no cost** - see step 3 below.

---

## Corpus provenance

The four guidelines are public and free to download from NICE. They are not
redistributed here.

{corpus}

Download each as PDF into `data/raw/` using the exact filenames in
`config.CORPUS`, then run `scripts/build_all.py`. NICE revises its guidelines,
so verify the SHA-256 above if you need to reproduce the published results
exactly.

---

## Running it

### 1. Environment (Python 3.11)

Use 3.11, not 3.12 or 3.13: `faiss-cpu` and `torch` wheels are best-tested there.

```bash
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

### 2. What runs with no API key and no cost

```bash
python -m pytest tests/ -q          # full test suite, offline
python scripts/verify_install.py    # no stale or duplicated code
python scripts/diagnose_scoring.py  # score-cache integrity
python scripts/effective_n.py       # effective sample size after tied pairs
python scripts/analyse.py           # significance tests, effect sizes, figures
```

`analyse.py` regenerates every statistic and figure from the shipped results.
This is the fastest way to confirm the reported findings are real.

### 3. Reproducing the scores without paying for them

```bash
python scripts/run_experiment.py --score
```

Every condition should report `60 cached, 0 to score`. No judge call is made;
the numbers come from `outputs/ragas_cache/`. This is how the results are
verified without an API key.

### 4. Rebuilding the pipeline from the source PDFs

Requires the four PDFs in `data/raw/` (see provenance above). No API key.

```bash
python scripts/build_all.py --docs NG28 NG136 NG238 NG106
python scripts/verify_offsets.py
python scripts/precision_ceiling.py
```

Expected: 547 fixed chunks and 509 semantic chunks, offsets 100% exact on both
arms. Offset integrity below 100% means chunk spans no longer address the right
passages, which silently invalidates every retrieval metric - stop if you see it.

### 5. Regenerating answers (needs API keys, and will NOT reproduce exactly)

```bash
cp .env.example .env    # add GOOGLE_API_KEY and DEEPINFRA_API_KEY
python scripts/run_experiment.py --all
```

**This overwrites cached answers.** Gemini 3.x deprecates `temperature` and
cannot fully disable thinking, so regeneration produces different answers,
different faithfulness scores, and different results. The published findings
rest on one fixed, archived set of generated answers. Run this only if you
intend a new experiment rather than a replication.

---

## Reading the code

| Path | Role |
|---|---|
| `config.py` | Single source of truth for every experimental variable |
| `src/ingest.py` | PDF to cleaned text, with frequency-based furniture removal |
| `src/chunking.py` | Fixed-size and semantic chunking, preserving character offsets |
| `src/embed_index.py` | sentence-transformers to FAISS IndexFlatIP (exact search) |
| `src/retrieve.py` | Dense and hybrid retrieval (BM25 + reciprocal rank fusion) |
| `src/spans.py` | Character-span overlap to binary relevance labels |
| `src/generate.py` | Grounded generation with an enforced refusal clause |
| `src/evaluate_ragas.py` | RAGAS harness with per-sample score caching |
| `scripts/analyse.py` | Wilcoxon signed-rank, Holm correction, rank-biserial effect sizes |

**The critical invariant:** every chunk carries `start_char`/`end_char` into its
source document, and gold evidence is stored as character spans. That is what
makes retrieval metrics comparable between chunking strategies whose boundaries
differ. `scripts/verify_offsets.py` checks it; `tests/` guards it.

---

## Scope and limitations

- Generation is **not** bit-reproducible (see step 5). Mitigated by generating
  once, caching, and scoring against that fixed set.
- `precision@k` is bounded by the number of relevant chunks per question.
  Report it against the ceiling computed by `scripts/precision_ceiling.py`, or
  report attainment; raw values understate retrieval quality.
- Wilcoxon discards tied pairs, so the effective sample size is below 60 on
  several comparisons. `scripts/effective_n.py` reports the real figure.
- This is a **research prototype**. It gives no medical advice and is not a
  clinical tool. The system prompt forbids answering beyond the retrieved
  extracts and requires an explicit refusal when they are insufficient.

---

## Ethics

Secondary analysis of public, non-personal data. No human participants, no
personal or special-category data. Approved via CU Ethics Online, project
P194982.
"""

PKG_GITIGNORE = """# Environment and secrets - never commit
.env
.venv/
venv/

# Python
__pycache__/
*.pyc
*.pyo

# Copyrighted corpus - see SUBMISSION.md for download URLs and hashes
data/raw/*.pdf

# Derived artefacts, rebuilt by scripts/build_all.py
data/index/*.faiss
data/interim/

# NOTE: outputs/ is deliberately NOT ignored in this package.
# The results are the evidence for the dissertation, and outputs/ragas_cache/
# lets any reader re-derive every reported number with no API key and no cost.
.DS_Store
"""


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build a verified, secret-free submission package.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Report what would be included; write nothing.")
    ap.add_argument("--include-corpus-text", action="store_true",
                    help="Also include extracted guideline text (data/interim). "
                         "Check NICE reuse terms before enabling.")
    args = ap.parse_args()

    print("=" * 78)
    print("BUILD SUBMISSION PACKAGE")
    print("=" * 78)

    secrets = load_secrets()
    print(f"  live keys found in .env : {len(secrets)} "
          f"(their VALUES will be scanned for, not just filenames)")

    # ------------------------------------------------------------- preflight
    problems: list[str] = []
    warnings: list[str] = []

    for name in DOCS:
        if not (ROOT / name).exists():
            problems.append(f"missing required file: {name}")
    for src_name, _ in CODE_DIRS:
        if not (ROOT / src_name).is_dir():
            problems.append(f"missing required directory: {src_name}/")

    dataset = config.DATA / "eval" / "eval_dataset.json"
    if not dataset.exists():
        problems.append("missing data/eval/eval_dataset.json")

    for f in RESULT_FILES:
        if not (config.OUTPUTS / f).exists():
            warnings.append(f"no outputs/{f} - run the experiment and analyse.py")

    figures = sorted((config.OUTPUTS / "figures").glob("*.png"))
    if not figures:
        warnings.append("no figures in outputs/figures/ - run analyse.py")

    cache = sorted((config.OUTPUTS / "ragas_cache").glob("*.json"))
    runs = sorted((config.OUTPUTS / "runs").glob("*.json"))
    print(f"  score cache             : {len(cache)} files")
    print(f"  run files               : {len(runs)} files")
    print(f"  figures                 : {len(figures)} files")

    if problems:
        print("\n  CANNOT BUILD:")
        for p in problems:
            print(f"    - {p}")
        sys.exit(1)
    for w in warnings:
        print(f"  WARNING: {w}")

    if args.dry_run:
        print("\n  --dry-run: nothing written.")
        return

    # ------------------------------------------------------------- assemble
    if STAGE.exists():
        shutil.rmtree(STAGE)
    pkg = STAGE / PKG_NAME
    pkg.mkdir(parents=True)
    counter = {"files": 0, "bytes": 0}

    for src_name, dst_name in CODE_DIRS:
        copy_tree(ROOT / src_name, pkg / dst_name, counter)
    for name in DOCS:
        shutil.copy2(ROOT / name, pkg / name)
        counter["files"] += 1
        counter["bytes"] += (ROOT / name).stat().st_size

    copy_tree(config.DATA / "eval", pkg / "data" / "eval", counter)
    if args.include_corpus_text:
        copy_tree(config.INTERIM, pkg / "data" / "interim", counter)
        print("  NOTE: extracted guideline text INCLUDED at your request.")

    for sub in ("data/raw", "data/index"):
        d = pkg / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").write_text("", encoding="utf-8")

    for f in RESULT_FILES:
        s = config.OUTPUTS / f
        if s.exists():
            (pkg / "outputs").mkdir(exist_ok=True)
            shutil.copy2(s, pkg / "outputs" / f)
            counter["files"] += 1
    for name, files in (("figures", figures), ("runs", runs),
                        ("ragas_cache", cache)):
        if not files:
            continue
        d = pkg / "outputs" / name
        d.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.copy2(f, d / f.name)
            counter["files"] += 1
            counter["bytes"] += f.stat().st_size

    (pkg / "SUBMISSION.md").write_text(
        SUBMISSION_MD.format(built=date.today().isoformat(),
                             corpus=corpus_provenance()),
        encoding="utf-8")
    (pkg / ".gitignore").write_text(PKG_GITIGNORE, encoding="utf-8")

    # ------------------------------------------------------------- verify
    print("\n" + "-" * 78)
    print("VERIFYING THE PACKAGE")
    print("-" * 78)

    fatal: list[str] = []

    hits = scan_for_secrets(pkg, secrets)
    if hits:
        fatal.extend(hits)
    print(f"  secret scan             : {'FAIL' if hits else 'clean'} "
          f"({counter['files']} files scanned)")

    if (pkg / ".env").exists():
        fatal.append(".env present in package")
    stray_pdf = list((pkg / "data" / "raw").glob("*.pdf"))
    if stray_pdf:
        fatal.append(f"copyrighted PDFs present: {[p.name for p in stray_pdf]}")
    print(f"  .env / PDFs             : "
          f"{'FAIL' if (pkg / '.env').exists() or stray_pdf else 'absent'}")

    bad_syntax = []
    for p in sorted(pkg.rglob("*.py")):
        try:
            ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            bad_syntax.append(f"{p.relative_to(pkg)}: {exc}")
    fatal.extend(bad_syntax)
    print(f"  python syntax           : "
          f"{'FAIL' if bad_syntax else 'all files parse'}")

    dup = ({p.name for p in (pkg / "src").glob("*.py")} - {"__init__.py"}) & \
          {p.name for p in (pkg / "scripts").glob("*.py")}
    if dup:
        fatal.append(f"module in both src/ and scripts/: {sorted(dup)}")
    print(f"  module collisions       : {'FAIL' if dup else 'none'}")

    if fatal:
        print("\n" + "=" * 78)
        print("  BUILD ABORTED - the package is NOT safe to distribute:")
        for f in fatal:
            print(f"    - {f}")
        print("=" * 78)
        shutil.rmtree(STAGE, ignore_errors=True)
        sys.exit(1)

    # ------------------------------------------------------------- zip
    zip_path = STAGE / f"{PKG_NAME}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(pkg.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(STAGE))

    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    manifest = {
        "package": PKG_NAME,
        "built": date.today().isoformat(),
        "files": counter["files"],
        "zip_bytes": zip_path.stat().st_size,
        "zip_sha256": digest,
        "score_cache_files": len(cache),
        "run_files": len(runs),
        "figures": len(figures),
        "includes_corpus_text": bool(args.include_corpus_text),
    }
    (STAGE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2),
                                         encoding="utf-8")

    print("\n" + "=" * 78)
    print("  PACKAGE BUILT AND VERIFIED")
    print("=" * 78)
    print(f"  folder   {pkg}")
    print(f"  zip      {zip_path}")
    print(f"  size     {zip_path.stat().st_size / 1_048_576:.1f} MB")
    print(f"  files    {counter['files']}")
    # Print the digest IN FULL, split over two lines for legibility.
    #
    # This previously printed `digest[:32]` followed by an ellipsis, while the
    # next line instructed the operator to record it as a SHA-256. A SHA-256 is
    # 64 hex characters; anyone following that instruction recorded a half
    # digest that looks like a valid MD5 and verifies nothing. That is exactly
    # what happened in LOGBOOK.md on 12 Aug 2026. A tool must never truncate a
    # value it is telling you to record. (Fixed 12 Aug 2026.)
    print(f"  sha256   {digest[:32]}")
    print(f"           {digest[32:]}")
    print(f"\n  Record that 64-character SHA-256 in LOGBOOK.md - it identifies")
    print("  exactly which build was submitted. It is also stored in full as")
    print("  zip_sha256 in MANIFEST.json inside the package folder, and can be")
    print("  recomputed at any time without rebuilding:")
    print(f"    Get-FileHash \"{zip_path.name}\" -Algorithm SHA256")
    print("\n  NOTE: MANIFEST.json is written to the package FOLDER after the zip")
    print("  is sealed, so it is not inside the zip - a manifest cannot contain")
    print("  the hash of an archive that contains the manifest. Folder and zip")
    print("  therefore differ by exactly that one file, by design.")
    print("\n  For GitHub: push the CONTENTS of the folder above. Its .gitignore")
    print("  already excludes keys, the venv, and the copyrighted PDFs.")
    print()


if __name__ == "__main__":
    main()
