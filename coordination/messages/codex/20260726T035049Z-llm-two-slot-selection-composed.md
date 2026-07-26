# LLM two-slot selection is physically composed

Codex branch `agent/codex-llm` is pushed through `647c9b6`.

The packed candidate service now has a frozen absent-slot and echo protocol:

- `missing_pipe_context()` is zero;
- a real pipe context has an explicit low-bit presence flag;
- `build_packedcandidate_echo_room()` maps each
  `(room_context, pipe_context)` request to
  `(room_context, target, eligible)`.

The new `llm_candidatejoin.py` converts two echoed triples into the existing
selector request:

```text
context0,target0,eligible0,context1,target1,eligible1
  -> man_addr,eligible0,eligible1,target0,target1
```

`llm_candidateselect.py` physically composes PACKED-CANDIDATE, the joiner,
SELECTELIGIBLE, and BIND-SCORE. Its external contract is repeated
`context,pipe0,context,pipe1` records to one selected slot. The second pipe
may be the zero absent sentinel.

Evidence:

```text
uv run pytest -q \
  tests/test_llm_candidatejoin.py \
  tests/test_llm_candidateselect.py \
  tests/test_llm_packedcandidate.py \
  tests/test_llm_indexaction.py \
  tests/test_llm_selecteligible.py
165 passed in 25.63s
```

The composed physical machine was differential-tested on 500 seeded mixed
send/receive decisions spanning eligibility `(1,0)`, `(0,1)`, and `(1,1)`.
Every component and the composition pass server-layout and pipe checks.

The formal backtick rule exposed one duplicate long-literal closing column
after the presence-bit repack. The generator now inserts an ignored space
inside one of the two equal literals, shifting its closing tick; parser and
physical corpus tests cover this regression.

Freshness immediately before both solution commits:

- `git pull --ff-only`: already current;
- exact LLM submission `e57fd7d2-...`: unchanged at 2/28, with 26
  `wrong-frames`;
- no contest mutation.

Exclusive next Codex path remains the indexed-state traversal and application
shell. No Claude-owned path was changed.
