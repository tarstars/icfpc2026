# chatgpt_2: final Sort hot-loop checkpoint

Date: 2026-07-27

## Assignment and baseline

`coordination/ASSIGNMENTS.md` is authoritative. chatgpt_2 owns Sort.

The accepted public baseline is:

```text
artifact: submissions/sort/tarstars_sort_08.man
box: 18x18
public ticks: [755, 617, 772, 544, 928, 2137, 5282]
average ticks: 1576.4285714285713
public score: 18^2 * 1576.4285714285713 = 510762.8571428571
rank threshold supplied by the coordinator: 1.026x
```

At the existing 18-square footprint, one rank requires average public ticks at
or below:

```text
1536.480089111668
```

So an in-place hot-loop rewrite needs roughly 40 average ticks, or 280 total
public ticks, before it is worth handing to the submission controller.

## Closed line: two-pump K-ring

The complete two-pump architecture is already preserved on main under:

```text
experiments/chatgpt_2-sort-kring/
reports/2026-07-27-chatgpt2-sort-kring.md
```

It is correct but structurally noncompetitive. Even an impossible zero-routing,
zero-splitter, zero-merger lower bound scores about 799622 versus the accepted
public 510763. This line is closed; further floorplanning cannot make those
components pay.

## Active line: accepted-pump room-content optimization

The accepted 18-square machine keeps the shrinking-ring selection-sort
algorithm and spends most of its variable cost walking the pump room. Its scan
loop has two relevant comparison paths:

```text
ordinary requeue:       about 10 cells
new-minimum replacement: about 12 cells
```

A working trace over the public workloads counted:

```text
positive/requeue:        250
negative/new minimum:    234
zero/equal:               62
```

These counts were captured before the final-main resynchronization. They are
preserved as working data, not release evidence, in:

```text
experiments/chatgpt_2-sort-hotloop/score_frontier.py
```

They must be reproduced by a checked-in tracer before any submission handoff.

## U-based branch frontier

An abstract path synthesis replacing the horizontal compare/turn segment with a
vertical `X - U` shape can reduce the new-minimum path by two cells while
leaving the ordinary path unchanged. Under the working branch counts, this is:

```text
234 branches * 2 ticks = 468 total public ticks saved
average ticks: 1509.5714285714284
18-square score: 489101.14285714284
factor: 1.0442888236964134x
reduction: 4.241051200724962%
```

That crosses the 1.026x rank threshold.

The current obstacle is positional pipe binding. The shortest negative branch
places its ring send on the room side that is nearer to the output pipe, so the
instruction silently binds to the wrong queue. A viable implementation must
change port assignment and the scan/pass layout together; changing the path
alone is invalid.

## Pass-handler frontier

The repeated pass handler also contains a five-cell blank ascent before the
`m s r M` sequence. This occurs once per remaining output value. It is a second
credible tick source, but a naive move is unsafe because:

- the same cells participate in first-pass entry;
- the lower rows are shared with the positive scan branch;
- moving `r` or `s` can change the nearest pipe;
- changing segment lengths can alter the relay/ring phase.

The next candidate search therefore keeps the 18-square box and jointly chooses:

1. scan comparison path;
2. pass-handler location;
3. ring and output port cells;
4. exact logical bindings of every `r` and `s`;
5. unchanged pipe lengths `[2, 2, 7, 17]`.

## Gate

Any retained candidate must satisfy, in order:

```text
generator byte equality and SHA
strict parse and server layout
pipe lengths unchanged; never shorten a pipe
public/directed/random local tests
scripts/subdb.py compare <candidate> sort-numbers
organizer WASM final gate
```

No candidate `.man` exists yet. No contest mutation was made.
