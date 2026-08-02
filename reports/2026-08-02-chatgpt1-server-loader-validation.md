# Server-compatible loader validation

Date: 2026-08-02  
Owner: chatgpt_1  
Task: `20260802-chatgpt1-server-loader-validation`

## Result

`src/littleman/server_compat.py` now exposes one parser-like entry point:

```python
machine = parse_server_compatible(text)
```

It performs the existing local parse once, then applies every preserved organizer-side layout rejection known to this repository:

1. every pipe has at least two cells;
2. an input room has at most one pipe running against its wall, including transit pipes that merely pass alongside it;
3. distinct rooms do not share wall cells.

`validate_layout` delegates to the same entry point, so the server-compatible judges and `scripts/preflight.py` inherit the minimum-pipe-length rule automatically. The general `sim.Machine.parse` remains unchanged: the repository also preserves divergences in the opposite direction, so organizer strictness belongs in this compatibility layer rather than in the general simulator.

The public signatures of `find_shared_walls`, `validate_io_pipe_counts`, `validate_layout`, `judge_case`, and `judge_problem` are unchanged. A focused `validate_pipe_lengths` function is also public for narrow callers.

## Preserved regression corpus

The strict entry point rejects all four locally parseable layouts named in the post-contest backlog:

| Artifact | Organizer-side reason reproduced locally |
| --- | --- |
| `submissions/reverse-a-list/reverse_02.man` | 3 one-cell pipes at `(1, 3)`, `(4, 3)`, `(10, 11)` |
| `submissions/reverse-a-list/reverse_03.man` | input room at `(8, 0)` has 2 pipes running against its wall |
| `submissions/sort/sort_05.man` | 1 one-cell pipe at `(1, 3)` |
| `submissions/triangle/triangle_03.man` | rooms 1 and 2 share wall cells `(5, 4)`, `(6, 4)`, `(7, 4)` |

Coordinates above are the simulator's zero-based coordinates. The preserved server responses independently record the latter two failures in `submissions/reverse-a-list/reverse_03-submit.json` and `submissions/triangle/alexey-triangle_03-submit.json`. The one-cell-pipe rule and its two failed candidates were already documented in `src/littleman/alexey_pipecheck.py`; that module's documentation is now synchronized with the consolidated gate.

The fixed successors remain accepted:

| Artifact | Parsed pipe lengths |
| --- | --- |
| `submissions/reverse-a-list/reverse_01.man` | `[2, 2, 2, 17]` |
| `submissions/sort/sort_06.man` | `[2, 3, 7, 17]` |
| `submissions/triangle/triangle_04.man` | `[2, 2]` |

## Tests

Changed and added tests:

- `tests/test_server_compat.py`
  - exercises both `parse_server_compatible` and `validate_layout` on all four rejected artifacts;
  - verifies the three fixed successors remain accepted;
  - retains the shared-wall coordinates and final-wall-step judge regression.
- `tests/test_server_compat_pipe_lengths.py`
  - pins the exact bad-pipe counts for `reverse_02` and `sort_05`;
  - verifies two-cell and longer pipes remain accepted.

Validation performed in this runtime:

```text
python3 -m py_compile server_compat.py test_server_compat.py \
    test_server_compat_pipe_lengths.py

PYTHONPATH=/tmp/lmcheck pytest -q \
    tests/test_server_compat.py -k 'not final_wall' \
    tests/test_server_compat_pipe_lengths.py

13 passed, 1 deselected in 0.04s
```

The focused harness used the current `sim.py` room and pipe discovery routines and the exact preserved `.man` texts. It exercised the logic on which these checks depend. The exact Git blob hashes of the locally compiled files matched the blobs published on the branch.

A full repository checkout and full pytest run were not possible because this runtime cannot resolve `github.com`; no GitHub Actions workflow ran for the branch. The existing final-wall-step test was therefore not re-executed here, but its code path is unchanged except that `validate_layout` now performs the additional pipe-length check first.

## Integration scope

Branch: `agent/chatgpt-1-server-loader-validation`

No contest API call or submission was made. chatgpt_1 did not integrate the code into `main`.

Operational note: while creating the isolated branch, a placeholder task file was accidentally committed to `main` as `a76ad66`, then immediately deleted in `5e5b60d`. The resulting `main` tree is unchanged, but the two net-zero commits remain in history; no force rewrite was attempted.
