# Littleman Cookbook — verified idioms and hard-won rules

Everything here was validated in the simulator and/or on the contest
server during 2026-07-24. Read this BEFORE designing or debugging any
machine. Written so that any teammate (human or model) can continue
without rediscovering these.

## 1. Register discipline (the core constraint)

You have A (main hand), B (off hand), BP (backpack, WRITE-ONLY).

- `s` does NOT clobber A. You can send the same value twice, or send
  and keep using it.
- B SURVIVES: `r s m d a x ] q b H > < ^ v X` and digits/literals.
  B is DESTROYED by: `M W + - * / % N & | ~ { }`.
  => You can carry one value in B through entire relay loops and
  branch chains. This is the single most used trick.
- `/` puts quotient in A AND remainder in B in one op. Use it for
  unpack/match tests (brackets: match iff (S-u)/3 has remainder 0).
- `%` result takes B's sign; with positive B the result is in [0,B) —
  safe mod for negative A (used for (addr-h)%100 in memory).
- BP can only be tested by sign (`d`,`a`: >0) and parity (`x`). You
  cannot read it. Never plan "stash a value in BP and get it back".
- All values signed 64-bit, wrapping. Literals must fit 64 bits read
  in BOTH directions.

## 2. Loop idioms (copy these, don't invent)

