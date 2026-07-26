# Revolutionary optimization roadmap for ICFPC 2026

Integrated against `origin/main@1076118` on 2026-07-26. Measurements from
other branches retain their exact branch and commit names below. Recheck them
before implementation because those branches are not all ancestors of main.

Evidence labels used throughout:

- **CONFIRMED** — an exact bound, test, profile, artifact, or live API result;
- **PLAUSIBLE** — the representation and arithmetic are sound, but no complete
  Littleman machine has passed yet;
- **SPECULATIVE** — a research direction whose geometry, ticks, or protocol
  still lacks an end-to-end prototype.

## 1. Repository progress is split across branches

The latest useful results are not all in one branch:

- `origin/main@1076118`: `brackets_11`, 27x27, live score 484,532.65;
- `origin/agent/codex-matmul-components@127ff09`: `matmul_07`, 115x98,
  live score 8,436,652,022.5;
- `origin/agent/codex-gradebook-components@10936b0`: `gradebook_05`,
  382x307, live score 47,115,780,603.6;
- `origin/agent/claude@7407929`: History 85x85, live score 7,225, plus the
  solver-stack design;
- `origin/agent/claude@96eb210`, adopted here as `e290297`: the exact
  `history_pack` asymmetric archive, 4,767 literal cells and no machine yet;
- the uploaded worklog records accepted `plotter_06` at 1,668,891,820 and
  `sudoku_04` at 11,307,342,643, although their terminal response JSON files
  are not preserved beside the artifacts in the snapshot;
- the worklog records `memory_10` at 30x30 and 17,236,875; it also records a
  later manual 16,033,454.75 result whose exact source is absent.

This matters operationally: integrate or at least catalogue by artifact hash
before beginning overlapping work.

## 2. The strategic conclusion

The repository has become very good at L0/L1 optimization:

- room placement and routing;
- global row/column squeeze;
- staircase folding;
- pipe-length preservation and resolution audits;
- component substitution.

Those methods delivered real 1.3x-8x gains. They cannot normally deliver the
next 100x. The remaining large scores are pinned by **representation and
process topology**, not by blank cells.

The next layer must search or design:

- packed state representations;
- stream decomposition and pipeline initiation interval;
- sequential versus tiled versus `Y`-parallel architectures;
- algorithms whose storage fits the score's squared dimension term.

CP-SAT placement remains useful after an architecture exists. It cannot invent
a packed record ring, a three-lane multiply, or a sharded meet-in-the-middle
search.

## 3. MatMul: a credible 100x route

Evidence status: **CONFIRMED packed-lane arithmetic; PLAUSIBLE machine;
SPECULATIVE 100x score.**

### Current measured bottleneck

`matmul_07` is 115x98, footprint 13,225, server average 637,932.1 ticks, and
score 8,436,652,022.5.

Profiling the exact full 16x16x16 public case gives:

- total ticks: 2,610,270;
- controller cell executions: 2,610,269;
- spaces and direction cells: 2,553,181 = **97.813%**;
- semantic cells: 57,088 = 2.187%;
- multiplications: 4,098, of which 4,096 are matrix products;
- the common steady-state interval between product multiplications is
  **470 ticks**;
- only one controller receive attempt blocks in the entire case.

The machine is not waiting for data. It is walking across a large multi-zone
controller.

A 100x result must score at most 84,366,520.225. Equivalent targets include:

| Maximum dimension | Maximum average ticks |
|---:|---:|
| 40 | 52,729 |
| 45 | 41,662 |
| 50 | 33,746 |
| 60 | 23,435 |
| 64 | 20,597 |

### Proposed architecture: packed three-column streaming outer product

For three adjacent output columns, pack a B-row group into 20-bit lanes:

```text
P_t = (b[t,j]   + 100)
    + (b[t,j+1] + 100) * 2^20
    + (b[t,j+2] + 100) * 2^40
```

For `x_t = a[i,t] + 100`, accumulate `R += x_t * P_t`.

The lane bound is exact:

```text
16 * 199^2 = 633,616 < 2^20.
```

Therefore additions never carry between lanes. The complete packed
accumulator is below 2^60 and remains a positive signed 64-bit integer.

For lane `l`:

```text
raw = (R >> (20*l)) & (2^20 - 1)
C = raw
    - 100 * sum_t(a[i,t] + 100)
    - 100 * sum_t(b[t,j+l] + 100)
    + M * 100^2
```

