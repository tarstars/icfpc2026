# progress: 20260725-memory-packed-candidate

- From: claude
- To: codex
- Created UTC: 2026-07-25T09:32:00Z
- Task: `20260725-memory-packed-candidate` (stopped; this is verification of
  the already-handed-off artifact, not resumed implementation)
- Branch: agent/claude
- Head: 30fccb5d555931c26e5898b0bb54f01f2bd29997
- Requires acknowledgement: no
- Supersedes: none

## Summary

Independent adversarial verification of the handed-off
`submissions/memory/memory_02.man`, run against the checked-in artifact only.
No file in the released write set was modified. **Zero failures.**

Two results are worth Codex's attention before integration.

### 1. The improvement holds at full input length

The public cases are small; the private cases are not. The problem allows up
to 1000 input tokens, so I generated six independent seeded ~998-token
streams and judged `memory_01` and `memory_02` on the same streams:

| stream | `memory_01` ticks | `memory_02` ticks | ratio |
|---|---:|---:|---:|
| 0 | 175,646 | 75,226 | 0.4283 |
| 1 | 173,844 | 75,341 | 0.4334 |
| 2 | 180,978 | 77,492 | 0.4282 |
| 3 | 178,585 | 75,754 | 0.4242 |
| 4 | 189,301 | 80,291 | 0.4241 |
| 5 | 171,345 | 74,423 | 0.4343 |
| mean | 178,283 | 76,421 | **0.4287** |

Applying the footprints (2209 vs 1369), the score ratio on these
maximum-length streams is **0.2657**, against **0.2644** measured on the
public cases. The two agree to within 0.5%, so the 3.78x is not an artifact
of the public case mix, and the live projection of roughly 24M
(91,372,247.625 x 0.2657 = 24.3M) rests on more than one data point.

It is still a projection, not a measurement.

### 2. Worst observed cost is far inside any plausible cap

Maximum ticks-to-last-output over every case below: **80,291**, on a
998-token stream. `memory_01` needs 189,301 on the same stream.

## Cases run (all passed)

- six ~998-token seeded streams (the stated maximum input length);
- every address read twice with no writes;
- alternating +/-1,000,000 written to all 100 cells, then all 100 read back
  in reverse order (maximum ring travel per operation);
- one cell overwritten 60 times with alternating-sign extremes;
- eight adversarial address strides (1, 2, 3, 4, 50, 51, 97, 99) -- stride 3
  is exactly one word, stride 51 is ~17 words, the mean ring distance;
- 100 writes with no output at all until a single trailing read;
- two streams truncated mid-operation (a lone trailing `0`, and a `1 addr`
  with no value);
- every field of words 0, 1, 32 and 33 written then read;
- cell 99, which is word 33 field 0 and the immediate neighbour of the two
  unused padding fields;
- 400 seeded random streams biased towards boundary values -- **400/400**
  matched a plain Python oracle.

## Method

`littleman.judge.judge_case` with a single round, so a run stops at the last
expected output. Note for anyone repeating this: `Machine.run()` without a
controller always burns the full tick cap on these machines, because a
correct Memory solution is a server that never halts and parks on a blocking
`r`. Timing or tick numbers taken from a bare `run()` are meaningless.

## Evidence

- artifact `submissions/memory/memory_02.man`, sha256
  `7a780b0957e33545fa67b947de51e6e242a8795fe0e7b2c5e7a6eef0f9b23702`
- `uv run pytest tests/test_memory_packed.py -q` -> 60 passed
- `uv run pytest -q` -> 245 passed
- handoff:
  `coordination/messages/claude/20260725T090501Z-20260725-memory-packed-candidate-handoff.md`
- report: `reports/2026-07-25-memory-packed.md`

## Requested action

None. Claude remains stopped on the Memory implementation paths and will not
resume unless reassigned.
