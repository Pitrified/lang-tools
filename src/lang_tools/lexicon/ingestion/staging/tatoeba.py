"""Tatoeba staging - example sentences, and a lemma -> sentence index.

Tatoeba is the example-sentence candidate of phase 5.54 Topic 1. Its unit is a
sentence, joined to our lexicon only by **lemma surface form** (it has no sense
id), so it is sense-blind: usable for examples (which tolerate that) but never for
glosses. This module keeps the staging honest about that - it stages the raw
sentences and builds a lemma->sentence index, both flagged as a lemma-only join
the exploration must treat as sense-blind.

Two halves, the same split the OMW adapter uses:

- `download_tatoeba_sentences` is the **impure** part: it fetches the per-language
  sentence export over HTTPS and decompresses it. Network-isolated and not tested.
- `parse_tatoeba_tsv` and `build_lemma_sentence_index` are **pure**: they parse the
  export rows and map each lemma form to the sentence ids that contain it. Fully
  unit-tested with small inputs.
"""

from __future__ import annotations

import bz2
import re
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from urllib.request import Request
from urllib.request import urlopen

from loguru import logger as lg

from lang_tools.language.normalization import normalize
from lang_tools.lexicon.ingestion.staging.base import KNOWN_LICENSES
from lang_tools.lexicon.ingestion.staging.base import StagedDataset
from lang_tools.lexicon.ingestion.staging.base import dataset_dir
from lang_tools.lexicon.ingestion.staging.base import write_rows_parquet

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Iterator
    from collections.abc import Mapping
    from pathlib import Path

#: ISO 639-1 -> ISO 639-3 codes Tatoeba names its per-language exports by.
TATOEBA_ISO3: dict[str, str] = {
    "en": "eng",
    "pt": "por",
    "es": "spa",
    "fr": "fra",
    "it": "ita",
}

#: Per-language sentence export (``id<TAB>lang<TAB>text``, bz2-compressed).
TATOEBA_SENTENCES_URL = (
    "https://downloads.tatoeba.org/exports/per_language/{iso3}/{iso3}_sentences.tsv.bz2"
)

#: Columns of the staged sentence table.
SENTENCE_COLUMNS = ("sentence_id", "text")

#: Default cap on sentences kept per lemma form, so the index stays bounded.
DEFAULT_MAX_PER_LEMMA = 20

#: Network read timeout (seconds) for the sentence download.
_DOWNLOAD_TIMEOUT_S = 120

#: A user agent, as Tatoeba (like many hosts) rejects blank-UA requests.
_USER_AGENT = "lang-tools-staging/0.1 (+https://github.com/Pitrified)"

_TSV_FIELDS = 3

#: Word-token pattern for the lemma match (drops punctuation that ``normalize``
#: keeps, so ``"big."`` tokenizes to ``"big"``).
_WORD_RE = re.compile(r"\w+")


def _tokens(text: str) -> list[str]:
    """Return the normalized word tokens of a string (lowercase, accent-free)."""
    return _WORD_RE.findall(normalize(text))


class UnknownTatoebaLanguageError(KeyError):
    """Raised when no Tatoeba ISO 639-3 code is mapped for a language."""

    def __init__(self, language: str) -> None:
        """Initialize with the unsupported language code.

        Args:
            language: The ISO 639-1 code with no mapped Tatoeba export.
        """
        super().__init__(
            f"No Tatoeba export known for {language!r} "
            f"(known: {sorted(TATOEBA_ISO3)}).",
        )
        self.language = language


def _tatoeba_iso3(lang: str) -> str:
    """Return the ISO 639-3 code Tatoeba uses for a language, or raise."""
    try:
        return TATOEBA_ISO3[lang]
    except KeyError as exc:
        raise UnknownTatoebaLanguageError(lang) from exc


def parse_tatoeba_tsv(lines: Iterable[str]) -> Iterator[tuple[int, str]]:
    """Yield ``(sentence_id, text)`` from Tatoeba sentence-export TSV lines.

    The export is ``id<TAB>lang<TAB>text`` with no header. The language column is
    dropped (a single-language export is already filtered). Malformed lines (wrong
    field count, non-integer id) are skipped rather than raising, so one bad row
    does not abort a multi-million-row stream.

    Args:
        lines: Raw decoded TSV lines (newline-terminated or not).

    Yields:
        One ``(sentence_id, text)`` pair per well-formed line.
    """
    for line in lines:
        parts = line.rstrip("\n").split("\t")
        if len(parts) != _TSV_FIELDS:
            continue
        raw_id, _lang, text = parts
        try:
            sentence_id = int(raw_id)
        except ValueError:
            continue
        if text:
            yield sentence_id, text