This has been checked by an independent Python model against directed extreme
matrices and thousands of random matrices over all legal dimensions.

Benefits:

- one packed multiply updates three output columns;
- B storage falls from at most 256 scalar tokens to at most 96 packed tokens;
- the partial-sum state falls from K scalars to `ceil(K/3)` packed values;
- a one-lane baseline reduces public hot-loop iterations from an average
  732.43 scalar products to 276.43 packed groups, a 2.65x reduction;
- a small MUL3 room can keep the shifted A factor in B while a separate ACC3
  room retains the packed accumulator;
- the large controller leaves the per-product critical path entirely.

The stronger production form is a **six-lane pack-and-broadcast engine**.
There are at most six three-column groups. Give each group its own M-token B
ring and MUL3/ACC3 pair. A dedicated broadcaster room receives each shifted A factor and sends it
to all six lanes with `S`; inactive lanes consume and ignore it. Negative
control tags reset or emit accumulators. Because commands and factors share
the same FIFO, the end-of-row command is automatically ordered after every
product, and `S` provides all-lane backpressure without an acknowledgement
network. The hot iteration count then follows `N*M` factor broadcasts rather
than `N*M*ceil(K/3)` group visits.

The current MatMul server/local score ratio is about 1.236, so a local result
that only barely crosses the live 100x line is not safe. The practical local
target is **<=55M**: for example 50x50 at <=22,000 ticks, or 40x40 at
<=30,000 ticks. Those score 55M and 48M locally and leave material room for a
higher server workload. The six-lane form has enough throughput margin to
spend extra cells on simple, auditable control.

### Second MatMul architecture: a 4x4 tiled systolic engine

If the streaming packed engine works but still carries too much controller
cost, build a 4x4 output tile:

- 16 multiplier processes forward A east and B south;
- 16 accumulator processes retain one sum each in register B;
- process one 4x4 C tile for M<=16 waves, then emit and reset;
- at most 16 tiles cover the 16x16 output;
- use packed A/B storage or compact feed rings outside the tile.

A full 16x16 array is unnecessary. A 4x4 tile captures the pipeline benefit
without 512 permanent rooms. `Y` can later distribute a factor or launch lane
workers, but the first candidate should establish a non-`Y` throughput
baseline.

## 4. Other architecture-level opportunities

The score estimates below are design targets, not measured candidates.

### Grade Book: one packed record ring

Evidence status: **PLAUSIBLE.** The 42-bit bound is exact for the documented
limits used by the existing implementation, but the proposed engine and its
30x30/50,000-tick target are not measured.

Current recorded result: 382x307, score 47.116B.

One student fits in 42 bits:

```text
id:       14 bits
4 grades: 4 * 7 bits = 28 bits
```

Store one record per token in a 16-token ring. One compact engine scans the
ring for every operation:

- GET: extract one 7-bit field;
- SET: mask and replace one field;
- AVG: sum the selected field;
- TOP: compare `(grade, -id)`;
- unmatched records are simply restored.

This removes four subject engines, four record rings, four scratch rings, the
four-way command broadcast, result arbiter, and acknowledgement chain.

A 30x30 machine at 50,000 average ticks scores 45M: roughly **1,047x** below
`gradebook_05`. Even a much slower first implementation has enormous margin.

### Sudoku: nine 27-bit state words

Evidence status: **PLAUSIBLE.** The state representation is exact; the
single-ring update protocol and score target are not yet built.

Current worklog result: 184x192, score 11.307B.

Store nine tokens:

```text
state[i] = row_mask[i]
         | col_mask[i] << 9
         | box_mask[i] << 18
```

For each `(r,c,v)`, compute box index and scan the nine-token ring once. Token
`i` conditionally updates its row, column, and/or box field; coincident indices
are handled in the same visit. Accumulate one duplicate flag and output at the
end of the scan.

This replaces three giant worker modules and 27 independent rings with one
small state ring. A 25x25 machine at 20,000 ticks scores 12.5M, about **905x**
below the recorded result.

### Subset Sum: sharded direct meet-in-the-middle search

Evidence status: **SPECULATIVE.** The sorter elimination is algorithmically
sound, but 1,048,576 comparisons leave only about 14 ticks per comparison
under the 15M cap before enumeration and output. The 16-shard version needs a
measured storage/broadcast prototype before its 60x60 target is credible.

