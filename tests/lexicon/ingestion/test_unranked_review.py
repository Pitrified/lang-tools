"""Tests for the unranked-word review: worklist, labels, batches, buckets."""

from typing import TYPE_CHECKING

import pytest

from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.ingestion.form_review import MEMBER_FORM_DROPS_FILE
from lang_tools.lexicon.ingestion.form_review import FormDrop
from lang_tools.lexicon.ingestion.review_batches import LabelError
from lang_tools.lexicon.ingestion.unranked_review import BUCKETS_FILE
from lang_tools.lexicon.ingestion.unranked_review import DROP_KIND
from lang_tools.lexicon.ingestion.unranked_review import REVIEW_LOG_FILE
from lang_tools.lexicon.ingestion.unranked_review import CommonnessBucket
from lang_tools.lexicon.ingestion.unranked_review import UnrankedLogRow
from lang_tools.lexicon.ingestion.unranked_review import apply_batch
from lang_tools.lexicon.ingestion.unranked_review import build_worklist
from lang_tools.lexicon.ingestion.unranked_review import load_buckets
from lang_tools.lexicon.ingestion.unranked_review import parse_labels
from lang_tools.lexicon.ingestion.unranked_review import render_batch
from lang_tools.lexicon.ingestion.unranked_review import review_status
from lang_tools.lexicon.ingestion.unranked_review import save_worklist
from lang_tools.lexicon.ingestion.unranked_review import serve_batch
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.lemma_store import LexiconStore
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import read_jsonl
from lang_tools.lexicon.sense import Sense

if TYPE_CHECKING:
    from pathlib import Path

C_ONE = "c__one-thing__0011aabbccdd"
C_TWO = "c__two-thing__0022bbccddee"

PEUGA = Lemma(text="peúga", language="pt", part_of_speech="noun")
MAGESTOSO = Lemma(text="magestoso", language="pt", part_of_speech="adjective")
WALKOUT = Lemma(text="walkout", language="pt", part_of_speech="noun")
COMMON = Lemma(text="casa", language="pt", part_of_speech="noun")
MULTI = Lemma(text="guarda chuva", language="pt", part_of_speech="noun")
NAME = Lemma(text="Lisboa", language="pt", part_of_speech="noun")
SOCK = Lemma(text="sock", language="en", part_of_speech="noun")
HOUSE = Lemma(text="house", language="en", part_of_speech="noun")


def _store() -> LexiconStore:
    lemmas = [PEUGA, MAGESTOSO, WALKOUT, COMMON, MULTI, NAME, SOCK, HOUSE]
    return LexiconStore.from_models(
        lemmas=lemmas,
        concepts=[
            Concept(id=C_ONE, definitions={"en": "a short stocking"}),
            Concept(id=C_TWO, definitions={"en": "a place to live"}),
        ],
        senses=[
            Sense(lemma_id=PEUGA.id, concept_id=C_ONE),
            Sense(lemma_id=MAGESTOSO.id, concept_id=C_ONE),
            Sense(lemma_id=MAGESTOSO.id, concept_id=C_TWO),
            Sense(lemma_id=WALKOUT.id, concept_id=C_TWO),
            Sense(lemma_id=COMMON.id, concept_id=C_TWO, token_frequency=5.1),
            Sense(lemma_id=MULTI.id, concept_id=C_TWO),
            Sense(lemma_id=NAME.id, concept_id=C_TWO),
            Sense(lemma_id=SOCK.id, concept_id=C_ONE),
            Sense(lemma_id=HOUSE.id, concept_id=C_TWO),
        ],
        lookalikes=[],
        concept_relations=[],
        sense_relations=[],
    )


def _served(tmp_path: Path, batch: str = "u0001", size: int = 200) -> tuple:
    store = _store()
    save_worklist(tmp_path, build_worklist(store))
    return store, serve_batch(tmp_path, store, batch=batch, size=size)


def test_worklist_takes_single_lowercase_pt_words_without_frequency() -> None:
    texts = [item.lemma_text for item in build_worklist(_store())]
    assert texts == ["magestoso", "peúga", "walkout"]


def test_labels_parse_every_label() -> None:
    text = (
        "# a comment\n"
        "1 c\n"
        "2 u # unsure\n"
        "3 r # a mineral\n"
        "4 m majestoso # missing j\n"
        "5 f en # English loanword\n"
        "6 x # glued words\n"
    )
    labels = parse_labels("u0001", text, {1, 2, 3, 4, 5, 6})
    assert [labels[n].label for n in range(1, 7)] == list("curmfx")
    assert labels[2].reason == "unsure"
    assert (labels[4].extra, labels[4].reason) == ("majestoso", "missing j")
    assert (labels[5].extra, labels[5].reason) == ("en", "English loanword")


