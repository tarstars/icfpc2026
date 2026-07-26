# LLM indexed coordinator: packed candidate checkpoint

Codex branch `agent/codex-llm` is pushed through `3acf62b`.

Two coordinator boundaries are now executable:

1. `llm_indexaction.py` fixes the one-room and whole-indexed action contract;
   sequential room stages are exactly equivalent to the interleaved
   PIPEACTION oracle.
2. `llm_packedcandidate.py` compresses each nine-word selection request to
   `(room_context, pipe_context)` and physically emits
   `(target, eligible)`. It is self-contained; receive ownership is checked
   inline, so the traversal shell needs no BORDERCHECK fan-out.

Evidence:

```text
uv run pytest -q \
  tests/test_llm_packedcandidate.py tests/test_llm_indexaction.py
154 passed in 7.54s
```

The physical service was differential-tested on 2,000 seeded send/receive
requests, including directed source mismatch and destination-boundary cases.
It passes server-layout and pipe checks. Room geometry is 234x84; the
standalone rig is 234x111.

Freshness before each solution commit:

- `git pull --ff-only`: already current;
- exact LLM submission `e57fd7d2-...`: unchanged at 2/28, all 26 failures
  `wrong-frames`;
- no contest mutation.

Exclusive next Codex path: build the indexed traversal that extracts one
room context plus each global pipe context and drives this packed service.
Claude's independent incremental LLM paths remain untouched.
