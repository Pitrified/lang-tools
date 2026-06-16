"""Tests for `lang_tools.lexicon.concept_id`."""

import pytest

from lang_tools.lexicon.concept_id import CONCEPT_ID_RE
from lang_tools.lexicon.concept_id import EmptyConceptSlugError
from lang_tools.lexicon.concept_id import concept_id


def test_concept_id_is_deterministic() -> None:
    a = concept_id("library-building", "omw-en-03660909-n")
    b = concept_id("library-building", "omw-en-03660909-n")
    assert a == b


def test_concept_id_matches_expected_shape() -> None:
    value = concept_id("library-building", "omw-en-03660909-n")
    assert CONCEPT_ID_RE.match(value)
    assert value.startswith("c__library-building__")


def test_concept_id_ignores_slug_for_uniqueness() -> None:
    same_key = "omw-en-03660909-n"
    renamed = concept_id("public-library", same_key)
    original = concept_id("library-building", same_key)
    # Slug differs but the 12-hex suffix (hashed from the source key) is shared.
    assert renamed.rsplit("__", 1)[-1] == original.rsplit("__", 1)[-1]


def test_concept_id_distinct_keys_differ() -> None:
    assert concept_id("bank-river", "key-a") != concept_id("bank-river", "key-b")


def test_concept_id_rejects_blank_slug() -> None:
    with pytest.raises(EmptyConceptSlugError):
        concept_id("  ", "some-key")
