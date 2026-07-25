# Claude: LOADER, fully specified — the first worked component contract

**Amended by `claude_13`: this contract captured WHAT LOADER must do and
not HOW MUCH STATE that costs; a `live_state` field belongs in the
schema. LOADER holds x, y, W, H, char and an accumulator against two
readable registers.**

Status: Working hypothesis made concrete; the first component specified
through all five contract layers (codex_01's structure) with real numbers.
Problem context: LLLM machine; the same contract generalizes to LLM's
LOADER with the padding rule unchanged.

## 0. One-sentence role

Consume the first round's token stream `W H c0 .. c(W*H-1)` and produce
the machine's static world: a canvas-ordered ring of packed CELL records
plus the man's start address — then hand its room over to the ROUND
controller phase in a declared park state.

## 1. Behavioral contract

```
consumes:  in       = [W, H] ++ [c_yx : ASCII codes, row-major, W*H items]
produces:  cells    = [rec_0 .. rec_255]     (canvas order, addr = y*16+x)
           man      = [man_addr]              (emitted once, after cells)
state:     none carried across transactions (runs once per case)
reference: the loader phase of the validated Python model (lllm.py /
           llm_components.Loader) — executable, trace-recordable
```

Record semantics (logical, before encoding):

```
rec = (color: 0..15, op_class: enum, op_value: 0..9, wall: bit)
```

Derivation rules — the actual content of the component:

| condition (position first, char second) | color | op_class |
|---|---|---|
| x >= W or y >= H (padding) | 0 | space |
| x in {0, W-1} or y in {0, H-1} (perimeter) | 4 | wall |
| char = `@` | 0 | space (start cell is ordinary space; man drawn separately) |
| char = space | 0 | space |
| `< > ^ v` | 3 | heading(dir) |
| `X` | 3 | branch-sign |
| `H` | 3 | halt |
| digit d | 8 | load-digit, op_value = d |
| `M` | 12 | copy-AB |
| `+` / `-` | 10 | add / sub |

Two rules are the classic traps, both position-driven: **walls are
classified by position, never by glyph** (`+ - |` on the border are wall;
`+ -` in the interior are arithmetic), and **padding is invisible**
(color 0, unreachable — the program's own perimeter walls enclose the
man, so padding needs no wall bit).

Assumption, declared not checked: input is well-formed per the problem
statement ("programs you receive will be well-formed"). LOADER performs
zero validation. Evidence: spec text; all 10 public cases.

## 2. Protocol contract

- Framing: counted — the count `W*H` is fully determined after two
  tokens. No lookahead, no sentinels.
- Production interleaves with consumption **row-wise**: consume W tokens,
  emit W records, then emit `16-W` padding records; after H rows, emit
  `(16-H)*16` padding records. Streaming keeps LOADER's internal state at
  O(1) registers — it never holds the program.
- `man_addr` is discovered mid-stream (the `@` record is emitted as
  space) and **emitted once, after the last cell record**. Rationale: the
  consumer (EXEC) needs it exactly once, and emitting last means EXEC can
  read cells into its ring first and man state second, with no
  reordering.
- Ownership: single producer, single consumer per queue. Backpressure
  allowed everywhere (patient class — pure blocking r/s).

## 3. Timing and capacity contract

- Runs **once per case**; its entire cost is `prologue_ticks` (the metric
  memory_02 taught us to price: init hits every case's average).
- Per-token cost: receive + classify + pack + send. The classifier is a
  compare ladder over ~13 glyph codes: machine estimate 30-60 ticks per
  token worst case => prologue ≈ 8k-15k ticks unpacked. Against LLLM's
  15M cap and ~200-tick interpreted budgets: negligible; no cleverness
  warranted in v1.
- **Capacity — the load-bearing number.** The cells net must PARK the
  whole world: ring capacity >= 256 records at packing=1. 256 pipe cells
  is the single largest footprint driver of the whole machine.
  **Encoding decision** (declared, codex_02-style, on the net not the
  component): a record is 13 bits, so **4 records pack into one 52-bit
  token**, shrinking the ring to 64 tokens (+ slack). Consequences:
  ring footprint /4; FETCH scan cost per interpreted tick drops from
  ~2.3k to ~0.6k machine-ticks (64 tokens x ~9, with two `/`-peels per
  token adding ~4 fields' worth of work only at the matched token);
  LOADER's packer needs a 4-cycle accumulator (shift-or into B, emit
  every 4th). Baseline packing=1 remains a VALID implementation of the
  same contract — packing is an encoding declaration, not a behavior
  change, and the trace tests only see logical records.

## 4. Physical contract

The architecture unifies LOADER with the round controller: the station
cycle is a packet train `IN -> EXEC -> DRAW -> IN` (the shipped Snake
pattern), and LOADER is **phase one of the IN room's man**. Contract
consequences:

- Ports of the IN room: `input` (incoming, from the I room), `train_in`
  (incoming, from DRAW), `train_out` (outgoing, to EXEC). Two incoming
  pipes in one room => a **resolution certificate is mandatory**: the
  input-reading `r` cells must bind to `input`, the train-relay `r`
  cells to `train_in`, verified by the engine's own resolver on the
  final grid (ir_export map), not by hand distance math.
- Phase-transition obligation (the join invariant handed to phase two):
  after emitting `man_addr`, the man parks at the round loop's entry
  with a declared register state — A dead, B dead, BP dead — and the
  next `r` he executes binds to `input` (expecting the first `k`).
- No output room anywhere in the machine (frame-judged problem).

## 5. Evidence contract (acceptance for any implementation)

1. **Trace equality**: driven with the recorded `in` stream of every
   public case + >= 100 fuzz cases, the emitted `cells`/`man` streams
   equal the reference model's, token for token (engine pipe injection;
   no harness rooms).
2. Directed edges: 4x4 minimum and 16x16 maximum programs; `@` on a
   corner-adjacent interior cell; digits 0 and 9; every op glyph; a `+`
   ON the border (must classify wall, not add).
3. Property: padding records never render (all-zero color) and are never
   addressed by any reachable man position (walls enclose).
4. Prologue measurement recorded on the artifact: ticks from first input
   token to park, per public case.
5. The composed machine passes `scripts/preflight.py` and the 10 public
   cases — LOADER accepts blame for any initial-frame mismatch (INIT
   consumes its records downstream).

## The four decisions this spec actually pinned

1. Reindexing lives in LOADER (row-wise streaming with inline padding) —
   downstream components see a uniform 16x16 world and W/H die here.
2. Wall/padding classification is positional and *baked into records* —
   nobody downstream ever needs geometry (the Sonnet-A amendment,
   promoted to a rule).
3. `man_addr` emits last — fixes consumer ordering without buffers.
4. Packing 4/token is a net-level encoding declaration cutting the
   machine's dominant footprint term by 4 — with packing=1 as the valid
   conservative baseline.
