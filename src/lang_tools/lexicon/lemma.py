"""Canonical thin `Lemma` model and supporting types.

The `Lemma` is the lexical *token*: a surface form in one language, with its
normalized key, part of speech, topic tags, curated examples, and provenance.
It deliberately carries no meaning of its own - definitions, cross-lingual
links, frequency, and CEFR complexity all live on the `Concept` and `Sense`
that the lemma participates in (see `lang_tools.lexicon.concept` and
`lang_tools.lexicon.sense`). This keeps the token thin and free of the
per-sense values that the "bank" polysemy trap shows must not live here.

See ``scratch_space/09_concept_model/02_core_models.md`` for the full design.
"""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field
from pydantic import computed_field
from pydantic import model_validator

from lang_tools.language.normalization import extract_accented_chars
from lang_tools.language.normalization import has_accent as _has_accent
from lang_tools.language.normalization import normalize as _normalize
from lang_tools.lexicon.lemma_id import lemma_id


class LemmaExample(BaseModel):
    """Curated example sentence in the lemma's language.

    Attributes:
        sentence: Example sentence in the lemma's language.
        translation: Translation in the user's language (optional).
    """

    sentence: str
    translation: str | None = None


class Lemma(BaseModel):
    """A lexical token: one surface form in one language.

    Meaning is not stored here; reach it through the `Sense` edges that link a
    lemma to its `Concept`s.

    Attributes:
        text: Canonical form with accents preserved.
        language: ISO 639-1 code.
        normalized: Accent-stripped, lowercased form. Auto-derived from `text`
            when not supplied.
        part_of_speech: Lemma class label (``"noun"``, ``"verb"``, ...).
        topics: Free-form topic tags.
        examples: Curated example sentences.
        sources: Provenance tags (``"wiktionary"``, ``"csv"``, ``"llm"``, ...).
    """

    text: str
    language: str
    normalized: str = ""
    part_of_speech: str | None = None
    topics: list[str] = Field(default_factory=list)
    examples: list[LemmaExample] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _fill_normalized(self) -> Lemma:
        """Auto-fill `normalized` when blank using the language-agnostic helper."""
        if not self.normalized:
            self.normalized = _normalize(self.text)
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def id(self) -> str:
        """Deterministic ID derived from ``(text, language)``."""
        return lemma_id(self.text, self.language)

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
