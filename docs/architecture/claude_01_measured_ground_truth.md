# Claude: measured ground truth the platform must encode

Status: evidence base. Every claim here is **Observed** unless labeled
otherwise, with the artifact that proves it. If a platform design
contradicts a row of this file, the design is wrong or the row needs
re-measuring — nothing in between.

## 1. The register model (corrected 2026-07-25)

| Register | Written by | Readable | Notes |
|---|---|---|---|
| A | almost everything | yes | the accumulator |
| B | `M`, `W`, `/` **only** | yes (via ops/`W`) | survives `+ - * % N & | ~ { }` and all of `r s m d a x ] q b`, digits, arrows, literals |
| BP | `b`, `m`, `]`, `q` | **no** — sign (`d`,`a`) and low bit (`x`) only | write-only counter |

The struck-through cookbook claim (B destroyed by arithmetic) survived two
days because every machine was conservative in the same direction. Two
consequences:

- **Correctness debt: zero.** All shipped machines over-save B; none relies
  on the wrong claim.
- **Design debt: real.** Every "needs three live values" rejection
  (two are recorded in `reports/2026-07-25-memory-packed.md`'s alternatives
  section) was argued from a false premise and deserves re-examination.
- **Evidence gap: CLOSED (2026-07-25T13:5xZ).** The Snake builder proved
  the server implements B-survival: monkey-patching `Machine._execute` to
  zero B after every `+ - * % N & | ~ { }` drops `brackets_00.man` — live
  26/26 on the server — from 9/9 to 3/9 locally. A machine that scored on
  the server therefore *relies* on B surviving arithmetic. (Label:
  Observed, server-corroborated by a live artifact.)

Platform rule derived: `effects.json` {reads, writes, blocks, turns,
clobbers} per opcode is *generated* from `sim.py` and diffed against the
language-reference tables in CI. Prose never carries op semantics again.

## 2. Throughput algebra (why the memory rebuild won 3.15x live)

Profile of `memory_01` on the public "interleaved cells" case
(instrumented `Machine._execute`):

- 125 operations; sum of ring distances 6108 items; 55,482 ticks.
- The three ring rooms execute ~93% of all instructions — but run
  **concurrently**. Per-item cost = one station lap ≈ **8.9 ticks**, not
  three laps.
- Therefore the only lever was circulating-item count: 3-per-word packing
  cut 6108 -> 1994 relays (3.06x); measured end-to-end tick ratio 0.4287 on
  maximum-length streams (not 1/3 — fixed per-op overhead persists;
  Amdahl).

The algebra the composer should enforce statically:

```
II_pipeline   = max(II_stage_i)          (stages overlap; slowest lap rules)
latency_total = sum(latency_i) + sum(route_lengths on the request path)
ticks_case    ~ ops * II_bottleneck + prologue + drain
```

Route length on a *ring* does not tax throughput (values park for free —
cookbook §5); route length on a *request path* taxes every operation.
Weight routed-net length by measured traversal counts, not uniformly.

**Prologue is a first-class metric.** memory_02 seeds 34 zeros in ~200
ticks and that regressed the shortest public case 179 -> 264 while every
long case improved; init cost hits every test in the average. A contract
records `prologue_ticks` next to II.

## 3. Score projection policy

Observed: local:server tick ratio is **not constant across machines** —
memory_01 4.243x, memory_02 4.874x; the handoff projection missed by
+12.5% (predicted 17,733 server avgTicks; measured 20,273; submission
`c9708792`). Policy: projections may *rank* candidates, only submissions
*measure*; any promised number carries ±15% and the label "projection".
Corollary for the optimizer: prefer scale-invariant objectives (footprint,
II, item counts) over projected server scores.

## 4. The geometry-changes-semantics catalog (the DRC list)

Everything below makes *placement* affect *meaning* — the exact ways the
latency-insensitive theorem leaks, and therefore the checker list for any
composer. Sources: cookbook, `language-reference.md`, and the named
incidents.

