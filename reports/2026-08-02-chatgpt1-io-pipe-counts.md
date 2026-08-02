# Correct input-room pipe counting

Date: 2026-08-02  
Owner: chatgpt_1  
Task: `20260802-chatgpt1-io-pipe-counts`

## Result

`server_compat.validate_io_pipe_counts` now counts actual outward pipe starts immediately outside an input-room border. It no longer treats every parsed pipe body cell beside the wall as another connection.

This task is stacked on `agent/chatgpt-1-server-loader-validation`; the corrected check is therefore also used by `parse_server_compatible` and `validate_layout`.

## Root cause

The organizer's pipe-start rule is local geometry:

- take a border cell;
- step one cell outward from that side;
- the outside cell is a pipe start only when it is an arrowhead pointing in that same outward direction.

The local parser cannot be used as the source of truth for this count. It discovers rooms in reading order and marks traced pipe cells globally as `used`. An arrowhead beside a later input room can already belong to a pipe traced from an earlier room and disappear from the input room's attributed pipe list.

That is exactly the preserved `reverse_03` failure. Its input room spans zero-based rows 8..10 and columns 0..2. The cells `(7, 1)` and `(7, 2)` are both `^`, immediately above the top border and pointing outward. The organizer reports more than one outgoing input pipe; the corrected check reports those exact two starts.

The previous compatibility heuristic overcorrected by counting every cell of every parsed pipe whenever that cell had a wall cell as a Manhattan neighbour. The accepted `matmul_05` and `matmul_06` layouts place several `|` and `-` body cells beside the input room, but have only one outward start: the `^` above the top-wall centre. Both artifacts loaded on the organizer engine and passed 7/7 public and 20/20 live cases, as recorded in `submissions/matmul/alexey-variants.json`.

## Implementation

`src/littleman/server_compat.py` adds the private `_outward_pipe_starts(machine, room)` geometry scan. It checks the four sides directly against `ARROWS`, `UP`, `DOWN`, `LEFT`, and `RIGHT`, independently of `machine.pipes` ownership.

`_validate_io_pipe_counts` now rejects only when an input room has more than one such start. The diagnostic includes the room corner and all start coordinates.

The check remains deliberately input-only. The preserved organizer error names the input room, and earlier attempts to generalize an adjacency rule to output rooms falsely rejected the live, organizer-accepted `tcp_06` machine.

## Regression coverage

`tests/test_server_compat_io_pipes.py` now:

- retains the corpus scan over artifacts with successful preserved submission records;
- explicitly accepts `matmul_05.man` and `matmul_06.man`, whose aggregate live evidence is stored in the variants catalog rather than per-file response records;
- requires `reverse_03.man` to report two starts at `(7, 1)` and `(7, 2)`;
- confirms the rule is reached through `validate_layout`.

`tests/test_server_compat.py` updates the consolidated loader regression to expect the corrected `outward pipe starts` diagnostic.

## Validation performed

The exact published `server_compat.py` was copied from the branch, compiled, and hashed:

```text
python3 -m py_compile /tmp/server_compat_check.py
git hash-object /tmp/server_compat_check.py
8348e23d85da062640a6b1f8bf932619250dad78
```

The hash matches the branch blob. The exact modified test files also compiled and matched their branch blobs:

```text
test_server_compat_io_pipes.py  8f4415da2e66151bc0b03c98e02719fba42c4c5b
test_server_compat.py           3e6d6209864e99ac6a84d2a96dd7daf6e7112f81
```

A focused geometry execution used the full preserved `reverse_03` text and the exact input-room neighbourhood extracted from both matmul artifacts:

```text
reverse_03 rejected at starts (7,1),(7,2); matmul neighborhood accepted
```

The exact modified pytest module then ran against that focused harness:

```text
4 passed, 1 skipped in 0.05s
```

The skip is the dynamic accepted-submission corpus, which is empty in the focused temporary tree. The real repository test will populate it from all preserved submission records and will exercise the full `matmul_05`/`matmul_06` artifacts explicitly.

A full checkout and full repository pytest remain unavailable in this runtime because direct access to `github.com` cannot resolve. Reviewer commands:

```text
uv run pytest -p no:xdist tests/test_server_compat_io_pipes.py \
    tests/test_server_compat.py tests/test_server_compat_pipe_lengths.py
uv run pytest
```

## Integration

Branch: `agent/chatgpt-1-io-pipe-counts`  
Stacked dependency: integrate `agent/chatgpt-1-server-loader-validation` first, or review the combined stacked diff.

No contest API call or submission was made. chatgpt_1 did not update `main`.
