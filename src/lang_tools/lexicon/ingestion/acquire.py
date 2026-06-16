"""Acquire stage: download raw OMW + kaikki into a reproducible local cache.

This is stage A of the initial build: pull the external sources into a gitignored
``data/_raw/lexicon/`` cache and pin their exact versions in a ``_build.json``
manifest. The cache is regenerable (not LFS, not committed); the manifest is the
seam a future re-ingestion merge diffs against - it records *what upstream
originally gave us* so the deterministic transform can rebuild the machine
baseline without a committed snapshot.

The actual network calls are isolated and lazy: `download_omw` wraps ``wn`` (the
``ingest`` extra) and `fetch_kaikki` is a thin HTTP GET. The manifest read/write
helpers are pure and unit-tested; the downloads are not exercised in tests.
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
import json
from typing import TYPE_CHECKING
from typing import Any

from loguru import logger as lg

from lang_tools.lexicon.codec import LEXICON_SUBDIR

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

#: Gitignored raw-cache subdirectory of the data folder (regenerable, not LFS).
RAW_SUBDIR = "_raw/lexicon"

#: Manifest filename written under ``<data_fol>/lexicon/`` (pins source versions).
MANIFEST_NAME = "_build.json"

#: kaikki.org per-language dump URL template (full Wiktionary extraction).
KAIKKI_URL_TEMPLATE = (
    "https://kaikki.org/dictionary/{name}/kaikki.org-dictionary-{name}.jsonl"
)

#: ISO 639-1 -> kaikki language folder name (its dumps are keyed by English name).
_KAIKKI_LANG_NAMES: dict[str, str] = {
    "en": "English",
    "pt": "Portuguese",
    "es": "Spanish",
    "fr": "French",
    "it": "Italian",
}


def raw_dir(data_fol: Path) -> Path:
    """Return the raw-cache directory under a data folder."""
    return data_fol / RAW_SUBDIR


def kaikki_path(data_fol: Path, language: str) -> Path:
    """Return the cached kaikki JSONL path for a language."""
    return raw_dir(data_fol) / f"kaikki_{language}.jsonl"


class UnknownKaikkiLanguageError(KeyError):
    """Raised when no kaikki dump name is known for a language code."""

    def __init__(self, language: str) -> None:
        """Initialize with the unsupported language code.

        Args:
            language: The ISO 639-1 code with no known kaikki dump.
        """
        super().__init__(
            f"No kaikki dump name known for {language!r} "
            f"(known: {sorted(_KAIKKI_LANG_NAMES)}).",
        )
        self.language = language


def download_omw(
    langs: Iterable[str],
    *,
    data_fol: Path,
    omw_version: str = "omw:1.4",
) -> dict[str, Any]:
    """Download the OMW wordnets for `langs` via ``wn`` and return manifest info.

    ``wn`` keeps its own data directory; this points it at the raw cache so the
    download is reproducible alongside the kaikki dumps. Idempotent: ``wn`` skips
    a lexicon it already has.

    Args:
        langs: ISO 639-1 codes to install.
        data_fol: Project data folder; ``wn`` data goes under the raw cache.
        omw_version: The OMW collection spec passed to ``wn.download``.

    Returns:
        A manifest fragment recording the ``wn`` version, the OMW spec, and the
        installed lexicons.

    Raises:
        IngestDependencyMissingError: When the ``ingest`` extra (``wn``) is absent.
    """
    from lang_tools.lexicon.ingestion.sources.omw import _require_wn  # noqa: PLC0415

    wn = _require_wn()
    wn_data = raw_dir(data_fol) / "wn_data"
    wn_data.mkdir(parents=True, exist_ok=True)
    wn.config.data_directory = str(wn_data)

    langs = list(langs)
    lg.info("Downloading OMW {} for {}", omw_version, langs)
    wn.download(omw_version)
    lexicons = sorted({lex.specifier() for lex in wn.lexicons()})
    return {
        "wn_version": wn.__version__,
        "omw_version": omw_version,
        "languages": langs,
        "lexicons": lexicons,
        "wn_data_dir": str(wn_data),
    }


def fetch_kaikki(
    langs: Iterable[str],
    *,
    data_fol: Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Download the kaikki.org JSONL dumps for `langs` into the raw cache.

    Args:
        langs: ISO 639-1 codes to fetch.
        data_fol: Project data folder; dumps land under the raw cache.
        overwrite: Re-download even when a cached dump already exists.

    Returns:
        A manifest fragment mapping each language to its source URL and the
        UTC date it was fetched.

    Raises:
        UnknownKaikkiLanguageError: When a language has no known kaikki dump.
    """
    import urllib.request  # noqa: PLC0415 - lazy; only the download path needs it

    raw_dir(data_fol).mkdir(parents=True, exist_ok=True)
    fetched: dict[str, Any] = {}
    for language in langs:
        if language not in _KAIKKI_LANG_NAMES:
            raise UnknownKaikkiLanguageError(language)
        dest = kaikki_path(data_fol, language)
        url = KAIKKI_URL_TEMPLATE.format(name=_KAIKKI_LANG_NAMES[language])
        if dest.exists() and not overwrite:
            lg.info("kaikki {} already cached at {}", language, dest)
        else:
            lg.info("Fetching kaikki {} from {}", language, url)
            urllib.request.urlretrieve(url, dest)  # noqa: S310 - fixed https kaikki host
        fetched[language] = {
            "url": url,
            "fetched_at": datetime.now(UTC).date().isoformat(),
        }
    return fetched


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
