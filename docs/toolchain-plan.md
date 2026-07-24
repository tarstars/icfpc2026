# .man Toolchain Plan — hierarchy and implementation notes

Goal: replace error-prone hand reasoning with machine checks and
generators. Each level below states WHAT to build, the exact API,
HOW to implement it against the existing code, and a test plan.
Levels 2 and 3 are pure checkers (safe, build first). Level 1 is the
big time-saver. Level 5 is post-contest.

Existing code to reuse (do not duplicate):
- `littleman.sim.Machine` — parser, `_nearest_outgoing/_nearest_incoming`
  (authoritative pipe resolution), full semantics.
- `littleman.canvas.Canvas` — cell placement + pipe drawing.
- `littleman.judge` — round/frame controllers, footprint.
- `docs/littleman-cookbook.md` — the rules the tools must encode
  (B-survival table sec.1, shared-cell rules sec.6, X geometry sec.3).

------------------------------------------------------------------
## Level 2 — Pipe-intent checker  (BUILD FIRST, ~50 lines, 1 hour)

Problem it kills: an `s`/`r`/`q` cell silently resolving to the wrong
pipe (happened 3 times; hardest bug class to notice).

API (new module `littleman/intents.py`):

    check_intents(text: str, intents: dict[tuple[int,int], str],
                  pipe_names: dict[str, tuple[tuple[int,int], ...]]) -> None

- `intents`: absolute (row, col) of each s/r/q cell -> logical name,
  e.g. {(11, 8): "ring_out", (5, 3): "cmd_in"}.
- `pipe_names`: name -> a cell that identifies the pipe (any cell of
  it), e.g. first waypoint used when drawing it.

Implementation:
1. `m = Machine.parse(text)`.
2. Map each named pipe: find the Pipe object whose `cells` contains
   the identifying cell.
3. For each intent cell: find the room containing it
   (`room.contains_interior`), make a dummy object with attributes
   r, c, room, and call `m._nearest_outgoing(dummy)` for `s`,
   `m._nearest_incoming(dummy)` for `r`/`q`. For `S`/`R`/`U` assert
   the room's pipe SET matches instead.
4. Raise AssertionError listing cell, expected pipe, resolved pipe,
   and both distances (compute Manhattan to segment cells for the
   message — segment = cells[0] outgoing, cells[-1] incoming).
5. Warn (print) when the winning margin is 0 (reading-order tie) or 1.

Generators should call this at the end of every build_* function.
Retrofits: brackets, memory, sort_ring, reverse builders — add their
intent tables (this also documents the machines).

Test: tests/test_intents.py — a 2-pipe fixture where the intent is
correct, one where it is wrong (assert raises), one tie (warns).

------------------------------------------------------------------
## Level 3 — Symbolic register & queue tracker (~150 lines, 2-3 h)

Problem it kills: hand-tracing "is B still holding dy here?" and
"is the scratch FIFO back to canonical order on every path?".

API (new module `littleman/symbolic.py`):

    t = Trace(queue=["dy", "E", "dx"])       # named FIFO contents
    t.r("dy")        # pop head, assert name matches, A := that name
    t.s()            # push current A name to queue (or .s_out("pipe"))
    t.M(); t.W(); t.add(); t.sub(); t.lit("32"); t.b(); t.m() ...
    t.assert_A("dy"); t.assert_B("E"); t.assert_queue("dx", "E'")
    t2 = t.fork()    # branch; later t.join(t2) asserts same state

Implementation notes:
- State: A, B, BP as strings (symbolic names) or derived expressions
  like "E+2dy" (just string concat — no algebra needed; equality of
  intent is by string).
- Encode the survival table from cookbook sec.1: r sets A only;
  s reads A only; M: B=A; W: swap; arith: A = f(A,B) and mark B dead
  for / (B="rem(...)"); digits/literals set A; b/m touch BP only.
- fork/join for X-branches: join asserts queue contents equal and
  (optionally) A/B equal; different B allowed if caller passes
  allow={"A"} etc.
- This is NOT a simulator: no numbers, no layout — it validates the
  SEQUENCE design before any cell is placed. Use it in tests next to
  each generator: re-express each room's op sequence and assert the
  invariants (e.g. memory P3W entry: after M 1 + N s W the queue and
  A=tok claim; plotter EUPD lanes end with queue "dy E' dx").

Test: encode two known-good sequences (triangle program; reverse's
skip loop) and one known-bad (the brackets re-seed bug: sequence that
pushes seeds twice) — assert the checker catches the bad one.

------------------------------------------------------------------
## Level 1 — Lane assembler (block graph -> room) (~300 lines, 1 day)

Problem it kills: manual row/column allocation, turn glyphs, descent
routing, collision whack-a-mole (the plotter ETEST failure mode).

API (new module `littleman/asm.py`):

    room = RoomAsm()
    b0 = room.block("entry", ">@ then ops", ops="rX", entry=True)
    # terminators:
    b0.x_branch(neg="lane_n", zero="lane_c", pos="lane_c")  # merge ok
    b1 = room.block("lane_c", ops="+Mrs-")
    b1.x_branch(...)
    b2 = room.block("done", ops="`3`", then="send_delta")
    room.block("send_delta", ops="s", then="entry")   # loop closes
    grid_rows = room.layout()   # -> list[str] incl. borders

