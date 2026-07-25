# WORK ORDER: LLLM LOADER room (implementer: Codex)

Self-contained implementation spec. Supersedes `claude_08` §4 (physical):
specifying the rig exposed a simplification — LOADER needs only TWO pipes
and doubles as the round-input relay, eliminating the resolution
certificate and the phase-join entirely.

## Role in the machine

```
I --pipe--> [LOADER room] --pipe--> EXEC (owns the cell ring; not yours)
```

One man. Phase 1 (setup): consume `W H c0..c(W*H-1)`, emit the packed
world. Phase 2 (forever): relay each further input token (`k` values)
verbatim. Exactly one incoming and one outgoing pipe for the room's whole
life — no nearest-pipe ambiguity exists.

## Frozen interface (EXEC is built against this; do not alter)

Output token stream, in order:
1. **64 packed cell tokens**, canvas order (addr = y*16+x, addr 0..255,
   4 consecutive records per token, little-endian):
   `t = rec[4j] + rec[4j+1]*8192 + rec[4j+2]*8192^2 + rec[4j+3]*8192^3`
2. **1 man token**: `man_addr` (0..255), the canvas address of `@`.
3. **k tokens relayed verbatim**, one per later round, forever.

Record (13 bits): `rec = color | class<<4 | value<<8 | wall<<12`.
All tokens are in `[0, 2^52)` — signed-64 safe by construction.

| class | code | value | color |
|---|---|---|---|
| space | 0 | 0 | 0 |
| wall | 1 | 0 | 4 |
| heading | 2 | 0=N 1=E 2=S 3=W | 3 |
| digit | 3 | d | 8 |
| M | 4 | 0 | 12 |
| add | 5 | 0 | 10 |
| sub | 6 | 0 | 10 |
| branchX | 7 | 0 | 3 |
| halt | 8 | 0 | 3 |

Classification rules, position first (4 <= W,H <= 16; input well-formed
per the problem statement — NO validation):

1. padding (x >= W or y >= H): space record.
2. perimeter of the PROGRAM (x in {0, W-1} or y in {0, H-1}): wall record
   — regardless of glyph (`+ - |` on the border are walls, not ops).
3. `@`: space record; remember `man_addr = y*16+x` (emit in step 2 above).
4. interior glyph per the table (`^ > v <` map to heading values 0..3;
   note the LLLM op set has no uppercase V).

## Deliverables and write set (yours exclusively)

- `src/littleman/lllm_loader.py`:
  `reference_stream(tokens: list[int]) -> list[int]` — pure-Python
  reference of the frozen interface (~25 lines; the oracle);
  `build_loader_rig() -> str` — a TEST RIG grid: 3x3 `I` room -> LOADER
  room -> 3x3 `O` room (output rooms are legal in rigs; the real machine
  has none). The LOADER room grid inside the rig is the deliverable;
  the assembler will lift it verbatim (same 2-pipe shape).
- `tests/test_lllm_loader.py` (acceptance below).
- Do NOT touch `src/littleman/lllm.py`, `llm*.py`, `snake.py`,
  `split_probe.py`, or `submissions/` — other work in flight.

## Acceptance (all must pass)

1. RIG EQUALITY: for all 10 public LLLM cases and
   `littleman.llm_fuzz.corpus(20260726, 50)`: run the rig with the case's
   round-1 tokens followed by every round's k via
   `littleman.judge.judge_case`-style controller or a plain
   `Machine.run(inputs)`, and assert `res.output` equals
   `reference_stream(...)` for the setup prefix AND that each k appears
   relayed after it. (A plain run works: the rig HAS an output room.)
2. Directed: 4x4 minimum; 16x16 maximum; `+` and `-` ON the border
   (must classify wall); `@` at several interior positions incl. corners
   of the interior; digits 0 and 9; every op glyph once.
3. Determinism: `build_loader_rig()` byte-identical across calls.
4. Layout gates on the rig: `Machine.parse` OK; no shared walls
   (`server_compat.validate_layout`); all pipes >= 2 cells
   (`alexey_pipecheck.check`).
5. Prologue measured: report ticks from first input token to the first
   relayed k on the 4x4 and 16x16 directed cases.
6. Register discipline note in the report: where the packing accumulator
   lives during classification (see hint), or your better alternative.

## Implementation hints (non-normative — improve freely)

- Classification ladder: char in A; test equality via subtract-constant
  then `X` (zero arm = match). Constants via walked literals; B is
  clobbered per test — that is fine in phase 1.
- Packing accumulator: B cannot hold it across classification (ladders
  clobber B), so use a 2-cell scratch pipe loop as a 1-register spill:
  after classifying rec: `s_scratch(rec)`; then rebuild
  `acc = acc*8192 + rec` with the doubling trick — `M +` doubles A, 13
  times = *8192 with NO constants and NO B dependency — then
  `M`(B=acc*8192)... simplest exact order: acc in A -> 13x(`M +`) ->
  `s_scratch2`? One workable sequence with one scratch loop:
  acc in A -> double x13 -> M (B = acc*8192) -> r_scratch (A = rec) ->
  `+` (A = acc*8192 + rec... wait + is A+B: A=rec, B=acc*8192 -> `+`
  gives the sum — correct and B survives `+` if needed again).
  Emit every 4th token; BP counts to 4 via `b`/`m`/`d`.
- Scratch pipe = a second outgoing pipe? NO — that would break the
  2-pipe shape. Route the scratch INSIDE the room as a man-walk
  (values can also be "stored" by path position) or restructure so rec
  is computed AFTER the doubling (classify -> hold rec in A -> swap
  dance). If a scratch pipe proves genuinely necessary, attach it as a
  room-internal loop pipe pair and REPORT it — then the s/r cells need
  a binding audit (`littleman.ir_export.machine_ir` gives the
  engine-true resolution map; assert your bindings in the test).
- Phase 2 is the cookbook racetrack `> r s v / ^ <` with the prologue
  off-loop. The phase-1 circuit must not be re-entered (brackets rule).
- Budget: prologue <= ~25k ticks is fine (15M cap; 30x margins
  everywhere). Dumb-and-correct beats clever.

## Context files (read-only)

`docs/architecture/claude_08_loader_spec.md` (contract rationale),
`data/small/problems/little-little-little-man.json` (spec + cases),
`src/littleman/llm.py` (frame oracle), `docs/littleman-cookbook.md`
(idioms; note §1's B-rule is corrected: B is written only by M, W, /),
`scripts/preflight.py` (gate pattern), `claude/official-sim/NOTES.md`
(organizers' engine, second opinion).

## Report format

pytest tail; prologue ticks (4x4, 16x16); LOADER room dimensions; any
interface deviation (should be none — the interface is frozen); explicit
no-git-mutation-outside-write-set, no-submission.