def test_labels_list_every_problem() -> None:
    text = (
        "1 m # no spelling\n"
        "2 f # no language\n"
        "3 q\n"
        "4 m majestoso\n"
        "5 c extra\n"
        "6 x\n"
        "7 f english # long code\n"
        "9 c\n"
        "oops\n"
        "1 c\n"
    )
    with pytest.raises(LabelError) as caught:
        parse_labels("u0001", text, {1, 2, 3, 4, 5, 6, 7, 8})
    problems = caught.value.problems
    assert "item 1: m needs the correct spelling, one word" in problems
    assert "item 2: f needs a language code (en, it, ...)" in problems
    assert any(p.startswith("item 3 has no known label") for p in problems)
    assert "item 4: m needs a reason after #" in problems
    assert "item 5: c takes nothing before the reason" in problems
    assert "item 6: x needs a reason after #" in problems
    assert "item 7: f needs a language code (en, it, ...)" in problems
    assert "item 9 is not in the batch" in problems
    assert "unparseable line 'oops'" in problems
    assert "item 1 is labelled twice" in problems
    assert "missing item(s) 3, 8" in problems


def test_serve_renders_links_and_reserves_distinct_items(tmp_path: Path) -> None:
    store, items = _served(tmp_path, size=2)
    assert [item.lemma_text for item in items] == ["magestoso", "peúga"]
    assert "1 magestoso (adjective)" in render_batch(items)
    assert "  a short stocking [sock]" in render_batch(items)
    assert {link.concept_key for link in items[0].links} == {
        concept_key(C_ONE),
        concept_key(C_TWO),
    }
    assert serve_batch(tmp_path, store, batch="u0001") == items
    second = serve_batch(tmp_path, store, batch="u0002", size=2)
    assert [item.lemma_text for item in second] == ["walkout"]
    assert serve_batch(tmp_path, store, batch="u0003") == []
    assert review_status(tmp_path).pending == ["u0001", "u0002"]


def test_apply_writes_drop_bucket_and_log_rows(tmp_path: Path) -> None:
    _, items = _served(tmp_path)
    by_text = {item.lemma_text: item.n for item in items}
    labels = "\n".join(
        [
            f"{by_text['magestoso']} m majestoso # missing j",
            f"{by_text['peúga']} c",
            f"{by_text['walkout']} f en # English word",
        ]
    )
    guide = tmp_path / "guide.md"
    guide.write_text("rules")
    log = apply_batch(tmp_path, "u0001", labels, guide_path=guide)
    assert {row.text: row.label for row in log} == {
        "magestoso": "m",
        "peúga": "c",
        "walkout": "f",
    }

    drops = read_jsonl(FormDrop, curated_path(tmp_path, MEMBER_FORM_DROPS_FILE))
    assert sorted((d.form, d.concept_key) for d in drops) == sorted(
        [
            ("magestoso", concept_key(C_ONE)),
            ("magestoso", concept_key(C_TWO)),
            ("walkout", concept_key(C_TWO)),
        ]
    )
    assert {d.kind for d in drops} == {DROP_KIND}
    assert {d.status for d in drops} == {"accepted"}
    assert {d.prompt_sha for d in drops} == {log[0].rulebook_sha}
    assert log[0].rulebook_sha
    magestoso = next(d for d in drops if d.form == "magestoso")
    assert "majestoso" in magestoso.reason
    assert "missing j" in magestoso.reason

    buckets = read_jsonl(CommonnessBucket, curated_path(tmp_path, BUCKETS_FILE))
    assert [(b.text, b.bucket, b.status) for b in buckets] == [
        ("peúga", "common", "accepted")
    ]
    rows = read_jsonl(UnrankedLogRow, curated_path(tmp_path, REVIEW_LOG_FILE))
    assert {row.text: row.label for row in rows} == {
        "magestoso": "m",
        "peúga": "c",
        "walkout": "f",
    }
    status = review_status(tmp_path)
    assert (status.labelled, status.labels, status.pending) == (
        3,
        {"c": 1, "f": 1, "m": 1},
        [],
    )
    with pytest.raises(ValueError, match="already applied"):
        serve_batch(tmp_path, _store(), batch="u0001")


def test_bad_labels_write_nothing(tmp_path: Path) -> None:
    _, items = _served(tmp_path)
    guide = tmp_path / "guide.md"
    guide.write_text("rules")
    with pytest.raises(LabelError):
        apply_batch(tmp_path, "u0001", "1 c", guide_path=guide)
    assert not curated_path(tmp_path, REVIEW_LOG_FILE).exists()
    assert not curated_path(tmp_path, MEMBER_FORM_DROPS_FILE).exists()
    assert serve_batch(tmp_path, _store(), batch="u0001") == items


def test_apply_without_pending_batch_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        apply_batch(tmp_path, "u0009", "1 c", guide_path=tmp_path / "guide.md")


def test_latest_bucket_row_wins(tmp_path: Path) -> None:
    path = curated_path(tmp_path, BUCKETS_FILE)
    assert load_buckets(tmp_path) == {}
    first = CommonnessBucket(
        lemma_id="a", language="pt", text="w", bucket="rare", status="accepted"
    )
    later = first.model_copy(update={"bucket": "common"})
    other = CommonnessBucket(
        lemma_id="b", language="pt", text="v", bucket="uncommon", status="proposed"
    )
    path.parent.mkdir(parents=True)
    path.write_text(
        "".join(row.model_dump_json() + "\n" for row in (first, other, later))
    )
    buckets = load_buckets(tmp_path)
    assert {lid: row.bucket for lid, row in buckets.items()} == {"a": "common"}
