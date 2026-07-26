# claude_30: STEP3 finish + fold, as work packages for simple builders

Written 2026-07-26 ~11:00Z after the post-mortem in claude_29: "finish
the room" killed every agent given it; rig-scoped packages shipped at
~90%. Each package below is TRANSCRIPTION, not design — the design is
finished and byte-exact in `Step3Model` (`src/littleman/llm_step3.py`,
verified vs `llm_lockstep.from_stream` on 10 LLLM + 14 LLM public + 340
fuzz). A builder's job is to turn ONE named model function into room
cells and prove it against the model. If a package seems to require a
design decision, STOP and report — that is a spec bug, not your job.

## Frozen interfaces (violating any of these = automatic reject)

- Room = `Room(ROWS3, COLS3)`, COLS=96. Ports: REQ row 2; RESP top
  col 8; DRAW row 20; LOAD row 21 west; scr1 east rows 30/33.
- Binding rule: `r`/`s` at col >= 48 binds the scratch ring
  (boundary (COLS-9)/2). Keep ALL ring1 r/s rows <= 112; ring2's south
  ports live ~row 220+ (phase C) — publish exact ports in the module
  docstring when placed (the harness reserved the band).
- MEMW margin is 1 (inherited, proven) — never worsen; all else >= 2.
- Ring1 16 slots `[C,A,I,B]x3 + [MARK=-1, SP=0, SHIFTM, K]`; CTRL
  encoding `walled<<4|intent<<3|frozen<<2|heading`. Ring2 canonical
  `[seg0, seg1, MARK2=-1]`, MARK2 at the TAIL. Do not "improve" these.
- NEVER relay-until-MARK across A/I/B/value slots (they can hold -1).
- Files: `src/littleman/llm_step3.py`, `tests/test_llm_step3.py` ONLY.
  Never touch llm_scan3/llm_lockstep/llm_assemble3/lllm_*/codex llm_*.
  Never commit/push/submit.

## Already DONE on disk (do not rebuild)

Chain (classify), intake (stream -> FETCH, green in a 127x122 rig),
initial-frame emit — proven END-TO-END by the harness: `first steps`
round 1 passes through the full assembled machine; stall is at the
round_in seam, room-rel (26,96).

## The packages

Verify command for every package:
`uv run pytest tests/test_llm_step3.py -q` (model tests stay green) plus
the package's own rig test; full-machine check when named:
`uv run python scripts/build_llm3.py --case "first steps"`.

### WP1 — round_in parking  [small; UNBLOCKS EVERYTHING]
Transcribe `Step3Model.round_in` (line ~548). The row-26 `rWs` lap must
park and rejoin instead of running off its east end at (26,96). Done
when: the harness advances past tick ~8.03M on `first steps` and stalls
somewhere NEW (report where), with rounds 1-2 still byte-exact.

### WP2 — loop_top scanner  [small]
Transcribe `Step3Model._loop_top` (line ~482): straight-line scan of the
12 man slots, three tracks — all walled>=16 -> drain K + emit; none
live -> idle tick; else -> tick. Exit on MARK sign; NO man counter. Rig:
drive ring1 states from the model's annotated tapes; byte-exact ring
after each of the three tracks.

### WP3 — pass1 + pass2 (tick, no pipes)  [medium]
Transcribe `_pass1` (line ~264, SKIPPING its `_pipe_arm` branch — that
is WP6) and `_pass2` (~417): fetch-dispatch per man via the existing
chain, record intents, apply moves against live occupancy (collision
compares +3/+7/+11 after the ADDR peek; SP is the never-matching dummy;
collision arms relay 15-4k to own CTRL). Rig vs model on single-man and
2-3-man no-pipe programs.

### WP4 — pass3 + per-round repaint  [medium]
`_pass3` (~459): wall detection, CTRL+=20 on fetch resp==16,
position-relative only. `emit_frame` (~513) for rounds >= 2: full-frame
repaint — 256 colours via FETCH -1, pipe cells 14/6, man pixels
addr*16+9 skip addr 0, commit -1. Done when the FULL MACHINE passes
`first steps` 4/4 AND the 10 LLLM-shaped publics (phase A) then
`bounce house` + `pileup` (phase B) — run `build_llm3.py --all`,
report per-case pass/stall.
==> SUBMIT CHECKPOINT: at phase B green the supervisor submits.

### WP6 — ring2 + shift lap  [medium; parallel with WP3/4 after WP1]
Ring2 segments `[-rawHDR, (addr,pres,val) x L]` cells TAIL-FIRST; the
shift = one structural lap with the pending-gap FSM (addr early,
pres/val deferred, giver addr in B). Sign-test ONLY addr-or-sentinel
slots. Rig: seed ring2 from the model, run one shift, byte-compare.
Publish the south-wall ports in the docstring (harness wires them).

### WP7 — s/r arms  [medium]
`_pipe_arm` (~357): BP=3 count-to-MARK (relay 2, then test-CTRL-or-MARK
per hop), BP=mi+1, 3 static sub-arms; nearest = (d, cell addr)
lexicographic; s writes head cell = LAST group, r reads tail = FIRST;
blocked -> CTRL-=8. Parks in MARK/SP allowed mid-arm if restored.

### WP8 — phase C integration  [gate]
`build_llm3.py --all`: all 14 public. Binding audit
(`room_ports.audit`, `ir_export.machine_ir`) 0 role diffs, margins per
the frozen table. ==> SUBMIT.

## Stage 3 (only after WP8, separate builders)

- WP9: fold SCAN3's P1 (3247x116) into a serpentine <= ~700 wide —
  P1 is a generator refold, not a press; oracle unchanged
  (`machine_stream` byte-exact, 65 tests).
- WP10: re-balance the assembly toward square (target max-dim <= 2000,
  fp <= 4M); press rules apply (rooms rigid, 0 role diffs).
- Payoff ladder (measured 10:40Z): score <= 1e14 -> ~rank 18 (+0.21);
  <= 5e13 -> ~rank 13 (+0.36); <= 1.5e13 -> ~rank 8 (+0.51).

## Kill-gates (claude_14, binding)

Any package failing twice -> the LANE stops, not the prompt. Stage-2
submission no later than 06:00Z 07-27; no stage-3 start after 04:00Z.
Process rules per package: <= 60-line writes, no grids in output, read
in slices, test between edits, replies <= 10 lines.
