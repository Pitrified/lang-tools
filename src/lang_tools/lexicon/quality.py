"""Data-quality checks and report renderer for the Parquet corpus.

Phase 05.56 extracted the 05.4 diagnosis notebook's inline DuckDB SQL and
hand-written report prose into this module: each check is a named query
returning a typed `CheckResult`, `run_quality_checks` executes them all over a
corpus and evaluates the regression invariants, and `render_report` /
`write_report` turn the result into a markdown report. The queries and the
report text live here as the single source of truth; the notebook under
``scratch_space/09_concept_model/05.4_data_quality/`` is only a thin caller
that regenerates ``report.md`` on every run.

Invariants:
    The report leads with four regression invariants read against the rebuilt
    corpus (see ``05.56_rebuild_gate.md``):

    - kaikki-tagged rows are zero (the 5.5 Step-1 cleanup holds on disk),
    - dangling edges (sense or relation endpoints) are zero,
    - lemmas without a sense are zero,
    - ``definition == lemma`` rows do not exceed the recorded baseline
      (`DEFINITION_EQUALS_LEMMA_BASELINE`). Re-scoped in phase 5.55 (Q3): a
      gloss that equals a *different* member of a multi-member synset is a
      valid OMW gloss ("capital of Louisiana" for Baton Rouge), so the check
      counts only glosses equal to the concept's *sole* member form in that
      language (genuinely thin); the 5.55 gloss repair drove this to 0 and the
      baseline is now 0, so any new thin gloss fails the gate.
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

from pydantic import BaseModel
from pydantic import Field

from lang_tools.lexicon.codec import LEXICON_SUBDIR
from lang_tools.lexicon.codec import StoreDependencyMissingError
from lang_tools.lexicon.lemma_store import CorpusNotFoundError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

#: `definition == lemma` row count under the 5.55 Q3 scope (gloss equals the
#: sole member form). The invariant reads as "at most the baseline"; the 5.55
#: gloss repair fixed the single remaining row, so the baseline is 0 and any
#: newly introduced thin gloss fails the gate.
#: History: the pre-re-scope check (gloss equals *any* member) measured 7,220
#: on the kaikki-era build and 20 on the 05.56 rebuild; the re-scoped check
#: measured 1 on the 2026-07-11 tier-1 rebuild, repaired 2026-09-01.
DEFINITION_EQUALS_LEMMA_BASELINE = 0

#: Tables queried by the checks; partitioned tables glob their per-language files.
_TABLE_GLOBS = {
    "concepts": "concepts.parquet",
    "lemmas": "lemmas/*.parquet",
    "senses": "senses/*.parquet",
    "false_friends": "false_friends.parquet",
    "concept_relations": "concept_relations.parquet",
}


class CheckResult(BaseModel):
    """One executed check: a captioned table of rows.

    Attributes:
        name: Stable snake_case identifier of the check.
        title: Section title used in the rendered report.
        description: One-paragraph explanation rendered under the title.
        columns: Column names of the result table.
        rows: Result rows, one list per row, values already plain scalars.
    """

    name: str
    title: str
    description: str
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)


class InvariantResult(BaseModel):
    """One evaluated regression invariant.

    Attributes:
        name: Stable snake_case identifier of the invariant.
        title: Human-readable label used in the report's leading table.
        value: The measured number.
        requirement: The pass condition, in words.
        passed: Whether the measured value satisfies the requirement.
    """

    name: str
    title: str
    value: int
    requirement: str
    passed: bool


class QualityReport(BaseModel):
    """The full outcome of a quality pass over one corpus.

    Attributes:
        corpus: The corpus directory the checks ran against.
        generated_at: UTC timestamp of the run.
        invariants: The evaluated regression invariants (report leads with these).
        results: Every executed check, in execution order.
    """

    corpus: str
    generated_at: datetime
    invariants: list[InvariantResult]
    results: list[CheckResult]

    @property
    def passed(self) -> bool:
        """True when every invariant holds."""
        return all(inv.passed for inv in self.invariants)


def _connect() -> Any:  # noqa: ANN401 - duckdb connection, lazy optional dep
    """Open an in-memory DuckDB connection, failing loud without the extra."""
    try:
        import duckdb  # noqa: PLC0415 - lazy so the `store` extra stays optional
    except ImportError as exc:  # pragma: no cover - only without the extra
        raise StoreDependencyMissingError from exc
    return duckdb.connect()


def _table_sources(data_fol: Path) -> dict[str, str]:
    """Map each table to its ``read_parquet(...)`` source expression."""
    table_dir = data_fol / LEXICON_SUBDIR
    return {
        name: f"read_parquet('{table_dir / glob}')"
        for name, glob in _TABLE_GLOBS.items()
    }


def _fetch(con: Any, sql: str) -> tuple[list[str], list[list[Any]]]:  # noqa: ANN401
    """Run a query and return (columns, rows) with plain list rows."""
    cursor = con.execute(sql)
    columns = [d[0] for d in cursor.description]
    rows = [list(row) for row in cursor.fetchall()]
    return columns, rows


def _scalar(con: Any, sql: str) -> int:  # noqa: ANN401
    """Run a single-value query and return it as an int."""
    return int(con.execute(sql).fetchone()[0])


def _has_column(con: Any, source: str, column: str) -> bool:  # noqa: ANN401
    """Report whether the Parquet source exposes the given column."""
    described = con.execute(f"DESCRIBE SELECT * FROM {source}").fetchall()
    return column in [row[0] for row in described]


# --------------------------------------------------------------------------- #
# Check registry: (name, title, description, sql builder over the source map).
# --------------------------------------------------------------------------- #

def _def_eq_sole_member_hits(t: dict[str, str]) -> str:
    """Return the shared CTE prefix selecting `definition == lemma` hits.

    Scope (phase 5.55 Q3): a hit is a per-language gloss that, normalized,
    equals the concept's **sole** member form in that language - a genuinely
    thin gloss. A gloss equal to a *different* member of a multi-member synset
    is a valid short definition and is excluded. Used by the two rendered
    checks and the invariant so the three can never drift.
    """
    return f"""
