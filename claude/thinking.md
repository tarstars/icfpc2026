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
- UNSOLVED: A-pump has 3 incoming (SETUP, delta-from-E, const-loop).
  Options: route delta through the const-loop relay room (relay merges
  streams? no — FIFO corruption); or split A into plot-room (stateless,
  receives addr stream) + update-room; or accept 3-in with wide audits.
- Public case frames confirm SWAP 0 per round (clears next buffer).
