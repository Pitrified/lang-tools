"""Topic stage: tag concepts with learner topics from a reviewed table (phase 8).

A topic belongs to a *meaning*, not a word - "bank" is `money` in one sense and
`nature` in another - so topics are stored on `Concept`, and a lemma's topics are
derived from its senses when the store is built (`lemma_store`), never persisted
twice. That is the argument that put frequency and CEFR on the sense in phase 6.

Source: the committed, human-reviewed ``data/curated/topics.json``. It holds the
learner vocabulary (a learner's topics, not WordNet's), a ``lexfile -> topics``
map over the 45 WordNet lexicographer classes every concept carries, and a small
``domain -> topics`` map over the OMW English ``domain_topic`` links worth
surfacing to a learner (music, sport, cooking, ...; most of OMW's 430 domains are
specialist - law, chemistry, mythology - and stay unmapped).

Two more maps reach what the lexfile and domain miss. ``hypernym`` maps a root
concept id to topics, and tags the root and every concept below it through the
taxonomy edges (diseases are ``noun.state`` and drugs ``noun.artifact``, so neither
class can carry a medical topic). ``gloss_tag`` maps a field tag to topics, and
tags a concept whose English gloss opens with ``(<tag>)``.

Unmapped on purpose: classes that name a grammatical or abstract bucket rather
than something a learner would browse by (``adj.all``, ``adv.all``,
``noun.attribute``, ``noun.state``, ``verb.change``, ``verb.stative``, ...).
Topics are a filter, so no topic is better than a meaningless one.

Like the curated gloss overrides (05.58), the table is a build input applied by
`ingestion.pipeline.build_initial`: editing it and rebuilding is the only way
topics change, so a rebuild can never silently revert them.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from dataclasses import field
import json
from typing import TYPE_CHECKING

from loguru import logger as lg

from lang_tools.lexicon.relations import TAXONOMY_RELATIONS

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from pathlib import Path

    from lang_tools.lexicon.concept import Concept
    from lang_tools.lexicon.relations import ConceptRelation

#: Committed curated topic table, relative to the project data folder. Under the
#: gitignored ``data/``, so it is force-added like the other curated inputs.
TOPICS_SUBPATH = "curated/topics.json"


class UnknownTopicError(ValueError):
    """Raised when the topic table maps to a topic outside its own vocabulary."""

    def __init__(self, source: str, topic: str) -> None:
        """Initialize with the mapping key and the offending topic.

        Args:
            source: The ``lexfile`` / ``domain`` key whose mapping is invalid.
            topic: The topic that is not in the vocabulary.
        """
        super().__init__(
            f"Topic table maps {source!r} to {topic!r}, which is not in its "
            "vocabulary; add it there or fix the mapping.",
        )
        self.source = source
        self.topic = topic


@dataclass(frozen=True)
class TopicTable:
    """The reviewed learner-topic mapping.

    Attributes:
        vocabulary: Every topic a concept may carry.
        by_lexfile: WordNet lexfile class -> topics.
        by_domain: OMW English ``domain_topic`` name -> topics.
        by_hypernym: Root concept id -> topics given to it and all its
            descendants.
        by_gloss_tag: Field tag opening an English gloss, as in ``(pathology)``
            -> topics.
    """

    vocabulary: frozenset[str]
    by_lexfile: dict[str, tuple[str, ...]]
    by_domain: dict[str, tuple[str, ...]]
    by_hypernym: dict[str, tuple[str, ...]] = field(default_factory=dict)
    by_gloss_tag: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Reject a mapping that points outside the vocabulary."""
        for kind in (
            self.by_lexfile,
            self.by_domain,
            self.by_hypernym,
            self.by_gloss_tag,
        ):
            for source, topics in kind.items():
                for topic in topics:
                    if topic not in self.vocabulary:
                        raise UnknownTopicError(source, topic)

    def topics_for(self, lexfile: str | None, domains: set[str]) -> list[str]:
        """Return the sorted topics for a concept's lexfile and domains."""
        topics: set[str] = set(self.by_lexfile.get(lexfile or "", ()))
        for domain in domains:
            topics.update(self.by_domain.get(domain, ()))
        return sorted(topics)

    def topics_for_gloss(self, gloss: str | None) -> tuple[str, ...]:
        """Return the topics of the field tag a gloss opens with, if any."""
        if not gloss or not gloss.startswith("("):
            return ()
        tag = gloss[1:].split(")", 1)[0]
        return self.by_gloss_tag.get(tag, ())


