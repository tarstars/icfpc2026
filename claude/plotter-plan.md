# Plotter build plan (v2) — implementable spec

Status: display support in sim/judge is DONE and tested. The machine
is fully designed; `src/littleman/plotter.py` contains ONLY BROKEN
SKETCHES from an earlier attempt — rewrite it from this plan, do not
trust its room maps. Read docs/littleman-cookbook.md first.

## Problem

32x24 display, Bresenham line per round (<=20 rounds), color 15,
commit exactly one frame per round with SWAP 0 (rounds don't persist).
Must match Bresenham's symmetric form pixel-exactly (spec pseudocode
in data/small/problems/plotter.json). Endpoints are on-screen.

## Key reformulation (all verified by reasoning; verify vs reference)

- addr = 32*y + x. Steps: addr += SX (+-1) for x, addr += SYW (+-32)
  for y. addr==addr1 identifies the endpoint (not needed in v2).
- Iteration count N = max(dx, -dy) is exact (dominant axis steps every
  iteration). Both pumps count BP down from N; no handshakes.
- Store E = 2*err. Tests: c1 = (E - dy >= 0), c2 = (dx - E >= 0).
  Updates: E += 2*dy if c1 (two `+` with B=dy), E += 2*dx if c2.
  At least one of c1,c2 always holds.
- Per pixel the test side sends code delta = c1 + 2*c2 in {1,2,3}.

Reference implementation to test against (also validates the frames):
run Python Bresenham per spec, build 24x32 grids, compare with
res.frames from the simulator.

## Topology (every room <=2 in, <=2 out)

    I -> S1 -> S2 -> S3 -> S4 -> S5 -> ETEST <-> EUPD -> A -> DISP
                                          (state ring)      /    \
                                                        PLOT      SWAPR
                                                       /    \        \
                                                 ADDR pipe  DATA   SWAP pipe
                                                       \     |      /
                                                        [ display ]

- ETEST->EUPD "code" pipe also carries A's init [SX,SYW,addr] and the
  per-iter codes; EUPD's "to-A" pipe carries A-init then deltas then
  the END sentinel -1.

## Stream protocols (exact orders)

S5 output (once per round): [N, N, dy, E0, dx, SX, SYW, addr]
  (first N for ETEST's BP, second forwarded to EUPD's BP).
ETEST->EUPD code pipe: [N, SX, SYW, addr] at init, then one code per
  pixel iteration.
ETEST<->EUPD state ring order: [dy, E, dx] (E in the middle! TEST1
  uses B-held dy then recovers E with `+`; TEST2 reads dx last).
EUPD->A: [SX, SYW, addr] at init, then delta per iteration, then -1.
A->DISP: addr per pixel (>=0), then -1 at round end.

## Room-by-room instruction sequences (register-traced)

S1 (in: input; out: to-S2). [x0,y0,x1,y1] -> [y0,x0,x0,y0,y1,x1]:
  r M r s W s s W s | r M | r s W s
  (r(x0) M(B=x0) r(y0) s(y0) W s(x0) s(x0) W s(y0); r(x1) M; on the
  return row r(y1) s(y1) W s(x1).) Racetrack 2 rows, verified shape:
  row1 ">@rMrsWssWsrMv", row2 "^        sWsr<" (walk-left order!).

S2 (addr): [y0,x0 | rest] -> [x0,y0,y1,x1,addr]:
  r(y0) M `32` * M(B=32y0) r(x0) + (A=addr) M(B=addr)
  then forward r s r s r s r s (x0',y0',y1,x1), then W s(addr).
  addr rides in B through the four forwards (B survives r/s).

S3 (dx/SX): [x0,y0,y1,x1,addr] -> [y0,y1,dx,SX,addr]:
  r(x0) M(B=x0) r(y0) s r(y1) s r(x1) - X:
    >=0 lane: s(dx) 1 s(SX=1)          (dx = x1-x0 already in A)
    <0  lane: N s(dx) 1 N s(SX=-1)
  (x0==x1 -> spec says sx=-1 but sx is never used when dx=0; +1 fine.)
  merge lanes, then r(addr) s(addr).

S4 (dy/SYW + duplicates): [y0,y1,dx,SX,addr] ->
                          [dy,dx,dy,dx,SX,SYW,addr]:
  r(y0) M r(y1) - X on (y1-y0):
    >0 & 0 lane: N (A=dy=-(y1-y0)) then common;
    <0 lane: (A already = dy) then common with SYW negated.
  common: M(B=dy) s(dy) r(dx) s(dx) W s(dy) W s(dx)   [dup via W-holds]
          r(SX) s `32` [N] s(SYW) r(addr) s(addr).
  CAUTION: two `32` literals on different rows must not share columns
  with junk between (vertical pairing rule).

