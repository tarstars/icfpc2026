# 20260727-chatgpt2-sort-hotloop

- Status: active
- Record owner: chatgpt_2
- Work owner: chatgpt_2
- Reviewer / integrator / submission controller: claude
- Problem: `sort-numbers`
- Branch: `agent/chatgpt_2-sort-hotloop`
- Base main commit: `1767a740a5b8e9536844f9901ea06c1b55b62366`
- Created UTC: `2026-07-27T09:10:00Z`
- Progress lease: 15 minutes without concrete pushed evidence

## Outcome

Produce a score-positive successor to accepted `tarstars_sort_08` by optimizing
the walk inside its existing rooms, with preference for a same-18-square tick
improvement and a stretch target of a verified 17-square machine.

## Exclusive write set

- `src/littleman/chatgpt2_sort_hotloop.py`
- `tests/test_chatgpt2_sort_hotloop.py`
- `experiments/chatgpt_2-sort-hotloop/`
- new immutable artifacts `submissions/sort/chatgpt2_sort_hotloop_*.man`
- `reports/2026-07-27-chatgpt2-sort-hotloop.md`
- this task, `coordination/status/chatgpt_2.md`, and
  `coordination/messages/chatgpt_2/`

## Shared read-only inputs

- `submissions/sort/tarstars_sort_08.man` and its generator/tests/report;
- Sort problem data and accepted submission evidence;
- parser, simulator, Canvas, `room_lab`, `room_shrink`, `room_compact`,
  `scripts/preflight.py`, and `scripts/wasm_judge.py`.

## Do not touch

- `src/littleman/sort_kring.py` and the released two-pump experiment;
- all Brackets and Reverse/chatgpt_1 paths;
- Claude's generic room/layout/optimizer implementation;
- existing immutable Sort artifacts, response JSON, catalogs;
- `main` and contest state.

## Score gate

Like-for-like organizer-WASM public baseline:

```text
tarstars_sort_08: 18x18, avgTicks 1576.428571, score 510762.857143
```

At the same footprint, a candidate must average below `1536.48` ticks to clear
the freshly measured 1.026x rank threshold. The internal target is at least a
5% public reduction for hidden-case margin. A 17-square candidate may tolerate
up to `1767.35` average ticks and still beat the accepted public score.

## Search

1. Trace the accepted machine and identify repeated routing segments.
2. Extract ordered operation sequences and binding roles per man.
3. Apply path-aware segment shortening / loop re-anchoring in isolated code;
   do not reorder operations or shorten pipes.
4. Preserve nearest-pipe binding and relative timing where observable.
5. Evaluate exact score after every viable checkpoint.

## Acceptance

- exact generator/artifact equality and SHA;
- parse, server layout, one input pipe, minimum two-cell pipes;
- no pipe length shortened;
- intended I/O binding roles preserved;
- all public and directed/random multi-round cases;
- organizer WASM 7/7 is mandatory before handoff;
- exact score below accepted public baseline, preferably by >=5%;
- no contest mutation by chatgpt_2.
