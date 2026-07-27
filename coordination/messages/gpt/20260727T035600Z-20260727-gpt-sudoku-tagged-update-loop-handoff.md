# handoff: tagged-loop Sudoku candidate

- From: gpt
- To: codex
- CC: claude, alexey
- Created UTC: 2026-07-27T03:56:00Z
- Task: `20260727-gpt-sudoku-tagged-update-loop`
- Branch: `agent/gpt-sudoku-loop`
- Payload head: `3d2690f4ccd8564b07d3a7980553aa90a1f899de`
- Requires acknowledgement: yes

## Summary

The accepted single-ring Sudoku controller had three generated copies of one
skip/update body. The candidate encodes the fourth skip count as a negative tail
tag and loops one update body over the first three nonnegative counts.

Exact artifact:

```text
experiments/gpt-sudoku-loop/sudoku_tagged_loop.man
sha256 776348949535acf9ba500c2cf1b8cbc2d1df67cf5e6231674155ba494ba7143e
77×101
```

## Measured comparison

```text
accepted sudoku_05: 75×131, avg 533,614.33, local 9,157,355,574.33
candidate:          77×101, avg 596,352.33, local 6,083,390,152.33
local reduction: 33.5683%
```

The candidate is slower by 11.7572%, but footprint falls 40.5571% and the
binding dimension falls from 131 to 101.

## Validation performed

From the uploaded repository environment:

```text
generator byte equality: pass
public cases: 6/6
public ticks: [1011332, 44854, 949606, 57340, 503658, 1011324]
directed/random: 66/66
server layout: pass
rooms/pipes/men: 11/18/9
minimum pipe: 2
pipe-length multiset versus sudoku_05: identical
```

Directed coverage includes a full valid grid, 60 deterministic shuffled valid
prefixes with forced row/column/box duplicates, and explicit low/high index
boundaries.

Commands:

```bash
PYTHONPATH=src python experiments/gpt-sudoku-loop/build_candidate.py /tmp/sudoku.man
cmp /tmp/sudoku.man experiments/gpt-sudoku-loop/sudoku_tagged_loop.man
PYTHONPATH=src python experiments/gpt-sudoku-loop/verify_candidate.py
```

## Integration notes

The generator reuses the accepted parent generator at
`experiments/gpt-submission-candidates/sudoku_single_generator.py`; it does not
modify shared source. Promotion should copy exact bytes to a new immutable
submission name and add a release test/catalog entry.

GPT has no contest API credential path. Before a solution commit or submission,
Codex must fetch current main, query the exact Sudoku live result, reconcile
catalogue naming, rerun risk-proportionate checks, and preserve the terminal
response.

No contest mutation occurred.