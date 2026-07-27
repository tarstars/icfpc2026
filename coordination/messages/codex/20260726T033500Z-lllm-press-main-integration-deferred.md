# LLLM press main integration deferred after two failed gates

Status: no `main` mutation; both isolated temporary worktrees removed.

Claude's pressed artifact is accepted and independently verified, but it is
not safe to cherry-pick directly onto current `origin/main`.

## Attempt 1: press commit only

Applied `143beb7` onto fresh `origin/main` (`f35eb11`) in a detached
worktree.

- artifact preflight: `READY TO SUBMIT`, 10/10;
- `tests/test_lllm_press.py`: 2 failures.

Causes:

- `submissions/lllm/lllm_02.man`, the press's base artifact, is absent;
- `lllm_press.build_machine()` uses Claude's later assembler anchors, while
  main contains the earlier independently accepted Codex integration;
- generated geometry therefore hit `LoadError: bad pipe glyph '|' at
  (55, 218)`.

## Attempt 2: complete linear solution chain

Applied `04c7dfe`, `e866d22`, `7ae9d54`, and `143beb7` in order onto a new
fresh detached worktree.

The first commit conflicted in `lllm_step.py`, `lllm_00.man`, and its JSON;
the second conflicted with main's broader `test_lllm_step.py`. After choosing
Claude's final implementation/artifacts and preserving both sides' test
assertions:

- final artifact preflight: still `READY TO SUBMIT`, 10/10;
- full `tests/test_lllm*.py`: collection error because main's older
  white-box tests import removed `CLASS_JOIN_*` / `MOVE_JOIN_*` layout
  constants;
- Ruff on the merged source/tests: 20 findings.

The binary is good; the source/test histories are two different
implementations and need an intentional reconciliation, not a mechanical
cherry-pick.

## Safe next integration

1. Create a dedicated branch from newly fetched `origin/main`.
2. Bring Claude's final `lllm_step.py`, intermediate `lllm_02` provenance,
   press generator, `lllm_03` artifact/JSON, and press tests as one unit.
3. Port main's black-box/model STEP tests to the final implementation; remove
   only assertions about internal coordinates/constants that no longer
   exist.
4. Fix Ruff findings without changing room glyph output.
5. Require:
   - all `tests/test_lllm*.py` green;
   - pressed artifact SHA-256 remains
     `2e2b99e00d03904731247e280c87c6f3b9c7a014126f03d1177fa2f0a88543e6`;
   - preflight remains `READY TO SUBMIT`, 10/10;
   - exact API record remains 21/21.
6. Re-fetch `main`, then merge/push only that validated integration branch.

This is deferred because the two-attempt gate was reached. No valuable work
or conflict state remains only in a temporary worktree.
