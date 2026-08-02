# Handoff: production `Y` split semantics

- Task: `20260802-chatgpt1-y-semantics`
- Sender: chatgpt_1
- Timestamp UTC: 2026-08-02T12:51:00Z
- Branch: `agent/chatgpt-1-y-semantics`
- Handoff checkpoint: `1dae45a16ca991ebf1e3967434c52f45494997ce`
- Base: `main` at `5e5b60d812f12d95023432699f187f2f9cf0fe8e`

## Diff scope

- `src/littleman/__init__.py`
  - installs the post-release population semantics before executors import `sim.Machine`.
- `src/littleman/y_semantics.py`
  - exposes the installed class as `littleman.sim.Machine`;
  - implements `Y`, stable creation-order slots, register inheritance, next-tick newborn activation, immediate wall birth, `split-limit`, birth conflicts, simultaneous same-cell/swap/standing-man deaths, and corpse removal;
  - wraps `fastsim.Machine.run` at class creation so `Y` and same-room multi-man machines use the production reference loop, while ordinary independent one-man rooms keep the existing optimized path.
- `tests/test_y_semantics.py`
  - directed lifecycle/collision tests, official demo, default-entry fallback, and exact multi-round Reverse baseline.
- `tests/test_y_fastsim_fallback.py`
  - explicit fast-executor routing tests for final same-room collision semantics.
- `reports/2026-08-02-chatgpt1-y-semantics.md`
  - design, evidence, exact hashes, validation, and limitations.

The large existing `sim.py` and `fastsim.py` files are unchanged. Their public runtime classes are affected through the package initializer and subclass hook. This keeps all existing parser, pipe, literal, display, arithmetic, ordinary-execution, and optimized-executor code as the single source of truth.

## Organizer contract covered

- right/left births relative to incoming heading, both heading away;
- A/B/BP inheritance;
- right child takes parent slot, left child is newest;
- children first act on the following tick;
- wall birth is immediate `wall`, with no normal grace tick;
- more than 65,536 live men is `split-limit`;
- birth onto a man, conflicting split births, same-cell arrivals, swap-through, and movement onto standing men annihilate participants without error;
- dead participants leave scheduling, wait maps, and occupancy.

## Validation

The exact published blobs were reconstructed with the exact current `sim.py` and archived fixtures. Hashes:

```text
src/littleman/__init__.py             71c847aae067549e60c6f817e746fcb80ec13cee
src/littleman/y_semantics.py          0cda3d820208aa6cfcb59b0efe5a68d794002a07
tests/test_y_semantics.py             710bee91c3e96010ba3402feacf210890d8d504b
tests/test_y_fastsim_fallback.py      decba9198d05c243fd08f8d4008b6680bd633eca
current main `src/littleman/sim.py`   150378fe3711c287c30108e1ec0df1238db8278f
```

Focused command:

```text
PYTHONPATH=/tmp/yactual pytest -q \
    tests/test_y_semantics.py tests/test_y_fastsim_fallback.py

14 passed in 0.10s
```

All four changed Python files also passed `python3 -m py_compile`.

`experiments/gpt-reverse-fresh/reverse_fresh_23.man` passed all eight archived public cases through both explicit reference mode and the default fastsim entry point:

```text
[175, 94, 152, 238, 138, 154, 280, 420]
average = 206.375
```

This exactly matches the organizer-WASM evidence preserved in `reports/2026-07-27-gpt-reverse-fresh-baseline.md`.

## Reviewer checks / limitations

Direct cloning from `github.com` is unavailable in this runtime, and no GitHub Actions run exists for the branch. The complete repository suite was not run.

The current full `fastsim.py` source and its `Machine(_SimMachine)` class boundary were inspected. The hook/fallback was executed using a minimal equivalent subclass with an intentionally failing original fast run, proving that the installed wrapper selects the reference loop. The complete optimized Python/C executor was not reconstructed and executed locally.

Before integration run:

```text
uv run pytest -p no:xdist tests/test_y_semantics.py \
    tests/test_y_fastsim_fallback.py tests/test_split_probe.py
uv run pytest
```

Pay particular attention to ordinary fastsim parity/performance tests; the intended invariant is that one-man-per-room programs never take the new fallback.

## Integration

The branch is based on current `main` and was 0 commits behind at the last comparison. Review and integrate as one focused unit through the maintainer workflow.

No contest API call or submission occurred. chatgpt_1 did not update `main`. The task write set is released.
