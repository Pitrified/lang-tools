"""Acquire stage: download the raw OMW backbone into a reproducible local cache.

This is stage A of the initial build: pull OMW into a gitignored
``data/_raw/lexicon/`` cache and pin its exact version in a ``_build.json``
manifest. The cache is regenerable (not LFS, not committed); the manifest is the
seam a future re-ingestion merge diffs against - it records *what upstream
originally gave us* so the deterministic transform can rebuild the machine
baseline without a committed snapshot.

The network call is isolated and lazy: `download_omw` wraps ``wn`` (the
``ingest`` extra). The manifest read/write helpers are pure and unit-tested; the
download is not exercised in tests. The kaikki enrichment fetch was removed in
phase 5.5 (OMW + a CILI English fallback cover the gloss need).
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
import json
from typing import TYPE_CHECKING
from typing import Any

from loguru import logger as lg

from lang_tools.lexicon.codec import LEXICON_SUBDIR
from lang_tools.lexicon.ingestion.sources.omw import OMW_VERSION

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

#: Gitignored raw-cache subdirectory of the data folder (regenerable, not LFS).
RAW_SUBDIR = "_raw/lexicon"

#: Manifest filename written under ``<data_fol>/lexicon/`` (pins source versions).
MANIFEST_NAME = "_build.json"

#: ``wn`` project id for the Collaborative Interlingual Index (the permissive
#: English ILI glosses used as the concept English-gloss fallback, phase 5.5).
CILI_PROJECT = "cili"


def raw_dir(data_fol: Path) -> Path:
    """Return the raw-cache directory under a data folder."""
    return data_fol / RAW_SUBDIR


def download_omw(
    langs: Iterable[str],
    *,
    data_fol: Path,
    omw_version: str = OMW_VERSION,
) -> dict[str, Any]:
    """Download the OMW wordnets for `langs` via ``wn`` and return manifest info.

    Downloads **per lexicon**, not the ``omw`` collection: the collection
    specifier pulls every member wordnet regardless of `langs`, so we resolve
    each language to a single lexicon via `_omw_lexicon` and download exactly
    those. ``wn`` keeps its own data directory; this points it at the raw cache so
    the download is reproducible. Idempotent: ``wn`` skips a lexicon it already
    has.

    Args:
        langs: ISO 639-1 codes to install.
        data_fol: Project data folder; ``wn`` data goes under the raw cache.
        omw_version: OMW release version used to build the lexicon specifiers.

    Also downloads the CILI resource (`CILI_PROJECT`): it carries the
    language-independent English ILI glosses that `sources.omw` uses as the
    English-gloss fallback (phase 5.5 Step 2). Like the lexicons it is idempotent.

    Returns:
        A manifest fragment recording the ``wn`` version, the OMW version, the
        languages, the exact lexicons requested, and the ILI resource.

    Raises:
        IngestDependencyMissingError: When the ``ingest`` extra (``wn``) is absent.
        UnknownOmwLanguageError: When a language has no mapped OMW lexicon.
    """
    from lang_tools.lexicon.ingestion.sources.omw import _omw_lexicon  # noqa: PLC0415
    from lang_tools.lexicon.ingestion.sources.omw import _require_wn  # noqa: PLC0415

    wn = _require_wn()
    wn_data = raw_dir(data_fol) / "wn_data"
    wn_data.mkdir(parents=True, exist_ok=True)
    wn.config.data_directory = str(wn_data)  # pyright: ignore[reportPrivateImportUsage]

    langs = list(langs)
    specs = [_omw_lexicon(lang, omw_version) for lang in langs]  # raises on unknown
    lg.info("Downloading OMW {} lexicons {} for {}", omw_version, specs, langs)
    for spec in specs:
        wn.download(spec)  # idempotent: wn skips an installed lexicon
    lg.info("Downloading ILI resource {} (English gloss fallback)", CILI_PROJECT)
    wn.download(CILI_PROJECT)  # idempotent: the permissive CILI English glosses
    return {
        "wn_version": wn.__version__,
        "omw_version": omw_version,
        "languages": langs,
        "lexicons": specs,  # only what we asked for, not everything installed
        "ili_resource": CILI_PROJECT,
        "wn_data_dir": str(wn_data),
    }


def manifest_path(data_fol: Path) -> Path:
    """Return the ``_build.json`` manifest path under ``<data_fol>/lexicon/``."""
    return data_fol / LEXICON_SUBDIR / MANIFEST_NAME


def write_manifest(data_fol: Path, manifest: dict[str, Any]) -> Path:
    """Write the build manifest, stamping a UTC ``built_at`` timestamp.

    Args:
        data_fol: Project data folder.
        manifest: The manifest payload (source fragments + counts).

    Returns:
        The path the manifest was written to.
    """
    path = manifest_path(data_fol)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"built_at": datetime.now(UTC).isoformat(), **manifest}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def read_manifest(data_fol: Path) -> dict[str, Any] | None:
    """Read the build manifest, or ``None`` when it has not been written yet."""
    path = manifest_path(data_fol)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