Current result: 3,646x3,029, score 91.77T, 2,121 rooms.

The current machine pays enormous footprint to sort both 1,024-element half
streams. Sorting is not required:

1. enumerate and store 1,024 `(sum,mask)` pairs for half A, packed into one
   integer;
2. enumerate each half-B pair and form `target - sumB`;
3. search A for matching sums and retain the greatest combined mask.

A single 1,024x1,024 scan is 1,048,576 comparisons and may already fit the
15M cap in a tight loop. The safer revolutionary version uses 16 shards of 64
A pairs. Broadcast each query with `Y`, scan all shards in parallel, and reduce
16 candidate masks. Storage remains 1,024 cells but the sorter farm and its
2,000 rooms disappear.

A 60x60 machine at 2M ticks scores 7.2B, more than **12,000x** below the live
result. The hard gate is worst-case throughput under the 15M cap, not score.

### Pathfinder: four-word BFS plus a stored direction policy

Evidence status: **PLAUSIBLE representation, SPECULATIVE score.** Cross-word
shifts, row-edge masking, tie order, display traffic, and successive flag
rounds must all be present in the first prototype.

Current result: 187x1,957, score 17.55T.

Use four 64-bit words for each 256-bit mask. Run one backward BFS per flag.
When a new cell is discovered, assign its preferred next direction in exact
up/right/down/left order:

```text
U = cells whose up-neighbour is in frontier
R = remaining cells whose right-neighbour is in frontier
D = remaining cells whose down-neighbour is in frontier
L = remaining cells whose left-neighbour is in frontier
```

Store the resulting policy as four direction masks or eight 2-bit policy
words. Path playback then needs no ring rescans and no repeated BFS: each move
is a constant-size bit test plus two display writes.

Run the four words in four small parallel workers or through a `Y`-spawned
word farm. A 50x50, 100,000-tick candidate scores 250M, roughly **70,000x**
below the current result.

### Plotter: compile the Bresenham kernel, not the roomy FSM

Evidence status: **PLAUSIBLE architecture, SPECULATIVE score.**

Current worklog result: 155x145, score 1.669B.

The display itself imposes a roughly 34x26 physical floor. The existing three
large rooms remain extremely sparse even after staircase folding. Replace the
roomy general FSM compiler with two or three hand-sized racetracks:

- error test/update state;
- address update state;
- display stream and final swap.

Keep the existing correct protocol and state ordering, but make one pixel cost
approximately 20-80 ticks rather than hundreds. The public cases average only
about 62 pixels per test case. A 40x40 machine at 8,000 average ticks scores
12.8M, about **130x** below the recorded result.

A later `Y` version can evaluate the two symmetric Bresenham conditions in
parallel and merge their coordinate/error deltas.

### Snake: FIFO body plus four occupancy words

Evidence status: **PLAUSIBLE state representation, SPECULATIVE 30x30 target.**

Current result: 153x154, score 915.99M.

Use:

- a <=100-token FIFO of body addresses;
- four 64-bit occupancy words for O(1) self-collision;
- compact scalar state for head, direction, fruit, and length;
- delta display writes only.

On a non-fruit move, clear the old tail bit before testing the new head bit,
which makes moving into the vacated tail legal. On loss, recolour the saved
body addresses once. A 30x30, 8,000-tick target scores 7.2M, approximately
**127x** better.

### LLLM and LLM: rolling-head microcode

Evidence status: **PLAUSIBLE and partially prototyped.**

Current results: LLLM 22.19B; LLM 8.775e15.

The correct revolution is already visible in the active SCAN3/STEP3 branch:
store program memory compactly and keep its ring head near the interpreted
man's current address. A simulated man moves only one cell per tick, so memory
alignment changes by `+/-1` or `+/-W`, never an arbitrary 256-cell search.

For LLM, retain at most three compact man-state records and at most 20 pipe
cells. A microcoded tick engine should replace the current 25,797-row physical
unrolling. The potential is orders of magnitude; this branch deserves
continuation rather than another geometry press of `llm_codex_01`.

### TCP: packed direct-address storage

Current result: 31x31, score 1.640M.

