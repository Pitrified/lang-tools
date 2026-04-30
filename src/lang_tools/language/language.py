"""`Language` model and per-language presets.

Languages are identified by their ISO 639-1 code. Each preset bundles the
accented characters set, normalization map (covering ligatures NFD cannot
decompose), Wordle word-length config, and on-screen keyboard layout.
"""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field

_QWERTY_ROWS: list[list[str]] = [
    list("qwertyuiop"),
    list("asdfghjkl"),
    list("zxcvbnm"),
]


class UnknownLanguageError(KeyError):
    """Raised when a language code is not present in `LANGUAGE_PRESETS`."""

    def __init__(self, code: str) -> None:
        """Initialize with the offending code.

        Args:
            code: The unknown ISO 639-1 language code.
        """
        super().__init__(f"Unknown language code: {code!r}")
        self.code = code


class Language(BaseModel):
    """Per-language configuration shared across exercises and ingestion.

    Attributes:
        code: ISO 639-1 code (e.g. ``"pt"``).
        name: English name (e.g. ``"Portuguese"``).
        native_name: Native spelling (e.g. ``"Portugu\u00eas"``).
        accented_chars: Set of accented/composed characters used by the language.
        normalization_map: Explicit per-character map from accented to base form
            (covers ligatures and special cases NFD cannot decompose).
        word_lengths: Allowed word lengths for the Wordle exercise.
        default_word_length: Default Wordle word length.
        keyboard_rows: Rows of base letters for the on-screen keyboard.
        accent_keys: Extra keys for diacritic input.
    """

    code: str
    name: str
    native_name: str
    accented_chars: set[str] = Field(default_factory=set)
    normalization_map: dict[str, str] = Field(default_factory=dict)
    word_lengths: list[int] = Field(default_factory=lambda: [4, 5, 6, 7])
    default_word_length: int = 5
    keyboard_rows: list[list[str]] = Field(default_factory=lambda: _QWERTY_ROWS)
    accent_keys: list[str] = Field(default_factory=list)


def _pt() -> Language:
    chars = set("\u00e2\u00e3\u00e0\u00e9\u00ea\u00ed\u00f3\u00f4\u00f5\u00fa\u00e7")
    return Language(
        code="pt",
        name="Portuguese",
        native_name="Portugu\u00eas",
        accented_chars=chars,
        normalization_map=dict.fromkeys([], "")
        | {
            "\u00e7": "c",
        },
        accent_keys=sorted(chars),
    )


def _fr() -> Language:
    chars = set(
        "\u00e2\u00e0\u00e9\u00e8\u00eb\u00ea\u00ef\u00ee\u00f4\u0153\u00fc\u00f9\u00fb\u00e7",
    )
    return Language(
        code="fr",
        name="French",
        native_name="Fran\u00e7ais",
        accented_chars=chars,
        normalization_map={"\u0153": "oe", "\u00e6": "ae", "\u00e7": "c"},
        accent_keys=sorted(chars),
    )


def _es() -> Language:
    chars = set("\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\u00fc")
    return Language(
        code="es",
        name="Spanish",
        native_name="Espa\u00f1ol",
        accented_chars=chars,
        normalization_map={"\u00f1": "n"},
        accent_keys=sorted(chars),
    )


def _it() -> Language:
    chars = set("\u00e0\u00e8\u00e9\u00ec\u00f2\u00f9")
    return Language(
        code="it",
        name="Italian",
        native_name="Italiano",
        accented_chars=chars,
        accent_keys=sorted(chars),
    )


def _en() -> Language:
    return Language(
        code="en",
        name="English",
        native_name="English",
        accented_chars=set(),
        accent_keys=[],
    )


def _de() -> Language:
    chars = set("\u00e4\u00f6\u00fc\u00df")
    return Language(
        code="de",
        name="German",
        native_name="Deutsch",
        accented_chars=chars,
        normalization_map={"\u00df": "ss"},
        accent_keys=sorted(chars),
    )


LANGUAGE_PRESETS: dict[str, Language] = {
    lang.code: lang
    for lang in (_pt(), _fr(), _es(), _it(), _en(), _de())
}


def get_language(code: str) -> Language:
    """Return the preset `Language` for the given ISO 639-1 code.

    Args:
        code: ISO 639-1 code (case-insensitive).

    Returns:
        The matching `Language` preset.

    Raises:
        UnknownLanguageError: If the code is not in `LANGUAGE_PRESETS`.
    """
    key = code.lower()
    if key not in LANGUAGE_PRESETS:
        raise UnknownLanguageError(code)
    return LANGUAGE_PRESETS[key]
