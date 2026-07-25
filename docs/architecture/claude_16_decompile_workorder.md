# WORK ORDER: decompile the .man corpus to block-graph notation

Goal (user's): convert our proven machines into the block-graph language
of `claude_15` / `src/littleman/blockgraph.py` and re-validate them
through the block interpreter — proving the notation is expressive
enough for real machines, and yielding a library of proven components in
compilable form.

## Honest scoping: this is THREE problems, phased

The task description hides three distinct pieces of work. Deliver them in
order; each phase is independently valuable, so STOP AND REPORT at
whatever phase you reach rather than risking all of it.

### Phase A — the decompiler (.man -> block graphs)

For each room containing a man, recover the control-flow graph over
**(row, col, heading)** states — that triple, not the cell, is the node,
because one cell crossed in two headings is two different nodes.

- start state: the `@` cell, heading EAST;
- walking: each cell executes; `< > ^ v` set heading; a backtick span is
  ONE op token (walk direction determines its value); `H` terminates;
  stepping onto a WALL terminates the path — emit a distinguished
  `__wall` block (an unrouted arm is a deliberate assertion in our
  machines, not a bug);
- forks: `X` -> 3 successors, `d`/`a` -> 2, `x` -> 2. Their successor
  states are physically determined by the turn each outcome makes;
- blocks: maximal straight chains; start a new `(mark ...)` at every
  fork target and at every state with more than one predecessor;
- serialize to the s-expression text, re-parse with
  `blockgraph.parse(..., allow_timing_ops=True)`, and assert the graph is
  identical (round-trip gate).

### Phase B — single-man equivalence (the real test of the notation)

For every machine with exactly ONE man (I/O rooms hold no men, so many
machines qualify): run `littleman.sim` on the problem's public inputs,
and run `blockgraph.run()` with `recv` bound to the same input list and
`send` collecting output.

Assert identical: output sequence, final A/B/BP, termination reason.
This comparison is exact — with one man there is no interleaving.

### Phase C — network interpreter (multi-man)

`src/littleman/blocknet.py`: N block graphs + FIFO pipes (capacity = the
pipe's cell count), blocking `r`/`s`, round-robin until quiescent.

Compare **output sequences only, never tick counts** — block-atomic
execution cannot reproduce tick timing, and it does not need to: for
`patient` networks (blocking r/s only) the latency-insensitivity result
in `docs/synthesis-stack.md` guarantees the outputs match.

SKIP, with a recorded reason, any machine that uses `q`, `R`, `U`, or a
display: those observe occupancy, arrival order or tick-level display
races, so they are NOT patient and are out of scope for this interpreter.

### Phase D — coverage report

`reports/2026-07-25-blockgraph-corpus.md`: one row per artifact —
rooms, men, decompiled?, phase B/C verdict, skip reason, block/edge
counts. Plus a short conclusion on whether the notation proved expressive
enough, and any construct it could NOT express (that is the most
valuable finding available here — report it prominently).

## Write set (yours exclusively)

`src/littleman/decompile.py`, `src/littleman/blocknet.py`,
`tests/test_decompile.py`, `reports/2026-07-25-blockgraph-corpus.md`.

Read-only: `blockgraph.py`, `sim.py`, `judge.py`, everything under
`submissions/`, all other `src/littleman/*.py`. Do NOT edit them.

## Acceptance

1. every `.man` under `submissions/` that `Machine.parse` accepts also
   decompiles without error and round-trips (one known exception is
   allowed: `history_00.man` does not parse locally);
2. every single-man machine passes phase B exactly on its public cases;
3. at least the memory family (`memory_01`, `memory_04`) passes phase C;
4. the report explains every skip and every failure.

## Method notes

- Reachability is a graph walk, not simulation: at an `X` explore all
  three arms, since the branch is data-dependent.
- Loops are natural (a state already visited becomes a `goto` to its
  block); do not unroll.
- A merge point needs its own mark even mid-run — track predecessors.
- Blocked `r`/`s` does not change control flow, only timing; ignore it in
  phase A.
- Start with the SMALLEST artifacts (`triangle_04.man`, `max_00.man`) to
  get the pipeline green, then scale up.

## Process rules

Output-budget discipline (see `docs/architecture/claude_14`): <=120-line
Writes/Edits, >=5 incremental calls, Edit-append over rewrite, a cheap
test between calls, never print grids or file bodies, responses <=10
lines. No git mutations, no `icfpc-api submit`.
