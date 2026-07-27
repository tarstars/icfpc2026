# codex_3 Grade Book reverse-ack experiment

Date: 2026-07-27

## Scope

This branch contains a self-contained experimental generator for a new Grade
Book layout. It does not modify shared solver or simulator code.

The candidate idea is:

1. reverse the physical order of the four subject workers while preserving the
   logical `1 -> 2 -> 3 -> 4` acknowledgement chain;
2. return the final acknowledgement beside the parser rather than from the far
   right edge;
3. make the result collector broadcast both to `O` and to a dedicated parser
   confirmation pipe, so the next output-producing operation cannot overtake a
   previous result;
4. retain the already judge-selected staircase fold prefixes, mirrored for the
   reversed worker order.

Files:

- `experiments/codex_3-gradebook/build.py`
- `experiments/codex_3-gradebook/stress.py`
- `tests/test_codex3_gradebook_rank_step.py`

The current `main` still has `src/littleman/gradebook.py` at blob
`699608b38cc4516fde774e60450f995eda2ae6fe`, the same source version against
which this experiment was written.

## Validation status

This connector runtime has repository write access but no local checkout,
GitHub CLI, organizer WASM runtime, or contest credentials. Therefore none of
the numerical assertions encoded in the experimental test have been
independently executed in this session. They are **targets to verify**, not
reported measurements.

Before any integration or contest submission, the reviewer must run:

```sh
uv run python experiments/codex_3-gradebook/build.py
uv run pytest -q tests/test_codex3_gradebook_rank_step.py
uv run python experiments/codex_3-gradebook/stress.py
uv run python scripts/subdb.py compare \
  submissions/gradebook/codex3_gradebook_06.man gradebook
```

Because Grade Book is value-output based, the organizers' WASM comparison is
the authoritative final gate. Preserve the generated `.man` and its SHA-256
only after those checks pass.

## Handoff policy

No contest mutation was performed. The branch is intentionally submitted as a
draft experimental contribution. Claude remains the integration and submission
controller and should reject, repair, or submit the generated candidate based
on reproduced measurements rather than the embedded targets.