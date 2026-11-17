"""Command line for the meaning review (see `meaning_review`).

Usage, with ``CLI=lang_tools.lexicon.ingestion.meaning_review_cli``::

    uv run --no-sync python -m $CLI worklist
    uv run --no-sync python -m $CLI serve --batch w0001
    uv run --no-sync python -m $CLI apply --batch w0001 --labels w0001.labels.txt
    uv run --no-sync python -m $CLI recheck --batch w9001 --labels d
    uv run --no-sync python -m $CLI status

A batch id starting with ``w`` serves meanings (their pt words), with ``l``
leads (their first en word). ``serve`` prints the batch's lines to stdout.
``apply`` validates the label file and records it, or prints every problem and
exits 1 without writing anything. ``recheck`` serves again the reviewed meanings
with a word carrying one of the given labels, for a re-label after a rule change.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

from lang_tools.lexicon import get_store
from lang_tools.lexicon.ingestion.meaning_review import DEFAULT_BATCH_SIZE
from lang_tools.lexicon.ingestion.meaning_review import LEAD_PREFIX
from lang_tools.lexicon.ingestion.meaning_review import MEMBER_PREFIX
from lang_tools.lexicon.ingestion.meaning_review import apply_batch
from lang_tools.lexicon.ingestion.meaning_review import build_lead_worklist
from lang_tools.lexicon.ingestion.meaning_review import build_member_worklist
from lang_tools.lexicon.ingestion.meaning_review import drill_cards
from lang_tools.lexicon.ingestion.meaning_review import recheck_batch
from lang_tools.lexicon.ingestion.meaning_review import render_batch
from lang_tools.lexicon.ingestion.meaning_review import review_status
from lang_tools.lexicon.ingestion.meaning_review import save_worklist
from lang_tools.lexicon.ingestion.meaning_review import serve_batch
from lang_tools.lexicon.ingestion.review_batches import LabelError
from lang_tools.params.lang_tools_params import get_lang_tools_params

#: The review rules every batch is labelled against.
GUIDE = Path("docs/guides/meaning_review.md")


def _out(text: str) -> None:
    sys.stdout.write(text + "\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="meaning_review_cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("worklist", help="rebuild both worklists from the corpus")
    serve = sub.add_parser("serve", help="reserve and print the next batch")
    serve.add_argument("--batch", required=True)
    serve.add_argument("--size", type=int, default=DEFAULT_BATCH_SIZE)
    apply = sub.add_parser("apply", help="validate and record a batch's labels")
    apply.add_argument("--batch", required=True)
    apply.add_argument("--labels", type=Path, required=True)
    recheck = sub.add_parser("recheck", help="serve reviewed meanings again")
    recheck.add_argument("--batch", required=True)
    recheck.add_argument("--labels", required=True, help="label letters, e.g. d or d,f")
    sub.add_parser("status", help="print the progress")
    return parser


def _apply(data_fol: Path, guide: Path, args: argparse.Namespace) -> int:
    """Apply a batch's labels and print its counts, or every problem."""
    try:
        rows = apply_batch(
            data_fol, args.batch, args.labels.read_text(), guide_path=guide
        )
    except LabelError as error:
        _out(
            "NOT APPLIED, fix and re-run:\n"
            + "\n".join(f"- {p}" for p in error.problems)
        )
        return 1
    counts = Counter(row.label for row in rows)
    _out(f"applied {args.batch}: {len(rows)} label(s), {dict(sorted(counts.items()))}")
    return 0


def _worklist(data_fol: Path) -> None:
    store = get_store()
    cards = drill_cards(store)
    for prefix, items in (
        (MEMBER_PREFIX, build_member_worklist(cards)),
        (LEAD_PREFIX, build_lead_worklist(store, cards)),
    ):
        path = save_worklist(data_fol, prefix, items)
        _out(f"{prefix}: {len(items)} meaning(s) -> {path}")


def _status(data_fol: Path) -> None:
    for prefix, name in ((MEMBER_PREFIX, "meanings"), (LEAD_PREFIX, "leads")):
        status = review_status(data_fol, prefix)
        _out(
            f"{name}: reviewed {status.reviewed}/{status.worklist}, {status.labels}, "
            f"batches {status.batches}, pending {status.pending}"
        )


def main(argv: list[str] | None = None) -> int:
    """Run one review command; return the exit code."""
    args = _parser().parse_args(argv)
    params = get_lang_tools_params()
    data_fol = params.paths.data_fol
    guide = params.paths.root_fol / GUIDE
    match args.command:
        case "worklist":
            _worklist(data_fol)
        case "serve":
            items = serve_batch(data_fol, get_store(), batch=args.batch, size=args.size)
            _out(render_batch(items) if items else "nothing left to serve")
        case "recheck":
            items = recheck_batch(
                data_fol,
                get_store(),
                batch=args.batch,
                labels=set(args.labels.split(",")),
            )
            _out(render_batch(items) if items else "nothing to re-check")
        case "apply":
            return _apply(data_fol, guide, args)
        case _:
            _status(data_fol)
    return 0


if __name__ == "__main__":
    sys.exit(main())
