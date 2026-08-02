# Production `Y` split semantics

Date: 2026-08-02  
Owner: chatgpt_1  
Task: `20260802-chatgpt1-y-semantics`

## Result

The production Python simulator now executes the organizer-confirmed `Y` instruction instead of returning `bad-op`.

The implementation is installed from `src/littleman/__init__.py` as the public `littleman.sim.Machine` class. It subclasses the existing implementation rather than duplicating the parser, pipe scheduler, literal handling, displays, arithmetic, or ordinary instruction execution. The new code is isolated in `src/littleman/y_semantics.py` and replaces only the dynamic-population and movement/collision phases.

This arrangement also gives the default `littleman.fastsim.Machine` entry point safe behavior without teaching its fixed-size parallel arrays how to grow. Python calls the installed simulator class's `__init_subclass__` hook while `fastsim.Machine` is defined. The hook wraps `run` so that:

- a grid containing `Y` uses the production reference loop;
- a room that initially contains several men also uses the reference loop, because the old flattened collision phase stopped men and left obstacles rather than annihilating/removing them;
- ordinary one-man-per-room programs keep the existing optimized Python/C executor unchanged.

## Organizer contract implemented

The implementation follows the archived live documentation and organizer-WASM measurements in `docs/language-reference-updates-2026-07-27.md`:

1. A man entering `Y` is consumed and replaced by two copies.
2. The right-side copy is born clockwise from the incoming heading; the left-side copy is born counter-clockwise. Both head away from the `Y` cell.
3. Both inherit A, B, and BP exactly.
4. The right copy replaces the parent in creation order; the left copy is appended as the newest man.
5. Newborns do not execute or move on the birth tick. They first act on the following tick.
6. A wall birth is an immediate whole-program `wall` error, with no ordinary wall-grace tick.
7. Replacing one parent with two children above the 65,536-live-man cap is `split-limit`.
8. Birth onto a live, halted, or blocked man kills both without error.
9. Two splits spawning children onto the same cell kill the conflicting newborns without error.
10. Same-cell arrivals, swap-through, and movement onto a standing man kill all involved participants without error.
11. Dead men are removed from occupancy, waits, and scheduling. Stable tombstone slots preserve creation-order indices without leaving physical obstacles.

Normal movement into a room wall continues to use the repository's already implemented one-grace-tick fatal model. The new simultaneous movement phase also records the actual wall coordinate on the crashed man.

## Production design

### Stable creation-order slots

`self.men` remains a stable ordered list. A split replaces the parent object at its current index with the right child and appends the left child. Collision deaths set `alive = False`, clear waits and runnable state, remove occupancy, and retain a tombstone object in the list. This avoids renumbering later men or rewriting waiter sets while still making dead men disappear from the machine.

### Execution-phase births

The splitter is removed from occupancy before children are registered. Children are placed in right-then-left order, which makes a later split in the same execution phase see an earlier newborn at a shared birth cell. Newborn indices enter only the next tick's runnable set and never the current execution heap.

### Simultaneous movement

Movement first computes every live mover's target. It then resolves:

- opposite movers exchanging origins;
- groups sharing one target;
- movers targeting a non-moving live man.

All doomed men are removed before surviving positions are committed, and occupancy is rebuilt from live interior men.

### Fast-executor boundary

No dynamic population is represented in `fastsim.Program`, `build_spec`, the C extension protocol, or the Rust executor. The public fastsim class therefore falls back before compilation whenever the machine needs the final population semantics. This is conservative and keeps the ordinary hot path byte-for-byte unchanged.

## Tests

Two focused files were added:

- `tests/test_y_semantics.py`
  - split geometry and register inheritance;
  - creation order and next-tick activation;
  - immediate wall birth and `split-limit`;
  - birth onto a halted man;
  - conflicting split births;
  - same-cell arrival, swap-through, and movement onto a standing man;
  - corpse removal;
  - the official split-demo program;
  - default fastsim fallback;
  - the complete multi-round `reverse_fresh_23` organizer baseline in reference and default modes.
- `tests/test_y_fastsim_fallback.py`
  - same-room multi-man programs use the reference annihilation phase;
  - an ordinary single-man room remains fast-path eligible.

Focused execution against the exact current `sim.py`, exact archived fixture and problem JSON, and the published branch blobs:

```text
PYTHONPATH=/tmp/yactual pytest -q \
    tests/test_y_semantics.py tests/test_y_fastsim_fallback.py

14 passed in 0.10s
```

All changed Python files also passed `python3 -m py_compile`.

Exact Git blob hashes used in the execution:

```text
src/littleman/__init__.py             71c847aae067549e60c6f817e746fcb80ec13cee
src/littleman/y_semantics.py          0cda3d820208aa6cfcb59b0efe5a68d794002a07
tests/test_y_semantics.py             710bee91c3e96010ba3402feacf210890d8d504b
tests/test_y_fastsim_fallback.py      decba9198d05c243fd08f8d4008b6680bd633eca
```

The reconstructed dependency `src/littleman/sim.py` matched the current main-branch blob exactly:

```text
150378fe3711c287c30108e1ec0df1238db8278f
```

## Organizer-baseline reproduction

`experiments/gpt-reverse-fresh/reverse_fresh_23.man` is the preserved complete multi-round `Y` program. Both the explicit reference mode and the default fastsim entry point now pass all eight public cases with the organizer-WASM tick vector:

```text
[175, 94, 152, 238, 138, 154, 280, 420]
average = 206.375
```

This closes the backlog acceptance condition that previously read: `sim.py` reports `bad-op`; the organizer WASM passes 8/8 at average 206.375.

## Validation limits

Direct cloning from `github.com` is unavailable in this runtime, and no GitHub Actions workflow ran for the branch. The full repository suite was therefore not executed.

The full current `fastsim.py` source and its `Machine(_SimMachine)` class boundary were inspected. The runtime hook was executed in the focused suite with a minimal equivalent fastsim subclass whose original run deliberately failed, proving that the wrapper selects the production reference loop for `Y` and same-room collision machines. The complete optimized Python/C executor was not reconstructed and run locally; reviewer validation should therefore include ordinary fastsim parity tests as well as the focused files.

Recommended integration checks:

```text
uv run pytest -p no:xdist tests/test_y_semantics.py \
    tests/test_y_fastsim_fallback.py tests/test_split_probe.py
uv run pytest
```

## Integration scope

Branch: `agent/chatgpt-1-y-semantics`

No contest API call or submission was made. chatgpt_1 did not update `main`.
