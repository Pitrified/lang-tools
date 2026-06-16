"""Canonical concept-centric lexical model and read/query helpers.

Public API:
    Lemma, LemmaExample: the thin lexical token and its curated examples.
    Concept: a language-independent unit of meaning (synset).
    Sense: the explicit lemma <-> concept edge, hosting per-sense signals.
    FalseFriendRelation, ConceptRelation: decoupled relation edge tables.
    lemma_id, concept_id, sense_id: deterministic id constructors.
    get_all_lemmas, get_lemma_by_id, get_lemmas_by_language, get_lemmas_by_topic,
        get_lemmas_filtered: read/query helpers over the on-disk lemma store.

The read/query helpers are the stable surface ``lang-tutor`` imports to pull
the lemma pool it drills the user on. Importing this subpackage loads the
bootstrap content from disk (see `lang_tools.lexicon.lemma_store`).
"""

from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.concept_id import concept_id
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.lemma import LemmaExample
from lang_tools.lexicon.lemma_id import lemma_id
from lang_tools.lexicon.lemma_store import get_all_lemmas
from lang_tools.lexicon.lemma_store import get_lemma_by_id
from lang_tools.lexicon.lemma_store import get_lemmas_by_language
from lang_tools.lexicon.lemma_store import get_lemmas_by_topic
from lang_tools.lexicon.lemma_store import get_lemmas_filtered
from lang_tools.lexicon.relations import ConceptRelation
from lang_tools.lexicon.relations import FalseFriendRelation
from lang_tools.lexicon.sense import Sense
from lang_tools.lexicon.sense_id import sense_id

__all__ = [
    "Concept",
    "ConceptRelation",
    "FalseFriendRelation",
    "Lemma",
    "LemmaExample",
    "Sense",
    "concept_id",
    "get_all_lemmas",
    "get_lemma_by_id",
    "get_lemmas_by_language",
    "get_lemmas_by_topic",
    "get_lemmas_filtered",
    "lemma_id",
    "sense_id",
]
