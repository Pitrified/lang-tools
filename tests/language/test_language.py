"""Tests for `lang_tools.language.language`."""

import pytest

from lang_tools.language import LANGUAGE_PRESETS
from lang_tools.language import UnknownLanguageError
from lang_tools.language import get_language


def test_presets_include_main_languages() -> None:
    for code in ("pt", "fr", "es", "it", "en", "de"):
        assert code in LANGUAGE_PRESETS


def test_get_language_returns_preset() -> None:
    pt = get_language("pt")
    assert pt.code == "pt"
    assert pt.name.lower().startswith("portuguese")


def test_get_language_unknown_raises() -> None:
    with pytest.raises(UnknownLanguageError):
        get_language("xx")


def test_keyboard_rows_present() -> None:
    fr = get_language("fr")
    assert fr.keyboard_rows
    assert all(isinstance(row, list) for row in fr.keyboard_rows)
