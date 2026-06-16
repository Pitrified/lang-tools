"""Tests for the kaikki source adapter (`ingestion.sources.kaikki`)."""

from io import StringIO

from lang_tools.lexicon.ingestion.sources.kaikki import load_kaikki_entries


def test_load_kaikki_entries_collects_glosses_and_examples() -> None:
    line = (
        '{"word": "casa", "pos": "noun", "senses": ['
        '{"glosses": ["house", "home"], '
        '"examples": [{"text": "a casa", "english": "the house"}]}]}'
    )
    [entry] = list(load_kaikki_entries(StringIO(line + "\n"), language="pt"))
    assert entry.text == "casa"
    assert entry.language == "pt"
    assert entry.definitions == ["house", "home"]
    assert entry.examples[0].sentence == "a casa"
    assert entry.examples[0].translation == "the house"


def test_key_is_normalized_text_and_language() -> None:
    line = '{"word": "Ação", "senses": [{"glosses": ["action"]}]}'
    [entry] = list(load_kaikki_entries(StringIO(line + "\n"), language="pt"))
    assert entry.key == ("acao", "pt")


def test_malformed_and_headless_lines_skipped() -> None:
    lines = [
        "not json",
        '{"word": "", "senses": []}',
        '{"word": "ok", "senses": [{"glosses": ["fine"]}]}',
    ]
    entries = list(load_kaikki_entries(StringIO("\n".join(lines)), language="en"))
    assert [e.text for e in entries] == ["ok"]
