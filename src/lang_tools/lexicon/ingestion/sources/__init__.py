"""Per-source adapters that map an external corpus onto the lexical models.

One adapter per dataset, each with a single responsibility (phase 5.5 Step 3).
The contract every adapter follows - so no source can silently corrupt another's
rows the way the dropped kaikki join did:

- An adapter either **creates backbone rows** (OMW only) or **annotates existing
  rows by a declared key**; it never invents a gloss for a sense it cannot
  identify.
- Cross-source fills are **sense-aware or they do not ship**: a precise key (ILI
  id, sense id) is required for glosses; a lemma-only join (e.g. Tatoeba) is
  allowed only for examples, which tolerate sense-blindness.
- Every written field carries its own ``source`` tag and license bucket; per-row
  provenance stays the licensing source of truth (phase 10).

Adapter registry:

- `omw` - the **concept backbone** (synsets -> `Concept`/`Lemma`/`Sense`),
  permissive. Yields a small pure intermediate shape so `transform` and its tests
  never touch ``wn``.
- `cili` - the **English-gloss annotator** (ILI id -> English gloss), permissive,
  used only to fill a missing English gloss (a dormant safety net for OMW builds;
  see `cili`).
- **Tatoeba** (CC-BY example sentences) and **Wikidata Lexemes** (CC0) are
  deferred (phases 6/8); when added they follow the same annotator contract.
- `kaikki` was removed in phase 5.5 (sense-blind gloss join, CC-BY-SA).
"""

from lang_tools.lexicon.ingestion.sources.cili import load_cili_glosses
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
    "load_cili_glosses",
    "slugify",
    "wn_synset_entries",
]
