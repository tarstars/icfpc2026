# Claude: machine IR first, Rust executor second, parser never (this window)

Status: Proposed concrete plan for the Tier-1 build of
`claude_00_position.md`; supersedes nothing, implements Delta 1.

## The split

```
.man text --Python Machine.parse--> machine IR (JSON, hashed)
machine IR --Rust lm-exec--> verdict, ticks, frames, traces   (hot path)
machine IR --Python render--> .man text --re-parse--> same IR (release gate)
```

Python keeps everything that has historically diverged (parsing: rooms,
pipe tracing, literals, displays, I/O discovery) and everything that runs
once per candidate. Rust gets exactly the loop that runs 1e4-1e9 times.
Search operates on IR, not text: a "move room 3 by (dr,dc)" is an IR edit
plus a Python re-trace of its pipes — pennies, off the hot path.

## Machine IR v0 (schema sketch)

Deliberately denormalized, execution-ready, content-addressable:

```jsonc
{
  "version": 1,
  "grid": ["...rows as strings..."],          // for provenance + re-render
  "rooms":   [{"top":0,"left":6,"bottom":4,"right":34}],
  "cells":   {"opcode grid as flat array or the rows above"},
  "men":     [{"r":1,"c":8,"room":0}],
  "pipes":   [{"cells":[[5,10],[6,10]], "source":0, "dest":2}],
  "literals":[{"cells":[[1,21],[1,24]], "axis":"h", "value":21}],
  "io":      {"input_pipe":1, "output_pipe":null},
  "displays":[{"top":..., "addr_pipe":..., "data_pipe":..., "swap_pipe":...}],
  "resolution": {"(r,c)-of-every-s/r/q": "pipe index"},   // precomputed!
  "sha256":  "of the canonical serialization"
}
```

The `resolution` map is the key simplification: nearest-pipe selection is
*static* (it depends on geometry, not on run state), so Python precomputes
it once per candidate and the Rust engine does zero geometric reasoning.
`R`/`U`/`S` keep their pipe *sets* the same way. If a proposed IR edit
changes geometry, Python recomputes the map — and that recomputation IS the
resolution-intent check of `claude_00` Delta 4 when diffed against the
component's declared bindings.

## Engine scope (Rust `lm-exec`)

In: exactly `sim.py`'s `_tick` semantics —

1. pipe shift (per-pipe, one cell toward dest if free);
2. output emission, input feed (or round-controller gating);
3. execute every man (opcode table from the generated `effects.json`);
4. move non-blocked men; collisions stop pairs; walls per configured
   policy (error vs final-step-lenient — both exist; the judge picks).

Plus the round controller (withheld input, expected output/frame matching,
last-output tick) because scoring stops there — a bare run always burns the
cap on server-style machines (measured lesson, twice this session).

Out of scope, permanently for this window: parsing, rendering, display of
any UI, and any geometry math beyond "is the next cell interior".

Determinism contract: given IR + input stream, `lm-exec` must equal
`sim.py` in verdict, tick count, output sequence, output ticks and frame
sequence — bit-exact, no tolerance.

## Differential gates (in CI, in order of cost)

1. **Golden corpus:** every `.man` in `submissions/` x its public cases —
   verdict+ticks exact vs Python. (~46 artifacts today; seconds in Rust.)
2. **Session-adversarial corpus:** the ~430 memory adversarial cases,
   replayed. Catches controller/tick-accounting drift.
3. **IR fuzz:** random legal IRs (random rooms, racetracks, pipes with
   valid endpoints) x random inputs, 1e5/night on YT; any mismatch is a
   bug in one of the two engines — bisect by tick trace diff.
4. **Server evidence:** the preserved `*-submit.json` responses pin
   area2/avgTicks for live artifacts; any engine disagreeing with a server
   number on a live artifact fails closed.

## Interface for search drivers

`lm-exec` is a library + a batch CLI:

```
lm-exec eval --ir candidate.json --workload memory-public.json
  -> {"verdict":"pass","cases":7,"avg_ticks":4159.0,"score":5693671.0}
stdin JSONL of {ir, workload} -> stdout JSONL of results   (batch mode)
```

Workload files are extracted once from `data/small/problems/*.json` plus
generated adversarial streams. No network, no filesystem writes, static
musl binary — the exact shape YT vanilla operations want (`claude_03`).

## Milestones (Tier-1 budget: 4-6 h)

| # | Deliverable | Gate |
|---|---|---|
| 1 | `ir_export.py`: Machine -> IR + resolution map; round-trip re-parse gate | every submissions/ artifact round-trips |
| 2 | `effects.json` generator + spec-table diff | matches language reference; flags the §1 correction |
| 3 | `lm-exec` core loop + round controller | golden corpus verdict+tick exact |
| 4 | batch CLI + adversarial corpus replay | 430 cases exact; throughput >= 5e7 ticks/s/core measured |
| 5 | IR fuzz harness (runs locally; YT later) | first 1e4 IRs mismatch-free |

Fallback if Rust stalls (honest): milestone 1+2 alone already pay — the IR
+ precomputed resolution map speeds the *Python* engine (its per-tick
nearest-pipe work disappears) and enables the Tier-2 composer regardless of
executor language. Measure before assuming; a 5-10x Python win from the
resolution cache is plausible and would fund Tier 2 by itself.

## Non-goals recorded so nobody re-litigates them at hour 40

- No Rust parser (Delta 1 rationale; revisit post-contest).
- No GPU port (branch-heavy 1-bit-scale integer state machine; a warp
  would idle. CPU fleet arithmetic in `claude_01` §6 is already sufficient).
- No JIT/approximate fast path: exactness is the product; speed comes from
  the language being tiny (a tick is ~10 array ops x men + pipe shifts).
