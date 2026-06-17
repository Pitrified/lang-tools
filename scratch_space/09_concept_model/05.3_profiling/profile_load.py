"""Profile the full-corpus LexiconStore load (phase 5.3, Observation 2/3).

Runs against the real en/pt corpus under ``data/lexicon/`` produced by the first
successful build. Times each stage of the load and reports peak RSS, so the
>5 min load (and the OOM) has a named cause rather than a guess.

Memory-frugal by design: the per-row timing pass processes one table at a time
and frees it before the next, so it does not itself OOM. The real ``from_data_fol``
path (which holds the whole corpus as models, then re-dumps it) is measured last
and may still OOM - that is the point of Observation 3.

Run: ``uv run python scratch_space/09_concept_model/05.3_profiling/profile_load.py``
"""

from __future__ import annotations

import gc
import os
from pathlib import Path
import resource
import sqlite3
import time

from lang_tools.lexicon.codec import _read_parquet
from lang_tools.lexicon.codec import model_from_row
from lang_tools.lexicon.codec import row_from_model
from lang_tools.lexicon.lemma_store import TABLES
from lang_tools.params.lang_tools_params import get_lang_tools_params

#: Crash-survivable log: every line is flushed + fsync'd so an OOM kill (SIGKILL,
#: no atexit, no buffer drain) still leaves the partial results on disk.
_LOG_PATH = Path(__file__).with_name("profile_run.log")
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


def _partition_paths(data_fol, name):  # noqa: ANN001, ANN202 - scratch helper
    """Yield the parquet file paths backing a (possibly partitioned) table."""
    table_dir = data_fol / "lexicon"
    if name in {"lemmas", "senses"}:
        yield from sorted((table_dir / name).glob("*.parquet"))
    else:
        p = table_dir / f"{name}.parquet"
        if p.exists():
            yield p


def per_table_timings(data_fol) -> None:  # noqa: ANN001
    """Time read / validate / dump per table, freeing each before the next.

    This isolates the cost of each load stage at row scale without ever holding
    more than one table resident, so it reports the *per-row* costs that the real
    (whole-corpus) path pays all at once.
    """
    log("\n== per-table stage timings (frugal: one table at a time) ==")
    log(f"  {'table':<18}{'rows':>9}  {'read':>8}  {'validate':>9}  {'dump':>8}  "
          f"{'us/row(v)':>10}")
    for name in TABLES:
        # Stage 1: pyarrow read -> list[dict]
        t0 = time.perf_counter()
        raw: list[dict] = []
        for path in _partition_paths(data_fol, name):
            raw.extend(_read_parquet(path))
        t_read = time.perf_counter() - t0
        n = len(raw)

        # Stage 2: pydantic validate every row -> models
        t0 = time.perf_counter()
        models = [model_from_row(name, row) for row in raw]
        t_validate = time.perf_counter() - t0
        raw.clear()
        del raw

        # Stage 3: pydantic dump every model back to a row
        t0 = time.perf_counter()
        for model in models:
            row_from_model(name, model)
        t_dump = time.perf_counter() - t0

        us_per_row = (t_validate / n * 1e6) if n else 0.0
        log(f"  {name:<18}{n:>9,}  {t_read:>7.2f}s  {t_validate:>8.2f}s  "
              f"{t_dump:>7.2f}s  {us_per_row:>9.1f}")
        models.clear()
        del models
        gc.collect()
    log(f"  peak RSS after per-table pass: {_max_rss_mb():.0f} MB")


def raw_to_sqlite_direct(data_fol) -> None:  # noqa: ANN001
    """Time a model-free load: parquet rows -> SQLite, no pydantic round-trip.

    This is the candidate fix - stream the lean Parquet rows straight into SQLite,
    skipping the validate+dump passes the real path does. Measured here only to
    show the headroom; not wired into the store.
    """
    import json  # noqa: PLC0415

    from lang_tools.lexicon.codec import _COLUMNS  # noqa: PLC0415
    from lang_tools.lexicon.lemma_store import _JSON_COLUMNS  # noqa: PLC0415
    from lang_tools.lexicon.lemma_store import _build_schema  # noqa: PLC0415

    log("\n== candidate: parquet rows -> SQLite directly (no pydantic) ==")
    t0 = time.perf_counter()
    conn = sqlite3.connect(":memory:")
    _build_schema(conn)
    for name in TABLES:
        cols = _COLUMNS[name]
        json_cols = _JSON_COLUMNS[name]
        placeholders = ", ".join("?" for _ in cols)
        sql = f"INSERT INTO {name} ({', '.join(cols)}) VALUES ({placeholders})"  # noqa: S608
        for path in _partition_paths(data_fol, name):
            rows = _read_parquet(path)
            conn.executemany(
                sql,
                [
                    tuple(
                        json.dumps(r.get(c), ensure_ascii=False)
                        if c in json_cols
                        else r.get(c)
                        for c in cols
                    )
                    for r in rows
                ],
            )
            rows.clear()
    conn.commit()
    dt = time.perf_counter() - t0
    conn.close()
    log(f"  direct parquet->sqlite: {dt:.2f}s   (peak RSS {_max_rss_mb():.0f} MB)")


def end_to_end(data_fol) -> None:  # noqa: ANN001
    """Time the real from_data_fol (may OOM - that is Observation 3)."""
    from lang_tools.lexicon.lemma_store import LexiconStore  # noqa: PLC0415

    log("\n== end to end (the REAL load path; may OOM) ==")
    t0 = time.perf_counter()
    store = LexiconStore.from_data_fol(data_fol)
    log(f"  from_data_fol: {time.perf_counter() - t0:.2f}s   "
          f"(peak RSS {_max_rss_mb():.0f} MB)")
    t0 = time.perf_counter()
    concepts = store.get_all_concepts()
    log(f"  get_all_concepts() [{len(concepts):,}]: {time.perf_counter() - t0:.2f}s")
    t0 = time.perf_counter()
    lemmas = store.get_all_lemmas()
    log(f"  get_all_lemmas() [{len(lemmas):,}]: {time.perf_counter() - t0:.2f}s")


def main() -> None:
    """Run the frugal passes first, then attempt the real (heavy) path."""
    data_fol = get_lang_tools_params().paths.data_fol
    log(f"data_fol = {data_fol}")
    log(f"start peak RSS {_max_rss_mb():.0f} MB")

    per_table_timings(data_fol)
    gc.collect()
    raw_to_sqlite_direct(data_fol)
    gc.collect()
    end_to_end(data_fol)

    log(f"\nfinal peak RSS {_max_rss_mb():.0f} MB")


if __name__ == "__main__":
    main()