WITH defs AS (
  SELECT c.id AS concept_id, unnest(map_entries(c.definitions)) AS kv
  FROM {t["concepts"]} c
),
members AS (
  SELECT s.concept_id, l.language, l.normalized, l.text,
         count(*) OVER (PARTITION BY s.concept_id, l.language) AS n_members
  FROM {t["senses"]} s JOIN {t["lemmas"]} l ON l.id = s.lemma_id
),
hits AS (
  SELECT d.concept_id, d.kv.key AS lang, d.kv.value AS definition, m.text AS lemma
  FROM defs d
  JOIN members m ON m.concept_id = d.concept_id AND m.language = d.kv.key
  WHERE m.n_members = 1 AND lower(strip_accents(d.kv.value)) = m.normalized
)
"""


_CHECKS: list[tuple[str, str, str, Callable[[dict[str, str]], str]]] = [
    (
        "row_counts",
        "Row counts",
        "Total rows per source-of-truth table.",
        lambda t: f"""
SELECT 'concepts' AS tbl, count(*) AS n FROM {t["concepts"]}
UNION ALL SELECT 'lemmas', count(*) FROM {t["lemmas"]}
UNION ALL SELECT 'senses', count(*) FROM {t["senses"]}
UNION ALL SELECT 'false_friends', count(*) FROM {t["false_friends"]}
UNION ALL SELECT 'concept_relations', count(*) FROM {t["concept_relations"]}
""",
    ),
    (
        "lemmas_per_language",
        "Lemmas per language",
        "Lemma rows by language (OMW member forms).",
        lambda t: f"""
SELECT language, count(*) AS n_lemmas FROM {t["lemmas"]}
GROUP BY language ORDER BY n_lemmas DESC
""",
    ),
    (
        "edge_reconciliation",
        "Edge reconciliation (must be zero)",
        "Senses and relations must point at real rows and every lemma must have "
        "an edge; any nonzero is a transform bug.",
        lambda t: f"""
SELECT 'sense->missing lemma' AS check, count(*) AS n
  FROM {t["senses"]} s LEFT JOIN {t["lemmas"]} l ON s.lemma_id = l.id
  WHERE l.id IS NULL
