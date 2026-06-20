"""Per-source adapters that map an external corpus onto the lexical models.

`omw` is the **concept backbone** (synsets -> `Concept`/`Lemma`/`Sense`) and the
sole source: the kaikki enrichment adapter was removed in phase 5.5. The adapter
yields a small, pure intermediate shape so the `transform` step - and its tests -
never touch the network or the heavy ``wn`` dependency.
"""

from lang_tools.lexicon.ingestion.sources.omw import OMW_LEXICONS
from lang_tools.lexicon.ingestion.sources.omw import OMW_VERSION
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.ingestion.sources.omw import UnknownOmwLanguageError
from lang_tools.lexicon.ingestion.sources.omw import group_to_records
from lang_tools.lexicon.ingestion.sources.omw import slugify
from lang_tools.lexicon.ingestion.sources.omw import wn_synset_entries

__all__ = [
    "OMW_LEXICONS",
    "OMW_VERSION",
    "SynsetEntry",
    "UnknownOmwLanguageError",
    "group_to_records",
    "slugify",
    "wn_synset_entries",
]
