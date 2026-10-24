"""Learner-facing drill view of a lemma: `LemmaCard` and its `CardQuery`.

The thin `Lemma` carries no meaning; a drill needs one. A `LemmaCard` is the
lemma joined with its **best sense** - the sense with the highest
`Sense.sense_frequency`, ties going to the more common concept
(`Concept.commonness`) and then the easier CEFR band - and, through that
sense's concept, a gloss, the translations, and example sentences. It is a read
model computed by the store at query time, never persisted: the phase-6 rule
that per-sense values must not be cached on the lemma still holds, and the card
simply names which sense it picked (`concept_id`).

`CardQuery` is the bounded filter the store answers with a list of cards, so a
consumer (``lang-tutor``) asks for "20 easy single-word pt nouns with an en
translation" instead of pulling a whole language and joining client-side.

See ``scratch_space/09_concept_model/09_sample_and_consumer.md`` for the design.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel
from pydantic import Field

from lang_tools.lexicon.lemma import Lemma  # noqa: TC001 - pydantic field type

#: CEFR bands in learning order; the store compares them lexicographically,
#: which matches this order.
CEFR_LEVELS: tuple[str, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")

#: Hard cap on the cards one query may return.
MAX_CARD_LIMIT = 500

CefrLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]


class LookalikeHint(BaseModel):
    """A look-alike of a card's lemma in one of the learner's known languages.

    Attributes:
        language: The known language.
        text: The look-alike word.
        kind: ``full`` / ``partial`` false friend, or ``cognate``.
        note: The learner note (English) for a false friend.
    """

    language: str
    text: str
    kind: Literal["full", "partial", "cognate"]
    note: str = ""

    @property
    def is_trap(self) -> bool:
        """True for a false friend (``full`` or ``partial``)."""
        return self.kind != "cognate"


class LemmaCard(BaseModel):
    """A lemma with the meaning, level, and translations of its best sense.

    Attributes:
        lemma: The thin lexical token, unchanged.
        concept_id: Concept of the best sense (None for a lemma with no sense).
        cefr_level: Estimated CEFR band of the best sense.
        sense_frequency: Frequency of the best sense (Zipf-like scale).
        gloss: Definition of the best concept in the query's gloss language.
        translations: Language -> lemma texts realising the same concept, most
            frequent first. The card's own lemma is never listed; the lemma's
            own language, when requested, holds its synonyms.
        examples: Example sentences of the best concept in the lemma's language.
        lookalikes: The lemma's look-alikes in the query's known languages
            (phase 11): false friends first, then cognates. Empty when the
            query names no known language.
    """

    lemma: Lemma
    concept_id: str | None = None
    cefr_level: str | None = None
    sense_frequency: float | None = None
    gloss: str | None = None
    translations: dict[str, list[str]] = Field(default_factory=dict)
    examples: list[str] = Field(default_factory=list)
    lookalikes: list[LookalikeHint] = Field(default_factory=list)

    @property
    def is_trap(self) -> bool:
        """True when the lemma is a false friend of a word the learner knows."""
        return any(hint.is_trap for hint in self.lookalikes)

    @property
    def has_cognate(self) -> bool:
        """True when the lemma is a cognate of a word the learner knows."""
        return any(not hint.is_trap for hint in self.lookalikes)


class CardQuery(BaseModel):
    """Filter for a bounded list of `LemmaCard`s.

    Every filter is optional; ``language`` is the one a drill always sets.

    Attributes:
        language: ISO 639-1 code of the drilled lemmas.
        gloss_language: Language of `LemmaCard.gloss`.
        translation_languages: Languages to fill `LemmaCard.translations` with.
        require_translation: Keep only cards with at least one translation in
            every language of ``translation_languages``.
        require_example: Keep only cards with an example sentence.
        example_mentions_lemma: Keep only cards with an example sentence that
            contains the lemma's text. Example sentences belong to the
            concept, so without this any of its lemmas can draw a sentence
            that never uses it.
        min_cefr: Lowest CEFR band of the best sense (inclusive).
        max_cefr: Highest CEFR band of the best sense (inclusive).
        topic: Topic tag (the lemma's own or a sense concept's).
        part_of_speech: Lemma part of speech (``"noun"``, ``"verb"``, ...).
        length: Exact character length of the lemma text.
        min_length: Minimum character length (drops one- and two-letter
            tokens such as letter names from a drill).
        accented_only: Keep only lemmas whose text carries a diacritic.
        single_word: Keep only one lowercase alphabetic token (no spaces,
            hyphens, digits, apostrophes, or capitals - so no proper nouns).
        exclude_ids: Lemma ids to leave out (e.g. the ones already drilled).
        known_languages: The learner's known languages; each card then
            carries its look-alikes in them (`LemmaCard.lookalikes`).
        lookalike: Filter on those look-alikes: ``"trap"`` keeps lemmas that
            are a false friend of a known word, ``"cognate"`` lemmas that are a
            cognate of one and no trap, ``"none"`` lemmas with neither.
            Needs ``known_languages``.
        order: ``"random"`` samples the matches, ``"frequency"`` returns the
            most frequent best senses first.
        seed: Makes ``"random"`` order deterministic when set.
        limit: Maximum cards returned, at most `MAX_CARD_LIMIT`.
    """

    language: str | None = None
    gloss_language: str = "en"
    translation_languages: list[str] = Field(default_factory=lambda: ["en"])
    require_translation: bool = False
    require_example: bool = False
    example_mentions_lemma: bool = False
    min_cefr: CefrLevel | None = None
    max_cefr: CefrLevel | None = None
    topic: str | None = None
    part_of_speech: str | None = None
    length: int | None = Field(default=None, ge=1)
    min_length: int | None = Field(default=None, ge=1)
    accented_only: bool = False
    single_word: bool = False
    exclude_ids: list[str] = Field(default_factory=list)
    known_languages: list[str] = Field(default_factory=list)
    lookalike: Literal["trap", "cognate", "none"] | None = None
    order: Literal["random", "frequency"] = "random"
    seed: int | None = None
    limit: int = Field(default=50, ge=1, le=MAX_CARD_LIMIT)
