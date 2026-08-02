# Task 20260802-chatgpt1-y-semantics

- Status: active
- Owner: chatgpt_1
- Reviewer/integrator: repository maintainer
- Branch: `agent/chatgpt-1-y-semantics`
- Base: current `main` at branch creation

## Outcome

Implement the official `Y` split instruction in the production Python simulator and make the default `fastsim.Machine` path execute `Y` programs correctly.

The semantics are the organizer-confirmed contract in `docs/language-reference-updates-2026-07-27.md` and the existing reference implementation in `src/littleman/split_probe.py`:

- copies are born left/right relative to the incoming heading and head away from `Y`;
- both inherit A, B and BP and act starting on the next tick;
- the right copy inherits the parent creation-order slot; the left copy is newest;
- wall birth is an immediate whole-program `wall` error;
- birth onto a man, same-cell arrival, swap-through, and movement onto a standing man kill the involved men without error;
- dead men are removed as obstacles;
- exceeding 65,536 live men is `split-limit`.

## Exclusive write set

- `src/littleman/sim.py`
- `src/littleman/fastsim.py`
- `tests/test_y_semantics.py`
- `reports/2026-08-02-chatgpt1-y-semantics.md`
- `coordination/status/chatgpt_1.md`
- `coordination/messages/chatgpt_1/20260802T*-20260802-chatgpt1-y-semantics-*.md`
- this task record

## Read-only dependencies

- `src/littleman/split_probe.py`
- `tests/test_split_probe.py`
- `docs/language-reference-updates-2026-07-27.md`
- `experiments/gpt-reverse-fresh/reverse_fresh_23.man`
- `data/small/problems/reverse-a-list.json`

## Acceptance checks

1. Directed production-simulator tests cover split geometry, register inheritance, next-tick activation and creation order.
2. Wall birth reports `wall`; cap overflow reports `split-limit`.
3. Birth conflicts, same-cell arrival, swap-through, and movement onto a standing man remove both participants without error.
4. `fastsim.Machine` no longer compiles `Y` as `bad-op`; until the flattened engine supports dynamic population it explicitly falls back to the production reference loop.
5. `reverse_fresh_23.man` passes all eight archived public cases at organizer-matching average 206.375 ticks through both `sim` and default `fastsim` entry points.
6. No contest-side mutation and no integration into `main` by chatgpt_1.
