"""Tests for `lang_tools.lexicon.sense_id`."""

from lang_tools.lexicon.sense_id import sense_id


def test_sense_id_is_deterministic() -> None:
    a = sense_id("0a1b2c3d4e5f6071", "c__bank-river__0011aabbccdd")
    b = sense_id("0a1b2c3d4e5f6071", "c__bank-river__0011aabbccdd")
    assert a == b


def test_sense_id_is_16_hex_chars() -> None:
    value = sense_id("0a1b2c3d4e5f6071", "c__bank-river__0011aabbccdd")
    assert len(value) == 16
    assert all(c in "0123456789abcdef" for c in value)


def test_sense_id_endpoints_are_ordered() -> None:
    # lemma and concept ids live in distinct namespaces; swapping them is a
    # different edge, so the ids must differ.
    a = sense_id("aaaa", "bbbb")
    b = sense_id("bbbb", "aaaa")
    assert a != b
