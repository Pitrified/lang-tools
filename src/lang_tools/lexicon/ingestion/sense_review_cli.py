"""Command line for the card-sense batch review (see `sense_review`).

Usage, with ``CLI=lang_tools.lexicon.ingestion.sense_review_cli``::

    uv run python -m $CLI worklist --language pt
    uv run python -m $CLI worklist-removed --language pt
    uv run python -m $CLI import-gold
    uv run python -m $CLI serve --batch s0001
    uv run python -m $CLI recheck --batch m0001 --keys keys.txt [--shadow]
    uv run python -m $CLI apply --batch s0001 --labels s0001.txt [--shadow]
    uv run python -m $CLI agreement --first m0001 m0002 --second n0001 n0002
    uv run python -m $CLI concepts --word yes --language pt
    uv run python -m $CLI status
    uv run python -m $CLI restore --language pt --word moderna --reason "..."
    uv run python -m $CLI pin --language pt --word copa --key e7aeea438f7f
    uv run python -m $CLI add --language pt --word sim --key 0123456789ab --reason ".."
    uv run python -m $CLI drop --language pt --word yes --key 0123456789ab --reason ".."

``serve`` and ``recheck`` print the batch's lines to stdout (gold items look
like the others); ``recheck`` serves listed worklist lemmas again (one lemma id
per line), and with ``--shadow`` as a second review that writes no curated row.
``apply`` validates the label file and records it, or prints every problem and
exits 1 without writing anything. ``agreement`` compares a first review with a
second one. ``worklist-removed`` appends the lemmas a review removed to the
worklist. ``concepts`` looks up the concept keys an English word names.
``restore``, ``pin``, ``add`` and ``drop`` are the hand corrections: a later
row that retracts a drop, pins another sense, adds a link and pins it, or drops
a wrong link.
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
from lang_tools.lexicon.ingestion.sense_review import SenseWorkItem
from lang_tools.lexicon.ingestion.sense_review import add_sense
from lang_tools.lexicon.ingestion.sense_review import agreement
from lang_tools.lexicon.ingestion.sense_review import apply_batch
from lang_tools.lexicon.ingestion.sense_review import build_worklist
from lang_tools.lexicon.ingestion.sense_review import drop_sense
from lang_tools.lexicon.ingestion.sense_review import find_concepts
from lang_tools.lexicon.ingestion.sense_review import import_gold
from lang_tools.lexicon.ingestion.sense_review import load_gold
from lang_tools.lexicon.ingestion.sense_review import load_worklist
from lang_tools.lexicon.ingestion.sense_review import pin_sense
from lang_tools.lexicon.ingestion.sense_review import recheck_batch
from lang_tools.lexicon.ingestion.sense_review import removed_lemmas
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


def _worklist_removed(data_fol: Path, language: str) -> None:
    """Append the lemmas a review removed to the worklist, after its last rank."""
    items = load_worklist(data_fol)
    listed = {item.lemma_id for item in items}
    removed = [
        (lid, text)
        for lid, text in removed_lemmas(data_fol, get_store(), language)
        if lid not in listed
    ]
    rank = max((item.rank for item in items), default=-1) + 1
    added = [
        SenseWorkItem(rank=rank + i, lemma_id=lid, lemma_text=text, language=language)
        for i, (lid, text) in enumerate(removed)
    ]
    path = write_jsonl([*items, *added], curated_path(data_fol, WORKLIST_FILE))
    _out(f"{len(added)} removed {language} lemma(s) appended -> {path}")


def _concepts(word: str, language: str) -> None:
    """Print the concepts an English word names, for an addition."""
    found = find_concepts(get_store(), word, language=language)
    for option, members in found:
        _out(
            f"{option.concept_key} {option.gloss} [{', '.join(option.translations)}]"
            f" {language}: {', '.join(members) or '-'}"
        )
    if not found:
        _out(f"no concept for en {word!r}")


def _correct(data_fol: Path, args: argparse.Namespace) -> None:
    """Write one hand correction and print its rows."""
    if args.command == "restore":
        rows = restore_drops(
            data_fol, args.word, args.language, reason=args.reason, keys=args.keys
        )
    elif args.command == "add":
        rows = add_sense(
            data_fol,
            get_store(),
            args.word,
            args.language,
            args.key,
            reason=args.reason,
            form_note=args.form_note,
        )
    elif args.command == "drop":
        rows = [
            drop_sense(
                data_fol,
                get_store(),
                args.word,
                args.language,
                args.key,
                reason=args.reason,
            )
        ]
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
    removed = sub.add_parser(
        "worklist-removed", help="append the lemmas a review removed"
    )
    removed.add_argument("--language", required=True)
    sub.add_parser("import-gold", help="record the gold lemmas as reviewed rows")
    serve = sub.add_parser("serve", help="reserve and print the next batch")
    serve.add_argument("--batch", required=True)
    serve.add_argument("--size", type=int, default=DEFAULT_BATCH_SIZE)
    serve.add_argument("--language")
    serve.add_argument("--gold", type=int, default=DEFAULT_GOLD_PER_BATCH)
    recheck = sub.add_parser("recheck", help="serve listed lemmas again")
    recheck.add_argument("--batch", required=True)
    recheck.add_argument("--keys", type=Path, required=True)
    recheck.add_argument("--size", type=int, default=DEFAULT_BATCH_SIZE)
    recheck.add_argument("--gold", type=int, default=DEFAULT_GOLD_PER_BATCH)
    recheck.add_argument("--shadow", action="store_true")
    apply = sub.add_parser("apply", help="validate and record a batch's labels")
    apply.add_argument("--batch", required=True)
    apply.add_argument("--labels", type=Path, required=True)
    apply.add_argument("--shadow", action="store_true")
    agree = sub.add_parser("agreement", help="compare a first and a second review")
    agree.add_argument("--first", nargs="+", required=True)
    agree.add_argument("--second", nargs="+", required=True)
    concepts = sub.add_parser("concepts", help="look up concepts by English word")
    concepts.add_argument("--word", required=True)
    concepts.add_argument("--language", required=True)
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
    add = sub.add_parser("add", help="link a lemma to a concept and pin it")
    add.add_argument("--language", required=True)
    add.add_argument("--word", required=True)
    add.add_argument("--key", required=True)
    add.add_argument("--reason", required=True)
    add.add_argument("--form-note", default="")
    drop = sub.add_parser("drop", help="drop one of a lemma's senses")
    drop.add_argument("--language", required=True)
    drop.add_argument("--word", required=True)
    drop.add_argument("--key", required=True)
    drop.add_argument("--reason", required=True)
    return parser


def _serve(data_fol: Path, guide: Path, args: argparse.Namespace) -> None:
    """Serve the next batch, or re-serve listed lemmas, and print it."""
    if args.command == "serve":
        items = serve_batch(
            data_fol,
            get_store(),
            batch=args.batch,
            size=args.size,
            language=args.language,
            gold_per_batch=args.gold,
        )
    else:
        items = recheck_batch(
            data_fol,
            get_store(),
            batch=args.batch,
            lemma_ids=args.keys.read_text().split(),
            guide_path=guide,
            size=args.size,
            gold_per_batch=args.gold,
            shadow=args.shadow,
        )
    _out(render_batch(items) if items else "nothing left to serve")


def _apply(data_fol: Path, guide: Path, args: argparse.Namespace) -> int:
    """Apply a batch's labels and print its log row, or every problem."""
    try:
        log = apply_batch(
            data_fol,
            args.batch,
            args.labels.read_text(),
            guide_path=guide,
            store=get_store(),
            shadow=args.shadow,
        )
    except LabelError as error:
        _out(
            "NOT APPLIED, fix and re-run:\n"
            + "\n".join(f"- {p}" for p in error.problems)
        )
        return 1
    _out(log.model_dump_json(indent=1, exclude={"outcomes"}))
    return 0


