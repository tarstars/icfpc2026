# codex_3 Grade Book v2 search checkpoint

- Date: 2026-07-27
- Agent: `codex_3`
- Task: `20260727-gradebook-extra-fold-search`
- Branch: `agent/codex_3-gradebook-v2`
- Base and current `main`: `b240cc2d67a125a31cc50c167283b7049de47210`
- Live baseline: `submissions/gradebook/codex3_gradebook_06.man`
- Live response: `submissions/gradebook/codex3_gradebook_06-submit.json`
- Live result: 20/20, 379x315, score `34,760,655,166.75`
- Submission ID: `c2a5a3e9-0341-4f67-9127-ce0c035eb21d`

## Saved work

The branch contains two deterministic follow-up searches starting from the
live `codex3_gradebook_06` artifact.

### 1. Extra staircase folds

`experiments/codex_3-gradebook-v2/search_extra_folds.py`

This beam-searches one additional staircase merge at a time inside the parser
and four subject engines. A candidate is rejected unless it preserves:

- occupied dimensions exactly at 379x315;
- all 16 parsed rooms;
- all 14 little men;
- all 31 pipes;
- the exact ordered pipe-length tuple from the live artifact;
- server-compatible layout rules;
- all seven public cases.

Finalists also run the first handoff's deterministic randomized stress cases
and all 256 ordered adjacent output-operation transitions. The script writes
`submissions/gradebook/codex3_gradebook_07.man` only after finding a strictly
better local public score that passes every local gate.

### 2. Shape search

`experiments/codex_3-gradebook-v2/search_shape.py`

This attacks the remaining 379x315 shape mismatch. It tries to vacate sparse
columns by sliding non-structural instructions along already-walked straight
runs, then asks `room_shrink.verify` to approve the shave. The gate rejects:

- any non-shrinking box;
- any lost or shortened pipe;
- any changed nearest-pipe binding;
- any changed room boundary contract;
- any public-case failure;
- any randomized or ordered-transition failure.

It writes the same numbered candidate path only after a verified improvement.
The searches are intended to be run serially; whichever creates the candidate
first owns that local result.

## Focused regression checks

`tests/test_codex3_gradebook_v2_search.py` freezes the live baseline at:

- 379x315 occupied dimensions;
- footprint `379**2`;
- 16 rooms;
- 31 pipes;
- 14 men;
- no one-cell pipe;
- server-compatible layout.

It also checks every available one-fold successor for exact structural and
pipe-capacity equality before any expensive judging.

## Exact commands

From a checkout of this branch:

```sh
uv run pytest -q tests/test_codex3_gradebook_v2_search.py

uv run python experiments/codex_3-gradebook-v2/search_extra_folds.py \
  --beam 12 --depth 8

# Run only if the fold search did not create candidate 07:
uv run python experiments/codex_3-gradebook-v2/search_shape.py
```

When either search creates `submissions/gradebook/codex3_gradebook_07.man`:

```sh
uv run python scripts/preflight.py \
  submissions/gradebook/codex3_gradebook_07.man gradebook

uv run python scripts/subdb.py compare \
  submissions/gradebook/codex3_gradebook_07.man gradebook

uv run python scripts/wasm_judge.py \
  submissions/gradebook/codex3_gradebook_07.man gradebook

sha256sum submissions/gradebook/codex3_gradebook_07.man
```

Grade Book is value-output based, so the organizers' WASM result remains the
final local authority. Claude must also perform the mandatory live freshness
read before committing or submitting a candidate.

## Validation status

This connector runtime cannot execute the repository, the organizer WASM, or
the contest API. Therefore:

- no `codex3_gradebook_07.man` is claimed to exist;
- no additional score improvement is claimed;
- no test command is represented as having run here;
- no contest mutation occurred.

The saved outcome is executable, deterministic search and validation tooling,
not a measured candidate. The branch is synchronized with current `main` and
contains only owner-specific task, status, message, experiment, test, and
report paths.
