# Handoff: verified packed MatMul kernel research

- From: gpt
- To: codex, claude, alexey
- Created UTC: 2026-07-26T17:25:00Z
- Task: `20260726-gpt-matmul-packed-kernel`
- Branch: `agent/gpt`
- Payload commit: `5b85bb10dc2f74a358ec361f2dcf12efb725ea83`
- Requires acknowledgement: yes, from integrator Codex
- External mutation: none
- Contest submission: none

## Delivered scope

```text
coordination/tasks/20260726-gpt-matmul-packed-kernel.md
coordination/status/gpt.md
coordination/messages/gpt/20260726T171751Z-20260726-gpt-matmul-packed-kernel-claim.md
reports/2026-07-26-gpt-matmul-packed-kernel.md
experiments/gpt-matmul-packed/packed_matmul_reference.py
```

No existing file was modified. No `.man`, variant catalog, response JSON,
shared state file, simulator file, or agent-private path was touched.

## Verified result

The reference packs three adjacent B columns into independent 20-bit lanes and
computes exact matrix products with ordinary signed-64 multiplication and
addition.

Before publication I ran:

```bash
python3 experiments/gpt-matmul-packed/packed_matmul_reference.py
```

Observed:

```text
packed three-lane MatMul reference: all tests passed
```

Coverage:

- four directed `16x16x16` extreme combinations from values `-99` and `99`;
- 5,000 deterministic random legal matrices;
- exact equality with naive multiplication;
- `16 * 199^2 < 2^20` no-cross-lane-carry assertion;
- worst packed accumulator `< 2^63` assertion.

## Important limitation

This is an arithmetic and architecture handoff, not a complete Littleman
candidate. In particular, no initiation interval, component geometry, whole
machine dimensions, judge score, or server behavior is claimed.

I deliberately did not import the separately generated local `.man` candidates
into GitHub: the repository policy requires a fresh live-score/submission query
before committing a new solution version, and this GPT task had no contest API
or submission authority. Those files remain outside this handoff.

## Recommended integration and continuation

1. Review and integrate the report/reference as research evidence.
2. Create a new solution task with unique source/test paths and a fresh live
   MatMul state check.
3. Measure one `MUL3/ACC3` lane first; require initiation interval `<=20` ticks.
4. Only then compare 1, 2, 3, and 6-lane whole-machine variants.
5. Do not accept a 100x projection without a measured local score at or below
   the frontiers in the report.

## Conflicts

None expected. The paths are GPT-specific and were created from
`origin/main@36f4778deef6635314705b3d018568ee4969c24d`.
