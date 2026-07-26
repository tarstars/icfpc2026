# Design notes: the `(nop n)` directive for the block-graph notation

Status: designed 2026-07-26 (user proposal + review); NOT implemented.
Companion gap: `U` -> `(if-recv ...)` lowering (strict-xfail in
`test_decompile`). Both are post-contest unless a contest need appears.

## Semantics

`(nop n)` = exactly `n` ticks pass for this man with no semantic effect.
EXACT, not "at least": the whole point is that block length stays a
faithful cost model, and timing-sensitive machines need exact delays.

- In the UNTIMED interpreter (`blocknet`, Kahn-style): a no-op. It must
  not influence correctness there, by construction.
- In the cost model: contributes `n` ticks.
- In a future TIMED graph interpreter: consumes `n` ticks.

## Three uses, in increasing depth

1. **Normalisation (decompile side).** Collapse maximal runs of pure
   corridor ops -- unconditional heading ops `< ^ v >`, spaces, `.` --
   into one `(nop n)`. Sound because every CONDITIONAL turn is already
   lifted to an explicit branch form with absolute targets and literal
   values are resolved at decompile time, so bare headings carry no
   control-flow meaning. This answers the "why are there `< ^ ^ >` in a
   geometry-free language" critique while preserving op-count == ticks.
   The round-trip test changes from verbatim equality to normalisation
   idempotence.

2. **Compile directive (assembler side).** Timing-sensitive machines
   (display driver lap alignment, ring phasing) are today built by
   hand-counting corridor cells. `(nop n)` names the intent; a layout
   engine must realise it as exactly-n cells of walk (serpentine if
   needed). This is the natural meeting point with Codex's lane
   assembler.

3. **Timing-completeness (the structural payoff).** Littleman timing is
   exactly three things: ops walked (1 tick each), pipe travel
   (length = delay) and blocking. `(nop n)` preserves the first under
   normalisation; annotating PIPE LENGTHS on port declarations adds the
   second; blocking is already semantic. With both annotations a
   tick-counting graph interpreter reproduces real timing exactly --
   which would make `q`/`R`/`U` machines validatable geometry-free and
   close the notation's one PROVEN limit (tcp_00 deadlocks untimed while
   the tick sim emits 17 outputs).

## Implementation sketch and cost

- `blockgraph.py`: parse/serialize `(nop N)`, N >= 1; treat as no-op in
  the untimed interpreter. Small.
- `decompile.py`: a `normalize=True` serializer pass collapsing corridor
  runs; tests for idempotence and for tick-count preservation
  (sum of ops+nops unchanged). ~1 agent-hour total.
- Timed interpreter + pipe-length annotations: a few hours; only worth
  it post-contest, but it converts the notation from "patient subset
  only" to fully faithful.

## Cautions

- Do not give `(nop n)` meaning in untimed semantics; keep the Kahn
  reading clean.
- Normalisation must NOT collapse across block boundaries or through
  ops that write state (only `< ^ v >`, space, `.`).
- When compiling, `(nop n)` interacts with literals walked backwards --
  the corridor realisation must not introduce cells that parse as ops.
