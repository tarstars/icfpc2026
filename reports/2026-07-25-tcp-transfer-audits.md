# TCP Lesson Transfer Audits

Date: 2026-07-25

This report records the bounded follow-up experiments from
`docs/tcp-derived-optimization-actions.md`. It distinguishes a retained
candidate from a plausible redesign so that unmeasured ideas do not become
contest facts.

## Results at a glance

| Target | Experiment | Result |
|---|---|---|
| Grade Book | Count acknowledgement/result routes; test tagged-route premise | Rejected as a standalone change: it removes routes but does not reduce the 454-cell binding width and serializes currently parallel result delivery |
| Matrix Multiply | Count collector/ack routes in `matmul_02` | Already consolidated: one controller, no worker acknowledgement chain, no result collector |
| Reverse | Carry phase and fold the feedback route inside a smaller square | Retained `reverse_02`: 15×15, local score 261,393.75, 12.15% below `reverse_01` |
| Brackets | Phase/final-wall audit | No cheap phase debt or final-wall saving; the 92-cell state return and side-by-side rooms bind width |
| Plotter | Phase/final-wall audit | No final-wall saving; height is the sequential room/display chain, so the next lever is a multi-column layout |
| Sudoku | Two-row worker-module rectangle packing | Projected 306×284 envelope (M=306), but routing is not implemented |
| Subset Sum | Relocate parser and second generation/sorter bank in-memory | Projected M=3029 and 30.98% footprint reduction, but the first mechanical route set collides at `(2029,2824)` |

No candidate in this report was submitted.

## Grade Book and Matrix: tagged collector audit

Parsing the exact current Grade Book generator gives 16 rooms, 14 men, and
30 pipes at 454×450. The pipe inventory is:

- one input pipe and four broadcast command pipes;
- 16 private state/data ring pipes (four per worker);
- four result pipes into the collector;
- four acknowledgement pipes (three worker-to-worker and one return);
- one collector-to-output pipe.

The direct result routes total 164 pipe cells; the collector output adds five.
The serialized acknowledgement route totals 1,406 pipe cells:

```text
161 + 157 + 157 + 931 = 1406
```

A negative acknowledgement tag could carry a nonnegative GET/AVG/TOP result
through the acknowledgement chain, eliminating the four direct result routes.
That change is not retained by itself:

1. the current 454-cell width already binds the score, while the result
   collector is in the 450-cell height;
2. removing the collector tail lowers height but leaves M=454;
3. direct results currently travel in parallel with the completion token,
   whereas putting them on the acknowledgement chain delays output.

It becomes worth revisiting only as part of a worker/parser width compaction
that also removes a full acknowledgement traversal.

The compact Matrix program parses as 12 rooms, 10 men, and 19 pipes. It has a
single controller, nine small relay processes, no worker acknowledgement
chain, no multi-source result collector, and one final output route. The
tagged-collector proposal is therefore already subsumed by its architecture.

## Reverse: retained 15×15 candidate

`reverse_01` already carries ring size in B and uses blocking receive, so it
has no `q` corridor or avoidable realignment lap. Its remaining opportunity
was geometric.

`reverse_02` keeps both active room programs byte-identical and changes only
placement and four pipes:

- the pump and relay move one column left;
- the relay moves one row up;
- pump-to-relay becomes a one-cell pipe;
- the 17-cell return FIFO wraps above the relay rather than below it.

| Variant | Dimensions | Footprint | Public average ticks | Local score |
|---|---:|---:|---:|---:|
| `reverse_01` | 16×16 | 256 | 1,162.25 | 297,536.00 |
| `reverse_02` | 15×15 | 225 | 1,161.75 | 261,393.75 |

The score reduction is 12.147%. `reverse_02` passes all eight public cases,
ten directed worst-shape workloads, 250 seeded randomized workloads, the
17-cell capacity assertion, and the server-layout check. Its source,
generator, and exact metrics are recorded in
`submissions/reverse-a-list/alexey-variants.json`.

## Brackets and Plotter: phase and final-wall audit

Strict local and server-final-wall semantics produce identical ticks for all
public cases:

| Program | Strict/server tick delta |
|---|---:|
| `brackets_00` | 0 |
| `plotter_01` | 0 |
| `reverse_02` | 0 |

There is therefore no final-wall saving to take.

Brackets occupies 50×39. Its three active rooms are 20×19, 22×6, and 32×10;
the longest pipe is the 92-cell CLOSE-to-OPEN state return that reaches column
49. The two-word state must visit OPEN and CLOSE in alternating order because
the unaddressed station is the relay for the addressed station. Removing that
trip is an algorithm replacement, not phase-debt accounting. A vertical room
packing can lower width, but its command and state-return lanes compete for
the same one-row gaps; no source candidate is retained from this audit.

Plotter `plotter_01` occupies 388×441. Its height is the sequential setup,
error, address, router, display-driver, and display chain; it has 14 rooms and
18 pipes. Its state is already held in explicit rings and there is no `q`
settling corridor. A further reduction needs a multi-column fold of the
sequential chain, with pipe-proximity audits at each receive. That is separate
from final-wall or phase-debt optimization.

## Sudoku: bounded two-row packing

The current 446×200 width is the horizontal broadcaster plus three worker
modules. Parsed module envelopes (worker and its four private relays) are:

```text
row worker:     138×98
column worker:  138×98
box worker:     138×112
```

Placing the two 98-row modules side by side and the 112-row module below,
with the current eight-cell inter-module gap, gives a 284×218 worker region.
Keeping the observed 45-row header and 43-row aggregator/output tail gives a
conservative 284×306 whole-program envelope:

```text
45 + 98 + 8 + 112 + 43 = 306
2*138 + 8 = 284
```

M would fall from 446 to 306, and footprint from 198,916 to 93,636
(52.93% lower) before tick effects. This is a placement bound, not a working
program: the broadcaster and three bottom-entry command routes must be
regenerated, and nearest-pipe resolution must be re-audited.

## Subset Sum: executable packing probe

The exact artifact's active x-range is 400–4045 (3,646 cells), while height
is 3,029. Its two generation/sorter banks occupy approximately x=500–1033
and x=3200–3718, leaving a 2,166-cell empty interval between their active
rooms.

An in-memory generator probe moved only the parser and second bank:

```text
parser_left: 3500 -> 2000
b_left:      3200 -> 1100
counter:     3400 -> 1300
```

The rendered probe was 8,655,389 bytes and had footprint 9,174,841
(`3029²`), 30.98% below the current 13,293,316. Parsing then failed at a
specific route collision:

```text
LoadError: bad pipe glyph '-' at (2029, 2824)
```

This is a useful positive bound and a negative implementation result. The
large-room packing is feasible in dimensions, but coordinate moves cannot be
accepted without regenerating the B-to-merge and parser routes. No 15M-tick
simulation was launched for an unparsable source.
