---
status: in progress
priority: 1
description: |
  Keep rare words out of the drill cards with a commonness floor, and add a medical topic
  that catches diseases, symptoms, drugs and treatments, so a learner app can switch
  specialist medical words off while common ones like cortisona stay.
comment: |
  Raised from the first phone use of acerta (acerta-word-drills, plans/01_bootstrap,
  phase 9 waits on this folder).
---

# Rare words and topics - start

## Original note

From the user, after a round of acerta on the phone (2026-11-15):
"remove fully medical terms - linked to a general topic picker", then, on what counts as
medical: "Keep relatively common ones. A thing like cortisone or lung is ok. atelectasia is
not. Probably the fix is in lang tools not in the app. In general, we have too many C2
words".

acerta draws Portuguese pair matching cards from this corpus through `tool/export_cards.py`
(in acerta), which reads `lemma_cards` and writes one asset; its topic picker (acerta phase
9) needs each card's topics, with a medical one among them.

## Current state

Measured read-only on the 2026-11-13 build (`data/lexicon/`) and on acerta's asset
(29,376 pt cards with an English translation, every card query result for pt):

- **C2 is the tail.** 25,310 of the 29,376 cards are C2; 4,556 of those have no token
  frequency at all (`freq` 0). The bands are cut by fixed cutoffs fitted against Kelly,
  which grades only the ~7.5k most frequent words, so 82% of the corpus lands in C2 by
  design (`docs/library/lexicon.md`, CEFR). C2 holds common words (hemorragia, zipf 3.57,
  is C2) and near-unknown ones in one band.
- **A floor would cut the tail.** Cards kept by a floor on the card's best-sense frequency
  (`sense_frequency`, the `freq` acerta writes; zipf scale): 1.5 keeps 21,806,
  2.0 keeps 18,214, 2.5 keeps 13,776, 3.0 keeps 8,936. A1 to C1 barely move (the floor
  bites almost only C2). On the user's examples: cortisona 2.25, atelectasia 1.43,
  pulmão 3.84, insulina 3.44, voluto 0.
- **Topics.** `ingestion.topics` tags concepts from `data/curated/topics.json`: 26 topics
  from a lexfile map and a WordNet domain map. `health` comes only from the `medicine`
  domain and tags 115 concepts, 43 cards. Diseases (`noun.state`) carry no topic, drugs are
  `objects`, so a medical filter on today's topics would miss nearly everything.
  11,392 cards have no topic (adjectives, adverbs, `noun.state`, `verb.change`, ...).
- **A hypernym rule finds the medical words.** A read-only probe over the closure of 14
  root concepts (ill health, disease, illness, pathology as a state, symptom, injury as a
  state, physical disorder, infection, medicine as a drug, medical care, medical treatment,
  therapy, and the medical sciences), plus glosses opening with a field tag such as
  `(medicine)` or `(pathology)`, catches 867 cards: 853 C2, 3 C1, 7 B2, 3 B1, 1 A2
  (doença, dor, cura, tratamento up to B1). Samples are right (poliomielite, conjuntivite,
  benzodiazepinas, aneurisma); one is wrong (inundações, "flooding", through behaviour
  therapy), which is the sense choice, not the rule.

## Approach

- The floor applies to drill cards, not to the corpus: the corpus keeps every word, a card
  query gets a minimum commonness (a `CardQuery` field, default off so other callers do not
  change), and acerta's export sets it.
- The medical topic is a third map in `topics.json`, from root concepts to topics, applied
  over the hypernym closure, next to the lexfile and domain maps. It is curated input,
  reviewed like the rest of the file, and the build re-applies it.
- The `health` topic stays as the everyday one; the new topic is `medical`, so a learner
  can drop specialist medicine without losing doença or dor. Whether those two overlap is
  Q2.
- The CEFR bands are re-cut (Q3) so that C2 stops being the whole tail: common words such
  as hemorragia move below C2. How (new cutoffs, a band above C2 for the rare tail, or a
  frequency term in the score) is the first phase's analysis, measured against Kelly as
  the bands are today. Every consumer of the bands sees the change; lang-tutor adapts after.
- The floor is zipf 2.0 on the card's best-sense frequency (Q1), applied by acerta's export through the new card
  query field.
- The medical topic tags every word the rule catches, at any level; acerta shows it on by
  default and switching it off removes all of them (Q2).
- Rebuilding the corpus is a deep probe: timed and agreed before it runs.

## Open questions

- Q1: Which floor for the drill cards? It drops words, so it decides what a learner can
  ever see.
  - a. 2.0: keeps 18,214 of 29,376 cards; cortisona (2.25) stays, atelectasia (1.43) goes.
  - b. 2.5: keeps 13,776; cortisona goes too.
  - c. 1.5: keeps 21,806; atelectasia stays.
  - Recommended: a, because it is the lowest floor that matches the user's two examples.
  - ANS: a (2.0).
- Q2: The two asks pull apart: "medical off" in the picker, and "cortisone is ok". With the
  floor of Q1 a, the rare medical words (atelectasia) are gone already, and what the rule
  still catches is the more common ones (cortisona 2.25, insulina 3.44, hemorragia 3.57,
  doença, dor). What should switching medical off remove?
  - a. Medical is on by default; the floor keeps the specialist tail out; switching medical
    off removes every medical word, common ones included ("remove fully").
  - b. Medical is off by default and tags only the words below a second, higher line
    (zipf 3.0): hemorragia, insulina, doença stay, but cortisona goes.
  - c. Medical is off by default and tags every word the rule catches; cortisona and
    doença go unless the learner turns medical on.
  - Recommended: a, because it keeps the user's own examples (cortisona stays by default,
    atelectasia never shows) and still gives the full removal on demand.
  - ANS: a: medical on by default, off removes every medical word.
- Q3: Should the C2 band itself be split (for example a C2 for common words and a band
  above it for the rare tail), beyond the floor?
  - a. No: the floor removes the tail from drills; the bands stay as validated.
  - b. Yes: re-cut the bands so C2 is not 86% of the cards.
  - Recommended: a, because the bands are fitted and validated against Kelly, and the
    complaint is about rare words, which the floor addresses directly.
  - ANS: b, re-cut the levels (the recommendation was a).
- Q4: Which re-cut (numbers in `01_band_analysis.md`)?
  - a. Move the upper edges for every language (C1 from .50, C2 from .60).
  - b. Rank quotas per language.
  - c. Per-language cutoffs: English keeps today's, fitted on English Kelly; Italian gets
    cutoffs fitted on Italian Kelly; pt, es and fr use the Italian ones.
  - Recommended: c, because it improves Italian to 38% exact / 79% within one band with no
    offset, leaves English as validated, and brings acerta's C2 from 79% to 41%.
  - ANS: a (the recommendation was c).
  - Note: C1 starts at 0.50 and C2 at 0.60 for every language; English drops to 29.1% exact,
    72.7% within one band, a mean offset of -0.50.
- Q5: A word with no known frequency (voluto, 8,597 pt lemmas) scores as average. Score it
  as rare instead?
  - a. Yes: an unknown frequency counts as the zipf floor, so such words land in C2.
  - b. No: leave it; the commonness floor keeps them out of acerta anyway.
  - Recommended: a, because "no frequency in wordfreq" means rare far more often than
    average, and a learner app without a floor would otherwise show voluto at B2.
  - ANS: neither; parked as two open points in `scratch_space/open_points.md`, "pt words with
    no frequency" (to be categorized by agents) and "Stray non-pt words in pt" (voluto is not
    Portuguese).