def build_lemma_sentence_index(
    sentences: Iterable[tuple[int, str]],
    lemma_forms: Iterable[str],
    *,
    max_per_lemma: int = DEFAULT_MAX_PER_LEMMA,
) -> dict[str, list[int]]:
    """Map each lemma form to the sentence ids that contain it (lemma-only join).

    The match is normalized (lowercase, accent-free) and word-boundary aware:
    a single-word lemma matches a whole token; a multi-word lemma matches a
    contiguous run of tokens. This is a **sense-blind** join - one surface form
    spans every sense of that lemma - so the result is for examples only, never
    for attaching glosses (the rule that keeps this from repeating the kaikki
    defect).

    Args:
        sentences: ``(sentence_id, text)`` pairs (from `parse_tatoeba_tsv`).
        lemma_forms: The lemma surface forms to index (one language's forms).
        max_per_lemma: Stop collecting once a form has this many sentences, so a
            common word does not pull in millions of matches.

    Returns:
        A mapping of the original lemma form to a bounded list of sentence ids.
        Forms with no match are omitted.
    """
    # Index the forms by their normalized text so the scan is driven by the
    # sentence's own tokens, not by the (huge) form list. A naive "for each form,
    # is it in this sentence" loop is O(sentences * forms) - millions x hundreds of
    # thousands - which never finishes; this is O(sentences * tokens).
    single: dict[str, str] = {}  # normalized token -> original form
    multi: dict[str, str] = {}  # normalized multi-word form -> original form
    max_multi = 1
    for form in lemma_forms:
        tokens = _tokens(form)
        if not tokens:
            continue
        if len(tokens) == 1:
            single[tokens[0]] = form
        else:
            multi[" ".join(tokens)] = form
            max_multi = max(max_multi, len(tokens))

    index: dict[str, list[int]] = {}
    for sentence_id, text in sentences:
        tokens = _tokens(text)
        matched: set[str] = set()
        for token in tokens:
            form = single.get(token)
            if form is not None:
                matched.add(form)
        if multi:
            _match_multiword(tokens, multi, max_multi, matched)
        for form in matched:
            _append_capped(index, form, sentence_id, max_per_lemma)
    return index


def _match_multiword(
    tokens: list[str],
    multi: dict[str, str],
    max_multi: int,
    matched: set[str],
) -> None:
    """Add multi-word forms found as a contiguous token run to `matched`.

    Builds only the n-grams the sentence actually contains (up to the longest
    indexed form), so the cost is ``O(tokens * max_multi)``, not ``tokens * forms``.
    """
    n = len(tokens)
    for i in range(n):
        gram = tokens[i]
        for j in range(i + 1, min(i + max_multi, n)):
            gram = f"{gram} {tokens[j]}"
            form = multi.get(gram)
            if form is not None:
                matched.add(form)


def _append_capped(
    index: dict[str, list[int]],
    form: str,
    sentence_id: int,
    cap: int,
) -> None:
    """Append a sentence id to a form's bucket unless it is already at the cap."""
    bucket = index.setdefault(form, [])
    if len(bucket) < cap:
        bucket.append(sentence_id)


def download_tatoeba_sentences(
    langs: Iterable[str],
    *,
    data_fol: Path,
) -> list[StagedDataset]:
    """Download and stage Tatoeba sentence exports for `langs`.

    For each language it fetches the bz2 export over HTTPS, parses it with
    `parse_tatoeba_tsv`, and writes a ``<staging>/tatoeba/<lang>.parquet`` table of
    ``(sentence_id, text)``. Network-isolated and not unit-tested.

    Args:
        langs: ISO 639-1 codes to stage (each must be in `TATOEBA_ISO3`).
        data_fol: Project data folder; the staging cache lives under it.

    Returns:
        One `StagedDataset` per language staged.

    Raises:
        UnknownTatoebaLanguageError: When a language has no Tatoeba export.
    """
    licence, url = KNOWN_LICENSES["tatoeba"]
    out_dir = dataset_dir(data_fol, "tatoeba")
    staged: list[StagedDataset] = []
    for lang in langs:
        iso3 = _tatoeba_iso3(lang)
        src = TATOEBA_SENTENCES_URL.format(iso3=iso3)
        lg.info("Downloading Tatoeba sentences for {} from {}", lang, src)
        raw = _download_bytes(src)
        lines = bz2.decompress(raw).decode("utf-8").splitlines()
        rows = [
            {"sentence_id": sid, "text": text}
            for sid, text in parse_tatoeba_tsv(lines)
        ]
        out = out_dir / f"{lang}.parquet"
        count = write_rows_parquet(rows, out, columns=SENTENCE_COLUMNS)
        lg.info("Staged {} Tatoeba sentences for {} -> {}", count, lang, out)
        staged.append(
            StagedDataset(
                name=f"tatoeba:{lang}",
                source="Tatoeba per-language sentence export",
                version="rolling (download date)",
                license=licence,
                license_url=url,
                path=str(out.relative_to(data_fol)),
                row_count=count,
                notes="sentences; lemma-only join is sense-blind (examples only)",
            ),
        )
    return staged


def _download_bytes(src: str) -> bytes:
    """Fetch a URL over HTTPS and return its bytes (scheme-checked)."""
    if urlsplit(src).scheme != "https":
        msg = f"Refusing non-HTTPS staging download: {src!r}"
        raise ValueError(msg)
    request = Request(src, headers={"User-Agent": _USER_AGENT})  # noqa: S310 - https checked above
    with urlopen(request, timeout=_DOWNLOAD_TIMEOUT_S) as response:  # noqa: S310 - https checked above
        return response.read()


def lemma_forms_by_language(lemmas: Iterable[object]) -> Mapping[str, list[str]]:
    """Group lemma surface forms by language, for the index builder.

    A small convenience so a notebook can turn the corpus `Lemma` rows into the
    ``{language: [form, ...]}`` shape `build_lemma_sentence_index` consumes, one
    language at a time.

    Args:
        lemmas: Any objects exposing ``.language`` and ``.text`` (the corpus
            `Lemma` rows, or lightweight stand-ins).

    Returns:
        A mapping of language code to its list of surface forms.
    """
    by_lang: dict[str, list[str]] = {}
    for lemma in lemmas:
        by_lang.setdefault(lemma.language, []).append(lemma.text)  # type: ignore[attr-defined]
    return by_lang
