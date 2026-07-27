# Snake state-ring margin release

Date: 2026-07-26

## Live result

`snake_04` passed all 17 contest cases at 150×129:

- average ticks: `37,711.82352941176`;
- score: `848,516,029.4117646`;
- submission: `f634a515-9393-4642-99f5-2fe7d85a4a9e`;
- artifact: `submissions/snake/snake_04.man`;
- SHA-256: `7694030a224b158c9649010dbf87168e730e2a85e00baa05cdb994f97e59304b`.

The preceding `snake_03` had the same footprint and averaged
`37,997.23529411765` ticks, scoring `854,937,794.1176472`. The new route is
0.7512% faster live and crosses the previous next-rank threshold at
`851,432,110.2941177`. The next standings refresh moved the team from rank
29 to rank 28 and increased Snake points from 1.53333 to 1.55.

## Change

All eleven rooms, their instruction components, and every pipe binding are
unchanged. Only the longest restored state-ring route, TICKC → DRAW, changes:
it is shortened from 89 to 85 cells. The exact artifacts differ at six glyph
positions, all inside the old/new route union. Geometry remains 150×129 with
footprint 22,500.

The earlier `ring_capacity()` helper reports 207 → 203 cells, but its room
selector also counts a nine-cell display-token leg. The new
`state_ring_capacity()` measure follows only the six state-FIFO stations:

| Variant | State FIFO | 68-cell growth gate |
| --- | ---: | --- |
| accepted `snake_03` | 198 | pass |
| submitted `snake_04` | 194 | pass |
| rejected sweep point | 192 | tick-cap deadlock |

The release therefore leaves the two shorter restored routes untouched and
uses the smallest capacity that passed the retained oversized adversary.

## Validation

Commands:

```bash
uv run pytest -q -n 0 tests/test_snake_components.py \
  tests/test_snake_fast.py tests/test_snake_press.py tests/test_snake.py \
  tests/test_snake_margin.py
uv run --with ruff ruff check src/littleman/snake_margin.py \
  tests/test_snake_margin.py
uv run python scripts/preflight.py submissions/snake/snake_04.man snake
```

Evidence:

- 73 focused and inherited Snake tests passed; Ruff passed;
- all five public cases passed at exact ticks
  `[9872, 3996, 17052, 16581, 78693]`;
- local public score improved from 572,157,000 to 567,873,000;
- 60 retained/new random full-game checks passed against the frame oracle;
- 48- and 68-cell maximal-growth games passed;
- server-compatible layout, pipe-length, component, and binding gates passed;
- generator output is deterministic and byte-identical to the artifact.

An independent read-only reviewer confirmed artifact parity, route-only
change scope, room and binding identity, public/random/adversarial behavior,
and the corrected six-leg capacity calculation.

## Freshness and release

Immediately before submission, `origin/main` had no commits absent from the
work branch. The exact API baseline refresh confirmed `snake_03` still
counted 17/17 at score `854,937,794.1176472`. The unfrozen standings snapshot
at `2026-07-26T21:20:05.480Z` placed the team at rank 29 and showed the next
threshold at `851,432,110.2941177`.

The exact terminal response is preserved in
`submissions/snake/snake_04-submit.json`.
The unfrozen standings refresh at `2026-07-26T21:24:05.924Z` records the new
score at rank 28 among 63 teams.
