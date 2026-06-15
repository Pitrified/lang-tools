"""Tests for `lang_tools.lexicon.ingestion.wiktionary`."""

from io import StringIO

from lang_tools.lexicon.ingestion.wiktionary import load_wiktionary_jsonl


def test_load_wiktionary_jsonl_basic() -> None:
    line = (
        '{"word": "amor", "lang_code": "pt", "pos": "noun", '
        '"senses": [{"glosses": ["love"]}]}'
    )
    lemmas = list(load_wiktionary_jsonl(StringIO(line + "\n"), language="pt"))
    assert len(lemmas) == 1
    assert lemmas[0].text == "amor"
    assert lemmas[0].sources == ["wiktionary"]


def test_load_wiktionary_jsonl_filters_pos() -> None:
    bad = '{"word": "x", "lang_code": "pt", "pos": "letter", "senses": []}'
    lemmas = list(load_wiktionary_jsonl(StringIO(bad + "\n"), language="pt"))
    assert lemmas == []


def test_load_wiktionary_jsonl_skips_form_of() -> None:
    line = (
        '{"word": "amei", "lang_code": "pt", "pos": "verb", '
        '"form_of": [{"word": "amar"}], '
        '"senses": [{"glosses": ["loved"]}]}'
    )
    lemmas = list(load_wiktionary_jsonl(StringIO(line + "\n"), language="pt"))
    assert lemmas == []