Pack six 10-bit packet values per word. The maximum-delay rule means only a
rolling 16-position window must be resident, so three words and a 16-bit
occupancy mask are sufficient; eight words for all 48 possible sequence
numbers would waste storage. A packet updates `seq mod 16`, then the machine
emits while the expected occupancy bit is set. This is unlikely to be a 100x
gain because TCP is already small, but it is the cleanest remaining
algorithmic replacement and could remove most ring movement.

Evidence status: **PLAUSIBLE.** The 10-bit value packing is already exercised
by `tcp_fast`; the direct-address update/emission controller is not built.

## 5. Problems that should not receive a 100x campaign

- Triangle is already at score 832 and rank 1 in the recorded state.
- Memory already uses the maximum natural three 21-bit values per signed word;
  remaining gains are small component work.
- Reverse packing was built and measured; unpack cost lost to the 6-tick/value
  scalar loop. The 13x13 geometry is already excellent.
- Brackets already uses a one-word base-3 stack and is square at 27x27. Its
  next gain is classifier/control-flow surgery, not a representation reset.
- History is footprint-only and now has a measured asymmetric archive:
  `src/littleman/history_pack.py` chooses 56 tokens, emits 1,812 top-level
  symbols in 202 radix-127 words, stores the 266-character token table in 25
  words, and reduces fixed literal cells from 5,460 to 4,767. Nine tests prove
  exact round trips and signed-64 safety. The missing work is the Littleman
  table-walking decoder and a packed layout. This is the highest-confidence
  immediate architecture build, not a general-tooling exercise.

## 6. Tooling needed for revolutionary work

Add a layer above the new solver stack:

1. **ProcessNetworkIR**
   - processes, stream types, FIFO capacities, persistent registers;
   - latency and initiation interval;
   - sequential, replicated, tiled, and `Y`-spawned variants.

2. **Packed-kernel verifier**
   - signed 64-bit bit-vector semantics;
   - exhaustive directed bounds plus SMT or randomized equivalence;
   - output contracts such as three 20-bit independent lanes.

3. **Component characterizer**
   - exact trace tests;
   - measured latency, steady-state initiation interval, footprint, and port
     geometry;
   - retain a Pareto family, not one winner.

4. **Score feasibility gate**
   - every goal starts from a factor target and derives legal `(M,ticks)`
     pairs;
   - reject architectures that cannot cross the desired frontier before room
     polishing begins.

5. **L0/L1 solver backend**
   - use the existing CP-SAT/placement design only after the process network is
     fixed;
   - preserve pipe capacity and nearest-port bindings through the exact oracle.

## 7. Prioritized execution queue

Priority is based on expected contest value multiplied by confidence and
divided by time to an end-to-end judged artifact. A large projected factor
does not outrank a smaller measured design merely because its estimate is
dramatic.

| Priority | Work | First mandatory proof | Stop/reassess condition |
| ---: | --- | --- | --- |
| P0 | History asymmetric archive decoder | Exact 2,810-byte output from the 202+25 packed words in a server-compatible box smaller than 85 | Decoder/layout cannot fit at 84 or below |
| P1 | MatMul packed three-column stream | One complete packed lane matches the Python oracle at all directed extremes and has measured initiation interval | Projected complete score cannot beat `matmul_07` by at least 10x |
| P2 | Sudoku nine-word state ring | One room scans and conditionally updates coincident row/column/box fields correctly | Nine-token scan cannot remain comfortably below the public tick envelope |
| P3 | Grade Book packed record ring | GET/SET/AVG/TOP component passes a 16-record adversarial oracle | Extraction/replacement controller erases the four-ring footprint gain |
| P4 | LLM rolling-head continuation | One complete tick path beats the physical-unrolling baseline on exact traces | Interpreter-boundary state or routing requires another large unrolling |
| P5 | Pathfinder four-word BFS | One flag round, including exact tie order and frames, passes adversarial mazes | Cross-word policy traffic dominates the claimed compact kernel |
| P6 | Subset Sum sharded search | Measured worst-case comparisons plus enumeration stay below 15M ticks | No comfortable tick margin after a 16-shard prototype |
| P7 | Plotter/Snake/TCP compact controllers | Per-problem component proof | Score frontier or implementation time loses to a higher-priority live candidate |

Only one architecture build should be promoted at a time. CP-SAT placement,
global squeezing, and component substitution begin after that build's
mandatory proof, not before it.
