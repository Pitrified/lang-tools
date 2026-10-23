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
