# WORK ORDER: LLLM EXEC (ring interpreter) — SUPERSEDED

**Superseded 2026-07-25 by `claude_11a` (FETCH) + `claude_11b` (STEP)** —
the single-room choreography split into two stations with a frozen
request grammar; external interfaces unchanged. Kept for the design
rationale. Originally boxed by two frozen interfaces: consumes `claude_09` (LOADER: 64 packed
world tokens, man_addr, then k per round), produces `claude_10` (deltas
`addr*16+color`, sentinel `-1` = commit). All four design decisions
approved 2026-07-25; do not re-litigate interfaces.

## Structure

```
LOADER ->(in)-> [EXEC station] <-> [2x4 relay room]   (the ring)
                     \->(deltas)-> DIST (claude_10)
```

Ring = EXEC + minimal relay (memory_04 pattern); combined ring-pipe
capacity >= 67 tokens. Canonical circulating order:
`[CTRL, W0..W63, A_i, B_i]` — CTRL packs
`man_addr | heading<<8 | halted<<10` (heading 0=N 1=E 2=S 3=W);
`A_i`/`B_i` are the interpreted registers, full-width, trailing.

## Setup phase

Receive 64 world tokens from LOADER, push into the ring; receive
man_addr, build CTRL (heading=1 East, halted=0), append; append A_i=0,
B_i=0. Then round 1: full-frame emission (below), then the round loop.

## Per interpreted tick (one ring rotation)

1. r CTRL; peel addr/heading/halted (/ by 256, 4). If halted: relay the
   whole ring unchanged, re-append CTRL, done (tick still consumed).
2. word = addr div 4, field = addr mod 4 (one / by 4). BP-counted relay
   of `word` tokens; target token: peel field's record (/ by 8192
   ladder + small X-ladder on field 0..3), extract class+value; token
   re-emitted UNCHANGED (world is read-only). Carry class/value packed
   in EXEC's B through the remaining `63-word` counted relays (B
   survives r/s and arithmetic — corrected register rule).
3. A_i arrives: dispatch on class (X-ladder):
   - wall: halted=1 (man stays on this cell — LLLM freeze semantics,
     matches the official engine's enter-then-fault; NO movement).
   - halt(H): halted=1, no movement.
   - space: no register effect.
   - digit: A_i = value. M: B_i = A_i. add/sub: A_i = A_i ± B_i (native
     wrap). heading: heading = value. branchX: heading turns cw if
     A_i>0, ccw if A_i<0 (3-way on sign).
   - movement (all non-halting classes): addr += {+1 E, -1 W, +16 S,
     -16 N} by heading — blindly; the NEXT tick's fetch discovers a
     wall (decision 3). No canvas-bounds check is needed: the program's
     own perimeter walls enclose the man before canvas edges can be
     reached.
4. B_i read/updated as dispatch requires; re-append CTRL' A_i' B_i' in
   canonical order (count appends — cookbook §5).

## Round loop

r k (relayed by LOADER); BP=k countdown of interpreted ticks (skip
straight to emission if halted). Then delta emission:

- Round 1 (no k precedes it — first action after setup): one full
  rotation peeling ALL 4 fields per token, emitting `addr*16+color` for
  all 256 cells, then `man_addr*16+9`, then `-1`.
- Every later round: one extra rotation stopping at round-start addr
  (recorded in EXEC's B or an extra CTRL field at round entry) to peel
  its static color; emit `old*16+color`, `new*16+9`, `-1`. If halted
  and old==new would repaint identically — emit anyway (harmless,
  simpler) or emit sentinel only; implementer's choice, note it.
- Order restore-first, man-second (self-correcting when old==new).

Budget: ~620 ticks/interpreted tick, ~3k for round 1, <<15M total.

## MODEL FIRST (hard requirement)

Before any ASCII: a restricted-subset Python model (`CycleModel` style,
as in snake.py — A/B/BP-disciplined, explicit ring list, one method per
machine step) that reproduces the `littleman.llm` oracle's frame
sequence for all 10 public cases and `llm_fuzz.corpus(20260726, 100)`
via the claude_10 delta grammar. The model IS the acceptance spec for
the transcription; transcribe only after it is green, and keep it as a
committed test.

## Deliverables / write set

`src/littleman/lllm_exec.py` (model + room generators + a rig:
I -> feeder standing in for LOADER (or reuse `lllm_loader` if landed) ->
EXEC+relay -> O capturing the delta stream), `tests/test_lllm_exec.py`.
Nothing else; snake.py/lllm.py/llm*.py read-only.

## Acceptance

1. Model green (above) — committed tests.
2. Rig: delta stream == model's for 10 public + 30 fuzz cases (O-room
   capture; output rooms legal in rigs only).
3. Directed: halt mid-round; wall freeze (enter + drawn there + all
   later rounds sentinel-only... per emission choice); X at A_i=0/pos/neg;
   wrap64 via +/- loops; k=64 max step; 30-round case.
4. Binding audit via ir_export resolution map (EXEC has 2 in / 2 out:
   in from LOADER, ring in; deltas out, ring out — 4 pipes, the audit is
   mandatory), layout gates, determinism, ticks report per public case.

Report: pytest tail, per-case interpreted-tick and machine-tick counts,
EXEC room dimensions, choreography deviations from this order (say what
and why), no-git/no-submit confirmation.