Layout algorithm (keep it dumb and predictable):
1. Assign each block a distinct ROW in topological-ish order
   (entry first). A block's ops are placed left-to-right from a base
   column (after reserved cols).
2. Column ledger: reserve col 1 for the home climb, col 2 spare;
   allocate one fresh DESCENT column per inter-row edge that goes
   downward, and one CLIMB column per upward edge, from opposite ends
   of a free-column pool to avoid crossings. Descent/climb cells are
   spaces except the first `v`/`^` and are recorded so later blocks
   must not place ops there (assembler enforces).
3. X-branch: the assembler knows heading is always RIGHT inside
   blocks, so: pos -> down (v-drop or direct), zero -> straight
   (auto `v` into merge), neg -> up. It routes: if the up-target
   block's row is below, raise (caller must reorder or mark the
   branch impossible via `neg=None`, which leaves it unrouted as a
   wall-assertion, cookbook style).
4. d/a loop terminators: emit the verified 2-row relay-loop idiom as
   a canned macro (see level 4) rather than routing arbitrary cycles.
5. After layout, verify by re-parsing: build a throwaway room text,
   run Machine.parse on it plus stub I/O, and walk a "dry man" (reuse
   sim movement with a mock execute) asserting every block is
   reachable and no op cell is entered from an unexpected direction.
   (Simplest robust check: simulate with a special Machine subclass
   that records (cell, heading) pairs.)

Non-goals: optimal packing, multi-entry blocks, arbitrary loop
shapes. If a room needs those, split the room (cookbook sec.4).

Test plan: rebuild ONE existing room with it (reverse's pump is the
best target: has corridor, two branches, loop, take, home) and assert
the assembled machine still passes tests/test_reverse.py. Then use it
for plotter ETEST/EUPD (claude/plotter-plan.md has the block graphs).

------------------------------------------------------------------
## Level 4 — Idiom macro library (~100 lines, grows organically)

In `littleman/idioms.py`, thin functions returning blocks/fragments
for the assembler (or raw strings for simple racetracks):

- relay_loop(): the `>rsv / ^ md` 6-cell idiom (BP+1 relays, exits
  below `d`, last value in A).
- corridor(machine_or_lengths) -> number of space-cells REQUIRED:
  compute out_len + 8 + in_len from the actual pipes and emit a
  serpentine of that many cells; expose the number so a unit test can
  assert it (replaces reverse's hand-counted test).
- literal(n, direction): digits, auto-reversed when the row is walked
  leftward; registers the columns so the builder can check vertical
  backtick pairing (cookbook sec.7).
- racetrack(seq): 2-row loop with entry '>', '@', auto turns, home.
- stream_room(name, ops): the 1-in/1-out S-room pattern: builds the
  room AND generates a pytest harness wrapping it with I/O rooms
  (this replaces the hand-built harness in tests/test_memory_rooms).
- dispatch3(): `M 2 W - X` three-way on token-2.

------------------------------------------------------------------
## Level 6 helpers (cheap, anytime)

- `littleman/debugger.py`: run a machine N ticks printing, per tick,
  each man's (room, rel pos, A, B, BP, blocked) plus non-empty pipe
  contents — the monkey-patch tracer from the brackets session,
  productized (~60 lines). Add `--watch CELL` to log executions of
  one cell.
- Footprint balancer: given built room blocks, brute-force the 2-3
  sensible arrangements (stack vs L-shape) and report bounding box.
- Tick profiler: count executions per cell over a judge run; hot
  cells tell you which loop to unroll (memory optimization work).

------------------------------------------------------------------
## Level 5 — Dataflow compiler (POST-CONTEST direction, do not start)

Compile a process-network DSL (processes with input/output streams
and a tiny body IR) into rooms: allocate the 2-in/2-out budget, split
processes whose live-value count exceeds A+B+one-hold, generate FIFO
plumbing and ring capacities, bin-pack rooms to a square. The
S1..S5 plotter pipeline is the existence proof; its derivation rules
ARE the compiler spec. Levels 1-4 are its backend; nothing built
above is throwaway.

------------------------------------------------------------------
## Build order and effort (for a session picking this up cold)

1. Level 2 intents checker — 1 h, pure win, retrofit brackets first
   (its intent table is in the build session notes / derivable).
2. Level 3 symbolic tracker — 2-3 h; validate against triangle +
   reverse sequences, then encode plotter-plan.md sequences BEFORE
   building the plotter rooms (they are written as op sequences —
   the tracker can verify all of them as-is).
3. Level 4 stream_room + harness generator — 1 h; needed for
   plotter S1..S5 step 1.
4. Level 1 assembler — 1 day; gate: reverse rebuild passes. Then
   plotter ETEST/EUPD.
5. Level 6 debugger — whenever debugging starts to hurt (~1 h).

Keep every tool as a CHECK first, a GENERATOR second: a generator
bug creates wrong machines, a checker bug only creates noise.
