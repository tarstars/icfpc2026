# 20260727-chatgpt1-reverse-17: compact linear-time Reverse to score-positive box

- Status: handoff-ready
- Record owner: chatgpt_1
- Work owner: chatgpt_1
- Reviewer: claude
- Integrator: claude
- Problem: `reverse-a-list`
- Base main commit: `a22c521ceac5d9e0fd4216ae339abb7bb0778f8e`
- Branch: `agent/chatgpt-1-solvers`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-27T08:01:00Z`
- Last updated UTC: `2026-07-27T09:52:00Z`

## Identity and synchronization

This task is owned by **chatgpt_1**. chatgpt_2 owns Sort and the Brackets
component line. Claude's room/layout modules and all peer coordination paths are
read-only here.

The branch is synchronized through the consolidated main commit
`a22c521ceac5d9e0fd4216ae339abb7bb0778f8e`, including the corrected wall-fatal
semantics and the mandatory organizer-WASM gate.

## Outcome

Starting from the organizer-WASM-proven single-`Y` Reverse farm, produce a whole
machine with `max(width,height) <= 17`, exact multi-round behavior for list
lengths 1..16, and a like-for-like public score below accepted `reverse_08`'s
`53,023.75`.

## Concrete candidate

```text
artifact  submissions/reverse-a-list/chatgpt1_reverse_09.man
sha256    aa057e97bb3335be37bc49fc652e7f966e8281af9f7ae61dde59035789f87a41
bytes     306
geometry  17x17
structure 3 rooms / 2 pipes / 1 initial man
pipes     [2, 3] cells
```

Architecture:

- four-tick rotated two-`Y` worker factory;
- worker index `k = n - 1 - i` after one common decrement;
- parity split with two shared 14-cell countdown loops;
- `14 / gcd(14,8) = 7` distinct phases per loop and no more than seven
  positive-lap workers of either parity;
- zero-lap bypasses for `k=0` and `k=1`;
- the `k=0` worker sends first, then waits at `U` as the next-round controller.

Independent-model prediction:

```text
public ticks [142, 82, 127, 202, 114, 124, 243, 382]
average      177.0
public score 17^2 * 177.0 = 51,153.0
ratio        0.9647186402 vs 53,023.75
```

The model first reproduced all eight recorded organizer-WASM ticks of
`reverse_fresh_20_fast` exactly, then passed every one-to-three-round length
tuple over 1..16 (4,368 streams), sixteen extreme-value families, and 3,000
seeded random streams with zero failures.

## Exclusive write set

- `coordination/tasks/20260727-chatgpt1-reverse-17.md`
- `coordination/status/chatgpt_1.md`
- `coordination/messages/chatgpt_1/`
- `experiments/chatgpt1-reverse-17/`
- `reports/2026-07-27-chatgpt1-reverse-17.md`
- new immutable artifacts named `submissions/reverse-a-list/chatgpt1_reverse_*.man`

## Shared read-only paths

- all existing Reverse artifacts, generators, tests, catalogs, and submit records;
- `scripts/wasm_judge.py`, `scripts/subdb.py`, and organizer-WASM files;
- parser, simulator, package, lock, policy, room/layout, and peer coordination files.

## Do not touch

- chatgpt_2, `gpt`, Alexey, Claude, or Codex write sets;
- `main`;
- existing immutable `.man` files or submission responses;
- contest state.

## Acceptance checks

Run in Claude's normal checkout:

```bash
PYTHONPATH=src uv run python \
  experiments/chatgpt1-reverse-17/verify_candidate.py
uv run python scripts/wasm_judge.py \
  submissions/reverse-a-list/chatgpt1_reverse_09.man reverse-a-list
uv run python scripts/subdb.py compare \
  submissions/reverse-a-list/chatgpt1_reverse_09.man reverse-a-list
```

Required:

- deterministic generator equals the immutable artifact byte-for-byte;
- pinned SHA, 17x17 geometry, 3/2/1 structure, legal `[2,3]` pipes;
- organizer WASM passes all eight public cases and 1,277 additional lifecycle
  streams;
- actual WASM public score is below `53,023.75`;
- `subdb.py compare` confirms improvement against the currently counted exact
  artifact;
- no wall birth, wall fatal, collision race, live-man leak, shared wall,
  phantom/one-cell pipe, or extra input-room adjacency.

## Contest authority

chatgpt_1 may create and push immutable candidates but may not submit. Claude is
the current coordinator and sole submission controller.

## Handoff

The exact handoff is
`coordination/messages/chatgpt_1/20260727T094500Z-chatgpt1-reverse09-17-square-handoff.md`.
Claude should submit only the pinned SHA after all authoritative gates pass.
