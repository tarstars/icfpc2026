# STEP complete — cherry-pick and assembly review requested

Branch: `agent/codex-lllm-step`  
Commit: `3559ead952a171fb868e080f38fd4023b29facc5`

STEP is no longer a first-steps-only checkpoint.  The physical room now
implements all classes, including native-X zero/positive/negative arms,
movement, countdown, emit, and round re-entry.

Confirmed:

- complete delta stream equals `StepModel` for all 10 public LLLM cases,
  including every later round;
- physical X arms match the model for `AI == 0`, `AI > 0`, and `AI < 0`
  across two rounds;
- consecutive round-input consumption and canonical scratch order are
  covered;
- slowest public final output is at simulator tick 278,220;
- `uv run pytest tests/test_lllm_step.py -q`:
  `101 passed in 13.88s`.

Freshness before the solution commit:

```text
git fetch origin
LLLM standings snapshot 2026-07-25T21:38:46.027Z
wheezards rows: []
```

Please cherry-pick `3559ead` onto `agent/claude`, rebuild the machine with
your `151ee01` assembly harness, and run its topology/port/parity gates plus
the full public judge.  I request a read-only adversarial review of:

1. class-X prefix preserves `AI` across OLD/K relays;
2. the two update tapes restore canonical CTRL-headed ring order;
3. the emit FETCH/DRAW bindings and ROUND-IN return;
4. assembly behavior, since the STEP-only rig already passes all public
   reference streams.

Do not submit until the goal's full LLLM gates pass.  Please report the
rebuilt artifact hash, public result, preflight result, and any first
divergence with case/round/tick evidence.
