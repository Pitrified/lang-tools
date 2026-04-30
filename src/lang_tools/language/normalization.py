"""Accent / diacritic normalization helpers.

Pattern rules:
    Stateless utility module. Uses ``unicodedata.NFD`` decomposition and
    combining-character filtering as the default backbone. Per-language
    overrides (via the `Language.normalization_map`) handle special cases like
    French ``\u0153 -> oe`` or German ``\u00df -> ss`` which NFD does not
    decompose.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import unicodedata

if TYPE_CHECKING:
    from lang_tools.language.language import Language


def normalize(text: str, language: Language | None = None) -> str:
    """Strip diacritics and lowercase a string.

    Uses Unicode NFD decomposition followed by combining-mark removal. If a
    `Language` is supplied, its `normalization_map` is applied first to handle
    ligatures and other characters NFD cannot decompose.

    Args:
        text: Input string.
        language: Optional language whose `normalization_map` is applied first.

    Returns:
        Lowercased, accent-stripped form of ``text``.

    Example:
        Stripping Portuguese diacritics::

            normalize("A\u00e7\u00e3o")  # -> "acao"
    """
    if language is not None:
        for src, dst in language.normalization_map.items():
            text = text.replace(src, dst)
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.lower()


def has_accent(text: str, language: Language | None = None) -> bool:
    """Return True if `text` contains any accented or composed character.

    Args:
        text: Input string.
        language: Optional language whose `normalization_map` participates in
            the comparison (so ligatures count as accents).

    Returns:
        True when `normalize(text)` differs from `text.lower()`.
    """
    return normalize(text, language) != text.lower()


def extract_accented_chars(text: str, language: Language | None = None) -> list[str]:
    """List every accented or composed character present in `text`.

    Args:
        text: Input string.
        language: Optional language whose `normalization_map` is applied to the
            per-character check.

    Returns:
        Characters from `text` whose normalized form differs from themselves,
        preserving original order. Duplicates are kept (caller can deduplicate).
    """
    return [ch for ch in text if normalize(ch, language) != ch.lower()]
