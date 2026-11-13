"""Command line for the agent-written pt glosses (see `gloss_write`).

Usage, with ``CLI=lang_tools.lexicon.ingestion.gloss_write_cli``::

    uv run --no-sync python -m $CLI serve --batch g0001
    uv run --no-sync python -m $CLI apply --batch g0001 --glosses g0001.txt
    uv run --no-sync python -m $CLI correct --key pt:0011aabbccdd --gloss "..."
    uv run --no-sync python -m $CLI status

``serve`` prints the batch's lines to stdout; ``apply`` screens the gloss file
and records it, or prints every problem and exits 1 without writing anything.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from lang_tools.lexicon.ingestion.gloss_write import DEFAULT_BATCH_SIZE
from lang_tools.lexicon.ingestion.gloss_write import RULES
from lang_tools.lexicon.ingestion.gloss_write import GlossCorrectionError
from lang_tools.lexicon.ingestion.gloss_write import apply_batch
from lang_tools.lexicon.ingestion.gloss_write import correct_gloss
from lang_tools.lexicon.ingestion.gloss_write import render_batch
from lang_tools.lexicon.ingestion.gloss_write import serve_batch
from lang_tools.lexicon.ingestion.gloss_write import write_status
from lang_tools.lexicon.ingestion.review_batches import LabelError
from lang_tools.params.lang_tools_params import get_lang_tools_params


def _out(text: str) -> None:
    sys.stdout.write(text + "\n")


def main(argv: list[str] | None = None) -> int:
    """Run one command; return the exit code."""
    parser = argparse.ArgumentParser(prog="gloss_write_cli")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="reserve and print the next batch")
    serve.add_argument("--batch", required=True)
    serve.add_argument("--size", type=int, default=DEFAULT_BATCH_SIZE)
    apply = sub.add_parser("apply", help="screen and record a batch's glosses")
    apply.add_argument("--batch", required=True)
    apply.add_argument("--glosses", type=Path, required=True)
    correct = sub.add_parser("correct", help="record a corrected gloss")
    correct.add_argument("--key", required=True)
    correct.add_argument("--gloss", required=True)
    sub.add_parser("status", help="print the progress")
    args = parser.parse_args(argv)
    params = get_lang_tools_params()
    data_fol = params.paths.data_fol
    match args.command:
        case "serve":
            items = serve_batch(data_fol, batch=args.batch, size=args.size)
            _out(render_batch(items) if items else "nothing left to serve")
        case "apply":
            try:
                log = apply_batch(
                    data_fol,
                    args.batch,
                    args.glosses.read_text(),
                    rules_path=params.paths.root_fol / RULES,
                )
            except LabelError as error:
                _out(
                    "NOT APPLIED, fix and re-run:\n"
                    + "\n".join(f"- {p}" for p in error.problems)
                )
                return 1
            _out(f"applied {log.batch}: {log.items} gloss(es), rules {log.rules_sha}")
        case "correct":
            try:
                row = correct_gloss(data_fol, args.key, args.gloss)
            except GlossCorrectionError as error:
                _out(f"NOT CORRECTED: {error}")
                return 1
            _out(
                f"{args.key}: {row.current_definition!r} -> {row.proposed_definition!r}"
            )
        case _:
            status = write_status(data_fol)
            _out(
                f"left {status.left}, written {status.written} in {status.batches} "
                f"batch(es), pending {', '.join(status.pending) or 'none'}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
