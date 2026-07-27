# Progress: fine Subset Sum search baseline and first group wave

- From: gpt
- To: alexey
- CC: codex, claude
- Created UTC: `2026-07-26T18:39:00Z`
- Task: `20260726-gpt-subset-sum-fine-bisect`
- Branch: `agent/gpt-subset-bisect-fine`
- Requires acknowledgement: no

## Baseline

The regenerated original passes all seven public cases with the C fastsim
backend:

```text
case ticks: 6,640,497; 7,199,445; 6,718,443; 7,274,629;
            6,468,694; 7,263,957; 7,378,811
footprint: 13,293,316
local score: 92,947,769,417,488
wall time: 126.377 s
```

## Fine partition

The script defines exactly:

```text
32 balanced contiguous row groups over 655 deletable rows
64 balanced contiguous column groups over 3,040 deletable columns
```

The first four row groups all pass independently:

```text
row-000 7/7, 140.082 s
row-001 7/7, 138.811 s
row-002 7/7, 141.017 s
row-003 7/7, 139.343 s
```

Four workers remain active. Every completed group is atomically checkpointed in
`fine_group_results.json`; a host/process interruption can resume without
re-running completed groups. No candidate or submission path is touched.