UNION ALL
SELECT 'sense->missing concept', count(*)
  FROM {t["senses"]} s LEFT JOIN {t["concepts"]} c ON s.concept_id = c.id
  WHERE c.id IS NULL
UNION ALL
SELECT 'lemma with no sense', count(*)
  FROM {t["lemmas"]} l LEFT JOIN {t["senses"]} s ON l.id = s.lemma_id
  WHERE s.lemma_id IS NULL
UNION ALL
SELECT 'relation->missing concept', count(*)
  FROM {t["concept_relations"]} r
  LEFT JOIN {t["concepts"]} ca ON r.concept_id_a = ca.id
  LEFT JOIN {t["concepts"]} cb ON r.concept_id_b = cb.id
  WHERE ca.id IS NULL OR cb.id IS NULL
""",
    ),
    (
        "cardinality_distributions",
        "Cardinality distributions",
        "Lemmas per concept and concepts per lemma (min/p50/p95/max/avg).",
        lambda t: f"""
WITH per_concept AS (
  SELECT concept_id, count(*) n FROM {t["senses"]} GROUP BY concept_id
),
per_lemma AS (
  SELECT lemma_id, count(*) n FROM {t["senses"]} GROUP BY lemma_id
)
SELECT 'lemmas_per_concept' AS dist,
       min(n) AS min, quantile_cont(n, 0.5) AS p50,
       quantile_cont(n, 0.95) AS p95, max(n) AS max,
       round(avg(n), 2) AS avg
FROM per_concept
UNION ALL
SELECT 'concepts_per_lemma',
       min(n), quantile_cont(n, 0.5), quantile_cont(n, 0.95), max(n),
       round(avg(n), 2)
FROM per_lemma
""",
    ),
    (
        "degenerate_concepts",
        "Emptiness and degenerate cardinality",
        "Concepts with no gloss in any language, exactly one gloss, no member "
        "(orphan), or a single member.",
        lambda t: f"""
WITH members AS (
  SELECT concept_id, count(*) n FROM {t["senses"]} GROUP BY concept_id
),
glosses AS (SELECT id, len(map_keys(definitions)) g FROM {t["concepts"]})
SELECT
  (SELECT count(*) FROM glosses WHERE g = 0) AS concepts_no_gloss_any_lang,
  (SELECT count(*) FROM glosses WHERE g = 1) AS concepts_single_gloss,
  (SELECT count(*) FROM {t["concepts"]} c
     LEFT JOIN members m ON c.id = m.concept_id
     WHERE m.n IS NULL) AS concepts_orphan_no_member,
  (SELECT count(*) FROM members WHERE n = 1) AS concepts_single_member
""",
    ),
    (
        "language_span",
        "Single- vs multi-language concepts",
        "Concepts whose members span one vs several languages; multi-language is "
        "the cross-lingual grouping the design exists for.",
        lambda t: f"""
WITH langs AS (
  SELECT s.concept_id, count(DISTINCT l.language) nl
  FROM {t["senses"]} s JOIN {t["lemmas"]} l ON s.lemma_id = l.id
  GROUP BY s.concept_id
)
SELECT count(*) FILTER (WHERE nl = 1) AS single_language,
       count(*) FILTER (WHERE nl > 1) AS multi_language,
       round(100.0 * count(*) FILTER (WHERE nl > 1) / count(*), 1) AS pct_multi
FROM langs
""",
    ),
    (
        "gloss_coverage",
        "Gloss coverage per language",
        "Of the concepts that have a lemma in language L, how many carry an L "
        "gloss (post-cleanup: real OMW coverage, no kaikki inflation).",
        lambda t: f"""
WITH cl AS (
  SELECT DISTINCT s.concept_id, l.language
  FROM {t["senses"]} s JOIN {t["lemmas"]} l ON s.lemma_id = l.id
)
SELECT cl.language,
       count(*) AS concepts_touched,
       count(*) FILTER (
         WHERE list_contains(map_keys(c.definitions), cl.language)
       ) AS with_gloss,
       round(100.0 * count(*) FILTER (
         WHERE list_contains(map_keys(c.definitions), cl.language)
       ) / count(*), 1) AS pct_gloss
