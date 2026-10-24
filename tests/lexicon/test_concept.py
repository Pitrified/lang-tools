"""Tests for `lang_tools.lexicon.concept`."""

from pydantic import ValidationError
import pytest

from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.concept_id import concept_id


def test_concept_accepts_well_formed_id() -> None:
    cid = concept_id("library-building", "omw-en-03660909-n")
    concept = Concept(id=cid, definitions={"en": "a place full of books"})
    assert concept.id == cid


def test_concept_rejects_malformed_id() -> None:
    # Pydantic wraps the validator's `InvalidConceptIdError` in a ValidationError.
    with pytest.raises(ValidationError, match="not well-formed"):
        Concept(id="library-building")


def test_concept_definitions_default_empty() -> None:
    concept = Concept(id=concept_id("peace", "omw-en-00001-n"))
    assert concept.definitions == {}


def test_concept_round_trip() -> None:
    concept = Concept(
        id=concept_id("library-building", "omw-en-03660909-n"),
        definitions={"en": "a place full of books", "pt": "biblioteca"},
    )
    dumped = concept.model_dump()
    assert Concept.model_validate(dumped) == concept
    # Membership is never persisted on the concept; it lives on `Sense`.
    assert "lemmas" not in dumped
