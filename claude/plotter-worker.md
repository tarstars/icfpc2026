# Plotter WORKER spec (v3, simpler than plotter-plan.md's 11-room v2)

Status 2026-07-24: display infra + judge frames DONE. Driver chain
partly built and VALIDATED: ADDRDRV decodes+branches+forwards correctly
(tests/test_plotter_drivers.py: [3,6,1,-1] -> [2,5,0]). DATADRV/SWAPDRV
are structurally identical (built, not yet integration-tested). The
Bresenham WORKER is the remaining piece; spec below.

## Architecture (v3)

  I -> WORKER (state ring + relay) -> ADDRDRV -> DATADRV -> SWAPDRV
       (per pixel: emit addr+1; at end: emit -1)         -> display

Drivers already built in src/littleman/plotter.py. Token protocol: v>=1
= plot addr v-1; v=-1 = end (commit frame). Worker emits addr+1 per
pixel then -1 per round, parking on input r between rounds.

## Bresenham on addr = 32*y + x (matches spec pseudocode exactly)

Setup from [x0,y0,x1,y1]:
  dx = abs(x1-x0);  sx = +1 if x1>=x0 else -1     ; SXSTEP = sx
  dy = -abs(y1-y0); sy = +1 if y1>=y0 else -1     ; SYSTEP = 32*sy
  err = dx + dy
  addr  = 32*y0 + x0
  N = max(dx, -dy)          # pixel count = N+1
Loop i = 0..N:
  plot(addr)                # emit addr+1 to drivers
  if i == N: break
  e2 = 2*err
  if e2 >= dy: err += dy; addr += SXSTEP
  if e2 <= dx: err += dx; addr += SYSTEP
At round end emit -1, then park on input r for the next round.

Validate every worker build against this Python reference (identical
addr sequence). Endpoints on-screen (0<=x<32, 0<=y<24), so addr in
[0,768); addr+1 in [1,768]; ADDR writes need 0..767 (addr, not addr+1).

## SETUP sub-machine (compute the 7 constants, once per round)

Reuse the S1..S3 stream-room idea from plotter-plan.md but only as far
as needed. Input arrives as x0 y0 x1 y1 (4 ints). Produce, onto the
worker's ring, the initial tuple in RING ORDER (below). A chain of small
1-in/1-out stream rooms is the reliable pattern (no scratch loops):
  - compute addr0 = 32*y0 + x0    (r M `32` * M r + ; B-hold)
  - compute dx,SXSTEP via sign of x1-x0 (X: >=0 lane sx=+1; <0 lane
    N-negate and sx=-1)
  - compute dy,SYSTEP via sign of y1-y0 (dy = -abs; SYSTEP = 32*sy)
  - compute err0 = dx+dy and N = max(dx,-dy) (X on dx+dy... actually
    N: compare dx vs -dy: N = dx if dx>=-dy else -dy)
Emit initial ring tuple + N (N goes to BP via b at ring load).

## RING ORDER (fixed; every lane must restore it)

  [addr, err, dy, dx, SXSTEP, SYSTEP]

dy,dx,SXSTEP,SYSTEP are LOOP-INVARIANT: read and re-send unchanged.
addr,err change per iteration.

## WORKER per-iteration choreography (the crux — needs care)

BP = remaining steps (init N via b). Man loops the ring room. One lap:

  # --- plot ---
  r            A = addr            (from ring)
  M 1 +        A = addr+1  (B=addr) ... wait: need addr preserved to ring.
               Better: r (A=addr); s_ring(addr) re-send unchanged FIRST;
               then M 1 + ... no, s doesn't clobber A, so:
  r            A=addr
  s_plot?      NO: plot needs addr+1. Do: b?  Use B:
  (plot)       M(B=addr) 1 +(A=addr+1) s_plot   ; now A=addr+1,B=addr
               re-send addr to ring: W(A=addr) s_ring(addr)   [ring keeps addr; updated later? NO]
  --- PROBLEM: addr must be UPDATED before re-entering ring, but the
      update depends on err/dy/dx read later this lap. So DON'T re-send
      addr yet; HOLD it. But B is the only hold and it's needed for
      arithmetic on err. => Two options:
      (A) Re-send addr unchanged now, and have a SECOND pass apply the
          addr delta next lap (carry the delta). Messy.
      (B) Reorder ring so addr is read LAST, after err/dy/dx computed
          the deltas, so addr update happens with deltas in hand.

  Adopt option (B). RING ORDER -> [err, dy, dx, SXSTEP, SYSTEP, addr]
  Lap:
    r  A=err;  M(B=err) ... compute e2=2err: 1?  e2 = err+err: M(B=err) +(A=2err). B=err lost.
       Keep err to re-send: need err after computing c1,c2 and its update.
    This still needs err held across dy,dx reads.

  The honest conclusion: 6 cross-dependent values + 2 conditions do NOT
  fit a single A/B/BP lap cleanly. Use a SCRATCH pipe (a second small
  loop off the worker room) as a 3rd/4th register, exactly like memory's
  scratch. Plan:
    - Lap part 1: read err, compute e2=2err, stash e2 and err to scratch;
      read dy: c1 = sign(e2 - dy) via X (>=0 -> c1=1). Stash c1.
    - read dx: c2 = sign(dx - e2). Stash c2.
    - recompute err' = err + c1*dy + c2*dx (pull err,dy,dx from scratch
      or re-read; dy,dx must also go back to ring unchanged).
    - read SXSTEP,SYSTEP,addr; addr' = addr + c1*SXSTEP + c2*SYSTEP.
    - plot addr (emit addr+1) BEFORE stepping (plot is at the OLD addr).
    - re-send [err', dy, dx, SXSTEP, SYSTEP, addr'] in ring order.
    - m (BP--), d/a branch: BP>0 loop; BP==0 -> emit -1, park on input.

  This is ~memory-P3W complexity. Budget a focused session; build with
  the debug ladder (trace every r/s), validate emitted stream vs the
  Python reference for ~30 random segments before wiring the display.

## Build order

1. Python Bresenham reference (addr list) as the oracle. [tests]
2. SETUP chain: feed x0y0x1y1, collect the initial ring tuple + N at an
   O room; assert == reference constants. (Fake collector, no worker.)
3. WORKER alone: preload ring via SETUP, route the PLOT emit to O
   (instead of drivers); assert O == [a+1 for a in reference addrs] then
   -1. Multi-round.
4. Wire WORKER -> drivers -> 32x24 display; judge vs plotter.json
   (id 0c3e3d4d-2901-45f1-81cf-5704d49c9139). Frame-judged; emit NO ints.
5. submissions/plotter/variants.json per versioning rules.

## Risks

- The 6-value/2-condition lap is the hard part; the scratch-pipe plan
  above is the intended approach (memory-proven). If it balloons,
  fallback: split the worker into TEST room (emits c1,c2 codes) and
  UPDATE room (applies deltas), i.e. the v2 E-TEST/E-UPDATE split from
  plotter-plan.md, which trades rooms for per-room simplicity.
- ADDR/DATA interleave race: worker period (~30+ ticks/pixel) >> pipe
  skew, so safe; a display test will confirm.
