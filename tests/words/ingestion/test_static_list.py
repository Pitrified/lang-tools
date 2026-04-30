"""Tests for `lang_tools.words.ingestion.static_list`."""

from lang_tools.words.ingestion.static_list import load_static_list


def test_load_static_list_yields_words() -> None:
    entries = [
        {"text": "amor", "language": "pt"},
        {"text": "amour", "language": "fr"},
    ]
    words = list(load_static_list(entries))
    assert len(words) == 2
    assert all(w.sources == ["static_list"] for w in words)
