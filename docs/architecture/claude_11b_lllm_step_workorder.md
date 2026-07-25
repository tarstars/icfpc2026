# WORK ORDER: LLLM STEP station (interpreter)

Other half of EXEC. Knows NOTHING about world layout. Speaks three
frozen interfaces: claude_09 in (LOADER), claude_11a (FETCH grammar),
claude_10 out (DRAW deltas).

## Behavior

SETUP: receive 64 world tokens from LOADER, forward verbatim to FETCH;
receive man_addr; init CTRL (heading=E, halted=0), A_i=0, B_i=0.
ROUND 1 (immediately): send -1 to FETCH; receive 256 colors; emit to
DRAW `i*16+color` for i=0..255 (own counter), then `man_addr*16+9`,
then `-1`.
EACH ROUND: r k from LOADER; record old=addr; k times (skip if halted):
  send addr (op fetch); receive `class<<4|value`; dispatch:
  wall->halted=1 stay; halt->halted=1; space->nop; digit->A_i=value;
  M->B_i=A_i; add/sub->A_i=A_i±B_i (native wrap); heading->heading=value;
  branchX->cw if A_i>0, ccw if A_i<0;
  then (unless halted) addr += {E+1,W-1,S+16,N-16} blindly (next fetch
  discovers walls — spec-exact freeze semantics).
EMIT: send old+256; receive color; emit `old*16+color`, `addr*16+9`,
`-1`. (Emit even when old==addr: restore-first order self-corrects.)
Park on r for next k.

## State discipline — CORRECTED 2026-07-25 by the model build
Scratch loop is FIVE slots: `ADDR, CTRL, A_i, B_i, OLD` with
`CTRL = 4*halted + heading`. The original text suggested parking the
round-start address in the host's B, citing B-survives-arithmetic: WRONG
HERE — the *interpreted* add/sub arms legitimately clobber host B, and
6/10 public cases failed on it. `OLD` must ride the loop.
Alternative (not taken, recorded): emit the restore pixel at round START
rather than round end — byte-identical delta stream, only the FETCH
request order changes, and no fifth slot is needed.

## Deliverables / write set
`src/littleman/lllm_step.py` (restricted-subset model `StepModel` in the
snake CycleModel style + `build_step_room()` + an integration rig
composing 11a's FETCH: I -> STEP <-> FETCH+RELAY, STEP -> O capturing
deltas) and `tests/test_lllm_step.py`. Nothing else. Depends on 11a for
the integration rig; the MODEL depends on nothing.

## Acceptance
1. MODEL FIRST (hard gate): StepModel + a scripted FETCH stub reproduce
   the `littleman.llm` oracle's frames (via the claude_10 delta grammar)
   for all 10 public + `llm_fuzz.corpus(20260726,100)` cases.
2. Integration rig (with real FETCH): delta streams equal the model's
   for 10 public + 30 fuzz cases.
3. Directed: halt mid-round; wall freeze then later rounds sentinel-only
   emission behavior; X at A_i in {0,+,-}; wrap64 loop; k=64; 30 rounds;
   old==addr round.
4. Binding audit (2in/2out: LOADER-in, resp-in, req-out, DRAW-out);
   layout gates; determinism; interpreted-tick and machine-tick counts
   per public case.
