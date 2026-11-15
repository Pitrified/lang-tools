---
status: planned
---

# Phase 2 - Medical topic

## Overview

A learner app needs to switch specialist medicine off. Today's `health` topic comes only
from OMW's `medicine` domain (115 concepts); diseases are `noun.state` (no topic) and drugs
are `objects`. A read-only probe found the medical words through the hypernym closure of 14
root concepts plus a field tag at the start of the gloss (`00_start.md`, Current state).
Context: [`00_start.md`](00_start.md).

## Goals

1. `medical` in the topic vocabulary, tagged on every concept under the reviewed roots or
   whose English gloss opens with a reviewed field tag.
2. The roots and tags are curated input in `data/curated/topics.json`, re-applied by the
   build.

## Plan

- `topics.json`: a `hypernym` map (root concept id to topics) and a `gloss_tag` map (tag to
  topics), with the 14 roots and the tags of the probe; the vocabulary gains `medical`.
- `ingestion.topics`: `TopicTable` reads the two maps; `assign_topics` takes the hypernym
  closure (the same `hypernym` and `instance_hypernym` edges `hypernym_depths` walks) and
  the English gloss.
  A root id that the build no longer has is counted as stale in `_build.json`, like the
  other curated inputs.
- Tests on the bootstrap seed: a disease, a drug and a gloss-tagged concept get `medical`,
  an unrelated concept does not; a stale root is counted.
- Review: the 867 cards of the probe listed by root, a sample of 50 read, roots or tags
  adjusted; the wrong hit (inundações, "flooding", through behaviour therapy) is a sense
  choice and stays.
- Docs: `docs/library/lexicon.md`, Topics.

## Out of scope

- Other topics.

## Done when

- `make check` passes; the counts per root on the built corpus are logged in phase 5.
