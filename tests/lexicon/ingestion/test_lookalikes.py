"""Tests for look-alike candidates (`ingestion.lookalikes`, phase 11)."""

from pathlib import Path

import pytest

from lang_tools.lexicon.ingestion.lookalikes import DEFAULT_SELECT_THRESHOLD
from lang_tools.lexicon.ingestion.lookalikes import GoldPair
from lang_tools.lexicon.ingestion.lookalikes import LookalikeCandidate
from lang_tools.lexicon.ingestion.lookalikes import accept_run
from lang_tools.lexicon.ingestion.lookalikes import apply_lookalikes
from lang_tools.lexicon.ingestion.lookalikes import cognate_key
from lang_tools.lexicon.ingestion.lookalikes import find_candidates
from lang_tools.lexicon.ingestion.lookalikes import key_similarity
from lang_tools.lexicon.ingestion.lookalikes import load_gold
from lang_tools.lexicon.ingestion.lookalikes import proposals_from_verdicts
from lang_tools.lexicon.ingestion.lookalikes import score_against_gold
from lang_tools.lexicon.ingestion.lookalikes import select_candidates
from lang_tools.lexicon.ingestion.lookalikes import skeleton
from lang_tools.lexicon.ingestion.lookalikes import verify_chunks
from lang_tools.lexicon.ingestion.pipeline import build_initial
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.lemma_id import lemma_id
from lang_tools.lexicon.lemma_store import LexiconStore
from lang_tools.llm.lookalike_verify import KeyedVerdict
from lang_tools.llm.lookalike_verify import LookalikeVerifyOutput
from lang_tools.params.lang_tools_params import get_lang_tools_params


@pytest.mark.parametrize(
    ("a", "b"),
    [
        (("factory", "en", "noun"), ("fattoria", "it", "noun")),
        (("exquisite", "en", "adjective"), ("esquisito", "pt", "adjective")),
        (("nation", "en", "noun"), ("nação", "pt", "noun")),
        (("nação", "pt", "noun"), ("nazione", "it", "noun")),
        (("possible", "en", "adjective"), ("possível", "pt", "adjective")),
        (("balcony", "en", "noun"), ("balcão", "pt", "noun")),
        (("family", "en", "noun"), ("família", "pt", "noun")),
        (("actually", "en", "adverb"), ("atualmente", "pt", "adverb")),
        (("guardar", "pt", "verb"), ("guardare", "it", "verb")),
        (("soap", "en", "noun"), ("sopa", "pt", "noun")),
        (("escorpião", "pt", "noun"), ("scorpione", "it", "noun")),
    ],
)
def test_related_forms_share_a_key(
    a: tuple[str, str, str],
    b: tuple[str, str, str],
) -> None:
    assert cognate_key(*a) == cognate_key(*b)


def test_rules_that_need_context() -> None:
    # pt -ção is the -tion family; -cão (balcão) is not.
    assert cognate_key("nação", "pt").endswith("sion")
    assert not cognate_key("balcão", "pt").endswith("sion")
    # -ly is the adverb ending only on adverbs.
    assert cognate_key("family", "en", "noun") != cognate_key("family", "en", "adverb")
    # A verb loses its infinitive; the same form as a noun keeps it.
    assert cognate_key("puxar", "pt", "verb") == "pux"
    assert cognate_key("mar", "pt", "noun") == "mar"
    # The cedilla stays soft before a / o / u.
    assert cognate_key("cabeça", "pt") == "kabes"


def test_unrelated_forms_stay_apart() -> None:
    assert cognate_key("casa", "pt") != cognate_key("cast", "en")
    feia, festival = cognate_key("feia", "pt"), cognate_key("festival", "en")
    assert key_similarity(feia, festival) < DEFAULT_SELECT_THRESHOLD


def test_similarity_and_skeleton() -> None:
    assert key_similarity("abc", "abc") == 1.0
    assert key_similarity("abcd", "abce") == 0.75
    assert key_similarity("", "abc") == 0.0
    assert skeleton("lanx") == skeleton("lunx") == "lnx"


def _entries() -> list[SynsetEntry]:
    return [
        SynsetEntry("en", "en-1", "i1", "a people", ("nation",), pos="n"),
        SynsetEntry("pt", "pt-1", "i1", None, ("nação",), pos="n"),
        SynsetEntry("it", "it-1", "i1", None, ("nazione",), pos="n"),
        SynsetEntry("en", "en-2", "i2", "strange", ("weird",), pos="a"),
        SynsetEntry("pt", "pt-2", "i2", None, ("esquisito",), pos="a"),
        SynsetEntry("en", "en-3", "i3", "of rare beauty", ("exquisite",), pos="a"),
        SynsetEntry("en", "en-4", "i4", "a domestic feline", ("cat",), pos="n"),
        SynsetEntry("pt", "pt-4", "i4", None, ("gato",), pos="n"),
    ]


