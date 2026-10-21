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

Unmapped on purpose: classes that name a grammatical or abstract bucket rather
than something a learner would browse by (``adj.all``, ``adv.all``,
``noun.attribute``, ``noun.state``, ``verb.change``, ``verb.stative``, ...).
Topics are a filter, so no topic is better than a meaningless one.

Like the curated gloss overrides (05.58), the table is a build input applied by
`ingestion.pipeline.build_initial`: editing it and rebuilding is the only way
topics change, so a rebuild can never silently revert them.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import TYPE_CHECKING

from loguru import logger as lg

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from lang_tools.lexicon.concept import Concept

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
    """

    vocabulary: frozenset[str]
    by_lexfile: dict[str, tuple[str, ...]]
    by_domain: dict[str, tuple[str, ...]]

    def __post_init__(self) -> None:
        """Reject a mapping that points outside the vocabulary."""
        for kind in (self.by_lexfile, self.by_domain):
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
    )


def assign_topics(
    concepts: list[Concept],
    table: TopicTable | None,
    concept_domains: Mapping[str, set[str]],
) -> int:
    """Set each concept's `topics` from the table, in place.

    Args:
        concepts: The build's concepts (mutated).
        table: The reviewed topic table; ``None`` leaves every concept untagged.
        concept_domains: ``{concept_id: {domain name, ...}}`` from the OMW
            ``domain_topic`` links (English only in OMW 1.4).

    Returns:
        How many concepts received at least one topic.
    """
    if table is None:
        lg.info("No curated topic table; concepts stay untagged")
        return 0
    tagged = 0
    for concept in concepts:
        concept.topics = table.topics_for(
            concept.lexfile,
            concept_domains.get(concept.id, set()),
        )
        if concept.topics:
            tagged += 1
    lg.info("Tagged {} of {} concepts with a learner topic", tagged, len(concepts))
    return tagged