Relay loop (relays exactly BP+1 values, exits with the LAST value
still in A — because `s` doesn't clobber):

    >rsv        enter at '>' heading right (or fall in from above)
    ^ md        exit: d with BP=0 drops STRAIGHT DOWN below the loop

- Want exactly N relays then act on the (N+1)th? Set BP=N-... no:
  BP=k relays k+1. For "skip j-1 then take j-th consumed": BP=j-2
  via `q m m`, loop, then a separate r after exit (reverse-a-list).
- Counter-on-return-row trick: put the `m` ON the return row so the
  prologue enters through it: prologue loads BP=n (no n-1 fixup) and
  every lap decrements once (max-element).
- `d` at a corner IS the conditional turn: heading down, cw = left;
  heading left, cw = up; heading right, cw = down. ccw is `a`.
  Memorize: clockwise = N->E->S->W->N.

Racetrack room: row1 rightward, row2 leftward, `v` and `<` at the
right end, `^` at col1 back to `>` at (1,1). The man loops forever;
blocking `r` is the idle state. THE PROLOGUE (@, seeds) MUST BE OFF
THE LOOP — if the lap re-enters prologue cells you re-execute them
(brackets bug: re-seeded state every lap).

## 3. X-branch geometry

X: A>0 turn clockwise, A<0 counter-clockwise, A=0 straight.
Heading right: >0 goes DOWN, <0 goes UP, 0 straight.
- Two-outcome tests always split 3 ways. Standard merge: let 0 go
  straight into a `v` that drops one row, and the turning branch land
  beside it; a '>' (or shared 'v') merge-cell unifies them.
- One real branch will always want to go UP. Give it a real row above
  (brackets closer-recover) or restructure so the upward outcome is
  impossible (leave it unrouted: hitting a wall is then an assertion).
- Sign-encoding on command pipes: k>=0 means "act", -(k+1) means
  "relay k+1". The map x -> -(x+1) is bitwise NOT: `M 1 + N`
  computes it, and applying the SAME entry code to either encoding
  yields the correct forward for the other station (memory P3W).

## 4. Pipes: parsing and selection rules (bug source #1)

- A pipe STARTS with an arrowhead whose BACKWARD cell lies on the
  source room's border, pointing away. A pipe drawn leaving a right
  wall must start with `>' then bend; starting with `^` above the
  wall silently creates an orphan + a wrong short pipe (brackets bug).
- The terminal arrowhead may itself be a bend, but Canvas.pipe cannot
  express that: patch manually `cv.cells[(r,c)] = ">"` after pipe().
- Corner attachment is LEGAL for rooms, ILLEGAL for displays.
- `s`/`r`/`q` pick the NEAREST pipe by Manhattan distance from the
  instruction cell to the pipe's SEGMENT CELL: cells[0] for outgoing,
  cells[-1] for incoming. These are cells OUTSIDE the room adjacent
  to the wall. Ties break by reading order (row, then col) of the
  segment cell. ALWAYS measure to the actual pipe cell, not "the
  attachment" (off-by-one killed brackets twice).
- `R`/`U` take from any READY incoming pipe, ties by reading order —
  a SPATIAL, not temporal, priority (this kills delay-line designs).
- Audit resolution empirically, don't trust hand distance math:

      m = Machine.parse(text)
      class F: pass
      f = F(); f.r, f.c, f.room = R, C, room_obj
      print(m._nearest_outgoing(f).cells, m._nearest_incoming(f).cells)

- KEEP ROOMS SMALL so each has <=2 incoming and <=2 outgoing pipes on
  opposite walls. If a design wants 3 pipes on a room, SPLIT THE ROOM
  (memory, plotter-v2). Chains of 1-in/1-out "stream rooms" need zero
  audits and are the most reliable pattern (plotter S1..S5).

## 5. FIFO discipline (scratch loops and rings)

A scratch loop (room -> relay room -> back) is a FIFO register file.
Rules that keep you sane:

- Fix a CANONICAL queue order between operations; every code path
  must consume and re-append so the order is restored. Count appends!
- If order fights you, options in order of preference: (a) B-hold a
  value across the rotation; (b) re-append and do one extra full
  rotation; (c) reorder the canonical order; (d) send a value twice
  (upstream duplicates are cheap: `s` twice, or W-shuffle pairs:
  r M r s W s emits [second, first]).
- Ring storage: values PARK at the destination end of pipes for free
  (no ticks while parked). Capacity of the in-pipe must hold the whole
  parked set if `q` is used to count it.
- `q` RACE: q counts only the in-pipe; values still in flight around
  the loop are missed. Guarantee parking with a delay corridor of
  spaces whose tick length exceeds out-pipe + relay lap (<=8) +
  in-pipe. Assert corridor > round trip in a unit test (reverse).
- Tracked counters (BP countdowns) need no corridor; prefer them when
  the count is known (memory, plotter-v2).

## 6. Shared-cell rules (layout compression)

Two paths may cross one cell if BOTH treat it harmlessly:
- space: nop for everyone;
- an arrow in the SAME direction a passer already travels: redundant;
- digits / `q` / `m`: harmless if the crosser's A / BP is dead;
- `M`,`W`: harmless only if crosser's A and B are both dead (home
  paths). NEVER share `s`, `r`, `X`, turning cells with live state.
Only one man per room ever exists, so collisions are impossible —
sharing is purely about instruction side effects.

## 7. Literals

- Walked-direction reading: `001` walked leftward loads 100. Write
  literals reversed on leftward rows.
- Vertical pairing is STRICT (our sim errors if two backticks in one
  column have a non-digit/space between). When stacking rows of
  literals, offset their columns or align so between-cells are only
  digits/spaces. Backtick paired on one axis is a no-op on the other.

## 8. Displays (LM-75)

- Drawn with + = : . Pipes: TOP=ADDR (cursor = row*W+col), LEFT=DATA
  (pixel 0..15 at cursor, cursor++ wrap), BOTTOM=SWAP (0: commit,
  clear next, cursor home; 1: commit, keep). Right side/corner attach
  is a load error. Processes one value per pipe per tick, ADDR ->
  DATA -> SWAP, during the execute phase.
- Frame-judged problems: every SWAP commit is compared to the next
  expected frame (streaming). Emitting ANY integer output fails.
- ADDR/DATA interleave race: if pixel i's DATA and pixel i+1's ADDR
  are ready the same tick, ADDR wins and pixel i lands wrong. Safe
  when the sender's per-pixel period exceeds the pipe-length skew + 2.

## 9. Round/protocol patterns

- A server machine never halts: end each round parked on a blocking
  `r` of the next input. Ticks after the last correct output/frame
  don't count; infinite idle is free.
- H after the last send only if single-round; else loop to the input r.
- An error AFTER the correct output is emitted still passes, but the
  output must have LEFT the output pipe (emission tick), not merely
  been sent.
- Sentinels: offset data to positive (x+2_000_000) and use any
  negative as end-marker; X tests it with zero arithmetic and without
  touching B.

## 10. Scoring strategy

score = max(width,height)^2 x avg ticks (footprint-only for some).
- Footprint dominates: prefer ONE dense room/machine over parallel
  fleets; storage in pipes is 1 cell/value, unbeatable.
- Balance the bounding box (square beats long).
- Ticks count only to the last output; init cost hits every test.
- Only your best submission counts; submit early, iterate freely.
- Private tests exist even though the API says privateTestCount 0;
  you must pass >=1 private to score at all. Never hardcode.

## 11. Workflow (exact commands)

    uv run pytest                                   # 72+ tests, keep green
    uv run python -m littleman FILE.man SLUG        # judge vs public tests
    uv run icfpc-api problems                       # ids (graded vs practice)
    uv run icfpc-api submit ID FILE --confirm --wait > out.json  # KEEP JSON
    (capture the submission id; do not tail the output)

Versioning rules (submissions/README in each problem dir): .man files
are immutable; new attempt = new `<slug>_NN.man` + entry in
variants.json (generator path, dims, local ticks/score, live id).

Debug ladder used successfully all day:
1. build -> print the rendered canvas, eyeball rooms/pipes;
2. Machine.parse -> list rooms, pipes (kind, side, len);
3. smoke run with tiny inputs, inspect res.output/error + every man's
   rel-position, A, B, BP, blocked;
4. monkey-patch Machine._execute to log every r/s with positions
   (see brackets session) — finds protocol bugs in one run;
5. resolution probes (section 4) for every s/r cell in doubt;
6. full judge; only then submit.