def test_find_candidates_labels_cognates_and_lookalikes(tmp_path: Path) -> None:
    build_initial(["en", "pt", "it"], data_fol=tmp_path, omw_entries=_entries())
    found = {(c.target_text, c.known_text): c for c in find_candidates(tmp_path)}
    assert found[("nação", "nation")].kind == "cognate"
    assert found[("nação", "nazione")].kind == "cognate"
    assert found[("nação", "nazione")].same_key
    trap = found[("esquisito", "exquisite")]
    assert trap.kind == "full"
    assert not trap.shares_concept
    assert ("gato", "cat") not in found


def _cand(
    target: str, known: str, sim: float, zipf: float | None = 4.0
) -> LookalikeCandidate:
    return LookalikeCandidate(
        target_id=target,
        target_text=target,
        known_id=known,
        known_text=known,
        known_language="en",
        similarity=sim,
        kind="full",
        shares_concept=False,
        known_zipf=zipf,
    )


def test_select_keeps_the_best_per_target_above_the_floors() -> None:
    cands = [
        _cand("t1", "a", 0.95),
        _cand("t1", "b", 0.9),
        _cand("t1", "c", 0.85),
        _cand("t2", "d", 0.6),  # below the threshold
        _cand("t3", "e", 0.9, zipf=1.0),  # known word too rare to know
    ]
    kept = select_candidates(cands, per_target=2, threshold=0.75, min_known_zipf=2.0)
    assert [(c.target_id, c.known_id) for c in kept] == [("t1", "a"), ("t1", "b")]


def test_score_against_gold_counts_recall_per_kind() -> None:
    gold = [
        GoldPair(
            pair="pt-en",
            pt="t1",
            other_language="en",
            other="a",
            kind="full",
            reason="",
            pt_lemma_id="t1",
            other_lemma_id="a",
        ),
        GoldPair(
            pair="pt-en",
            pt="t9",
            other_language="en",
            other="z",
            kind="cognate",
            reason="",
            pt_lemma_id="t9",
            other_lemma_id="z",
        ),
    ]
    score = score_against_gold([_cand("t1", "a", 0.9)], gold)
    assert score.recall("full") == 1.0
    assert score.recall("cognate") == 0.0
    assert score.kind_agreement == {"full->full": 1}


def test_committed_gold_set_is_consistent() -> None:
    gold = load_gold(get_lang_tools_params().paths.data_fol)
    if not gold:
        pytest.skip("no committed gold set in this checkout")
    assert len(gold) == 200
    assert len({g.ids for g in gold}) == 200
    for g in gold:
        assert g.pt_lemma_id == lemma_id(g.pt, "pt")
        assert g.other_lemma_id == lemma_id(g.other, g.other_language)
        assert g.pair == f"pt-{g.other_language}"


def test_verify_chunks_proposals_and_edges(tmp_path: Path) -> None:
    build_initial(["en", "pt", "it"], data_fol=tmp_path, omw_entries=_entries())
    store = LexiconStore.from_data_fol(tmp_path)
    cands = select_candidates(find_candidates(tmp_path), min_known_zipf=0.0)
    chunks = verify_chunks(store, cands, size=1)
    assert len(chunks) == len(cands)
    first = chunks[0][1]
    assert first.target_language_name == "Portuguese"
    assert first.pairs[0].target_senses  # grounded in the word's senses

    trap = next(c for c in cands if c.target_text == "esquisito")
    nation = next(c for c in cands if c.known_text == "nation")
    output = LookalikeVerifyOutput(
        verdicts=[
            KeyedVerdict(key=trap.key, kind="full", note="pt esquisito means  weird"),
            KeyedVerdict(key=nation.key, kind="cognate", note="ignored"),
            KeyedVerdict(key="mistyped:key", kind="full", note="x"),
        ],
    )
    rows = proposals_from_verdicts(cands, [output], model="m")
    assert {(r.target_text, r.kind, r.status) for r in rows} == {
        ("esquisito", "full", "proposed"),
        ("nação", "cognate", "proposed"),
    }
    assert next(r for r in rows if r.kind == "full").note == "pt esquisito means weird"
    assert next(r for r in rows if r.kind == "cognate").note == ""

    accepted = accept_run(rows, languages=["en"])
    edges, stale = apply_lookalikes(
        [trap.target_id, trap.known_id, nation.target_id, nation.known_id],
        accepted,
    )
    assert stale == 0
    assert {e.kind for e in edges} == {"full", "cognate"}
    assert next(e for e in edges if e.kind == "full").explanation_notes == {
        "en": "pt esquisito means weird",
    }


def test_unrelated_and_noteless_verdicts_are_rejected() -> None:
    cand = _cand("t1", "a", 0.9)
    output = LookalikeVerifyOutput(
        verdicts=[KeyedVerdict(key=cand.key, kind="full", note="")],
    )
    assert proposals_from_verdicts([cand], [output])[0].status == "rejected"
    output = LookalikeVerifyOutput(
        verdicts=[KeyedVerdict(key=cand.key, kind="unrelated")],
    )
    row = proposals_from_verdicts([cand], [output])[0]
    assert row.status == "rejected"
    edges, stale = apply_lookalikes(
        ["t1", "a"], [row.model_copy(update={"status": "accepted"})]
    )
    assert edges == []
    assert stale == 0
