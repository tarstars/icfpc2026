# handoff: two-pump Sort is correct, but this component family cannot win

- From: chatgpt_2
- To: claude
- CC: chatgpt_1, alexey, codex
- Created UTC: `2026-07-27T09:05:00Z`
- Task: `20260727-chatgpt2-sort-two-pump-assembly`
- Branch: `agent/chatgpt_2-sort-v2`
- Payload head: `c59f5bdd36c4c89b243e0a0e96d7c85db3552906`
- Requires acknowledgement: no

## Exact result

```text
artifact: experiments/chatgpt_2-sort-kring/chatgpt2_sort_00.man
SHA-256: 8bc7495136458e5caf9bf8f46ded00df22c2d6de84558e879ba8967cbd83fdbe
Git blob: e97bf061b9baad9798b866adf4a8f4df6a357743
size: 154x153, 19,567 bytes
structure: 9 rooms / 12 pipes / 7 men
```

The complete splitter -> two pumps -> merger protocol passes all seven public
cases and 300/300 deterministic random multi-round differential workloads.
Public score is 61,187,280, so it is not a submission candidate.

## Why floorplanning cannot rescue it

The exact pumps were measured in a minimal rig. Pump-only public average is
691.7142857 ticks. Even deleting the prefixer and granting free splitter and
merger execution plus free routing, the remaining fixed rectangles occupy
1,110 cells, requiring at least a 34-square:

```text
34^2 * 691.7142857 = 799,621.714
accepted tarstars_sort_08 public = 510,762.857
```

This is a lower bound, not a projection. The current concrete component family
must be replaced before another parallel-Sort layout search is justified.

## Replay

```text
PYTHONPATH=src python -m pytest -q -o addopts='' \
  tests/test_chatgpt2_sort_kring.py
# 3 passed
```

Generator equality, SHA identity, server layout, minimum pipe lengths, public
cases, random reset/capacity workloads and `git diff --check` pass.

No contest mutation occurred. The implementation write set is released. The
artifact is useful as a semantic oracle for future splitter/pump/merger
component synthesis, but must not be submitted.
