"""Canonical lemma data model, ingestion pipelines, and read/query helpers.

Public API:
    Lemma: unified lemma entity.
    Gloss, GlossExample, LemmaExample, FalseFriend: supporting types.
    FrequencyLevel: literal type for lemma frequency.
    lemma_id: deterministic ID for a (text, language) pair.
    get_all_lemmas, get_lemma_by_id, get_lemmas_by_language, get_lemmas_by_topic,
        get_lemmas_filtered: read/query helpers over the on-disk lemma store.

The read/query helpers are the stable surface ``lang-tutor`` imports to pull
the lemma pool it drills the user on. Importing this subpackage loads the
bootstrap content from disk (see `lang_tools.lexicon.lemma_store`).
"""

from lang_tools.lexicon.lemma import FalseFriend
from lang_tools.lexicon.lemma import FrequencyLevel
from lang_tools.lexicon.lemma import Gloss
from lang_tools.lexicon.lemma import GlossExample
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.lemma import LemmaExample
from lang_tools.lexicon.lemma_id import lemma_id
from lang_tools.lexicon.lemma_store import get_all_lemmas
from lang_tools.lexicon.lemma_store import get_lemma_by_id
from lang_tools.lexicon.lemma_store import get_lemmas_by_language
from lang_tools.lexicon.lemma_store import get_lemmas_by_topic
from lang_tools.lexicon.lemma_store import get_lemmas_filtered

__all__ = [
    "FalseFriend",
    "FrequencyLevel",
    "Gloss",
    "GlossExample",
    "Lemma",
    "LemmaExample",
    "get_all_lemmas",
    "get_lemma_by_id",
    "get_lemmas_by_language",
    "get_lemmas_by_topic",
    "get_lemmas_filtered",
    "lemma_id",
]