FROM cl JOIN {t["concepts"]} c ON c.id = cl.concept_id
GROUP BY cl.language ORDER BY concepts_touched DESC
""",
    ),
    (
        "concept_example_coverage",
        "Concept example coverage",
        "Concepts carrying at least one example sentence, per example language "
        "(examples are OMW synset examples, concept-level per 5.5 Step 4).",
        lambda t: f"""
WITH per_lang AS (
  SELECT unnest(map_keys(examples)) AS language FROM {t["concepts"]}
  WHERE len(map_keys(examples)) > 0
)
SELECT language, count(*) AS concepts_with_examples
FROM per_lang GROUP BY language ORDER BY concepts_with_examples DESC
""",
    ),
    (
        "lexfile_coverage",
        "Lexfile coverage",
        "Concepts carrying the WordNet lexicographer file label "
        "(concept-level per 5.5 Step 4).",
        lambda t: f"""
SELECT count(*) AS concepts,
       count(*) FILTER (
         WHERE lexfile IS NOT NULL AND lexfile <> ''
       ) AS with_lexfile,
       count(DISTINCT lexfile) AS distinct_lexfiles
FROM {t["concepts"]}
""",
    ),
    (
        "relation_types",
        "Concept relation types",
        "Typed concept-relation edges by type (hypernym edges from 5.5 Step 4; "
        "hyponymy is the reverse read, not stored).",
        lambda t: f"""
SELECT relation_type, count(*) AS n
FROM {t["concept_relations"]} GROUP BY relation_type ORDER BY n DESC
""",
    ),
    (
        "pos_distribution",
        "Part-of-speech distribution",
        "Mapped part-of-speech counts; a `<null>` bucket would flag OMW codes "
        "outside our map.",
        lambda t: f"""
SELECT coalesce(part_of_speech, '<null>') AS pos, count(*) AS n
FROM {t["lemmas"]} GROUP BY 1 ORDER BY n DESC
""",
    ),
    (
        "kaikki_tagged_lemmas",
        "kaikki-tagged lemmas (must be zero)",
        "Lemmas whose `sources` list still includes kaikki; the 5.5 Step-1 "
        "cleanup removed the writer, so any hit means a stale corpus.",
        lambda t: f"""
SELECT language,
       count(*) AS n_lemmas,
       count(*) FILTER (WHERE list_contains(sources, 'kaikki')) AS kaikki_tagged
FROM {t["lemmas"]} GROUP BY language ORDER BY n_lemmas DESC
""",
    ),
    (
        "slug_collisions_top",
        "Top shared concept slugs",
        "Most-collided `c__{slug}__{hash}` slugs - a legibility issue (ids stay "
        "unique via the hash); routed to phase 8.",
        lambda t: f"""
WITH s AS (SELECT split_part(id, '__', 2) AS slug FROM {t["concepts"]})
SELECT slug, count(*) AS n_concepts FROM s GROUP BY slug
HAVING count(*) > 1 ORDER BY n_concepts DESC, slug LIMIT 20
""",
    ),
    (
        "slug_collision_totals",
        "Slug collision totals",
        "Distinct slugs vs total concepts, and the generic `concept` fallback "
        "count.",
        lambda t: f"""
WITH s AS (SELECT split_part(id, '__', 2) AS slug FROM {t["concepts"]})
SELECT count(*) AS concepts,
       count(DISTINCT slug) AS distinct_slugs,
       count(*) FILTER (WHERE slug = 'concept') AS generic_concept_slug
FROM s
""",
    ),
    (
        "definition_equals_lemma",
        "definition == lemma (the `house` smell)",
        "Per-language definitions that, normalized, equal the concept's *sole* "
        "member form in that language - a genuinely thin gloss (5.55 Q3 scope; "
        "gloss-equals-other-member coincidences are valid and excluded). The "
        "residual count is the 5.55 gloss-repair worklist.",
        lambda t: _def_eq_sole_member_hits(t)
        + """
SELECT (SELECT count(*) FROM hits) AS definition_equals_lemma_rows,
       (SELECT count(DISTINCT concept_id) FROM hits) AS concepts_affected
""",
    ),
    (
        "definition_equals_lemma_samples",
        "definition == lemma samples",
        "A sample of offending (concept, language, definition, lemma) rows "
        "under the 5.55 Q3 sole-member scope.",
        lambda t: _def_eq_sole_member_hits(t)
        + """
