# chatgpt_1 Brackets 22-square checkpoint

Date: 2026-07-27

Status: fixed-component placement, exact port assignment, and detailed routing
frontier exhausted; no 22x22 `.man` claimed.

## Synchronization and authority

`agent/chatgpt-1-solvers` was merged with the current `main` line before this
checkpoint. `coordination/ASSIGNMENTS.md` remains authoritative: chatgpt_1 owns
Brackets 22x22, and Claude owns all judging and platform submissions.

The previous chatgpt_1 Reverse artifact is already live through Claude:

```text
chatgpt1_reverse_09.man   17x17   20/20   score 62,568.5
```

chatgpt_1 made no contest API call.

## Saved artifacts

```text
experiments/chatgpt1-brackets-22/README.md
experiments/chatgpt1-brackets-22/macro_frontier.py
experiments/chatgpt1-brackets-22/macro_frontier.json
experiments/chatgpt1-brackets-22/exact_frontier.py
experiments/chatgpt1-brackets-22/exact_frontier.json
```

The immutable baseline component sizes are:

```text
CLOSE       22x7
CLASSIFY    16x6
OPEN        18x8
INPUT        3x3
OUTPUT       3x3
room area  412 / 484
parent pipe cells 53
```

## Correction to the first endpoint model

The first exact-frontier draft incorrectly applied the source-arrow rule to
destination endpoints. A source endpoint's arrow points away from its room and
therefore needs its outward neighbor free. A destination endpoint's arrow
points into its wall and may be approached sideways. That draft was retired;
`exact_frontier.py` now prints the corrected schema-2 certificate instead of
silently reproducing the bad rule.

The correction materially changes the intermediate count:

```text
big-room placements                         420
big-room exact-binding survivors            119
ordered I/O placements examined          33,576
full room-option survivors                3,176
all six pipes independently connected     1,884
```

## Joint port-and-routing result

Every one of the 1,884 independently connected placements was passed to a
joint binary MILP. Variables select one exact nearest-pipe-preserving port map
per room and one directed grid flow for each of the six logical pipes. Hard
constraints enforce:

- the accepted named `s`/`r`/`q` pipe roles;
- unique endpoint cells;
- correct source and destination arrow direction;
- one unit of flow for each logical pipe;
- vertex capacity one across all six paths.

Result:

```text
fixed-component 22x22 six-pipe witnesses: 0 / 1,884
```

Thus area and individual connectivity are not the blocker. With the five room
rectangles unchanged, the six directed paths cannot be made mutually
vertex-disjoint while retaining the accepted positional bindings.

## Component work and useful negative results

Several width-21 CLOSE sketches were evaluated with the calibrated local
Brackets simulator, which reproduces `gpt_brackets_17`'s exact public tick
vector.

1. Shifting the central arithmetic chains left broke the shared relay junction:
   the relay entered literal `4` instead of `M`. It was rejected immediately.
2. A path-aware variant compressed the empty-stack result using the invariant
   `B=1` at its branch and used `U` to combine the unclosed-position read with a
   turn. Its logical paths were promising, but exact port assignment forced the
   CLOSE output source onto the canvas boundary, where its first arrow could
   not leave. No full macro placement survived.
3. The output sockets are therefore a first-class interface constraint. A
   useful successor must keep all CLOSE result sends clustered so a bottom
   source port remains possible; simply moving one result arm to the left makes
   the room unplaceable even when its internal behavior is correct.

The next useful component families are a 21x7 CLOSE with clustered output
sockets, or a 21x8 shape variant that spends one extra row to fold the two
`p+1` result paths. Re-running rigid-room placement without such a variant is
now known duplicate work.

## Release gate

Any concrete successor must still run:

```bash
uv run python scripts/wasm_judge.py <candidate.man> brackets
uv run python scripts/subdb.py compare <candidate.man> brackets
```

No Brackets submission or candidate validity claim is made in this checkpoint.
