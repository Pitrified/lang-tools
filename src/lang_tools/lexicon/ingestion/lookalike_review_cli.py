"""Command line for the look-alike batch review (see `lookalike_review`).

Usage, with ``CLI=lang_tools.lexicon.ingestion.lookalike_review_cli``::

    uv run python -m $CLI worklist
    uv run python -m $CLI import-gold
    uv run python -m $CLI serve --batch a0001
    uv run python -m $CLI apply --batch a0001 --labels a0001.txt
    uv run python -m $CLI status

``serve`` prints the batch's lines to stdout (gold items look like the others);
``apply`` validates the label file and records it, or prints every problem
and exits 1 without writing anything.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from lang_tools.lexicon import get_store
from lang_tools.lexicon.ingestion.lookalike_review import DEFAULT_BATCH_SIZE
from lang_tools.lexicon.ingestion.lookalike_review import DEFAULT_GOLD_PER_BATCH
from lang_tools.lexicon.ingestion.lookalike_review import TIERS
from lang_tools.lexicon.ingestion.lookalike_review import WORKLIST_FILE
from lang_tools.lexicon.ingestion.lookalike_review import LabelError
from lang_tools.lexicon.ingestion.lookalike_review import apply_batch
from lang_tools.lexicon.ingestion.lookalike_review import build_worklist
from lang_tools.lexicon.ingestion.lookalike_review import gold_key
from lang_tools.lexicon.ingestion.lookalike_review import import_gold
from lang_tools.lexicon.ingestion.lookalike_review import lemma_frequencies
from lang_tools.lexicon.ingestion.lookalike_review import render_batch
from lang_tools.lexicon.ingestion.lookalike_review import review_status
from lang_tools.lexicon.ingestion.lookalike_review import serve_batch
from lang_tools.lexicon.ingestion.lookalikes import find_candidates
from lang_tools.lexicon.ingestion.lookalikes import load_gold
from lang_tools.lexicon.ingestion.lookalikes import select_candidates
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import write_jsonl
from lang_tools.params.lang_tools_params import get_lang_tools_params

#: The review rules every batch is labelled against.
GUIDE = Path("docs/guides/lookalike_review.md")


def _out(text: str) -> None:
    sys.stdout.write(text + "\n")


def _worklist(data_fol: Path) -> None:
    candidates = select_candidates(find_candidates(data_fol))
    skip = {gold_key(pair) for pair in load_gold(data_fol)}
    items = build_worklist(candidates, lemma_frequencies(data_fol), skip=skip)
    path = write_jsonl(items, curated_path(data_fol, WORKLIST_FILE))
    by_tier = {tier: sum(item.tier == tier for item in items) for tier in TIERS}
    _out(f"{len(items)} item(s) -> {path}: {by_tier}")


def main(argv: list[str] | None = None) -> int:
    """Run one review command; return the exit code."""
    parser = argparse.ArgumentParser(prog="lookalike_review_cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("worklist", help="rebuild the ordered worklist from the corpus")
    sub.add_parser("import-gold", help="record the gold pairs as reviewed rows")
    serve = sub.add_parser("serve", help="reserve and print the next batch")
    serve.add_argument("--batch", required=True)
    serve.add_argument("--size", type=int, default=DEFAULT_BATCH_SIZE)
    serve.add_argument("--tier", choices=TIERS)
    serve.add_argument("--gold", type=int, default=DEFAULT_GOLD_PER_BATCH)
    apply = sub.add_parser("apply", help="validate and record a batch's labels")
    apply.add_argument("--batch", required=True)
    apply.add_argument("--labels", type=Path, required=True)
    sub.add_parser("status", help="print the progress per tier")
    args = parser.parse_args(argv)
    params = get_lang_tools_params()
    data_fol = params.paths.data_fol
    guide = params.paths.root_fol / GUIDE
    match args.command:
        case "worklist":
            _worklist(data_fol)
        case "import-gold":
            _out(f"imported {import_gold(data_fol)} gold row(s)")
        case "serve":
            items = serve_batch(
                data_fol,
                get_store(),
                batch=args.batch,
                size=args.size,
                tier=args.tier,
                gold_per_batch=args.gold,
            )
            _out(render_batch(items) if items else "nothing left to serve")
        case "apply":
            try:
                log = apply_batch(
                    data_fol, args.batch, args.labels.read_text(), guide_path=guide
                )
            except LabelError as error:
                _out(
                    "NOT APPLIED, fix and re-run:\n"
                    + "\n".join(f"- {p}" for p in error.problems)
                )
                return 1
            _out(log.model_dump_json(indent=1))
        case _:
            status = review_status(data_fol)
            for tier, (done, total) in status.tiers.items():
                _out(f"tier {tier}: {done}/{total}")
            _out(
                f"batches {status.batches}, pending {status.pending}, "
                f"gold agreement {status.gold_agree}/{status.gold_total}, "
                f"edge cases {status.edge_cases}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
