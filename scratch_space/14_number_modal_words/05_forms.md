---
status: done
---

# Phase 5 - inflected forms of the top 1,000

## Overview

Give the frequent inflected forms a card on their base word's meaning, with a form note, as
*são* has (Q7 a).
Context: [`00_start.md`](00_start.md) Q5, Q7; [`01_gap_assessment.md`](01_gap_assessment.md).
After phase 4, so the forms of *poder* and *dever* are already done and skipped here.

## Plan

- The list: the absent words of the pt top 1,000 that phase 1 grouped as forms of a word the
  corpus has (197), less the modal forms, the numbers and the names the rules mistook for forms
  (*rui*, *gomes*), which I strike by hand first.
- Labels (Q6): subagents in batches of about 50. Each line names the base word, the concept
  (the base word's card unless the form is used in another meaning), and the form note in the
  house style (`plural of "ano": years`, `1st person singular preterite of "ficar": I
  stayed`). I check every line, then apply them in one process.
- Rebuild, gate, read every card on 8010.
- At the end, raise Q7 b (an inflection model for the forms beyond the top 1,000) again in
  `00_start.md`, with what this phase cost per form.

## Out of scope

- The forms beyond the top 1,000 (Q7 b).
- Forms of a word the corpus lacks (*questões*): they follow their base word in phase 2.

## Done when

- Every listed form has a lemma on its concept with a form note, zero stale rows, `make check`
  and the gate pass, each card was read, and Q7 b is raised again.

## What the implementation found

- 195 rule-found forms less 13 struck (10 modal forms, *milhões*, *segunda*, the name
  *silva*), plus 5 the rules missed (*boa*, *boas*, *meses*, *tá*, *fiquei*): 187 forms.
- Four subagents in batches of 47 (about 223k tokens, 1 to 2 minutes each), 195 adds. They
  corrected 8 wrong bases (*gosta* to *gostar*, *novas* to *novo*, *algumas* to *algum*, ...)
  and moved about 20 forms off the base word's card where the form means something else (*todos*
  "all" not "each", *muitos* "many" not "very", *pais* "parents", *redes* "networks", *graças*
  "thanks to", *reais* the currency).
- They found base words whose own card is wrong: *rede* "cloth", *graça* "joke", *atividade*
  "action", *receber* "get, acquire", none of them in the 1,000 cards `13_missing_senses`
  reviewed; raised as Q12. (*pouco* "a little" was reviewed, and is right for the singular.)
- Cost per form: about 1,200 subagent tokens and a check line each. Q7 b raised again as
  Q11.
