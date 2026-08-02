# Task 20260802-chatgpt1-y-semantics

- Status: complete; handoff ready
- Owner: chatgpt_1
- Reviewer/integrator: repository maintainer
- Branch: `agent/chatgpt-1-y-semantics`
- Base: `main` at `5e5b60d812f12d95023432699f187f2f9cf0fe8e`
- Completed UTC: 2026-08-02T12:50:00Z

## Outcome

Implement the official `Y` split instruction in the production Python simulator and make the default `fastsim.Machine` entry point execute `Y` programs correctly.

The runtime implementation is installed from `src/littleman/__init__.py` as the public `littleman.sim.Machine` subclass in `src/littleman/y_semantics.py`. It preserves the existing parser, pipes, literals, displays, arithmetic, and ordinary instructions while replacing the dynamic-population and collision phases.

The semantics are the organizer-confirmed contract in `docs/language-reference-updates-2026-07-27.md` and the existing read-only reference implementation in `src/littleman/split_probe.py`:

- copies are born left/right relative to the incoming heading and head away from `Y`;
- both inherit A, B and BP and act starting on the next tick;
- the right copy inherits the parent creation-order slot; the left copy is newest;
- wall birth is an immediate whole-program `wall` error;
- birth onto a man, same-cell arrival, swap-through, and movement onto a standing man kill the involved men without error;
- dead men are removed as obstacles while stable tombstone slots preserve creation order;
- exceeding 65,536 live men is `split-limit`.

## Exclusive write set used

- `src/littleman/__init__.py`
- `src/littleman/y_semantics.py`
- `tests/test_y_semantics.py`
- `tests/test_y_fastsim_fallback.py`
- `reports/2026-08-02-chatgpt1-y-semantics.md`
- `coordination/status/chatgpt_1.md`
- `coordination/messages/chatgpt_1/20260802T*-20260802-chatgpt1-y-semantics-*.md`
- this task record

`src/littleman/sim.py` and `src/littleman/fastsim.py` remained read-only. The installed subclass is the public production simulator at runtime; `fastsim.Machine` is wrapped at class creation and falls back before compiling any machine that needs dynamic population or final same-room collision semantics.

## Read-only dependencies

- `src/littleman/sim.py`
- `src/littleman/fastsim.py`
- `src/littleman/split_probe.py`
- `tests/test_split_probe.py`
- `docs/language-reference-updates-2026-07-27.md`
- `experiments/gpt-reverse-fresh/reverse_fresh_23.man`
- `data/small/problems/reverse-a-list.json`

## Acceptance results

1. PASS — directed production-simulator tests cover split geometry, register inheritance, next-tick activation and creation order.
2. PASS — wall birth reports `wall`; cap overflow reports `split-limit`.
3. PASS — birth conflicts, same-cell arrival, swap-through, and movement onto a standing man remove participants without error; dead men leave occupancy.
4. PASS — default `fastsim.Machine` falls back to the production reference loop for `Y` and same-room multi-man machines instead of compiling `Y` as `OP_BAD`; ordinary independent one-man rooms remain fast-path eligible.
5. PASS — `reverse_fresh_23.man` passes all eight archived public cases in reference and default modes with exact ticks `[175, 94, 152, 238, 138, 154, 280, 420]`, average `206.375`.
6. PASS — no contest-side mutation and no integration into `main` by chatgpt_1.

Focused validation: `14 passed in 0.10s`; exact changed files compiled and matched their branch blob hashes. Full repository pytest and the complete optimized executor remain reviewer checks; see the report.
