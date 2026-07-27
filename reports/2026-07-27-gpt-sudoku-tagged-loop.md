# Sudoku Auditor: tagged update loop

Date: 2026-07-27

Problem: `sudoku-validity`

Status: exact generated candidate, locally validated; not submitted by GPT.

## Result

The accepted `sudoku_05` architecture stores all row, column, and box masks in
one canonical 27-token ring. Its controller, however, contains three generated
copies of the same operation:

1. pop a skip count;
2. relay that many state tokens;
3. read one mask;
4. test and set the current value bit;
5. return the updated mask.

`experiments/gpt-sudoku-loop/sudoku_tagged_loop.man` represents this operation
once and loops over it three times.

| Metric | accepted `sudoku_05` | tagged loop | Change |
| --- | ---: | ---: | ---: |
| dimensions | 75×131 | **77×101** | max dimension −22.90% |
| footprint | 17,161 | **10,201** | **−40.56%** |
| public average ticks | 533,614.33 | **596,352.33** | +11.76% |
| local score | 9,157,355,574.33 | **6,083,390,152.33** | **−33.57%** |

The extra loop control makes execution 11.76% slower, but removing thirty rows
from the binding dimension wins decisively under the squared-footprint score.

The exact artifact is 7,746 bytes, 77×101, SHA-256:

```text
776348949535acf9ba500c2cf1b8cbc2d1df67cf5e6231674155ba494ba7143e
```

## Tagged protocol

The existing skip ring receives four counts that partition one canonical scan:

```text
row skip, column skip, box skip, tail skip
```

The first three stay nonnegative. The fourth is encoded as:

```text
box - 9 = -(tail_skip + 1)
```

which is always in `-9..-1`. The shared controller therefore dispatches on the
sign of the next skip token:

- zero: update the next mask immediately;
- positive: relay that many state tokens, then update the next mask;
- negative: decode `-tag-1`, relay the canonical tail, and finish the verdict.

No mask, bit, old-mask, flag, row, column, or box representation changes. The
state ring still begins each cell in exact `row0..8, column0..8, box0..8` order.

## Geometry and capacity

The same ring builder and relay rooms used by `sudoku_05` are retained. After
compiling the smaller controller:

- staircase folding frees 54 controller rows;
- whole-program squeeze removes 72 rows and 54 columns;
- the final machine has 11 rooms, 18 pipes, and 9 men;
- minimum pipe length is 2;
- the complete pipe-length multiset is byte-for-byte equal as a multiset to
  `sudoku_05`, including the 27-mask state-ring capacity;
- `littleman.server_compat.validate_layout` passes.

## Validation

The committed `verify_candidate.py` establishes:

- generator output equals the committed `.man` bytes;
- all six public cases pass at ticks
  `[1011332, 44854, 949606, 57340, 503658, 1011324]`;
- a full valid grid passes;
- 60 deterministic shuffled valid prefixes followed by forced row, column, or
  box duplicates pass;
- explicit index-zero and index-eight boundary workloads pass;
- 66/66 directed and randomized workloads pass in total;
- no pipe is shorter than two cells and the server-layout gate passes.

Run from the repository root:

```bash
PYTHONPATH=src python experiments/gpt-sudoku-loop/build_candidate.py /tmp/sudoku.man
cmp /tmp/sudoku.man experiments/gpt-sudoku-loop/sudoku_tagged_loop.man
PYTHONPATH=src python experiments/gpt-sudoku-loop/verify_candidate.py
```

## Live-score expectation and limitation

The current accepted `sudoku_05` server/local ratio is approximately 1.0145.
Applying that ratio only as a rough projection gives about **6.17B** for this
candidate, versus the current live **9.290B**. This is a projection, not a live
result.

GPT has no contest API credential path. Codex must fetch current Git and live
problem state, repeat risk-proportionate checks, choose an immutable promoted
name, and preserve the terminal response before any submission.

No contest mutation occurred in this task.
