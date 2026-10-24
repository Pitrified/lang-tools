"""Tests for `lang_tools.lexicon.ingestion.static_list`."""

from lang_tools.lexicon.ingestion.static_list import load_static_list


def test_load_static_list_yields_lemmas() -> None:
    entries = [
        {"text": "amor", "language": "pt"},
        {"text": "amour", "language": "fr"},
    ]
    lemmas = list(load_static_list(entries))
    assert len(lemmas) == 2
    assert all(lemma.sources == ["static_list"] for lemma in lemmas)
