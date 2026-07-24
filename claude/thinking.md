# Thinking — scratchpad, newest first

Messy on purpose. Hunches, dead ends, "why not X". Promote anything that
solidifies into STATE.md or a shared doc.

---

## 2026-07-24 — pre-contest posture

- Resist the urge to pre-build a "framework" before the task drops. ICFPC
  tasks vary wildly (optimization, interpreters, games, protocols); generic
  scaffolding usually gets thrown away. The scaffold that DOES always pay
  off: fast eval loop (score a solution locally), a submitter, and a run
  manifest habit.
- Historically the highest-leverage first-day artifacts: (1) correct
  parser/validator, (2) local scorer matching the judge, (3) dumb baseline
  submitted early to confirm the pipeline end-to-end.
- Keep an eye on the 400 GiB free-space floor on `medium_data` — generous
  now (~426 GiB free), but Monte Carlo / corpus generation eats disk fast.

## 2026-07-24 late — plotter machine design (for next session)

Display infra DONE (sim + judge frames). Machine plan:

- Reformulate Bresenham on addr = 32y + x: addr' = addr + SX(±1) and/or
  + SYW(±32); terminate when addr == addr1 (bijective, one compare).
  Store E = 2*err so tests are E>=dy / E<=dx and updates E += 2dy/2dx
  (via + + on a copy, no doubled constants needed).
- Rooms: SETUP -> A-pump -> E-pump cmd chain (memory-style);
  DISPATCH -> PLOT(ADDR+DATA) / SWAPROOM(bottom) for the display.
- SETUP full FIFO schedule derived (see below): stash [y0,x0,y1,x1]
  interleaved via B-hold at read time; addr passes: r M s `32` * M r s +;
  sign branches: X >=0 lanes send SX/SYW consts; tail discards y0,x0,
  computes E0 = 2(dx+dy), forwards [E0,dy,dx] to E via A.
- A-pump/E-pump ping-pong: A plots addr, compares addr1 (const loop
  [addr1,SX,SYW]); done -> -1 to E (reset lane) and -1 to DISPATCH
  (swap 0); else +1 to E; E (loops [E] and [dy,dx]) computes c1/c2 via
  two X-tests on dy-E / dx-E with B=E, updates E with + + per lane,
  sends delta = c1+2c2 in {1,2,3} to A; A updates addr by X-chain.
- SOLVED (v2 architecture, all rooms <=2-in/<=2-out):
  * N = max(dx,-dy) computed at SETUP -> both pumps BP-countdown, no
    handshake tokens at all.
  * SETUP = pipeline of 5 tiny 1-in/1-out STREAM rooms (S1..S5), no
    scratch loops: S1 reorders/dups [y0,x0,x0,y0,y1,x1]; S2 addr
    (B-hold); S3 dx/SX; S4 dy/SYW + dup dy,dx; S5 N/E0, emits
    [N, N, dy, E0, dx, SX, SYW, addr].
  * E split in two: E-TEST (state ring order [dy,E,dx]; TEST1 E-dy via
    B-held dy, recover E with +, TEST2 dx-E; terminals emit code 1/2/3
    on the code pipe; BP=N; X-up lanes are real rows, dead branch of
    n1's TEST2 left unrouted as an assertion) and E-UPDATE (in: ring +
    code; 3 lanes apply E+=2dy/2dx keeping ring order via W-holds;
    forwards [SX,SYW,addr] then per-iter delta to A; BP=N; sends -1 END).
  * A-pump: loop [SX,SYW,addr]; r(delta): <0 END (flush, -1 to
    DISPATCH); else 3-way on delta-2; adds via B-held const; plots to
    DISPATCH each iter + initial plot at init.
  * DISPATCH: >=0 -> PLOT room (s ADDR, `15` s DATA); <0 -> SWAP room
    (send 0: commit+clear). PLOT DATA-vs-next-ADDR race is safe when
    loop period > 2 (verified reasoning; test will confirm).
  * Chain: I->S1..S5->E-TEST->(ring)->E-UPDATE->A->DISPATCH; code pipe
    E-TEST->E-UPDATE also carries A-init [SX,SYW,addr] during init.
- Public case frames confirm SWAP 0 per round (clears next buffer).