S5 (N/E0): [dy,dx,dy,dx,SX,SYW,addr] -> [N,N,dy,E0,dx,SX,SYW,addr]:
  r(dy) M(B=dy) r(dx) + (A=e0=dx+dy, B=dy) X:
    >=0 (N=dx):  W(A=dy,B=e0) - (A=dy-e0=-dx) N (A=dx) s s
    <0  (N=-dy): W(A=dy,B=e0) N (A=-dy) s s
  both lanes then: r(dy') s | W(A=e0) M(B=e0) + (A=2e0=E0) s(E0)
    WAIT order is [N,N,dy,E0,dx]: after s s: r(dy') s(dy'), then
    E0 from B: at that point B=e0 still (r/s preserve B): W M + s(E0),
    then r(dx') s(dx'), then tail r s r s r s (SX,SYW,addr).
  Re-derive the register trace when implementing; the invariant to
  check: B holds e0 from the X until the E0 computation, and dy',dx'
  forwards use only A.

ETEST (in: from-S5, ring-in; out: ring-out, code-out):
  init: r(N) b | r(N') s_code | r(dy) s_ring r(E0) s_ring r(dx) s_ring
        | r(SX) s_code r(SYW) s_code r(addr) s_code
  iter (d-loop on BP): read ring [dy,E,dx], forwarding as it reads:
    r(dy) M(B=dy) s_ring(dy)
    r(E)  A=E     s_ring(E)
    - (A=E-dy, B=dy)  X1:
      c1 lanes (0 straight, >0 down; merge) and n1 lane (<0 up).
      every lane: + (A=E recovered, B=dy) M(B=E)
                  r(dx) s_ring(dx) - (A=dx-E, B=E) X2:
        c1&c2 -> code 3; c1&!c2 -> code 1; n1&c2 -> code 2;
        n1&!c2 -> impossible (leave unrouted = wall assertion).
    terminal: load digit, route to a shared bottom row, single shared
    s_code cell, m is on the return path, loop.
  flush (BP=0): discard ring r r r; home to init. (EUPD sends the END.)
  Layout warning: this room caused every collision in the first
  attempt. Use dedicated rows per lane, dedicated descent columns
  (keep a written ledger), shared cells only per cookbook section 6.

EUPD (in: ring-in(from ETEST), code-in; out: ring-out(to ETEST), to-A):
  init: r_code(N) b | r_code(SX) s_A r_code(SYW) s_A r_code(addr) s_A
  iter (a/d-loop on BP): r_code(code) M `2`?? compute code-2 via
    M(B=code) 2 W - X (3-way):
    delta=1: r(dy) M(B=dy) s_r(dy) r(E) + + (A=E+2dy) s_r(E')
             r(dx) s_r(dx) `1` s_A
    delta=2: r(dy) s_r(dy) r(E) M(B=E) r(dx) A=dx W(A=E,B=dx) + +
             s_r(E') W(A=dx) s_r(dx) `2` s_A
    delta=3: r(dy) M(B=dy) s_r(dy) r(E) + + M(B=E+2dy) r(dx)
             W(A=E+2dy,B=dx) + + s_r(E'') W(A=dx) s_r(dx) `3` s_A
    (ring order [dy,E,dx] preserved in every lane — re-trace!)
  flush (BP=0): `1` N s_A (END -1); home.

A (in: from-EUPD, loop-in; out: to-DISP, loop-out). Loop [SX,SYW,addr]:
  init: r(SX) s_l r(SYW) s_l r(addr) s_D(plot!) s_l
  iter: r(delta) X: <0 -> END: discard loop r r r, `1` N s_D(-1), home
        else M(B=d) 2 W - X (3-way):
    d1: r(SX) M(B=SX) s_l r(SYW) s_l r(addr) + s_D s_l
    d2: r(SX) s_l r(SYW) M(B) s_l r(addr) + s_D s_l
    d3: r(SX) M(B=SX) s_l r(SYW) s_l(SYW) + (A=SYW+SX, B=SX)
        M(B=sum) r(addr) + s_D s_l
        (note: in d3 the + happens on A=SYW before M; trace it)
DISP: r X: >=0 s_plotroom; <0 s_swaproom. tiny.
PLOT: r s(->ADDR pipe) `15` s(->DATA pipe). Loop period must be > 2
  (it is: ~8) to avoid the ADDR/DATA interleave race.
SWAPR: r 0 s(->SWAP pipe). SWAP value 0 = commit + clear (rounds
  don't persist).

## Build order (do it in this order, test each step)

1. Rewrite plotter.py: S1..S5 only. Unit test: feed [x0,y0,x1,y1]
   into the chain with a fake collector room instead of ETEST; assert
   the 8-value stream equals a Python-computed [N,N,dy,E0,dx,SX,SYW,
   addr] for ~20 random segments. (Collector = room that relays to O;
   judge output list.)
2. ETEST+EUPD pair with a fake code consumer: drive with hand-made
   init streams; assert the delta sequence equals the reference
   Bresenham's (c1+2c2) sequence per pixel.
3. A + DISP + PLOT + SWAPR + display: drive A with a hand-made
   [SX,SYW,addr,delta...,-1] stream; assert res.frames matches the
   reference frame.
4. Full chain; judge vs plotter.json (6 public cases); submit
   (id d0b...? NO — plotter id 0c3e3d4d-2901-45f1-81cf-5704d49c9139).
5. Record in submissions/plotter/variants.json per versioning rules.

Expected footprint ~3-4k (display 34 wide is a floor; stack rooms in
a left column ~ display height), ticks ~25-40 per pixel — far inside
the 5M cap. Don't optimize before it passes.