| # | Coupling | Incident / proof |
|---|---|---|
| 1 | `s`/`r`/`q` bind to the NEAREST pipe segment (Manhattan, reading-order ties) | brackets built wrong twice; memory station audited 11 bindings empirically |
| 2 | `R`/`U` priority is spatial (reading order), not temporal | killed a delay-line design (cookbook §4) |
| 3 | `q` counts only parked values; in-flight values are invisible | reverse needed a delay corridor sized > round trip |
| 4 | Display processes ADDR -> DATA -> SWAP within one tick | pixel-lands-wrong race (cookbook §8); Semester 4 machines rely on the exact order |
| 5 | Literals read by walking direction; vertical backtick pairing is strict | `history_00` parses on the server, rejected locally; the fixed-slot width formula's `+5` term |
| 6 | Shared cells execute for every crosser | brackets re-seeded state every lap until prologue moved off-loop |
| 7 | Two men colliding stop both (mover stays put) | unreachable in LLM (1 man/room) but implemented in `llm.py` after Codex's review |
| 8 | Rooms sharing wall cells: server rejects, parser accepts | `server_compat.validate_layout` exists because of it |
| 9 | Pipes < 2 cells: server rejects at load, local judge passes clean | `sort_05` and `reverse_02` built, validated, dead on arrival |
| 10 | Final wall step after last send: server lenient, strict judge errors | `alexey_walljudge` / server_compat divergence, confirmed live |

Rules 8-10 are *server-vs-local* divergences: they belong in load gates.
Rules 1-7 are *language semantics*: they belong in the composer's checkers
and in protocol classes (`arrival_ordered`, `occupancy_observing`,
`display_scheduled` per codex_01 — adopted).

Checking method (Delta 4 of `claude_00`): run the engine's own resolver and
parser on the final grid and compare against declared intent. One
implementation of the rules, used to run and to verify. `scripts/preflight.py`
is the assembled gate today.

## 5. Component patterns proven this contest (extraction seeds)

Beyond codex_01's extraction list, the Semester 4 work added three patterns
worth contracts of their own:

- **Draw-once, patch-per-frame display driver.** Commit with SWAP=1 (keep
  buffer); a frame update is ADDR old, DATA restore, ADDR new, DATA 9/10,
  SWAP — 5 tokens instead of 256. (LLLM: only the man's cell changes;
  Snake: 2-3 cells; Pathfinder: robot cell.) This is the difference between
  ~51k ticks and ~3M ticks per case on LLLM.
- **Interpreter-as-ring.** Program memory = 256-token pipe ring scanned
  once per interpreted tick; random access = full rotation with index
  compare. Deterministic, tiny, and the scan cost (51k token-visits per
  200-tick case) is far under every cap.
- **Bitboard rows with guaranteed-wall borders.** 16-bit rows packed low in
  signed-64 words; shift leakage across row boundaries is *self-healing
  only because the border is always wall* — an assumption that must be an
  assert in the generator, not a comment (pathfinder handoff,
  `claude/pathfinder-reference.py`; includes the distance-mod-3 bit-plane
  trick that fixes the frontier-order bug: on a bipartite grid, d-1 vs d+1
  are distinguishable mod 3, not mod 2).

## 6. Numbers for the engine plan (feeds claude_02)

- Python engine throughput today: "interleaved cells" 55,482 ticks in
  ~0.3 s ≈ 2e5 ticks/s with 5 men ≈ 1e6 man-ops/s.
- Full memory public suite (7 cases) ≈ 29k judged ticks ≈ 0.15 s Python.
- Adversarial batches this session: ~430 judged cases (six ~76k-tick
  max-length streams + 400 short streams + structured cases) ≈ 100 s.
- Straight-line Rust expectation: 5e7-2e8 ticks/s/core (conservative
  250x) => a full memory-suite evaluation ≈ 0.5 ms => ~1e6-7e6 candidate
  evaluations per core-hour; a 1000-core YT pool turns a night into ~1e10
  evaluations. Search designs in `claude_03` assume the conservative end.
