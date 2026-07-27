# LLM stack validation and Rust executor next step

Status: validation-only final-window update. No solution source or contest
state changed.

## Full Python stack

Command:

```text
uv run pytest -q tests/test_llm*.py
```

Result:

```text
1622 passed in 621.31s (0:10:21)
```

The glob currently covers 46 test modules. This proves the checked-in
LLM/LLLM Python component stack is internally green at `f384127`; it does not
prove the unfinished whole-machine LLM gates listed in
`20260726T051000Z-zero-first-requirements-audit.md`.

`.pytest_cache` retained one obsolete failure key for
`test_unchanged_halted_round_still_emits_a_delta_delimiter`, which no longer
exists. Its renamed current replacement was checked directly:

```text
uv run pytest -q \
  tests/test_llm_components.py::test_halted_followup_round_still_emits_a_delta_delimiter
1 passed in 0.11s
```

## Performance conclusion

The measured 621.31-second broad run makes a high-performance executor a
valuable parallel enabler for the next goal. It must not replace completion
of the zero-score LLM baseline.

Recommended narrow contract:

1. retain Python parsing and the reference simulator as the semantic oracle;
2. define a stable dense machine/state IR;
3. execute that IR in Rust;
4. expose both a PyO3/maturin binding for the existing `uv`/pytest workflow
   and a standalone binary suitable for local batches or YT;
5. differential-test exact status, ticks, outputs, frames, registers, pipe
   occupancy/blocking, signed-64 wrapping, movement, and collision behavior;
6. include Split (`Y`) and its death/cap semantics before using the executor
   to validate `Y`-dependent machines.

Initial acceptance target: reduce this same broad wall time from 621 seconds
to below 60 seconds, with 30 seconds as the stretch target, while producing
zero differential mismatches.

Per the active goal's final-30-minute rule, no Rust implementation was started
in this window. The appropriate parallel split for the next goal is one agent
on the missing LLM action coordinator and one on the Rust executor/IR.
