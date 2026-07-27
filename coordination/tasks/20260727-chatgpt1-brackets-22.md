# 20260727-chatgpt1-brackets-22: exact 22-square Brackets composition

- Status: active
- Record owner: chatgpt_1
- Work owner: chatgpt_1
- Reviewer: claude
- Integrator: claude
- Problem: `brackets`
- Base main commit: `2fd9ee6a41fbb2f06e4c3e12510c102be5376bdd`
- Branch: `agent/chatgpt-1-solvers`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-27T09:55:00Z`
- Last updated UTC: `2026-07-27T09:55:00Z`

## Assignment

Claude reassigned chatgpt_1 from the rank-neutral Reverse 17 result to Brackets.
The target is exact: **22x22 or do not submit**. The live
`gpt_brackets_17` machine is 24x24 and organizer-WASM/server accepted. A
23-square projection remains below the next leaderboard boundary, while a
22-square projection crosses four ranks.

chatgpt_2 remains on Sort. Historical `gpt_brackets_*` artifacts and builders
are read-only; chatgpt_1 writes only new names below.

## Outcome

Produce a deterministic 22x22 Brackets `.man` that:

- passes all nine public cases under the corrected one-grace-tick simulator and
  the organizers' WASM;
- passes exhaustive short strings and boundary/random oracle workloads;
- has exactly the intended five rooms, six pipes, and three initial men;
- preserves logical pipe bindings and server input-room adjacency;
- is measured against the currently counted exact artifact using
  `scripts/subdb.py compare`.

## Exclusive write set

- `coordination/tasks/20260727-chatgpt1-brackets-22.md`
- `coordination/status/chatgpt_1.md`
- `coordination/messages/chatgpt_1/`
- `experiments/chatgpt1-brackets-22/`
- `reports/2026-07-27-chatgpt1-brackets-22.md`
- new immutable artifacts named
  `submissions/brackets/chatgpt1_brackets_*.man`

## Shared read-only paths

- `submissions/brackets/gpt_brackets_17.man` and its exact generator/tests;
- all existing Brackets artifacts, catalogs, and submission responses;
- chatgpt_2, `gpt`, Alexey, Claude, and Codex namespaces;
- `scripts/subdb.py`, `scripts/wasm_judge.py`, parser, simulators, package and
  lock files;
- Claude-owned `room_*` and `layout_*` modules.

## Do not touch

- `main`;
- existing immutable `.man` files or submit records;
- peer task/status/message paths;
- contest state.

## Measured starting point

```text
live artifact       gpt_brackets_17
geometry            24x24
public WASM score   213,247.87
live hidden score   376,792.65
box 23 projection   about 346,000 live -- rank neutral
box 22 projection   about 316,600 live -- approximately four ranks
```

Claude measured 345 occupied glyphs in the 24-square canvas. Rooms plus pipes
consume 465 cells, so a 22-square solution is a 96% pack. The 39-cell pipe is
74% of all pipe cells and is the primary routing slack. Rows 7 and 8 are sparse
but load-bearing: deleting them directly destroys three pipes.

## Search order

1. Extract the five room rectangles, six named connections, exact endpoint
   binding ranges, and current route lengths from `gpt_brackets_17`.
2. Generate finite component variants only under behavioral and binding gates;
   prioritize a narrower CLOSE body and a shorter/relocated long transport pipe.
3. Jointly enumerate room order/origins, same-wall ports, and six disjoint
   routes inside a 22-square canvas.
4. Render every abstract survivor and reject parser-created phantom pipes,
   changed bindings, shared walls, one-cell pipes, or extra input adjacency.
5. Judge with the corrected simulator, then organizers' WASM, then
   `scripts/subdb.py compare`.

## Acceptance commands

```bash
PYTHONPATH=src uv run pytest -q -n 0 \
  experiments/chatgpt1-brackets-22/test_candidate.py
uv run python scripts/wasm_judge.py \
  submissions/brackets/<candidate>.man brackets
uv run python scripts/subdb.py compare \
  submissions/brackets/<candidate>.man brackets
```

`wasm_judge.py` is authoritative for value-output problems. The corrected local
simulator is useful for search; a candidate is not releasable merely because
preflight or an abstract router accepts it.

## Contest authority

chatgpt_1 may create and push immutable candidates but may not submit. Claude is
the current coordinator and sole submission controller.
