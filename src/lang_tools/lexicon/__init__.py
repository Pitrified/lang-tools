"""Canonical concept-centric lexical model and read/query helpers.

Public API:
    Lemma, LemmaExample: the thin lexical token and its curated examples.
    Concept: a language-independent unit of meaning (synset).
    Sense: the explicit lemma <-> concept edge, hosting per-sense signals.
    FalseFriendRelation, ConceptRelation: decoupled relation edge tables.
    lemma_id, concept_id, sense_id: deterministic id constructors.
    LexiconStore, get_store: the read/query store over the whole graph.
    get_all_lemmas, get_lemma_by_id, get_lemmas_by_language, get_lemmas_by_topic,
        get_lemmas_filtered: lemma read helpers.
    get_all_concepts, get_concept_by_id, concepts_for_lemma, lemmas_for_concept,
        senses_for_lemma, senses_for_concept, get_false_friends_for_lemma,
        concept_relations_for: concept/sense/edge read helpers.

The read/query helpers are the stable surface ``lang-tutor`` imports to pull
the lemma pool it drills the user on. The default store loads the Parquet corpus
lazily on first use - importing this subpackage never touches disk (see
`lang_tools.lexicon.lemma_store`).
"""

from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.concept_id import concept_id
from lang_tools.lexicon.hydration import NotHydratedError
from lang_tools.lexicon.hydration import SenseNotHydratedError
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.lemma import LemmaExample
from lang_tools.lexicon.lemma_id import lemma_id
from lang_tools.lexicon.lemma_store import CorpusNotFoundError
from lang_tools.lexicon.lemma_store import LexiconStore
from lang_tools.lexicon.lemma_store import concept_relations_for
from lang_tools.lexicon.lemma_store import concepts_for_lemma
from lang_tools.lexicon.lemma_store import get_all_concepts
from lang_tools.lexicon.lemma_store import get_all_lemmas
from lang_tools.lexicon.lemma_store import get_concept_by_id
from lang_tools.lexicon.lemma_store import get_false_friends_for_lemma
from lang_tools.lexicon.lemma_store import get_lemma_by_id
from lang_tools.lexicon.lemma_store import get_lemmas_by_language
from lang_tools.lexicon.lemma_store import get_lemmas_by_topic
from lang_tools.lexicon.lemma_store import get_lemmas_filtered
from lang_tools.lexicon.lemma_store import get_store
from lang_tools.lexicon.lemma_store import lemmas_for_concept
from lang_tools.lexicon.lemma_store import senses_for_concept
from lang_tools.lexicon.lemma_store import senses_for_lemma
from lang_tools.lexicon.relations import ConceptRelation
from lang_tools.lexicon.relations import FalseFriendRelation
from lang_tools.lexicon.sense import Sense
from lang_tools.lexicon.sense_id import sense_id

__all__ = [
    "Concept",
    "ConceptRelation",
    "CorpusNotFoundError",
    "FalseFriendRelation",
    "Lemma",
    "LemmaExample",
    "LexiconStore",
    "NotHydratedError",
    "Sense",
    "SenseNotHydratedError",
    "concept_id",
    "concept_relations_for",
    "concepts_for_lemma",
    "get_all_concepts",
    "get_all_lemmas",
    "get_concept_by_id",
    "get_false_friends_for_lemma",
    "get_lemma_by_id",
    "get_lemmas_by_language",
    "get_lemmas_by_topic",
    "get_lemmas_filtered",
    "get_store",
    "lemma_id",
    "lemmas_for_concept",
    "sense_id",
    "senses_for_concept",
    "senses_for_lemma",
]
