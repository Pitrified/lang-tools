"""Per-source adapters that map an external corpus onto the lexical models.

`omw` is the **concept backbone** (synsets -> `Concept`/`Lemma`/`Sense`); `kaikki`
is **enrichment only** (sparse glosses + example sentences joined onto the OMW
backbone). Each adapter yields a small, pure intermediate shape so the
`transform` step - and its tests - never touch the network or the heavy ``wn``
dependency.
"""

from lang_tools.lexicon.ingestion.sources.kaikki import KaikkiEntry
from lang_tools.lexicon.ingestion.sources.kaikki import load_kaikki_entries
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.ingestion.sources.omw import group_to_records
from lang_tools.lexicon.ingestion.sources.omw import slugify
from lang_tools.lexicon.ingestion.sources.omw import wn_synset_entries

__all__ = [
    "KaikkiEntry",
    "SynsetEntry",
    "group_to_records",
    "load_kaikki_entries",
    "slugify",
    "wn_synset_entries",
]
