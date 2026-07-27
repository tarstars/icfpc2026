# GPT Brackets 23-square solver result

Date: 2026-07-27

Status: exact 23x23 candidate preserved and independently replayed; ready for
Claude's freshness and release gate.

## Result

```text
artifact       submissions/brackets/gpt_brackets_18.man
experiment     experiments/gpt-solvers-usage/gpt_brackets_18.man
generator      littleman.gpt_brackets_23:build_gpt_brackets_18
sha256         50e85872d47e81c90f1205f0ae4c0341b62626630b1a1efb66552d357425320c
bytes          535
box            23x23
footprint      529
rooms/pipes/men 5/6/3
pipe lengths   [4, 14, 2, 8, 4, 2]
```

Public replay under `littleman.server_compat`:

```text
case ticks [256, 78, 114, 78, 158, 382, 140, 140, 2088]
average    381.55555555555554
score      max(23,23)^2 * average
           = 201842.88888888888
```

Comparison:

```text
brackets_11 public local score 276615.0       -> -27.031112%
gpt_brackets_17               213248.0       ->  -5.348285%
```

## Solver pipeline

The current component library contains three nontrivial room variants:

- CLASSIFY: outer 6x16;
- CLOSE: outer 7x22, with shared terminal result tail;
- OPEN: outer 8x18, with end-of-stream folded through the ordinary pair sender.

A finite mixed-integer model then chooses:

1. the vertical order and exact origins of the large rooms;
2. same-wall source/destination port cells satisfying every nearest-pipe role;
3. six directed vertex-disjoint grid routes;
4. source arrows pointing away from their source walls;
5. the minimum total route length.

The winning order is:

```text
CLOSE     origin (0,0)
CLASSIFY  origin (9,6)
OPEN      origin (15,0)
OUTPUT    origin (17,20)
INPUT     origin (20,18)
```

The selected routes are:

```text
CLASSIFY -> CLOSE     [(8,6), (7,6)]
CLOSE -> CLASSIFY     [(7,13), (8,13), (8,14), (8,15)]
CLOSE -> OUTPUT       [(7,18), (8,18)..(8,22), (9,22)..(16,22)]
OPEN -> CLOSE         [(14,3), (13,3)..(7,3)]
OPEN -> CLASSIFY      [(14,5), (13,5), (12,5), (11,5)]
INPUT -> OPEN         [(19,18), (18,18)]
```

## Why the parser remains part of the solver

The first geometrically valid multi-commodity solution was not a machine. Its
I-to-OPEN terminal also touched the output room, so the parser constructed a
seventh one-cell `OUTPUT -> OPEN` pipe.

That candidate passed the abstract flow constraints and failed the real
language. The search therefore promotes the following rendered checks to hard
acceptance gates:

- exactly five rooms, six pipes, and three initial men;
- exact six named source/destination pairs;
- minimum two-cell pipes;
- no shared walls and exactly one input-room pipe;
- exact named `s/r/q` binding signature.

With those gates in the loop, the next solver placement produced the preserved
candidate.

## Validation

- exact generator/artifact equality and pinned SHA-256;
- all nine public cases;
- all 9,331 strings over `()[]{}` of lengths zero through five;
- 71 directed boundary strings;
- 10,000 deterministic random strings of lengths zero through 64, seed
  `2026072708`;
- zero additional failures;
- exhaustive maximum 230 ticks;
- directed/random maximum 2,120 ticks, mean 125.862377;
- parser topology, exact binding signature, `server_compat`, pipe length, and
  input adjacency gates.

The server-compatible judge is required because CLOSE intentionally uses the
already server-proven final-wall-after-send rule.

## Next frontier

The 22x22 frontier is component-bound: CLOSE itself occupies 22 columns outside
its interior and leaves no horizontal routing clearance in a 22-square. A
successor therefore needs at least one more CLOSE implementation variant or a
joint CLOSE/CLASSIFY fusion. Moving ports alone cannot cross that bound.

## Requested action

Claude should fetch `agent/gpt-solvers-usage`, replay:

```bash
PYTHONPATH=src uv run pytest -q -n 0 tests/test_gpt_brackets_23.py
PYTHONPATH=src uv run python scripts/preflight.py \
  submissions/brackets/gpt_brackets_18.man brackets
```

Then refresh the exact live Brackets result and submit only the pinned SHA if it
still improves the counted submission. GPT made no contest API call.
