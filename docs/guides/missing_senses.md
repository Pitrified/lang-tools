# Missing senses

How to run the full card-sense pass on a language: review its most frequent cards, add the
meanings the corpus does not link, bring back the words an earlier review removed, and measure
how far two reviewers agree.
pt was the first language through it; es and fr follow the same steps.

The labels and their rules are in [Reviewing card senses](sense_review.md); the agent workflow
is the `sense-review` skill under `.claude/skills/`. This page is the order of the steps and
what to check between them.

All commands run from the repo root, with:

```bash
CLI="uv run --no-sync python -m lang_tools.lexicon.ingestion.sense_review_cli"
```

## 1. The worklist

```bash
$CLI worklist --language pt            # the 1,000 most frequent single-word cards
$CLI worklist-removed --language pt    # then the words a review removed, after them
```

`worklist-removed` appends every lemma a card-sense review dropped every link from and the
corpus no longer holds; it is served with the links that were dropped. Write the lemma ids to a
keys file, one per line, in worklist order:

```bash
uv run --no-sync python -c "
from lang_tools.lexicon.ingestion.sense_review import load_worklist
from lang_tools.params.lang_tools_params import get_lang_tools_params
data = get_lang_tools_params().paths.data_fol
print('\n'.join(i.lemma_id for i in load_worklist(data) if i.language == 'pt'))
" > data/work/sense_review/keys_pt.txt
```

## 2. The first review

Serve the keys under the current rulebook, 200 a batch, and hand each batch to its own
subagent:

```bash
$CLI recheck --batch m0001 --keys data/work/sense_review/keys_pt.txt
```

`recheck` skips a lemma whose latest best-sense row was written under the current rulebook, so
`m0002`, `m0003`, ... walk through the list, and a lemma reviewed by an earlier pass is served
again whenever the rules have changed since. Measure the cost of the first batch and report it
before serving the rest.

A batch shows each word as the built corpus holds it, and curated rows only take effect at
build. Rebuild before a re-check of words an earlier review changed, so the reviewer sees its
additions and pins; a `k` then endorses the card a learner sees. Dropped links are not shown:
a drop that was wrong after all is a hand `restore`.

After the batches, read each batch's notes file (`data/work/sense_review/<batch>.notes.txt`),
check every line against the corpus, and apply it by hand: `$CLI drop` for a wrong member,
`$CLI add` for a capitalised name.

## 3. The second review

A second, blind review measures how often two reviewers reach the same outcome under the same
rules. Pick at least 500 items, targeted: every item the first review changed, then kept items
to fill. Serve them as a second review, to subagents that never see the first labels:

```bash
$CLI recheck --batch n0001 --keys data/work/sense_review/second_pt.txt --shadow
$CLI apply --batch n0001 --labels data/work/sense_review/n0001.labels.txt --shadow
$CLI agreement --first m0001 m0002 m0003 m0004 m0005 m0006 --second n0001 n0002 n0003
```

Serve both reviews from the same build, so the second sees what the first saw. A word counts
as second-reviewed once per rulebook: after a rule change the same keys are served again.
A second review writes no curated row, only its outcomes, to
`data/curated/sense_review_shadow_log.jsonl`. `agreement` counts the items both labelled, how
many reach the same card, how many the same card, drops and addition, and, of the items the
first review changed, how many the second review changed the same way. It lists every
disagreement, and apart from them the twins: outcomes that differ only by a card on two
concepts sharing an English member (WordNet's two entries for "six"), counted again in
`agree_on_changed_twins`. Read the twins list before trusting that count.

Read it this way:

- 90% or more agreement on the changed items: the first review's labels stand, and a single
  review is enough for the next language.
- Less: the disagreements point at the rules. Group them by reason, fix the rule that splits
  the reviewers, and serve the affected items again under the new rulebook.

### What the pt run found

On pt the first review changed 157 of 1,000 cards, and a second review of 500 items agreed on
92% of all cards but on only 69% of the changed ones (75% counting twins). The split was not
noise; it came from three gaps in the rules, now closed in the rulebook:

- **Near misses.** When sense 1 was a narrow or neighbouring reading of the everyday meaning
  (*arquivos* "archives" for "files", *nenhum* "neither" for "no"), one reviewer added the
  everyday meaning and the other kept the card. `k` now means the everyday meaning itself.
- **Twins.** Two WordNet entries for one meaning ("six" as a quantity and as the number) were
  picked either way. The rule is now the concept holding the base word, else the most common.
- **Drops next to an addition.** A reviewer who added the right meaning often left the wrong
  one in place.

The disagreements were labelled again under the new rules, and a second review of all 1,000
cards on the rebuilt corpus kept 154 of the 157 changes (98%): a new language can start from
the fixed rules with a single review, and a second review of 500 targeted items to confirm.
That review would change 50 of the 1,000 cards (5%, against 157 before); they were labelled
once more and applied.

## 4. Rebuild and re-count

Rebuild ([Rebuilding the corpus](rebuild_corpus.md)), and check `_build.json` under
`sense_additions`: the senses added, the lemmas created, and zero stale. Then serve the same
1,000 cards once more, as a second review against the rebuilt corpus, and compare: the share of
cards kept is the after measurement.

Commit `data/curated/best_senses.jsonl`, `member_form_drops.jsonl`, `sense_additions.jsonl`,
both review logs, and the label and notes files under `data/work/sense_review/` (under Git LFS;
add them with `git add -f`).