def _status(data_fol: Path) -> None:
    status = review_status(data_fol)
    for language, (done, total) in status.languages.items():
        _out(f"{language}: {done}/{total}")
    _out(
        f"batches {status.batches}, pending {status.pending}, "
        f"gold agreement {status.gold_agree}/{status.gold_total}, "
        f"edge cases {status.edge_cases}"
    )


def main(argv: list[str] | None = None) -> int:
    """Run one review command; return the exit code."""
    args = _parser().parse_args(argv)
    params = get_lang_tools_params()
    data_fol = params.paths.data_fol
    guide = params.paths.root_fol / GUIDE
    match args.command:
        case "worklist":
            _worklist(data_fol, args.language, args.size)
        case "worklist-removed":
            _worklist_removed(data_fol, args.language)
        case "concepts":
            _concepts(args.word, args.language)
        case "import-gold":
            _out(f"imported {import_gold(data_fol, get_store())} gold row(s)")
        case "serve" | "recheck":
            _serve(data_fol, guide, args)
        case "agreement":
            _out(agreement(data_fol, args.first, args.second).model_dump_json(indent=1))
        case "apply":
            return _apply(data_fol, guide, args)
        case "restore" | "pin" | "add" | "drop":
            try:
                _correct(data_fol, args)
            except CorrectionError as error:
                _out(f"NOT WRITTEN: {error}")
                return 1
        case _:
            _status(data_fol)
    return 0


if __name__ == "__main__":
    sys.exit(main())
