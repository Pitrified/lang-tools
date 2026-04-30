"""Language configuration and accent / normalization utilities.

This subpackage provides the canonical `Language` model (code, name, accented
characters, normalization map, keyboard layout) and stateless helpers for
diacritic stripping and accent inspection.

Public API:
    Language: per-language configuration model.
    LANGUAGE_PRESETS: mapping of ISO 639-1 code to preset `Language`.
    get_language: lookup helper that raises `UnknownLanguageError` on miss.
    UnknownLanguageError: raised when an unknown language code is requested.
    normalize: strip diacritics and lowercase.
    has_accent: boolean check for any accented character in text.
    extract_accented_chars: list accented characters present in text.
"""

from lang_tools.language.language import LANGUAGE_PRESETS
from lang_tools.language.language import Language
from lang_tools.language.language import UnknownLanguageError
from lang_tools.language.language import get_language
from lang_tools.language.normalization import extract_accented_chars
from lang_tools.language.normalization import has_accent
from lang_tools.language.normalization import normalize

__all__ = [
    "LANGUAGE_PRESETS",
    "Language",
    "UnknownLanguageError",
    "extract_accented_chars",
    "get_language",
    "has_accent",
    "normalize",
]
