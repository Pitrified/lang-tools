"""Re-measure the store load after the phase 5.3 streaming + cache fix.

Sibling to ``profile_load.py`` (the before-the-fix profiling). Measures three
loads of the real en/pt corpus under ``data/lexicon/`` and logs each to
``profile_after.log`` (flushed + fsync'd so an OOM kill still leaves the partial
result on disk, same as the before-run):

1. cold  - cache cleared, streaming build + persist to ``_store.sqlite``;
2. warm  - the same call again, served from the persisted cache (bare connect);
3. validate - the slow model-validating path, for an apples-to-before number.

Run: ``uv run python scratch_space/09_concept_model/05.3_profiling/profile_after_fix.py``
"""

from __future__ import annotations

import os
from pathlib import Path
import resource
import time

from lang_tools.lexicon.lemma_store import STORE_DB_NAME
from lang_tools.lexicon.lemma_store import LexiconStore
from lang_tools.params.lang_tools_params import get_lang_tools_params

_LOG_PATH = Path(__file__).with_name("profile_after.log")
_LOG_FH = _LOG_PATH.open("w", encoding="utf-8", buffering=1)


def log(msg: str = "") -> None:
    """Print and append a line to the log file, flushing immediately."""
    print(msg, flush=True)
    _LOG_FH.write(msg + "\n")
    _LOG_FH.flush()
    os.fsync(_LOG_FH.fileno())


def _max_rss_mb() -> float:
    """Peak resident set size so far, in MB (Linux ru_maxrss is in KB)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def _timed(label: str, fn) -> object:  # noqa: ANN001 - scratch
    """Run fn, log elapsed + current peak RSS, return its result."""
    t0 = time.perf_counter()
    out = fn()
    log(f"  {label:<46} {time.perf_counter() - t0:8.3f} s   "
        f"(peak RSS {_max_rss_mb():7.0f} MB)")
    return out


def main() -> None:
    """Cold build (+persist), warm cache hit, and the validate path."""
    data_fol = get_lang_tools_params().paths.data_fol
    corpus_dir = data_fol / "lexicon"
    cache_db = corpus_dir / STORE_DB_NAME
    sig = cache_db.with_suffix(cache_db.suffix + ".sig")

    log(f"data_fol = {data_fol}")
    log(f"start peak RSS {_max_rss_mb():.0f} MB")

    # 1. COLD: clear the persisted cache, then streaming build + persist.
    cache_db.unlink(missing_ok=True)
    sig.unlink(missing_ok=True)
    log("\n== cold: streaming build + persist ==")
    store = _timed("cold from_data_fol (build + persist)",
                   lambda: LexiconStore.from_data_fol(data_fol))
    log(f"  cache file written: {cache_db.exists()}  ({cache_db.stat().st_size/1e6:.1f} MB)")
    n_concepts = len(store.get_all_concepts())
    n_lemmas = len(store.get_all_lemmas())
    log(f"  concepts={n_concepts:,}  lemmas={n_lemmas:,}")

    # 2. WARM: same call, served from the persisted cache (bare connect).
    log("\n== warm: cache hit (bare connect) ==")
    warm = _timed("warm from_data_fol (cache hit)",
                  lambda: LexiconStore.from_data_fol(data_fol))
    sample = warm.get_concept_by_id(warm.get_all_concepts()[0].id)
    log(f"  sanity: fetched a concept back -> {sample is not None}")

    # 3. VALIDATE: the slow model-validating path (no cache), for comparison.
    log("\n== validate=True: model-validating path (no cache) ==")
    _timed("from_data_fol(validate=True, db_path=:memory:)",
           lambda: LexiconStore.from_data_fol(
               data_fol, db_path=":memory:", validate=True, use_cache=False))

    log(f"\nfinal peak RSS {_max_rss_mb():.0f} MB")


if __name__ == "__main__":
    main()
