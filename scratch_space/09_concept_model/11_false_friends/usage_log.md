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