@dataclass(frozen=True)
class TopicStats:
    """What `assign_topics` did, for the build manifest.

    Attributes:
        tagged: Concepts that received at least one topic.
        stale_roots: Hypernym roots the build does not contain.
        per_root: Concepts under each present root, the root included.
    """

    tagged: int = 0
    stale_roots: int = 0
    per_root: dict[str, int] = field(default_factory=dict)


def _descendants(
    root: str,
    children: Mapping[str, list[str]],
) -> set[str]:
    """Return ``root`` and every concept below it (one BFS over the children)."""
    seen = {root}
    queue = deque([root])
    while queue:
        for child in children.get(queue.popleft(), ()):
            if child not in seen:
                seen.add(child)
                queue.append(child)
    return seen


def topics_path(data_fol: Path) -> Path:
    """Return the curated topic table path under a data folder."""
    return data_fol / TOPICS_SUBPATH


def load_topic_table(data_fol: Path) -> TopicTable | None:
    """Load the curated topic table, or ``None`` when the file does not exist.

    Args:
        data_fol: Project data folder.

    Returns:
        The validated `TopicTable`, or ``None`` (a build without the file tags no
        topics, which the gate's coverage section then shows).

    Raises:
        UnknownTopicError: When a mapping names a topic outside the vocabulary.
    """
    path = topics_path(data_fol)
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return TopicTable(
        vocabulary=frozenset(raw.get("vocabulary", [])),
        by_lexfile={k: tuple(v) for k, v in raw.get("lexfile", {}).items()},
        by_domain={k: tuple(v) for k, v in raw.get("domain", {}).items()},
        by_hypernym={k: tuple(v) for k, v in raw.get("hypernym", {}).items()},
        by_gloss_tag={k: tuple(v) for k, v in raw.get("gloss_tag", {}).items()},
    )


def assign_topics(
    concepts: list[Concept],
    table: TopicTable | None,
    concept_domains: Mapping[str, set[str]],
    relations: Iterable[ConceptRelation] = (),
) -> TopicStats:
    """Set each concept's `topics` from the table, in place.

    Args:
        concepts: The build's concepts (mutated).
        table: The reviewed topic table; ``None`` leaves every concept untagged.
        concept_domains: ``{concept_id: {domain name, ...}}`` from the OMW
            ``domain_topic`` links (English only in OMW 1.4).
        relations: Concept edges; the `TAXONOMY_RELATIONS` types carry the
            hypernym roots' topics down to their descendants.

    Returns:
        The tagged count, the hypernym roots this build lacks, and the concepts
        under each root that it has.
    """
    if table is None:
        lg.info("No curated topic table; concepts stay untagged")
        return TopicStats()
    children: dict[str, list[str]] = {}
    if table.by_hypernym:
        for rel in relations:
            if rel.relation_type in TAXONOMY_RELATIONS:
                children.setdefault(rel.concept_id_b, []).append(rel.concept_id_a)
    present = {concept.id for concept in concepts}
    inherited: dict[str, set[str]] = {}
    per_root: dict[str, int] = {}
    stale_roots = 0
    for root, root_topics in table.by_hypernym.items():
        if root not in present:
            lg.warning("Topic root {} is not in this build; skipped", root)
            stale_roots += 1
            continue
        below = _descendants(root, children)
        per_root[root] = len(below)
        for concept_id in below:
            inherited.setdefault(concept_id, set()).update(root_topics)
    tagged = 0
    for concept in concepts:
        topics = set(
            table.topics_for(
                concept.lexfile,
                concept_domains.get(concept.id, set()),
            ),
        )
        topics.update(inherited.get(concept.id, ()))
        topics.update(table.topics_for_gloss(concept.definitions.get("en")))
        concept.topics = sorted(topics)
        if concept.topics:
            tagged += 1
    lg.info("Tagged {} of {} concepts with a learner topic", tagged, len(concepts))
    return TopicStats(tagged=tagged, stale_roots=stale_roots, per_root=per_root)
