# Harness usage log

Data points linking token use to the 5-hour session limit meter, to size later review passes.
The meter is read by the user, and other sessions may share it, so note when they were stopped.

Tokens are rough. "Context" is the size of one call's prompt. "Processed" adds up every call's
prompt, since each call re-reads its whole context, though most of that is cache reads.
Subagent tokens come from the harness's per-agent usage line.

## 2026-10-23: two 200-pair batches (a0011, a0012)

Meter 79% to 86% (+7 points). Other sessions were stopped, so all of it is this session.

| Part | Calls | Context per call | Processed input | Output |
| --- | ---: | --- | ---: | ---: |
| Main session, after compaction | about 22 | 98k to 112k | about 2.3M | about 15k |
| Subagent a0011 (84.8k tokens, 6 tool uses) | about 7 | 25k to 85k | about 0.4M | about 15k |
| Subagent a0012 (83.8k tokens, 6 tool uses) | about 7 | 25k to 84k | about 0.4M | about 15k |
| **Total** | about 36 | | **about 3.1M** | **about 45k** |

- The meter also includes the `/compact` that started this segment: one call reading the long
  pre-compaction transcript and writing the summary. Its size is unknown, so these 7 points
  overstate the cost of the batches.
- Most of the processed input is the main session: a long orchestrating context, re-read on
  every small step (commits, notes, notifications). The subagents themselves took about 0.8M.
- Rough rate for sizing: 400 reviewed pairs for 7 points of a 5-hour window, including the
  orchestration. A lean orchestrator (fresh or short session, several batches per turn, one
  commit at the end) should get noticeably more pairs per point. Measure that next time.

## 2026-10-23: four 200-pair batches, lean orchestrator (a0013 to a0016)

Meter 35% to 45% (+10 points); weekly meter 43% to 44% (+1 point). The run began right after a
`/compact`, which the user read before the start (35%), so it is not counted here.

| Part | Calls | Context per call | Processed input | Output |
| --- | ---: | --- | ---: | ---: |
| Main session (serve all four in one call, launch in one turn, commit once) | about 8 | 85k to 95k | about 0.7M | about 5k |
| Subagent a0013 (82.0k tokens, 5 tool uses) | about 6 | 25k to 82k | about 0.35M | about 15k |
| Subagent a0014 (82.1k tokens, 6 tool uses) | about 7 | 25k to 82k | about 0.4M | about 15k |
| Subagent a0015 (82.1k tokens, 5 tool uses) | about 6 | 25k to 82k | about 0.35M | about 15k |
| Subagent a0016 (83.3k tokens, 6 tool uses) | about 7 | 25k to 83k | about 0.4M | about 15k |
| **Total** | about 34 | | **about 2.2M** | **about 65k** |

- Rough rate: 800 pairs for 10 points of the 5-hour window, about 80 pairs per point, against
  about 57 per point in the first run. The lean orchestrator is the difference: subagents now
  take most of the processed input.
- Each 200-pair subagent costs about 82k tokens, very stable across the four.
- Sizing the rest of the worklist (about 62.1k pairs): about 780 points of the 5-hour window,
  that is about 8 full windows at roughly 100 points each. On the weekly meter, 800 pairs moved
  it 1 point, so the rest is about 78 points: more than one week's budget at this rate.
- Quality held: gold 19/20 (the miss is pt *pagode* / en *pagoda*, gold `c`, agent `p` for the
  BR samba sense), 23 edge cases flagged over 800 pairs.

## 2026-10-23: second lean round, four 200-pair batches (a0017 to a0020)

Meter 45% to 52% (+7 points); weekly meter 44% to 45% (+1 point). No `/compact` before or during
the round, so this is the cleanest data point so far. The web UI also showed "thinking 5s ..
344k tokens" next to a reasoning step of the main session. That counter moves with each reasoning
step, so it tracks the running turn, not the meter; it is recorded here only as a reference.

| Part | Calls | Processed input | Tokens (harness) |
| --- | ---: | ---: | ---: |
| Main session (serve in one call, launch in one turn, short status replies, three commits) | about 10 | about 1M | |
| Subagent a0017 (5 tool uses) | about 6 | about 0.35M | 82.5k |
| Subagent a0018 (7 tool uses) | about 8 | about 0.45M | 82.7k |
| Subagent a0019 (7 tool uses) | about 8 | about 0.45M | 82.7k |
| Subagent a0020 (7 tool uses) | about 8 | about 0.45M | 85.7k |
| **Total** | about 40 | **about 2.7M** | **333.6k subagents** |

- Rough rate: 800 pairs for 7 points, about 115 pairs per point (versus 80 for round 1, which
  carried more orchestration, and 57 for the first run). Read the 5-hour meter as roughly 2
  points per 200-pair subagent, with orchestration on top.
- Weekly: 1 point per 800 pairs in both lean rounds. The rest of the worklist (about 61.3k
  pairs) is about 75 weekly points, so it spans more than one week.
