"""Tests for the Wikidata staging adapter's pure cores (`ingestion.staging.wikidata`).

The SPARQL request (`probe_wikidata_lexemes`/`_sparql_get`) is network-isolated
and not exercised; only the query builders, the language map, and the result
flatteners are tested.
"""

from __future__ import annotations

import pytest

from lang_tools.lexicon.ingestion.staging.wikidata import UnknownWikidataLanguageError
from lang_tools.lexicon.ingestion.staging.wikidata import _count_from_result
from lang_tools.lexicon.ingestion.staging.wikidata import _first_lemma
from lang_tools.lexicon.ingestion.staging.wikidata import _lang_item
from lang_tools.lexicon.ingestion.staging.wikidata import _sample_rows
from lang_tools.lexicon.ingestion.staging.wikidata import build_lexeme_count_query
from lang_tools.lexicon.ingestion.staging.wikidata import build_lexeme_sample_query
from lang_tools.lexicon.ingestion.staging.wikidata import parse_lexeme_dump_records


def test_lang_item_known_and_unknown() -> None:
    assert _lang_item("en") == "Q1860"
    with pytest.raises(UnknownWikidataLanguageError):
        _lang_item("xx")


def test_count_query_targets_the_language_item() -> None:
    query = build_lexeme_count_query("Q1860")
    assert "wd:Q1860" in query
    assert "COUNT(?l)" in query
    assert "ontolex:LexicalEntry" in query


def test_sample_query_has_limit_and_optional_category() -> None:
    query = build_lexeme_sample_query("Q652", 50)
    assert "wd:Q652" in query
    assert "LIMIT 50" in query
    assert "OPTIONAL" in query
    assert "wikibase:lemma" in query


def test_count_from_result_reads_binding_and_empty() -> None:
    result = {"results": {"bindings": [{"count": {"value": "942817"}}]}}
    assert _count_from_result(result) == 942817
    assert _count_from_result({"results": {"bindings": []}}) == 0


def test_first_lemma_prefers_language_then_falls_back() -> None:
    lemmas = {"en": {"value": "house"}, "en-gb": {"value": "house-gb"}}
    assert _first_lemma(lemmas, "en") == "house"
    # no exact-language key -> first available value
    assert _first_lemma({"it": {"value": "casa"}}, "en") == "casa"
    assert _first_lemma({}, "en") == ""


def test_parse_dump_filters_by_language_and_maps_back() -> None:
    records = [
        {
            "id": "L1",
            "language": "Q1860",
            "lexicalCategory": "Q1084",
            "lemmas": {"en": {"value": "house"}},
        },
        {"id": "L2", "language": "Q652", "lemmas": {"it": {"value": "casa"}}},  # it
        {"id": "L3", "language": "Q150", "lemmas": {"fr": {"value": "x"}}},  # not asked
    ]
    rows = list(parse_lexeme_dump_records(records, ["en", "it"]))
    assert rows == [
        {"lang": "en", "lexeme": "L1", "lemma": "house", "category": "Q1084"},
        {"lang": "it", "lexeme": "L2", "lemma": "casa", "category": ""},
    ]


def test_parse_dump_unknown_language_raises() -> None:
    with pytest.raises(UnknownWikidataLanguageError):
        list(parse_lexeme_dump_records([], ["xx"]))


def test_sample_rows_flattens_with_missing_category() -> None:
    result = {
        "results": {
            "bindings": [
                {
                    "l": {"value": "http://www.wikidata.org/entity/L1"},
                    "lemma": {"value": "casa"},
                    "category": {"value": "http://www.wikidata.org/entity/Q1084"},
                },
                {"l": {"value": "L2"}, "lemma": {"value": "gatto"}},  # no category
            ],
        },
    }
    rows = _sample_rows(result)
    assert rows == [
        {
            "lexeme": "http://www.wikidata.org/entity/L1",
            "lemma": "casa",
            "category": "http://www.wikidata.org/entity/Q1084",
        },
        {"lexeme": "L2", "lemma": "gatto", "category": ""},
    ]
