"""Command line for the card-sense batch review (see `sense_review`).

Usage, with ``CLI=lang_tools.lexicon.ingestion.sense_review_cli``::

    uv run python -m $CLI worklist --language pt
    uv run python -m $CLI import-gold
    uv run python -m $CLI serve --batch s0001
    uv run python -m $CLI apply --batch s0001 --labels s0001.txt
    uv run python -m $CLI status
    uv run python -m $CLI restore --language pt --word moderna --reason "..."
    uv run python -m $CLI pin --language pt --word copa --key e7aeea438f7f

``serve`` prints the batch's lines to stdout (gold items look like the others);
``apply`` validates the label file and records it, or prints every problem
and exits 1 without writing anything. ``restore`` and ``pin`` are the hand
corrections: a later row that retracts a drop, or pins another sense.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from lang_tools.lexicon import get_store
from lang_tools.lexicon.ingestion.review_batches import LabelError
from lang_tools.lexicon.ingestion.sense_review import DEFAULT_BATCH_SIZE
from lang_tools.lexicon.ingestion.sense_review import DEFAULT_GOLD_PER_BATCH
from lang_tools.lexicon.ingestion.sense_review import DEFAULT_WORKLIST_SIZE
from lang_tools.lexicon.ingestion.sense_review import WORKLIST_FILE
from lang_tools.lexicon.ingestion.sense_review import CorrectionError
from lang_tools.lexicon.ingestion.sense_review import apply_batch
from lang_tools.lexicon.ingestion.sense_review import build_worklist
from lang_tools.lexicon.ingestion.sense_review import import_gold
from lang_tools.lexicon.ingestion.sense_review import load_gold
from lang_tools.lexicon.ingestion.sense_review import load_worklist
from lang_tools.lexicon.ingestion.sense_review import pin_sense
from lang_tools.lexicon.ingestion.sense_review import render_batch
from lang_tools.lexicon.ingestion.sense_review import restore_drops
from lang_tools.lexicon.ingestion.sense_review import review_status
from lang_tools.lexicon.ingestion.sense_review import serve_batch
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import write_jsonl
from lang_tools.params.lang_tools_params import get_lang_tools_params

#: The review rules every batch is labelled against.
GUIDE = Path("docs/guides/sense_review.md")


def _out(text: str) -> None:
    sys.stdout.write(text + "\n")


def _worklist(data_fol: Path, language: str, size: int) -> None:
    """Rebuild one language's part of the worklist, keeping the others."""
    skip = [gold.lemma_id for gold in load_gold(data_fol)]
    items = build_worklist(get_store(), language, size=size, skip=skip)
    kept = [item for item in load_worklist(data_fol) if item.language != language]
    path = write_jsonl([*kept, *items], curated_path(data_fol, WORKLIST_FILE))
    _out(f"{len(items)} {language} item(s) -> {path}")


def _correct(data_fol: Path, args: argparse.Namespace) -> None:
    """Write one hand correction and print its rows."""
    if args.command == "restore":
        rows = restore_drops(
            data_fol, args.word, args.language, reason=args.reason, keys=args.keys
        )
    else:
        rows = [pin_sense(data_fol, get_store(), args.word, args.language, args.key)]
    for row in rows:
        _out(row.model_dump_json())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sense_review_cli")
    sub = parser.add_subparsers(dest="command", required=True)
    worklist = sub.add_parser("worklist", help="rebuild a language's worklist")
    worklist.add_argument("--language", required=True)
    worklist.add_argument("--size", type=int, default=DEFAULT_WORKLIST_SIZE)
    sub.add_parser("import-gold", help="record the gold lemmas as reviewed rows")
    serve = sub.add_parser("serve", help="reserve and print the next batch")
    serve.add_argument("--batch", required=True)
    serve.add_argument("--size", type=int, default=DEFAULT_BATCH_SIZE)
    serve.add_argument("--language")
    serve.add_argument("--gold", type=int, default=DEFAULT_GOLD_PER_BATCH)
    apply = sub.add_parser("apply", help="validate and record a batch's labels")
    apply.add_argument("--batch", required=True)
    apply.add_argument("--labels", type=Path, required=True)
    sub.add_parser("status", help="print the progress per language")
    restore = sub.add_parser("restore", help="retract a lemma's applied drops")
    restore.add_argument("--language", required=True)
    restore.add_argument("--word", required=True)
    restore.add_argument("--reason", required=True)
    restore.add_argument("--keys", nargs="*", default=[])
    pin = sub.add_parser("pin", help="pin one of a lemma's senses as its card")
    pin.add_argument("--language", required=True)
    pin.add_argument("--word", required=True)
    pin.add_argument("--key", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one review command; return the exit code."""
    args = _parser().parse_args(argv)
    params = get_lang_tools_params()
    data_fol = params.paths.data_fol
    guide = params.paths.root_fol / GUIDE
    match args.command:
        case "worklist":
            _worklist(data_fol, args.language, args.size)
        case "import-gold":
            _out(f"imported {import_gold(data_fol, get_store())} gold row(s)")
        case "serve":
            items = serve_batch(
                data_fol,
                get_store(),
                batch=args.batch,
                size=args.size,
                language=args.language,
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
        case "restore" | "pin":
            try:
                _correct(data_fol, args)
            except CorrectionError as error:
                _out(f"NOT WRITTEN: {error}")
                return 1
        case _:
            status = review_status(data_fol)
            for language, (done, total) in status.languages.items():
                _out(f"{language}: {done}/{total}")
            _out(
                f"batches {status.batches}, pending {status.pending}, "
                f"gold agreement {status.gold_agree}/{status.gold_total}, "
                f"edge cases {status.edge_cases}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