- Quality: gold 18/20 this round (misses pt *macaco* / it *macaco*, gold `p`; pt *estufa* /
  it *stufa*, gold `f`), 96/100 overall. 30 edge cases in 800 pairs.
- Open rule question raised by two agents: near-identical pairs against a common known word
  that nobody would confuse (pt *dado* / en *dad*, *cabo* / *cab*, *preto* / *pretty*) are
  labelled `f!` under the current guide, though `u` may fit better.

## Round 3: eight 200-pair batches in parallel, after `/compact` (a0021 to a0028)

Meter 53% to 72% (+19 points); weekly meter 45% to 48% (+3 points). `/compact` ran just before
the round; eight agents were launched in one turn, and the main session made two commits while
they ran.

| Part | Tokens (harness) |
| --- | ---: |
| Subagents a0021 to a0028 (5 to 7 tool uses each) | 83.6k, 82.6k, 84.9k, 81.9k, 83.5k, 81.4k, 83.4k, 84.7k |
| **Total** | **666.0k subagents** |

- Rough rate: 1,600 pairs for 19 points, about 84 pairs per point, or about 2.4 points per
  200-pair subagent. That is worse than round 2 (115), so eight in parallel did not save
  anything; the compact itself and the meter's 1-point granularity may account for part of it.
- Weekly: 1,600 pairs for 3 points, about 530 pairs per point. The rest of the worklist (about
  59.7k pairs) is about 110 weekly points at this rate, or 75 at the round 2 rate.
- Quality: gold 34/40 this round, 130/140 overall; 48 edge cases in 1,600 pairs. Misses:
  *sopa* / en *soap* (gold `f`, swapped letters not covered by the near-identical rule),
  *busto* / it *busta* and *seta* / it *setta* (gold `f`, agents applied "own cognate wins"),
  *andar* / it *andare* (gold `p`, agent `c`), *guardar* / it *guardare* and *brigar* / it
  *briga* (gold `p`, agents `f` when a minor sense is shared).
- Open rule questions: identical spelling versus own cognate (pt *branca* / it *branca*, agent
  `f!`); swapped letters; `p` versus `f` when only a minor sense is shared.
- Tier A stands at 4,600/5,499 after 28 batches.

## Round 4: tier A finish, five batches under the settled rules (a0029 to a0033)

Meter 74% to 86% (+12 points); weekly meter 48% to 50% (+2 points). No `/compact` before the
round; five agents were launched in one turn, and the main session made three commits while they
ran.

| Part | Tokens (harness) |
| --- | ---: |
| Subagents a0029 to a0032 (200 pairs each) | 84.6k, 86.1k, 83.6k, 82.9k |
| Subagent a0033 (99 pairs) | 73.7k |
| **Total** | **410.9k subagents** |

- Rough rate: 899 pairs for 12 points, about 75 pairs per point. The small last batch costs
  nearly as much as a full one, since most of each subagent's tokens go to reading the guide and
  the skill, not to the pairs.
- Weekly: 899 pairs for 2 points, about 450 pairs per point.
- Quality: gold 23/25 this round, 153/165 overall; 30 edge cases in 899 pairs. Misses: pt
  *torcer* / en *torque* (gold `c`, agent `u`; the gold row looks wrong) and pt *salá* / it
  *sala* (gold `f`, agent `u` because pt *salá* is rare).
- Tier A is complete: 5,499/5,499 after 33 batches.

### Corpus rebuild after tier A

`build_initial` (five languages, about 4 minutes) applied the 6,499 reviewed rows: 2,946
look-alike edges (2,468 cognate, 266 full, 212 partial), 0 stale; unrelated rows give no edge.
The previous build had 984 edges. The sample corpus carries 8.

## Round 5: tier B start, twelve 200-pair batches in parallel (b0001 to b0012)

Meter 60% at launch; the session limit was reached during the round's wrap-up (100%, +40
points or more, against the 30 planned). All twelve batches had applied by then. No `/compact` just before; the
twelve batches were reserved up front with `serve --tier B --size 200`, then twelve agents were
launched in one turn, sized for about 30 points at round 4's 2.4 points per agent.

| Part | Tokens (harness) |
| --- | ---: |
| Subagents b0001 to b0006 | 82.5k, 85.4k, 88.2k, 87.7k, 86.9k, 84.4k |
| Subagents b0007 to b0012 | 84.9k, 84.9k, 82.8k, 84.2k, 84.0k, 83.7k |
| **Total** | **1,019.6k subagents** |

- Quality: gold 54/60 this round, 224/245 overall; 130 edge cases in 2,400 pairs.
- Tier B stands at 2,400/6,701 after 12 batches.
- Rate: 2,400 pairs for at least 40 points, at most 60 pairs per point, against 75 to 115 in
  rounds 2 to 4. Twelve parallel agents plus a main session that committed after every few
  hand-backs cost more per pair than expected; size the next round at about 3.3 points per
  agent, and commit once at the end.