SELECT concept_id, lang, definition, lemma FROM hits
ORDER BY concept_id, lang LIMIT 25
""",
    ),
    (
        "suspicious_lemmas",
        "Suspicious lemmas",
        "Multi-word, digit-bearing, or very long member forms a cleanup pass "
        "might drop/flag.",
        lambda t: f"""
SELECT count(*) FILTER (WHERE text LIKE '% %') AS multiword,
       count(*) FILTER (WHERE regexp_matches(text, '[0-9]')) AS has_digit,
       count(*) FILTER (WHERE length(text) > 30) AS very_long
FROM {t["lemmas"]}
""",
    ),
]


def _provenance_check(con: Any, t: dict[str, str]) -> CheckResult:  # noqa: ANN401
    """Snapshot the on-disk `source` provenance column where present.

    The column is written only by the provenance-aware pipeline dump; the
    seed/sample corpus omits it, so presence is guarded per table rather than
    assumed.
    """
    parts = [
        f"SELECT '{name}' AS tbl, source, count(*) AS n "
        f"FROM {t[name]} GROUP BY source"
        for name in ("concepts", "lemmas", "senses")
        if _has_column(con, t[name], "source")
    ]
    description = (
        "Per-row on-disk source tag counts (omw|cili|llm|manual; kaikki is a "
        "legacy value no writer sets)."
    )
    if not parts:
        return CheckResult(
            name="provenance_snapshot",
            title="Provenance snapshot",
            description=description,
            columns=["note"],
            rows=[["no `source` column in this corpus (seed/sample build)"]],
        )
    columns, rows = _fetch(con, " UNION ALL ".join(parts) + " ORDER BY tbl, n DESC")
    return CheckResult(
        name="provenance_snapshot",
        title="Provenance snapshot",
        description=description,
        columns=columns,
        rows=rows,
    )


def _evaluate_invariants(
    con: Any,  # noqa: ANN401
    t: dict[str, str],
    *,
    definition_equals_lemma_baseline: int,
) -> list[InvariantResult]:
    """Measure and evaluate the four 05.56 regression invariants."""
    kaikki_lemmas = _scalar(
        con,
        f"SELECT count(*) FROM {t['lemmas']} "
        f"WHERE list_contains(sources, 'kaikki')",
    )
    kaikki_disk = sum(
        _scalar(
            con,
            f"SELECT count(*) FROM {t[name]} WHERE source = 'kaikki'",
        )
        for name in ("concepts", "lemmas", "senses")
        if _has_column(con, t[name], "source")
    )
    dangling = _scalar(
        con,
        f"""
SELECT (SELECT count(*) FROM {t["senses"]} s
          LEFT JOIN {t["lemmas"]} l ON s.lemma_id = l.id WHERE l.id IS NULL)
     + (SELECT count(*) FROM {t["senses"]} s
          LEFT JOIN {t["concepts"]} c ON s.concept_id = c.id WHERE c.id IS NULL)
     + (SELECT count(*) FROM {t["concept_relations"]} r
          LEFT JOIN {t["concepts"]} ca ON r.concept_id_a = ca.id
          LEFT JOIN {t["concepts"]} cb ON r.concept_id_b = cb.id
          WHERE ca.id IS NULL OR cb.id IS NULL)
""",
    )
    lemma_no_sense = _scalar(
        con,
        f"""
