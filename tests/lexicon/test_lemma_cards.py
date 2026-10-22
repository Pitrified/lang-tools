"""Tests for the drill view (`LemmaCard` / `CardQuery`) and lemma paging."""

import pytest

from lang_tools.lexicon.card import CardQuery
from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.lemma_store import LexiconStore
from lang_tools.lexicon.sense import Sense

C_HOUSE = "c__house-building__0011aabbccdd"
C_HOME = "c__home-dwelling__0022bbccddee"
C_COFFEE = "c__coffee-drink__0033ccddeeff"
C_LISBON = "c__lisbon-city__0044ddeeff00"


def _store() -> LexiconStore:
    """Build a small pt/en graph with one polysemous pt lemma (casa)."""
    casa = Lemma(text="casa", language="pt", part_of_speech="noun")
    lar = Lemma(text="lar", language="pt", part_of_speech="noun")
    cafe = Lemma(text="café", language="pt", part_of_speech="noun")
    lisboa = Lemma(text="Lisboa", language="pt", part_of_speech="noun")
    guarda_chuva = Lemma(text="guarda-chuva", language="pt", part_of_speech="noun")
    house = Lemma(text="house", language="en", part_of_speech="noun")
    home = Lemma(text="home", language="en", part_of_speech="noun")
    coffee = Lemma(text="coffee", language="en", part_of_speech="noun")
    lemmas = [casa, lar, cafe, lisboa, guarda_chuva, house, home, coffee]
    concepts = [
        Concept(
            id=C_HOUSE,
            definitions={"en": "a building to live in", "pt": "edificio"},
            examples={"pt": ["A casa é grande."], "en": ["The house is big."]},
            topics=["home"],
        ),
        Concept(id=C_HOME, definitions={"en": "where one lives"}),
        Concept(id=C_COFFEE, definitions={"en": "a hot drink"}),
        Concept(id=C_LISBON, definitions={"en": "capital of Portugal"}),
    ]
    senses = [
        # casa: the more frequent sense is HOUSE (A1); HOME is rarer.
        Sense(
            lemma_id=casa.id, concept_id=C_HOUSE, sense_frequency=5.0, cefr_level="A1"
        ),
        Sense(
            lemma_id=casa.id, concept_id=C_HOME, sense_frequency=3.0, cefr_level="A2"
        ),
        Sense(lemma_id=lar.id, concept_id=C_HOME, sense_frequency=3.0, cefr_level="B1"),
        Sense(
            lemma_id=cafe.id, concept_id=C_COFFEE, sense_frequency=4.5, cefr_level="A1"
        ),
        Sense(
            lemma_id=lisboa.id,
            concept_id=C_LISBON,
            sense_frequency=4.0,
            cefr_level="B2",
        ),
        Sense(
            lemma_id=house.id, concept_id=C_HOUSE, sense_frequency=5.5, cefr_level="A1"
        ),
        Sense(
            lemma_id=home.id, concept_id=C_HOME, sense_frequency=5.2, cefr_level="A1"
        ),
        Sense(
            lemma_id=home.id, concept_id=C_HOUSE, sense_frequency=2.0, cefr_level="B1"
        ),
        Sense(
            lemma_id=coffee.id,
            concept_id=C_COFFEE,
            sense_frequency=5.0,
            cefr_level="A1",
        ),
    ]
    return LexiconStore.from_models(
        lemmas=lemmas,
        concepts=concepts,
        senses=senses,
        false_friends=[],
        concept_relations=[],
        sense_relations=[],
    )


def _texts(cards) -> list[str]:  # noqa: ANN001
    return sorted(card.lemma.text for card in cards)


def test_card_picks_the_most_frequent_sense() -> None:
    store = _store()
    card = store.lemma_card(Lemma(text="casa", language="pt").id)
    assert card is not None
    assert card.concept_id == C_HOUSE
    assert card.cefr_level == "A1"
    assert card.gloss == "a building to live in"
    assert card.examples == ["A casa é grande."]


def test_card_translations_are_ordered_by_frequency() -> None:
    store = _store()
    card = store.lemma_card(
        Lemma(text="casa", language="pt").id,
        translation_languages=("en", "pt"),
    )
    assert card is not None
    # house (5.5) before home (2.0) on the HOUSE concept.
    assert card.translations["en"] == ["house", "home"]
    # The card's own lemma is never its own synonym.
    assert card.translations["pt"] == []


