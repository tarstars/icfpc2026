# WORK ORDERS: LOADER split into SCAN | CLASSIFY (claude_13 executed)

Codex stopped LOADER work; its `reference_stream` and 13 tests remain
ACCEPTED and frozen. Only the room is rebuilt, and per `claude_13` it is
split, because the monolith needs ~7 simultaneous live quantities
(x, y, W, H, char, accumulator, count) against two readable registers.

External interface is UNCHANGED (`claude_09`): the pair still consumes
`W H c0..` from I and produces 64 packed tokens + `man_addr` + relayed
`k`s to STEP.

```
I -> [SCAN] -> [CLASSIFY] -> STEP        (each room: 1 in, 1 out)
```

## Frozen interface BETWEEN them (both builders code against this)

SCAN emits, in order:
1. **256 cell tokens**, canvas order (addr = y*16 + x):
   `t = char + 256*perimeter + 512*padding`
   where `char` is the ASCII code (padding cells use 32, space; the `@`
   cell also emits 32 — it is ordinary space), `perimeter` is 1 for
   x in {0, W-1} or y in {0, H-1}, `padding` is 1 for x >= W or y >= H.
2. **1 man token**: the canvas address of `@` (0..255).
3. every later input token relayed verbatim, forever.

Note the division of labour this creates: SCAN owns ALL geometry (it is
the only room that ever knows W and H, and it finds `@` because it alone
tracks position); CLASSIFY owns ALL semantics and never computes a
coordinate.

## WORK ORDER A — SCAN room

Write `src/littleman/lllm_scan.py` (+ `tests/test_lllm_scan.py`):
`scan_reference(tokens) -> list[int]` (pure-Python oracle of the above)
and `build_scan_rig()` (3x3 I -> SCAN -> 3x3 O).

Live state is position + W + H + man_addr. Suggested reduction: keep a
single `addr` counter 0..255 and derive `y, x = divmod(addr, 16)` with
one `/` (quotient y, remainder x) instead of tracking x and y
separately; W and H then live in a small scratch loop. Padding is
`x >= W or y >= H`; perimeter is `x==0 or x==W-1 or y==0 or y==H-1`.
Each test is a subtraction plus a sign branch. Emit exactly 256 tokens
regardless of W*H: consume an input char only when the cell is real.

Acceptance: rig equality vs `scan_reference` on all 10 public LLLM cases
plus 30 fuzz worlds; directed 4x4 and 16x16, `@` in several positions,
a `+` on the border (perimeter bit set, char still '+'); round-trip
determinism; layout gates (parse, walls, pipes >= 2); prologue ticks
reported.

## WORK ORDER B — CLASSIFY room

Write `src/littleman/lllm_classify.py` (+ `tests/test_lllm_classify.py`):
`classify_reference(scan_tokens) -> list[int]` and
`build_classify_rig()`.

Consumes SCAN's stream; produces exactly the `claude_09` output: 64
packed tokens (`rec = color | class<<4 | value<<8 | wall<<12`, four per
token little-endian base 8192), then the man token forwarded unchanged,
then relays forever.

Rules: padding bit set -> space record; else perimeter bit set -> wall
record; else classify the char per the `claude_09` table. Live state is
char, accumulator, count — the classification ladder may clobber B
freely between records.

Acceptance: `classify_reference(scan_reference(t))` must equal
`lllm_loader.reference_stream(t)` from Codex's ACCEPTED module for all 10
public cases and 30 fuzz worlds — that single assertion proves the split
preserves the frozen interface. Plus rig equality vs
`classify_reference`, directed cases (every op glyph, digits 0 and 9,
border `+`), determinism, layout gates, ticks reported.

## Both

Process rules per `claude_14`: <=120-line writes, >=5 incremental calls,
Edit-append, cheap test between calls, never print grids, responses <=10
lines, no git mutations, no submissions. Read-only: `lllm_loader.py`
(the oracle), `lllm_fetch.py`/`lllm_step.py` (the consumers),
`memory_packed.py`/`snake.py` (idioms).
