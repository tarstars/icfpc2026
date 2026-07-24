# Synthesis Stack — a hardware-flow view of building .man programs

This is the top-down counterpart to `docs/toolchain-plan.md` (which is
bottom-up). They describe the SAME artifact from opposite ends and meet
at the netlist interface (see "Where the two plans meet"). Read the
cookbook first: `docs/littleman-cookbook.md`.

## Thesis

The right industry analogy for compiling to littleman is NOT software
(C -> x86 -> object files -> linker). It is **hardware synthesis**:
HLS -> RTL -> logic synthesis -> place & route -> layout. The littleman
machine is a 2D spatial substrate where instructions are cells,
control flow is physical turning, memory is FIFO delay lines (pipes),
concurrency is fundamental (lockstep men), and cost is
`footprint^2 x ticks` — spatial and temporal at once. That is a chip,
not a program. Every design decision below follows from taking that
literally.

Model of computation: a **Kahn process network** over bounded blocking
channels. `r`/`s` block on empty/full; pipes are FIFOs with
backpressure; each room is a small sequential process (a processing
element) with a 3-register file (A, B, BP) and geometric control flow.

## The three tiers, sharpened

The user's proposal was: HLL -> component library ("objects") ->
linker. Correct shape, but rename and re-weight:

1. **Top — HLL.** Prefer a STREAM / process-network DSL
   (StreamIt/Lustre/CSP flavor), not general imperative code, because
   it matches the dataflow grain. General mutable-RAM imperative code
   would force synthesizing a memory subsystem per variable. (Exception:
   the soft-core route, see "The fork".)

2. **Middle — netlist + standard-cell IP library** (the load-bearing
   interface; nail this FIRST). Not ".o files": geometry travels WITH
   the object. A component carries its bounding box, port walls, and
   pipe-per-wall demand. See schema below.

3. **Bottom — place & route** (NOT "linker"). This is floorplanning +
   planar routing to minimize the bounding square. It is the NP-hard
   heart of chip design and where footprint score is won or lost (a 20%
   linear shrink = 36% score cut, since footprint is squared). Rename
   it in your head; it is the flagship, not an afterthought. Use a
   **simulator-in-the-loop search** (annealing over placements, scored
   by the real `Machine.parse` + judge) rather than an analytical
   solver — we have a cheap exact oracle.

## Why the layering is sound — and where it leaks

**Correctness separates cleanly (there is a theorem).** Carloni et al.,
"Theory of Latency-Insensitive Design" (2001): a network of patient
processes over channels is functionally equivalent regardless of
channel latencies, given relay stations may be freely inserted. Our
`r`/`s` blocking = patient processes; pipes = channels; pipe cells =
relay stations. **=> the router may move components and change pipe
lengths without changing the computed result — only cost changes.**
This is the theoretical license for the whole separation.

Two load-bearing conditions (violate either and the theorem dies):
- **No `R`/`U` merges.** Read-any depends on arrival order -> process
  is not a deterministic function of its input streams -> not a Kahn
  process. Library components must use only deterministic single-pipe
  `r`/`s` in fixed program order.
- **Rigid, small components.** `s`/`r` resolve to the NEAREST pipe by
  geometry, so a component must be internally fixed with unambiguous
  port walls (<=1 relevant pipe per direction). This is exactly the
  cookbook rule "keep rooms small, <=2 pipes per wall". The hand-won
  discipline and the compiler theory demand the same thing.

**Cost does NOT separate (phase-ordering).** Tick cost depends on pipe
lengths (a layout property); layout feasibility depends on component
granularity; some algorithm choices are forced by layout cost (memory's
"pack 3/word" was forced by the 100-cell ring dominating footprint; the
sort pipeline lost 14x to the ring on footprint alone). => Budget for
**cost-report feedback signals flowing upward** (the equivalent of a
timing report), e.g. router->HLL "your ring dominates footprint,
consider packing", router->component "these want 3 pipes on one wall,
split". Expect systematic, measurable experiments — not clean
independence.

**Verify the theorem empirically (cheap, do this early):** place one
netlist two different ways, confirm identical output streams. If it
holds (it should, for deterministic r/s), the router can chase cost
freely and preserve correctness — the entire premise.

## The fork you must choose consciously: soft-core vs synthesis

Two opposite ways an HLL can target this machine:

- **Fork A — soft-core + compiler.** Build ONE general littleman CPU
  once (ALU + register file in pipes + the memory ring we have + a
  microsequencer fetching an instruction stream from a pipe/ROM).
  HLL -> bytecode; every problem reuses the machine with new bytecode.
  A NORMAL compiler targeting a NORMAL ISA — easy, fully general.
  Scores BADLY (interpreter tax on footprint and ticks) but PASSES
  (earns the test-fraction point + eligibility). This is breadth
  insurance.
- **Fork B — dataflow synthesis.** Compile HLL -> a SPECIALIZED process
  network per problem (what our hand machines are). Scores well; the
  compiler is a hardware-synthesis tool (hard); each program bespoke.

