# claude_25: lockstep STEP (llm_step3) handoff — 2026-07-26

## DONE and verified (committed: cb51c57, 272571c + this WIP)

`src/littleman/llm_step3.py` + `tests/test_llm_step3.py`.
**Step3Model — the machine-shaped choreography model — is byte-exact vs
`llm_lockstep.LockstepLLM.from_stream` on ALL THREE PHASES**: 10/10 LLLM,
14/14 LLM public (pileup, bounce house, all 11 pipe cases), 27 pytest tests
plus a 340-program fuzz sweep (300 piped, same-room collisions, shared
walls): 0 divergences. Every ring pull/push in the model is literal; every
in-hand computation is annotated with its opcode tape. The ROOM is a 1:1
transcription of this model — trust the model over any doc.

## Design (only in this doc + model comments)

- Ring1 (16 slots): `[C,A,I,B]x3 men + [MARK=-1, SP=0, SHIFTM, K]`.
  CTRL = walled<<4|intent<<3|frozen<<2|heading. Men in ring = reading
  order; absent men lead as frozen ADDR=0 (scan v2 zeros always trail
  stream[64:67], so reversed pushes need no compaction). Pass loops pull
  the head and exit on MARK's sign — no man counter anywhere. Collision
  compares read +3/+7/+11 after the ADDR peek; SP is the never-matching
  dummy (its k varies by man!); collision arms relay 15-4k to own CTRL.
- Loop-top = straight-line scan of the 12 man slots (3 parallel tracks:
  walled>=16 -> drain K + emit; none live (<4) -> idle tick; else tick),
  then K countdown. No OVER slot. Pass3 writes CTRL+=20 on wall (fetch
  resp==16), position-relative only. NEVER relay-until-MARK across
  AI/BI/value slots — they can hold -1 (that bug is fixed; keep it dead).
- SHIFTM = 2^(3-n) pushed by the 4 man-intake paths; arms test mask bit
  via literal 2^(21|24+mi)/SHIFTM & rawHDR.
- Ring2 canonical `[seg0, seg1, MARK2=-1]` (MARK2 at the TAIL — walks
  pull N slots exactly; a leading MARK2 double-pulls and rotates the
  ring off-canonical, that bug cost an hour). Segment = `[-rawHDR,
  (addr,pres,val) x L]` with cells TAIL-FIRST. -raw is safe: raw>=2
  (head addr 0 geometrically impossible). Only addr-or-sentinel slots
  are ever sign-tested (addr>=0; vals are 64-bit and CAN be -1).
- Shift = one structural lap, pending-gap FSM (addr pushed early,
  pres/val deferred; giver addr held in B) — reproduces the tail-first
  cascade. Cell-word reversal at intake: push w, relay t, relay 16
  through RING1 (men stay contiguous); hi-first divmod peel (2^42,
  2^21) with BP=21-L skipping the always-leading padding.
- s/r arms: BP=3 count-to-MARK (relay 2, then test-CTRL-or-MARK per
  group hop — CTRLs>=0 so sign-safe) -> BP=mi+1 -> 3 static sub-arms;
  parks in MARK/SP slots allowed mid-arm if restored. Nearest = (d,
  cell addr) lexicographic; s writes head cell = LAST group (BP=3(L-1)
  relay), r reads tail = FIRST group. Blocked -> CTRL-=8 (intent off).
- Full-frame repaint per round (256 colours via FETCH -1 + pipe cells
  14/6 + man pixels addr*16+9, skip addr 0, commit -1). No OLD slots.
- FETCH reused UNCHANGED (claude_11a): intake classifies scan-v2 ascii
  records to claude_09 `colour|class<<4|value<<8` (+classes 9=s,10=r,
  colour 13; table CHAR_REC/classify_record) and repacks 4x13 bits.
  World lap: ring rides [w,phase,acc,count]; divmod 8192 peels; phase
  staircase pushes literal p+1 and shifts crec<<13p; flush arm sends
  acc as FETCH's world feed.

## IN PROGRESS: the room (phase A transcription just started)

`Chain` class (classify chain emitter) — skeleton + `_put_w` (westward
token placer, literals auto-reversed) + private-descent-column allocator
are in; `build()` raises NotImplementedError listing exactly what goes
in `_main_row/_rungs/_low_block`. Geometry decided: BP staircase rungs
(BP=char-48; m-run+a per row-pair, routing row east to CH_ROUTE=41 then
down-west; A survives the staircase so each fall-through arm tests
`A-(T-48)`: 0 -> record literal -> private v-descent to a shared floor
row (`>` landings are same-direction-safe); <0 -> junk `0`). The v-X
merge idiom: `v` directly above an X re-executes it after the turn,
folding one sign back into straight — 2 cells per 2-way branch.

## Next step for a successor

1. Finish Chain._main_row/_rungs/_low_block; rig-test the chain alone
   (I -> room -> O over all 13 op chars + walls + junk + digits).
2. Intake world lap around it; sub-rig vs model FETCH words + ring.
3. Emit block (copy lllm_step round-1 loop shape rows 4..19), man-pixel
   loop, round-in; then loop-top/pass1/pass2/pass3. Ports: REQ row 2 /
   RESP top col 8 / DRAW 20 / LOAD 21 west, scr1 east rows 30/33;
   COLS=96 -> r/s col>=48 binds scratch (boundary (COLS-9)/2, depth-
   independent for ports above); chain/non-pipe cells may sit anywhere.
   Keep ALL ring1 r/s rows <= ~112 so phase C's ring2 ports (south wall
   ~row 220+) can't steal deep cells (midline is row-dependent there).
4. Audit every binding with room_ports.audit before trusting a run.
