"""Tests for `lang_tools.language.normalization`."""

from lang_tools.language import normalize
from lang_tools.language.language import LANGUAGE_PRESETS
from lang_tools.language.normalization import extract_accented_chars
from lang_tools.language.normalization import has_accent


def test_normalize_strips_accents() -> None:
    assert normalize("café") == "cafe"
    assert normalize("naïve") == "naive"
    assert normalize("Ação") == "acao"


def test_normalize_lowercases() -> None:
    assert normalize("HÉLLO") == "hello"


def test_normalize_uses_language_map() -> None:
    pt = LANGUAGE_PRESETS["pt"]
    # Portuguese preset still strips accents.
    assert normalize("São Paulo", pt) == "sao paulo"


def test_has_accent_detects_diacritics() -> None:
    assert has_accent("café") is True
    assert has_accent("hello") is False


def test_extract_accented_chars_returns_set() -> None:
    chars = extract_accented_chars("crème brûlée")
    assert "è" in chars
    assert "û" in chars
    assert "é" in chars