SELECT count(*) FROM {t["lemmas"]} l
LEFT JOIN {t["senses"]} s ON l.id = s.lemma_id WHERE s.lemma_id IS NULL
""",
    )
    def_eq_lemma = _scalar(
        con,
        _def_eq_sole_member_hits(t) + "SELECT count(*) FROM hits",
    )
    return [
        InvariantResult(
            name="kaikki_tagged_rows",
            title="kaikki-tagged rows (sources list + on-disk source)",
            value=kaikki_lemmas + kaikki_disk,
            requirement="0",
            passed=(kaikki_lemmas + kaikki_disk) == 0,
        ),
        InvariantResult(
            name="dangling_edges",
            title="dangling sense / relation endpoints",
            value=dangling,
            requirement="0",
            passed=dangling == 0,
        ),
        InvariantResult(
            name="lemmas_without_sense",
            title="lemmas with no sense",
            value=lemma_no_sense,
            requirement="0",
            passed=lemma_no_sense == 0,
        ),
        InvariantResult(
            name="definition_equals_lemma",
            title="definition == lemma rows (sole-member scope)",
            value=def_eq_lemma,
            requirement=f"at most the {definition_equals_lemma_baseline} baseline",
            passed=def_eq_lemma <= definition_equals_lemma_baseline,
        ),
    ]


def run_quality_checks(
    data_fol: Path,
    *,
    definition_equals_lemma_baseline: int = DEFINITION_EQUALS_LEMMA_BASELINE,
) -> QualityReport:
    """Run every quality check and invariant over the corpus at ``data_fol``.

    Args:
        data_fol: Project data folder; the corpus lives under
            ``<data_fol>/lexicon/``.
        definition_equals_lemma_baseline: Baseline row count the
            ``definition == lemma`` invariant compares against.

    Returns:
        The full `QualityReport` (invariants + every check result).

    Raises:
        CorpusNotFoundError: When no Parquet corpus exists at the location.
        StoreDependencyMissingError: When the ``store`` extra (duckdb) is
            not installed.
    """
    corpus_dir = data_fol / LEXICON_SUBDIR
    if not (corpus_dir / "concepts.parquet").exists():
        raise CorpusNotFoundError(corpus_dir)

    t = _table_sources(data_fol)
    con = _connect()
    try:
        results = []
        for name, title, description, builder in _CHECKS:
            columns, rows = _fetch(con, builder(t))
            results.append(
                CheckResult(
                    name=name,
                    title=title,
                    description=description,
                    columns=columns,
                    rows=rows,
                )
            )
        results.append(_provenance_check(con, t))
        invariants = _evaluate_invariants(
            con,
            t,
            definition_equals_lemma_baseline=definition_equals_lemma_baseline,
        )
    finally:
        con.close()
    return QualityReport(
        corpus=str(corpus_dir),
        generated_at=datetime.now(tz=UTC),
        invariants=invariants,
        results=results,
    )


def _md_cell(value: Any) -> str:  # noqa: ANN401 - arbitrary scalar cell
    """Render one table cell, escaping markdown pipes."""
    return "" if value is None else str(value).replace("|", "\\|")


def _md_table(columns: list[str], rows: list[list[Any]]) -> str:
    """Render a markdown table from columns and rows."""
    head = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = ["| " + " | ".join(_md_cell(v) for v in row) + " |" for row in rows]
    return "\n".join([head, sep, *body])


def render_report(report: QualityReport) -> str:
    """Render a `QualityReport` to the full markdown report text.

    The report leads with the invariant table so a regression is obvious on a
    re-run; every check section follows in execution order.
    """
    status = "PASS" if report.passed else "FAIL"
    lines = [
        "# 05.4 data quality - report",
        "",
        f"Generated: {report.generated_at:%Y-%m-%d %H:%M UTC} - "
        "**auto-generated by `lang_tools.lexicon.quality`** "
        "(re-run the quality notebook to refresh; never hand-edit).",
        f"Corpus: `{report.corpus}`",
        "",
        "Read-only QA pass; nothing is modified. "
        "Spec + interpretation: [`../05.4_data_quality.md`](../05.4_data_quality.md); "
        "gate: [`../05.56_rebuild_gate/05.56_rebuild_gate.md`]"
        "(../05.56_rebuild_gate/05.56_rebuild_gate.md).",
        "",
        f"## Invariants - {status}",
        "",
        _md_table(
            ["invariant", "value", "required", "status"],
            [
                [inv.title, inv.value, inv.requirement, "ok" if inv.passed else "FAIL"]
                for inv in report.invariants
            ],
        ),
        "",
    ]
    for result in report.results:
        lines += [f"## {result.title}", "", result.description, ""]
        lines += [_md_table(result.columns, result.rows), ""]
    return "\n".join(lines) + "\n"


def write_report(report: QualityReport, path: Path) -> Path:
    """Render the report and write it to ``path`` (parents created).

    Returns:
        The path written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(report), encoding="utf-8")
    return path
