# WORK ORDER: the room assembler (`lane.py`) — the missing multiplier

Motivated by measured failures, both from 2026-07-25:

- Codex's FSM->room compiler produced a CORRECT LLLM LOADER at
  **723 x 8134** (footprint ~66M; our best whole machine is 49,729).
  It lowers each state to its own corridor: no row sharing, no reuse.
- Three subagents failed to hand-lay corridors at all; the successful
  ones (snake, memory) spent most of their effort on turns, merges,
  literal placement and return paths — not on the algorithm.

Both failures are the same missing tool. `canvas.py` places ROOMS and
draws PIPES; nothing helps INSIDE a room. This order specifies that.

## Deliverable

`src/littleman/lane.py` + `tests/test_lane.py`. Pure geometry+layout;
no problem-specific knowledge.

## Core API (shape is fixed; naming may improve)

```python
Op = str            # one glyph, or a literal token "`123`"
Lane.seq(ops)                    # straight-line ops
Lane.branch_sign(neg=, zero=, pos=)   # X; sub-lanes; auto merge
Lane.branch_bp(taken=, straight=)     # d / a
Lane.loop_counted(body, bp_expr)      # >rsv/^md family
Lane.loop_forever(body)               # racetrack
Lane.label(name) / Lane.goto(name)    # explicit FSM edges (rare)
room = Lane(...).compile(max_width=W, ports={...})
room.grid        # list[str], walls included
room.cells[i]    # (r,c) of the i-th emitted op  <- test/audit handle
room.metrics     # rows, cols, cells_used, fill_ratio, ticks_per_lap
```

## Hard requirements (these are what make it worth building)

1. **Serpentine packing by default.** A straight run wraps at
   `max_width` with a two-cell turn (`v` then `<`), alternating
   direction. Literal tokens are emitted ATOMICALLY — never split
   across a wrap — and written reversed on right-to-left rows
   (cookbook §7).
2. **Backtick-column safety.** After layout, verify no two backticks
   share a column with only digits/spaces between them (the rule the
   organizers formalized 2026-07-25 and `sim.py` enforces). If a
   collision is detected, shift the offending literal by one cell and
   re-verify. This is the single most common silent load error.
3. **Branch geometry from a pattern library, not ad hoc.** X-fork with
   the standard merge cell; `d`-at-corner conditional turn; an
   `unreachable` arm compiles to an UNROUTED corridor (walking into a
   wall = the assertion). Arms re-converge at a declared merge with an
   invariant string recorded in `room.metrics`.
4. **Prologue placement off the lap.** Seeds/init emitted before the
   racetrack entry, never re-entered (the brackets bug, encoded).
5. **`room.cells` index map** so tests and the ir_export binding audit
   can refer to "the 3rd `s`" without hand-counting glyphs.
6. **Compaction pass (the part Codex's compiler lacks).** After a naive
   layout, run at least: (a) trailing-space trim per row; (b) merge
   adjacent single-use corridors that share a direction; (c) reuse the
   return column across sequential blocks; (d) tighten `max_width` by
   binary search, recompiling and keeping the best legal result by
   `max(rows, cols)`. Report before/after in metrics.

## Acceptance — reproduce hand-built rooms, then beat the compiler

1. **Byte-parity on a hand-built room**: express `memory_packed.py`'s
   HEAD room (a straight-line lane with two literals) as a Lane and
   compile it to the SAME grid, byte-for-byte. If exact parity proves
   impossible, produce a room that is no larger and passes memory_04's
   own tests when substituted (state which you achieved).
2. **Branching room**: same treatment for memory_packed's P2 (one `d`
   branch, two arms, merge) — parity or no-larger-and-passing.
3. **The motivating case**: compile the LLLM LOADER's op sequence (from
   `lllm_loader.reference_stream`'s logic — the 13-glyph classification
   ladder, BP-counted 4-record packing, phase-2 racetrack) and report
   its size. **Gate: <= 200 rows** (versus 8134). Correctness is proven
   by reusing Codex's existing `tests/test_lllm_loader.py` against the
   new room.
4. Every compiled room in tests: parses, no shared walls, pipes >= 2,
   backtick-column check clean, deterministic across calls.
5. Metrics table in the report: rows/cols/fill for each of the three
   rooms, before and after the compaction pass.

## Non-goals (do not build these here)

Inter-room placement and pipe routing (that is the composer,
`claude_03`); register allocation; behavior modelling. Lane takes an op
sequence as given.

## Notes for the implementer

`src/littleman/canvas.py` (placement), `docs/littleman-cookbook.md`
(§2 loops, §3 X-geometry, §6 shared cells, §7 literals),
`memory_packed.py` and `snake.py` (the hand-built ground truth),
`lllm_loader.py` on `origin/agent/codex-lllm-loader` (the compiler to
beat; `_compile`/`_literal_safe_fsm` are reusable ideas).
Output-budget rules apply: <=120-line writes, >=5 incremental calls,
Edit-append, cheap test between calls, never type out grids.
