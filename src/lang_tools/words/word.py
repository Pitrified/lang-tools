"""Canonical `Word` model and supporting types.

The `Word` model unifies the per-repo word shapes from `convo_craft`,
`brazilian-bites`, `fala-comigo-ai-tutor`, `go-accenter`, and `worldly-words`
into a single Pydantic schema. See
``linux-box-cloudflare/scratch_space/vibes/10-language-overview/02-shared-data-layer.md``
for the full design rationale and source-field mapping.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import computed_field
from pydantic import model_validator

from lang_tools.language.normalization import extract_accented_chars
from lang_tools.language.normalization import has_accent as _has_accent
from lang_tools.language.normalization import normalize as _normalize
from lang_tools.words.word_id import word_id

FrequencyLevel = Literal["high", "medium", "low"]


class GlossExample(BaseModel):
    """Usage example attached to a Wiktionary-style sense.

    Attributes:
        text: Example sentence in the word's language.
        translation: English translation (optional).
    """

    text: str
    translation: str | None = None


class Gloss(BaseModel):
    """A single sense / definition for a word.

    Attributes:
        text: Definition text (usually English).
        examples: List of usage examples.
    """

    text: str
    examples: list[GlossExample] = Field(default_factory=list)


class WordExample(BaseModel):
    """Curated example sentence in the word's language.

    Attributes:
        sentence: Example sentence in the word's language.
        translation: Translation in the user's language (optional).
    """

    sentence: str
    translation: str | None = None


class FalseFriend(BaseModel):
    """False-friend metadata pointing at a misleading cognate.

    Attributes:
        language: ISO 639-1 code of the language the cognate exists in.
        similar_word: The misleading cognate.
        similarity_score: Optional 0.0-1.0 visual / phonetic similarity.
        actual_meaning: What the cognate actually means.
    """

    language: str
    similar_word: str
    similarity_score: float | None = None
    actual_meaning: str


class Word(BaseModel):
    """Unified word entity covering vocab, dictionary, and game data sources.

    Attributes:
        text: Canonical form with accents preserved.
        language: ISO 639-1 code.
        normalized: Accent-stripped, lowercased form. Auto-derived from `text`
            when not supplied.
        part_of_speech: Word class label (``"noun"``, ``"verb"``, ...).
        frequency: Optional frequency tier.
        translations: Mapping from target language code to translated text.
        topics: Free-form topic tags.
        glosses: Wiktionary-style sense list.
        examples: Curated example sentences.
        false_friends: List of false-friend metadata entries.
        sources: Provenance tags (``"wiktionary"``, ``"csv"``, ``"llm"``, ...).
    """

    text: str
    language: str
    normalized: str = ""
    part_of_speech: str | None = None
    frequency: FrequencyLevel | None = None
    translations: dict[str, str] = Field(default_factory=dict)
    topics: list[str] = Field(default_factory=list)
    glosses: list[Gloss] = Field(default_factory=list)
    examples: list[WordExample] = Field(default_factory=list)
    false_friends: list[FalseFriend] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _fill_normalized(self) -> Word:
        """Auto-fill `normalized` when blank using the language-agnostic helper."""
        if not self.normalized:
            self.normalized = _normalize(self.text)
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def id(self) -> str:
        """Deterministic ID derived from ``(text, language)``."""
        return word_id(self.text, self.language)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_accent(self) -> bool:
        """True if `text` contains any accented character."""
        return _has_accent(self.text)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def accented_chars(self) -> list[str]:
        """Accented characters present in `text`, in original order."""
        return extract_accented_chars(self.text)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def length(self) -> int:
        """Length of `text` in characters (used by the Wordle exercise)."""
        return len(self.text)