Not exclusive. Strategy: **Fork A as fallback/breadth, Fork B for
problems worth optimizing. The component library serves BOTH** — the
soft-core is itself assembled from the same IP blocks (ring memory,
ALU, comparator, dispatcher). Fork A specifically rescues the
hand-synthesis-miserable problems: subset-sum (brute force via binary
counter under 15M-tick cap), matmul (triple nested loop over arrays),
sudoku (check 27 constraints) — trivial to WRITE imperatively, horrible
to hand-lay-out. "Ugly soft-core that passes" beats "elegant machine
unfinished".

## Techniques to steal from chip design

- **Standard-cell discipline.** Uniform component HEIGHT, ports on
  top/bottom, left-to-right dataflow => collapses 2D floorplan into
  row-based placement + channel routing (nearly 1D, well understood).
  Wastes some footprint (bad — squared) so use for FAST AUTO-LAYOUT
  BASELINES; reserve hand/annealing compaction for hero submissions.
  (Real flows: auto-place, then ECO the critical cells.)
- **Latency-insensitive protocol = the port contract** (valid/ready =
  r/s blocking). Make it explicit per port.
- **Retiming.** Move delay (pipe length) to balance arrival times
  without changing function (we did this by hand in triangle's pipe and
  the ring corridor).
- **Register allocation with spill.** Model A/B/BP + scratch-pipe spill
  slots as a classic allocator; the cookbook B-survival table is the
  interference model.
- **Crossers for non-planarity.** Pipes cannot cross => routing graph is
  planar => a non-planar netlist must spend a ROOM to relay data across
  a crossing (littleman's "jump to another metal layer"). The
  reverse-permutation-can't-be-wired result was the first instance.
- **ISA/microarchitecture split** = the HLL/component boundary: freeze
  component CONTRACTS, vary IMPLEMENTATIONS underneath, re-measure.

## Netlist schema (the middle tier — build this first)

    # a component IP block (standard cell)
    Component = {
      "name": str,
      "interior": (w, h),                 # inside walls
      "ports": [ {
          "name": str,
          "wall": "N"|"S"|"E"|"W",
          "offset": int,                  # cell index along that wall
          "dir": "in"|"out",
          "protocol": [str],              # value names in FIFO order
      } ],
      "pipes_per_wall": {"N":k, ...},     # placement demand
      "generator": "module:func",         # emits the room grid text
      "requires_no_RU": bool,             # latency-insensitive claim
    }

    # a program = structural netlist
    Netlist = {
      "components": [ {"id": str, "type": name, ...} ],
      "nets": [ {"from": (id, port), "to": (id, port),
                 "min_len": int} ],       # retiming/backpressure hint
      "io": {"input": (id, port)|None, "output": (id, port)|None,
             "display": (id, port...)|None},
    }

Difference from a `.o` file: "relocation" = choosing wall offsets +
routing pipes; the "symbol table" = port-name -> (wall, offset). A
component is position-independent in FUNCTION (latency-insensitivity)
but its PORTS have geometry.

## Bottom tier: pragmatic build order for the router

Do NOT build a from-scratch global planar router first. Order by ROI:

1. **Semi-automatic compactor (the 80/20, highest near-term value).**
   Input: an existing hand-placed machine (or its netlist). Do local
   LEGAL moves — slide components together, shorten pipes — with the
   simulator in the loop, keeping it parseable and re-scoring; keep any
   move that lowers footprint without breaking the judge. Harvests most
   footprint wins (memory at 67 wide is the first target) without
   solving global place & route. ~half a day; reusable on every
   existing AND future submission.
2. **Row-based auto-placer (standard-cell).** Given a netlist, place
   components in rows, route pipes in channels between rows, anneal
   offsets, score by simulator. Produces legal baselines from netlists.
3. **Global floorplanner** (annealing over 2D positions + orientations,
   crosser insertion for non-planar nets). Post-contest unless a
   problem demands it.

## Where the two plans meet

`toolchain-plan.md` is the BACKEND of this stack:
- L1 lane assembler = the component-body compiler (ops -> room grid) =
  the `generator` field above.
- L4 idiom macros = the library primitives (ring, relay, comparator,
  dispatcher, stream_room, display driver — already built in
  submissions/, extract them).
- L2 intent checker + L3 symbolic tracker = what makes component
  CONTRACTS trustworthy (port protocol == verified register/queue
  invariants).
- L5 "dataflow compiler" (deferred) = this stack's HLL front-end.
- The router/compactor is the NEW piece neither doc specced; add it
  here as the bottom tier.

## Honest ROI given the contest clock

The FULL stack (real HLL front-end especially) is very likely
NET-NEGATIVE on score inside the remaining ~2 days; a full compiler is a
multi-week build and mid-contest it risks producing nothing that
scores. Guardrail: **every tool stage must pay for itself on a specific
remaining problem within hours, or it defers to post-contest.**

Harvest the bottom and middle now, defer the top:
1. Freeze the netlist contract (an afternoon).
2. Extract existing machines as components (low risk, high doc value).
3. Build the semi-automatic compactor (best near-term tool; attacks the
   dominant cost term automatically).
4. Soft-core (Fork A) ONLY if we need breadth on a hard remaining
   problem and hand-synthesis is too slow.
5. Full HLL front-end + from-scratch annealing router: POST-CONTEST.

The idea is excellent as a PLATFORM and post-contest direction, and
partially harvestable now. Do not let the architecture's elegance
override score reality (footprint compaction + finishing problems by
hand, aided by cheap checkers, likely out-scores a half-built compiler).
