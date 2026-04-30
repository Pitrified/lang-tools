"""Tests for `lang_tools.words.ingestion.wiktionary`."""

from io import StringIO

from lang_tools.words.ingestion.wiktionary import load_wiktionary_jsonl


def test_load_wiktionary_jsonl_basic() -> None:
    line = (
        '{"word": "amor", "lang_code": "pt", "pos": "noun", '
        '"senses": [{"glosses": ["love"]}]}'
    )
    words = list(load_wiktionary_jsonl(StringIO(line + "\n"), language="pt"))
    assert len(words) == 1
    assert words[0].text == "amor"
    assert words[0].sources == ["wiktionary"]


def test_load_wiktionary_jsonl_filters_pos() -> None:
    bad = '{"word": "x", "lang_code": "pt", "pos": "letter", "senses": []}'
    words = list(load_wiktionary_jsonl(StringIO(bad + "\n"), language="pt"))
    assert words == []


def test_load_wiktionary_jsonl_skips_form_of() -> None:
    line = (
        '{"word": "amei", "lang_code": "pt", "pos": "verb", '
        '"form_of": [{"word": "amar"}], '
        '"senses": [{"glosses": ["loved"]}]}'
    )
    words = list(load_wiktionary_jsonl(StringIO(line + "\n"), language="pt"))
    assert words == []
