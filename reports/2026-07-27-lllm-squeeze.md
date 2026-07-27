# LLLM 04 blank-corridor squeeze

Date: 2026-07-27

## Candidate

`lllm_04` is an exact mechanical successor to live `lllm_03`. It deletes
globally blank row 310 and columns 74, 75, 76, and 78 (zero-based). The
deleted columns shorten two pipes by four cells each; every instruction and
every pipe-resolution decision is preserved.

| Property | `lllm_03` | `lllm_04` |
|---|---:|---:|
| Server dimensions | 307×312 | 303×311 |
| Footprint | 97,344 | 96,721 |
| Public average ticks | 220,854.7 | 212,578.6 |
| Public local score | 21,498,879,916.8 | 20,560,814,770.6 |

The measured local score reduction is 4.36332%. Scaling the live
`lllm_03` score by that ratio projects 21,219,359,062, below the current
rank-14 threshold 21,448,719,506 by about 1.07%.

- artifact: `submissions/lllm/lllm_04.man`
- generator: `src/littleman/lllm_squeeze.py:build_lllm_squeeze`
- SHA-256:
  `92c9ac64c2c1e7a2550a0e717e0e27e40dd10947eb2c2570a0958d512724f218`
- bytes: 78,602
- topology: 13 rooms, 18 pipes, 11 men

## Search and proof

The bounded audit tested each mechanically deletable row and column
independently, then tested corridor groups with a 500,000-tick fail-fast cap.
The chosen four-column group was the best green group. The eight-column
group at columns 23–30 and the union of the first four groups failed 0/10,
confirming that individually safe deletions cannot be combined blindly.

The release test translates all 628 operation coordinates through the five
deletions and proves the complete IR pipe-resolution map is byte-for-byte
unchanged. Strict parsing finds the same topology; server-layout and
pipe checks pass. The public cases pass at ticks:

`[198093, 122842, 340523, 180233, 232864, 177443, 134416, 142101, 226687, 370584]`.

Commands:

```bash
uv run pytest -q -n 0 tests/test_lllm_*.py
uv run python scripts/preflight.py \
  submissions/lllm/lllm_04.man little-little-little-man
uv run --with ruff ruff check src/littleman/lllm_squeeze.py \
  tests/test_lllm_squeeze.py experiments/codex-lllm-squeeze-audit.py
```

At the pre-commit freshness check, `lllm_03` remained live 21/21 at score
22,187,469,586.285713 and rank 15 in the unfrozen
`2026-07-27T00:46:10.398Z` standings snapshot.

## Live result

Submission `ec7af0d5-0d43-41c3-a1e0-07c448c7efbe` passed all 21 private
cases at 303×311, average 218,921.52380952382 ticks, and score
21,174,308,704.380955. This is a 4.56637% improvement over `lllm_03` and
274,410,801.90 below the pre-submit rank-14 threshold. The exact response is
preserved in `submissions/lllm/lllm_04-submit.json`.
