"""CILI source adapter - the permissive English-gloss annotator.

CILI (the Collaborative Interlingual Index) carries one language-independent
English gloss per ILI id. It is an **annotator**, not a backbone source: it adds
no concepts or lemmas, it only fills a concept's English gloss when OMW left it
blank, keyed by the concept's ILI id - a precise, concept-level key, not a fuzzy
text join (that key discipline is the rule that stops a repeat of the kaikki
mess). Anything it contributes is tagged ``cili`` (in `sources.omw`, where the
concept rows are built) and is permissively licensed.

Reached through ``wn``'s loaded ILI resource (the ``cili`` project added by
`acquire.download_omw`). Kept in its own module so each dataset has one
single-responsibility loader (phase 5.5 Step 3); `sources.omw` stays purely the
OMW backbone and never carries this source's data on its own records.
"""

from __future__ import annotations

from loguru import logger as lg


def load_cili_glosses(*, data_dir: str | None = None) -> dict[str, str]:
    """Return ``{ili_id: english_gloss}`` from ``wn``'s loaded ILI resource.

    Streams `wn.ili.find_ilis` and keeps only the short id+gloss strings (a few
    tens of MB for the full ~117k set), so it never materializes the ILI objects
    that `get_all` would. Returns an empty map when no ILI resource is loaded (the
    ``cili`` project from `acquire.download_omw`), so the English-gloss fallback
    in `group_to_records` simply does not fire rather than erroring.

    Args:
        data_dir: Optional override for ``wn``'s data directory; ``None`` uses its
            default. Pass the same value as `wn_synset_entries` so both read the
            same cache.

    Returns:
        A mapping of ILI id to its English CILI gloss (definitions only; ILIs
        without one are omitted).

    Raises:
        OptionalDependencyMissingError: When the ``ingest`` extra (``wn``) is absent.
    """
    # Lazy, and reuse the OMW adapter's dependency guard so a missing ``wn`` gives
    # the same clear error. `sources.omw` does not import this module, so there is
    # no import cycle.
    from lang_tools.lexicon.ingestion.sources.omw import _require_wn  # noqa: PLC0415

    wn = _require_wn()
    if data_dir is not None:
        wn.config.data_directory = data_dir  # pyright: ignore[reportPrivateImportUsage]

    from wn import ili as wn_ili  # noqa: PLC0415 - lazy; only the read path needs it

    # `find_ilis` is a public, documented wn function but is missing from
    # `wn.ili.__all__`, so pyright reports it as a private import; it is not.
    rows = wn_ili.find_ilis()  # pyright: ignore[reportPrivateImportUsage]
    glosses: dict[str, str] = {
        ili_id: gloss for ili_id, _status, gloss, _metadata in rows if gloss
    }
    lg.info("Loaded {} CILI English glosses for the gloss fallback", len(glosses))
    return glosses
