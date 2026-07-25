# WORK ORDER: LLLM DRAW subsystem (display side)

Decisions locked by the user 2026-07-25: no INIT-FRAME (round 1 = deltas
like any round); packed delta tokens; negative sentinel = commit; Snake
drivers lifted verbatim (correctness-first).

## Frozen interface: EXEC -> DRAW (one dedicated pipe)

- `t in [0, 4095]`: paint pixel. `addr = t // 16` (canvas addr 0..255,
  display cursor addr = same row-major), `color = t % 16`.
- `t < 0`: COMMIT — send SWAP=1 (commit, keep next buffer). Any negative
  value; EXEC emits -1.
- Frame grammar: round 1 = 256 static pixels + 1 man pixel (color 9) +
  sentinel; every later round = 0..2 pixels (restore old cell to its
  static color, draw new cell 9 — 0 pixels when the man is halted/frozen)
  + sentinel. DRAW is stateless about rounds: a pure stream transducer.

## AMENDED 2026-07-25 by the build: DIST has ONE outgoing pipe

The structure below said DIST splits addr/colour onto three driver
pipes. WRONG for these drivers: Snake's ADDRDRV/DATADRV/SWAPDRV are a
serial demux CHAIN -- each forwards the whole token and performs its own
`M \`16\` W /` -- so feeding them pre-split values corrupts ADDRDRV's
arithmetic, and replacing them would discard race tuning that is live on
the server at 17/17. Built instead: DIST is a one-in/one-out adapter for
the frozen interface (`t >= 0 -> t+1`; negatives passed through; a
three-way X merge because `t = 0` is a legal pixel), and the binding
audit widened from 3 cells to all 11. Measured: 46.0 ticks/pixel steady
state, block 19x42 (26x64 with the display).

## Structure (as originally specified; superseded above)

```
EXEC ->(deltas)-> [DIST] ->(addr)->  [ADDRDRV] -> display TOP
                         ->(color)-> [DATADRV] -> display LEFT
                         ->(swap)->  [SWAPDRV] -> display BOTTOM
```

DIST: r(t); X on sign — negative arm: send 1 to swap pipe; else
`M 16 W /` (A=addr, B=color), send addr, W, send color. Three outgoing
pipes => the three `s` cells' bindings MUST be asserted via
`littleman.ir_export.machine_ir`'s resolution map in tests (engine-true,
no hand math).

ADDRDRV/DATADRV/SWAPDRV + display placement: COPY from
`src/littleman/snake.py` (`build_addrdrv`, `build_datadrv`,
`build_swapdrv`, `place_display_block`) — snake.py itself is read-only.
Preserve its race tuning (ADDRDRV lap > DATADRV lap keeps pixel i's DATA
ahead of pixel i+1's ADDR); SWAP must reach the display strictly after
the frame's last DATA — Snake solved this by driver lap lengths; keep.

## Deliverables / write set

`src/littleman/lllm_draw.py` (`build_draw_rig() -> str`: 3x3 I room ->
DIST -> drivers -> display; the DIST+drivers block is what the assembler
lifts) and `tests/test_lllm_draw.py`. Nothing else.

## Acceptance

1. RIG FRAME EQUALITY: for all 10 public LLLM cases: compute the delta
   stream in Python from the frame sequence of the `littleman.llm`
   oracle (frame 1 full, then per-frame diffs — by construction <= 2
   pixels + sentinel), feed it through the rig via I, judge with
   `littleman.judge.judge_case` rounds `{"in": tokens, "frames": [f]}`
   per frame: 10/10 exact.
2. Directed: sentinel-only round (frame unchanged, still commits);
   257-delta first round; 60 back-to-back pixels (Snake's stress
   pattern); man on a wall cell drawn 9.
3. Binding audit: the three DIST sends resolve to the intended pipes
   (ir_export map).
4. Layout gates on the rig: parse, no shared walls, pipes >= 2 cells.
5. Determinism; report driver lap lengths used.

Context: `claude_09` (LOADER order, same conventions), snake.py drivers,
`docs/littleman-cookbook.md` §8, `claude/official-sim/` second opinion.
Report: pytest tail, dims of DIST+driver block, deviations (none
expected), no-git/no-submit confirmation.