def test_frequency_tie_goes_to_the_more_common_concept() -> None:
    """Outside English every sense ties on frequency; commonness breaks it."""
    pedra = Lemma(text="pedra", language="pt")
    rare = "c__aaa-rare__0055eeff0011"  # sorts first by id
    common = "c__zzz-stone__0066ff001122"
    store = LexiconStore.from_models(
        lemmas=[pedra],
        concepts=[
            Concept(id=rare, definitions={"en": "a rare meaning"}, commonness=0.3),
            Concept(id=common, definitions={"en": "a rock"}, commonness=2.1),
        ],
        senses=[
            Sense(lemma_id=pedra.id, concept_id=rare, sense_frequency=4.0),
            Sense(lemma_id=pedra.id, concept_id=common, sense_frequency=4.0),
        ],
        false_friends=[],
        concept_relations=[],
        sense_relations=[],
    )
    card = store.lemma_card(pedra.id)
    assert card is not None
    assert card.concept_id == common


def test_card_gloss_language() -> None:
    store = _store()
    card = store.lemma_card(Lemma(text="casa", language="pt").id, gloss_language="pt")
    assert card is not None
    assert card.gloss == "edificio"


def test_missing_card_is_none() -> None:
    assert _store().lemma_card("nope") is None


def test_single_word_drops_proper_nouns_and_compounds() -> None:
    store = _store()
    cards = store.lemma_cards(CardQuery(language="pt", single_word=True))
    assert _texts(cards) == ["café", "casa", "lar"]


def test_cefr_window() -> None:
    store = _store()
    easy = store.lemma_cards(CardQuery(language="pt", max_cefr="A2"))
    assert _texts(easy) == ["café", "casa"]
    hard = store.lemma_cards(CardQuery(language="pt", min_cefr="B2"))
    assert _texts(hard) == ["Lisboa"]


def test_accented_length_and_pos_filters() -> None:
    store = _store()
    assert _texts(store.lemma_cards(CardQuery(language="pt", accented_only=True))) == [
        "café",
    ]
    assert _texts(store.lemma_cards(CardQuery(language="pt", length=3))) == ["lar"]
    assert store.lemma_cards(CardQuery(language="pt", part_of_speech="verb")) == []


def test_require_translation_and_example() -> None:
    store = _store()
    with_en = store.lemma_cards(CardQuery(language="pt", require_translation=True))
    assert _texts(with_en) == ["café", "casa", "lar"]
    with_example = store.lemma_cards(CardQuery(language="pt", require_example=True))
    assert _texts(with_example) == ["casa"]


def test_topic_and_exclude() -> None:
    store = _store()
    assert _texts(store.lemma_cards(CardQuery(language="pt", topic="home"))) == ["casa"]
    casa_id = Lemma(text="casa", language="pt").id
    rest = store.lemma_cards(
        CardQuery(language="pt", single_word=True, exclude_ids=[casa_id]),
    )
    assert _texts(rest) == ["café", "lar"]


def test_frequency_order_and_limit() -> None:
    store = _store()
    cards = store.lemma_cards(CardQuery(language="pt", order="frequency", limit=2))
    assert [card.lemma.text for card in cards] == ["casa", "café"]


def test_seeded_order_is_deterministic() -> None:
    store = _store()
    query = CardQuery(language="pt", seed=7)
    first = [card.lemma.id for card in store.lemma_cards(query)]
    second = [card.lemma.id for card in store.lemma_cards(query)]
    assert first == second
    assert len(first) == 5


def test_limit_is_capped() -> None:
    with pytest.raises(ValueError, match="less than or equal"):
        CardQuery(limit=10_000)


def test_lemma_paging_and_prefix_search() -> None:
    store = _store()
    page_1 = store.get_lemmas_filtered(language="pt", limit=2)
    page_2 = store.get_lemmas_filtered(language="pt", limit=2, offset=2)
    assert [lem.text for lem in page_1] == ["café", "casa"]
    assert [lem.text for lem in page_2] == ["guarda-chuva", "lar"]
    # The prefix is folded like `normalized`, so "CAF" finds café.
    assert [lem.text for lem in store.get_lemmas_filtered(query="CAF")] == ["café"]
    assert store.count_lemmas_filtered(language="pt") == 5
    assert store.count_lemmas_filtered(language="pt", query="ca") == 2
