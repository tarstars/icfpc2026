# inventory: artifacts of the four stopped workers, for pickup or review

- From: claude
- To: codex
- Created UTC: 2026-07-26T11:45:00Z
- Requires acknowledgement: no
- Supplements: 20260726T112500Z-pause-checkpoint.md

Everything below is committed on `agent/claude` (HEAD 4c415cd or later).

## 1. SCAN v3 (LLM front-end) — resumable
- Files: `src/littleman/llm_scan3.py`, `tests/test_llm_scan3.py`,
  handoff `docs/architecture/claude_24_scan3_handoff.md` (62 tests green).
- Verified: Python model byte-exact vs `llm_lockstep.machine_stream` on
  61/61 corpora; S2 packer room 3/3 in sim; P1 ingest+emit through a
  312-slot memory subsystem 2/2 at 194k ticks.
- Remaining: P1 phases 2/3 (TODO-stubbed with the plan in the
  `_p1_rooms_walls` docstring). Successor entry point is in the handoff.

## 2. STEP3 (LLM lockstep interpreter) — model DONE, room just begun
- Files: `src/littleman/llm_step3.py`, `tests/test_llm_step3.py`,
  handoff `docs/architecture/claude_25_step3_handoff.md` (27 tests).
- Verified: lockstep model phases A+B+C byte-exact vs
  `llm_lockstep.from_stream` on 10 LLLM + 14 LLM public (ALL pipe cases)
  + **340-program fuzz, 0 divergences**. Room transcription is only a
  classify-chain emitter skeleton; full geometry is specified in the
  handoff.
- **Directly useful to your llm lane now**: the model is a second
  independent oracle for your wrong-frame debugging, finer-grained than
  llm.py because it exposes per-tick man/pipe state as plain ints.

## 3. reverse-a-list pass 2 — SHIPPED before the pause
- `reverse_05.man` live: 20/20 at **117,214** (was 193,481), submission
  `20a3f425-2ab2-4b41-aae8-503706a2810a`. Generator
  `src/littleman/reverse_faster.py`, 13 tests, handoff
  `docs/architecture/claude_27_reverse2_handoff.md` (tick breakdown,
  next lever, traps).

## 4. brackets pass 2 — died without artifacts; the knowledge to save
The worker was stopped before writing anything. What exists is the
PASS-1 builder's measured headroom notes, recorded here because they
otherwise lived only in my session:
- `brackets_03` (live, 26/26 at 943,438): CLOSE's closer arm is the
  critical loop, ~50 ticks of which **~20 is walking a detour
  rectangle** — folding it is a contained inner-loop edit, est. 1.3-1.5x.
- The bigger lever — killing the state-relay laps through both rooms per
  character — **requires a third live register** and is a real redesign;
  two agents died attempting brackets redesigns, so treat it as
  out-of-budget unless the contest is otherwise done.
- Generator `src/littleman/brackets_fast.py`; its constant-time classify
  (`t = c>>5` via `M 5 W }`, opener/closer from low bits in BP via
  `b ] x`, end-of-input from `q`) is reusable anywhere characters are
  classified.
