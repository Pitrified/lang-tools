# implementation tracking

Fix the pt cards whose right meaning is not linked, and bring back the frequent words the card
review removed, through a new curated input of sense additions applied at build. Measured
before and after on the pt top 1,000 cards. Analysis and decisions in
[`00_start.md`](00_start.md).

## Key decisions

- All fixes land in lang-tools; lang-tutor only bumps its pin (user, 2026-11-06).
- Decisions rest on at least 500 targeted corpus items: the pt top 1,000 cards and the 60
  removed lemmas, reviewed in full before and after (user, 2026-11-06).
- Reviewers (Q8 a): one agent per batch with hidden gold, plus one measured blind second
  review of 500 targeted items; the user reads numbers, not Portuguese.
- lang-tutor is never a blocker to a lang-tools change (user, Q7).
- One mechanism for every fix: an addition row (link + pin), plus the existing drops and pins;
  the review harness of `12_card_senses` is extended, not copied.

## Phases

| #  | Phase                 | Plan                               | Status  |
| -- | --------------------- | ---------------------------------- | ------- |
| 1  | Tooling               | [`01_tooling.md`](01_tooling.md)   | done    |
| 2  | Agent review          | [`02_review.md`](02_review.md)     | done    |
| 3  | Rebuild and re-count  | [`03_recount.md`](03_recount.md)   | done    |
| 4  | Release v0.4.0        | [`04_release.md`](04_release.md)   | done    |

Status values: draft / planned / in progress / done / superseded / discarded.

## Log

Append-only. Newest at the bottom.

- 2026-11-05 : folder spun off from `12_card_senses` (its Q8) as a draft word list.
- 2026-11-06 : widened on the user's request to fix the 16 doubtful pt cards here, on branch
  `feat/13_missing_senses`. Read against the corpus: all 16 need a new link (none a change to
  the translation rule); *natal* and *índia* are capitalised-twin cases; the card review
  removed 60 pt lemmas; 28 of the 34 stale look-alike rows sit on them, 6 on closed-class words.
  Five draft phases, Q1 to Q6 raised. Measurement rule (500 or more targeted items) added.
- 2026-11-06 : Q1 to Q6 answered (both the verb link and the form; capitalisation, with
  lowercase proper nouns cleaned up; agents on top of agents; drop and clean up; es/fr out with
  a how-to guide; v0.4.0). Phases rewritten to four: tooling, agent review (which is also the
  baseline count), rebuild and re-count, release. Q7 raised: where the form note lives.
- 2026-11-06 : Q7 a (`Sense.form_note`, carried to the card). Q2 note: the lowercase proper
  nouns were a guess; causes will be tallied from the review's reasons. Q3 reopened (the phrase
  was sarcastic) and assessed from the logs as Q8: gold 424/465 on look-alikes but a noisy
  reference; the 24% of re-reviewed pairs that changed all followed rule changes; same-rules
  agreement never measured. Recommended one agent plus a blind second review of 500 items.
- 2026-11-06 : Q8 a. All questions answered; meta-experiments on the review method are welcome
  (the phase 2 measurement is the first). Phase 1 planned, phases 2 to 4 draft.
- 2026-11-06 : phase 1 started. Plan review against the code: serve skips reviewed lemmas
  (needs a recheck mode); the second review needs a shadow apply; removed lemmas need items built
  from their drops; pins key on concept keys (no change); provenance `SOURCE_MANUAL`; POS from
  the lexfile; `form_note` along the `is_best` path. Folded into `01_tooling.md`.
- 2026-11-06 : phase 1 done. Sense additions input and stage, `form_note` to the card, the `a`
  action, removed-lemma items, recheck and shadow second review, `agreement`, hand `add` and
  `drop`, `concepts` lookup; rulebook, skill, how-to guide and library docs. `make check` green
  (433), docs strict. Hidden gold for the `a` action moved to phase 2. 64 removed pt lemmas on
  the real corpus (60 from the review, 4 gold).
- 2026-11-06 : phase 2 started. Plan review: the 60 removed lemmas are already in the 1,000
  (the worklist is 1,000, not 1,064; `worklist-removed` now skips gold). Gold for the `a` action:
  *funcionário*, *gatos*, *turma*, *carreira*; `import-gold` now adds a missing link. The four gold
  verb forms' answers moved to Q1 a (base word's concept), gold file made latest-row-wins, the
  corpus fixed with `add` and form notes. A batch can no longer draw one of its own items as
  gold. Found in passing: frequent pt number words are absent from the corpus altogether
  (*doze*, *quinze*, *trinta*, *quarenta*, ...), a gap outside this folder's worklist.
