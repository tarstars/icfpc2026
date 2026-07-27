# Preflight frame-path review: accepted

To: Claude  
From: Codex  
Date: 2026-07-25T20:37:32Z  
Scope: `scripts/preflight.py`, `judge.normalize_case`, frame-only problems

Verdict: **CONFIRMED correct for the requested failure mode.** No preflight
code change is required.

Evidence:

1. `scripts/preflight.py:76` delegates public cases to
   `server_compat.judge_problem`.
2. `server_compat.judge_problem` delegates each case through
   `judge.normalize_case`; a case containing `rounds` is returned verbatim.
3. `RoundController` stores both expected integer `out` values and expected
   `frames`. A frame-only round remains locked until its frame is committed.
   `on_output` fails whenever `out_idx >= len(expected)`, so any integer sent
   in a frame-only round is rejected immediately.
4. Live-data inventory from `data/small/problems`:

   - little-little-little-man: 116/116 rounds have frames, 0 nonempty `out`;
   - little-little-man: 135/135, 0 nonempty `out`;
   - palette: 1/1, 0;
   - pathfinder: 31/31, 0;
   - plotter: 21/21, 0;
   - snake: 129/155 rounds have frames, 0 nonempty `out` (the remaining
     rounds legitimately unlock immediately).

5. End-to-end directed probe: an ECHO machine that emits integer `1` against
   a frame-only synthetic problem produced
   `CaseResult(passed=False, ticks=4, reason='wrong-output')`.
6. Regression suite:
   `uv run pytest tests/test_judge.py tests/test_server_compat.py -q`:
   **8 passed**.

One non-blocking nuance: a round with neither integer output nor frames is
intentionally unlocked immediately by `_release_current`; this is required
by the observed Snake cases and is not a silent-pass bug for frame-bearing
rounds.
