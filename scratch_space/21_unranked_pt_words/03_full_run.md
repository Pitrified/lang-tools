---
status: done
---

# Phase 3 - The rest

## Plan

- The remaining ~4,314 words in batches of 100, a handful of subagents at a time.
- `status` at the end; 100 more labels read across the run.

## Done when

- Every worklist word has a label; the counts per label are logged.

## What the implementation found

- Four waves of parallel sonnet subagents, 10, 11, 11 and 12 batches (u0006 to u0049;
  u0045 got the last 14 words because parallel serves race), each batch about 30 s and
  52k tokens. Usage read by the user: 17% to 33% of the session over wave 1 (plus my own
  work), 21% to 23% of the week; the rest projected to about 86% of the session and ran.
- My read of a random 100 across the four waves: 5 disagreements, 95% agreement, the same
  as the pilot: favelar dropped (a real pt-BR verb), anguia and pintasilgo kept (`m enguia`,
  `m pintassilgo`), refundo kept (no pt word for a refund), desensitivizar kept
  (`m dessensibilizar`).
- Re-check `r0002`, by me: those 5 and 12 doubtful labels the subagents flagged
  (íngrime, gordurenta, tunesino, relojeiro, rádon, butâni, demobilizar, chapinar,
  bisbolhetice, vivisecção, bisagra, actinometria).
- Final over the 4,814 words: c 43, u 1,218, r 2,784 kept with a bucket (4,045); m 423,
  f 227, x 119 dropped (769, 16%).
- The subagents put the hard cases in their reports, which made the re-check list cheap
  to build; the labels most often wrong are `m` on a valid variant and `x` on a real but
  unfamiliar word, both of which drop a good word.