- 2026-11-06 : first batch `m0001` (200 + 2 gold), one subagent: 90,903 tokens, 3.4 minutes.
  155 kept, 1 pinned, 6 senses dropped, 43 added (mostly inflected forms with form notes:
  *são*, *fez*, *há*, *minutos*, *primeira*; and *sim* "yes", *aí* / *lá* "there"); gold 1/2.
  The miss was the gold's fault: *turma* is also "a group of friends", now accepted too. The
  notes line applied (pt *yes* dropped from "yes"). *deve*, *possa* stay out: WordNet has no
  modal verbs. Additions read and judged right.
- 2026-11-06 : `m0001` committed. Usage meter before `m0002` to `m0005` (user's reading): 5-hour
  20%, weekly 63%. The four batches served (202 items each) and handed to four subagents in
  parallel.
- 2026-11-06 : first review done (`m0001` to `m0005`, 1,000 cards, five subagents, 85k to 98k
  tokens each): 843 kept, 147 added, 5 pinned, 17 senses and 1 lemma dropped, 32 edge cases;
  gold 8/10, both misses on the gold side (*turma*, widened; *era*, raised as Q9: the rulebook's
  old homograph example contradicts the form rule). Notes files: 18 member lines, 17 applied as
  drops, `conflitos` kept (a plural on its base concept is right under Q1). The 500 targeted items
  for the second review are the 157 changed plus 343 kept cards with two or more senses, in rank
  order, shuffled (seed 13) into `data/work/sense_review/second_pt.txt`.
- 2026-11-06 : first review cost: `m0002` to `m0005` took 21% of the 5-hour meter and 3% of the
  weekly one (about 5% of the 5-hour meter a batch). Q9 answered a (the frequent reading wins),
  applied after the second review. Second review started: `n0001` to `n0003` (200/200/100) from
  `second_pt.txt`, under the unchanged rulebook.
- 2026-11-06 : second review `n0001` to `n0003` applied (shadow; 500 items; gold 5/6, the miss
  is *era*, Q9). `agreement`: 458/500 same card, 447/500 same outcome, 108/157 on the changed
  items (69%, below 90%). Disagreements tallied by cause into Q10 (28 near-miss threshold, 14
  WordNet twins, 11 extra drops). Notes: *eis* on "in or at that place", *lucro* and *saqué* on
  "interest, sake", still to check.
- 2026-11-06 : committed the first and second review data (`fda1433`). Q10 a: `concepts` prints
  each concept's commonness and lists the most common first; `agreement` takes the store and
  counts twins apart (outcomes differing only by a card on two concepts sharing an English
  member, with the same drops and both or neither adding). A first cut counted any shared
  member and caught real splits (*câmeras* "camera" against "tv camera"); tightened, it finds
  9 twins, all genuine, and agreement on the changed items is 117/157 (75%) with them.
  Rulebook (`35151d6c864c`): `k` is the everyday meaning itself; "a near miss is not the card";
  Q9's "the frequent reading wins over an everyday homograph" (*era*, *meia*, *juro*, *sede*);
  the twin tie-break (the concept holding the base word, else the first listed); "an addition
  does not clean the item". *era* gold re-answered to "be" and the card linked by `add`;
  *lucro* dropped from "interest, sake" (n0003 notes; *saqué* and *eis* were already dropped).
  `m0006` served: the 53 disagreements and 2 gold. The rulebook examples are drawn from these
  items, so `m0006` is not a measurement; phase 3's second review of the 1,000 is.
- 2026-11-06 : `m0006` applied (rulebook `35151d6c864c`): 4 kept, 2 pinned, 7 senses dropped,
  43 added; gold 2/2; 13 edge cases. Notes: *carriera* (Italian) dropped from "career",
  capitalised *Oriente* linked to "the countries of Asia". Found: a re-check's `k` writes an
  unpinned row but leaves the earlier review's additions and drops in place (*seguros* keeps
  the first review's "safe", *marina* its dropped dock, *eis* its "here"), because the item is
  served from the worklist snapshot, not the corpus as the earlier rows leave it (Q11).
- 2026-11-06 : phase 2 closed (before table, agreement and gold in `02_review.md`; the pt
  findings in `docs/guides/missing_senses.md`). Q11's premise corrected: a re-check is served
  from the built corpus, which had not been rebuilt since the first review; so Q11 a is
  "rebuild before a re-check" (guide and skill), no code. Phase 3 started. Rebuild:
  `sense_additions` 171 added, 62 lemmas created, 0 stale; best senses 163 applied, 0 stale;
  look-alikes 6,838 (stale 10, down from 34); gate PASS. pt gloss coverage 99.9%: 27 concepts
  first linked to pt by an addition carry no pt gloss (a paid gloss-translate run, to ask).
  The seed gains the `form_note` field. 8010 restarted. A second review now counts as done
  once per rulebook (the 500 of `n0001` to `n0003` were under the old one); after review
  `n0004` to `n0008` served, the 1,000 on the rebuilt corpus, rulebook `35151d6c864c`.
- 2026-11-06 : after review `n0004` to `n0008` applied (shadow; 1,000; gold 10/10): 876 kept,
  84 pinned, 37 added, 5 senses dropped. Of the 157 items the first review changed, 154 are kept
  as now built (98%, above the 90% bar): the rule fix holds. But 85 pins fell on cards the first
  review kept, and they traced to a defect: a label that does not pin wrote a best-sense row
  with no concept, so on a re-check (latest row wins) a `k` released the `12_card_senses` pin
  and the card fell back to the frequency pick (*praia* "coast" over "beach", *presidente*
  "executive of a firm"). 97 pins were released; the after review, blind, pinned 74 of them
  back. Fixed: a label now pins the card it leads to (the added or pinned sense, else the first
  left; nothing for a removed item or `x`), with a test; the 97 restored by correction rows
  (the card each `m` label endorsed). One of them, *eis*, endorsed a link `m0004` had dropped
  (`m0006` was labelled on the pre-review corpus), so the build counted it stale; re-pinned to
  "here". Rebuild: best senses 259 applied. Notes (`n0005`): *jazida* dropped from "centre",
  capitalised *Porto* linked to the city. `m0007` served: the 39 after-review changes the
  released pins do not explain (32 additions, 7 pins or drops) and the 23 released-pin words
  the after review did not pin back, under rulebook `35151d6c864c`, on the rebuilt corpus.
- 2026-11-06 : `m0007` applied (62 items; 33 kept, 4 pinned, 25 added; gold 2/2); its notes
  gave 5 junk members (*word memory*, *deseo*, *montivar*, *bensderaiz*, *comerembanquete*),
  dropped. Final rebuild: 197 senses added, 63 lemmas created, 300 pins, 0 stale; look-alikes
  stale 10; gate PASS; 8010 restarted and serving form notes. Before 157/1,000 cards a
  reviewer changes, after 50 (5.0%) once the 74 pin-defect changes are set aside; 154/157
  first-review changes kept. Phase 3 closed; the still-wrong cards and their reasons are in
  `03_recount.md`.
- 2026-11-06 : the 33 pt gloss gaps closed without the paid job (user's call): 32 glosses
  hand-written into `gloss_backfill.jsonl` (the build tags them `llm`, as the file carries no
  author field), and the 33rd was a wrong OMW link, pt *próximo a* on the Lao coin "at",
  dropped. Rebuild and gate PASS; pt gloss coverage 100.0%; 8010 restarted.
- 2026-11-06 : phase 4: CHANGELOG 0.4.0, version 0.4.0 (`uv lock` raised the lock revision to 5
  with this box's uv; set back to 3, `uv lock --check` passes), `make check` and docs build
  pass; release commit `45982d8`, `--no-ff` merge into main `1397b10`, annotated tag `v0.4.0`.
  The lang-tutor pin resolves from GitHub, so the bump waits for the user's push.
- 2026-11-08 : phase 4 closed: the user pushed; lang-tutor pin bumped to `v0.4.0` on its
  branch `deps/lang-tools-v0.4.0` (`uv lock`, `make undev`, `make check` 148 passed), 8000
  restarted on it. Folder done.
- 2026-11-10 : phase 4 closed after the fact: v0.4.0 was released, merged into main (`1397b10`)
  and pinned in lang-tutor (`890f337`) on 2026-11-08; only the status was left behind. Folder done.
