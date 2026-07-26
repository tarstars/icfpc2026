# SCAN v3 handoff (claude_24) — state at pause

Goal: room chain emitting `llm_lockstep.machine_stream` byte-exact.
Everything below is committed on `agent/claude` (HEAD 03c7042).

## DONE and verified

- **Model green**: `littleman/llm_scan3.py` `scan3_reference` =
  `pack64(p1_stream(strip256(scan_reference_v2(toks))))` byte-exact vs
  `machine_stream` + relayed tail on 14 LLM + 10 LLLM + 35 fuzz + 2
  adversarial (61/61; `tests/test_llm_scan3.py`, 62 passed).
- **S2 packer room** (`build_s2_room`, `_compile3` FSM): 39x105 rig,
  3/3 sim cases (scratchpad gate). Packs 256 fields -> 64 words, relays.
- **SR strip room** (`build_sr_room`): built, NOT yet sim-tested.
- **P1 phase 1** (`build_p1_rig(1)`): ingest 259 + drain emit through
  the 312-slot memory subsystem, 2/2 sim cases, 194k ticks, rig 55x136.

## Architecture (final, do not re-derive)

Chain: `I -> S1(build_scan_room_v2 VERBATIM) -> SR -> P1 -> S2 -> O`.
P1 = controller room + memory.py's P3W/P3R verbatim + RELAY312 +
serpentine (~374 cells) = a 312-slot FIFO memory. Slot map in module
constants (cells 0-255, MEN_S..S6, pad 308-311).

Key conventions (hard-won, in code as macros on `_Asm`):
- Every random access = op + dummy WRITE k'=310-slot to pad slot 310+?
  -> exactly one full lap; head position invariant. `rd_c` preserves B;
  `wr_c/rd_a/wr_a` clobber A/B (docstrings exact).
- k=0 ops ROLL the head +1: sequential ingest/emit are counter-free
  BP loops (this cut 10.9M -> 194k ticks). After 259 writes head=259,
  realign literal `52`; after emit no realign needed.
- `test(n, neg, zero, pos)`: arms receive A = A-n, B = n; restore with
  a bare `"+"` block (v2 miss idiom).
- Compiler `_compile3` = v2's `_compile` with 15-digit literal zones
  (`_lit`), zones lit_l=3 left=25 mid=37; only left zone touches I/O
  pipes, only right/lit_r touch cmd/val; verified resolution margins.
- Poked wall cells read char+256, so every glyph test in FR must accept
  g and g+256 (43/299, 45/301, 124/380) — model does %256.

## Traps found

- Literals load A, M clobbers B: any 2-live-values+constant needs a
  park; the memory IS the park. BP is write-only (sign/parity only).
- Pipe start arrow must point away from the source wall (memory.py's
  down-then-left shapes); terminal bends need `cv.cells[...] = "v"`.
- Dummy READs would emit junk; dummy WRITEs to pad emit nothing.
- tickCap LLM = 50M; current worst-case estimate for full P1 ~10-15M.

## NEXT STEP (successor start here)

Implement `_p1_rooms_walls` in llm_scan3.py exactly per its TODO
docstring (the full block-by-block plan incl. A/B choreography is
there; ~160 blocks), then `gate_p1.py 2` (scratchpad) must pass — it
compares against `p1_stream(...)[:256]` world bytes. Then phases 3
(`_p1_manrooms/_p1_cands/_p1_traces` TODOs), gate 3 = full stream.
Then a `build_scan3_machine()` composing the whole chain, byte-exact
gates on all 61 corpora cases + `room_ports.audit` + server_compat.
