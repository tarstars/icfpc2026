# Snake component-preserving compaction

Date: 2026-07-26

## Result

`snake_03` preserves every named logical component from `snake_02` and
changes only assembled geometry. It removes globally empty rows and columns,
then restores the three ring legs whose shorter buffers failed the established
68-cell maximal-growth test.

| Metric | `snake_02` | `snake_03` | Change |
| --- | ---: | ---: | ---: |
| occupied dimensions | 154×154 | 150×129 | max side −2.60% |
| footprint | 23,716 | 22,500 | −5.13% |
| public average ticks | 25,852.0 | 25,429.2 | −1.64% |
| public local score | 613,106,032 | 572,157,000 | −6.68% |
| ring capacity | 208 | 207 | −1 cell |

The exact artifact is `submissions/snake/snake_03.man`, SHA-256
`1832842a722cfb942da9db70354287fd75a2ca7667304eb3e0380840fa85b360`.
Submission `6086b11f-c948-4366-8aae-b0011994ae56` passed all 17 live
cases at 150×129, average 37,997.2353 ticks, and score
`854,937,794.1176472`. This is a 6.6653% reduction from the prior live
`915,991,438.3529412`.

## Component contracts

Snake already exposes its rooms as IN, DRAW, TICKA, TICKB, TICKC, the display
block, and I/O components. `tests/test_snake_components.py` adds two
assembly-level contracts:

1. each room's non-empty instruction matrix is identical after normalizing
   away empty local rows and columns;
2. every receive/send operation resolves to a pipe with the same source and
   destination room indices in reading order.

These complement the existing per-room tests in `tests/test_snake.py`, the
pressed-layout tests, and the lap-reduced machine tests.

## Rejected first attempt

A raw 25-row/6-column squeeze produced a 150×129 machine and passed all five
public cases, but shortened the ring from 208 to 175 cells. It passed the
48-cell growth case and then stalled at the 5,000,000-tick cap on the retained
68-cell case. Aggregate `MIN_RING_CELLS=160` was therefore not a sufficient
contract.

The accepted generator restores the affected legs individually:

| Ring leg | squeezed | restored |
| --- | ---: | ---: |
| DRAW → TOKENSPLIT | 22 | 26 |
| TOKENSPLIT → IN | 68 | 74 |
| TICKC → DRAW | 67 | 89 |

The routes remain inside the 150-column bound. Total ring capacity becomes
207 cells, and both 48- and 68-cell maximal-growth games pass.

## Validation

- `uv run pytest -q -n 0 tests/test_snake_components.py
  tests/test_snake_fast.py tests/test_snake_press.py tests/test_snake.py`:
  66 passed.
- `uv run python scripts/preflight.py submissions/snake/snake_03.man snake`:
  READY TO SUBMIT, 5/5 public cases.
- Ruff check and format checks passed for the new source and tests.
- `git diff --check` passed.
- The exact terminal submission response is preserved in
  `submissions/snake/snake_03-submit.json`; it reports 17/17, no error,
  and no load error.

Immediately before committing, `origin/main` and this branch had zero
left/right commits. The authenticated standings snapshot at
`2026-07-26T15:34:05.655Z` showed the current Wheezards result at 17/17,
score `915,991,438.3529412`, rank 24.
