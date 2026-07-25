# Subset Sum: Meet-in-the-Middle Systolic Sort

## Outcome

`subset_sum_00` is the first accepted Subset Sum candidate. The exact
9,743,784-byte artifact passed all seven public cases locally and all 20 live
cases. Live submission `edda50dc-411e-49b6-83eb-0e895d4c1f7e` scored
91,769,596,778,389.8 at 3,646×3,029 and an average 6,903,439.05 ticks.

The unfrozen standings snapshot at `2026-07-25T00:56:57.514Z` placed
`wheezards` 20th of 26 rows with 1.2083333333 points.

## Architecture

The generator splits the at-most-20 values into two ten-slot halves and pads
missing tail slots with zero. Two pipelines enumerate all 1,024 subset
sum/mask pairs for their half. A chosen original index is represented by a
more-significant one bit than every later index, so the numerically greatest
combined mask is exactly the contest's lexicographically first index list.

Two 1,024-stage systolic insertion pipelines sort the pair streams:

- half A by descending `(sum, mask)`;
- half B by ascending sum and descending mask within an equal-sum group.

A two-pointer merge compares the current pair sum with the target. Matching
pairs flow into a reducer that retains the greatest combined mask. The final
selector reverses that mask into input order, emits the selection count, and
then emits the selected original values. Padded zero slots always clear their
mask bits and therefore cannot become false selections.

## Explored designs

The initial direct enumeration design required too many radix passes: both the
30-pass binary form and a reduced 20-pass form reached the 15,000,000-tick cap
on a single-element public case. A base-four loader reduced pass count but did
not give a sufficiently compact and fast final design.

The first complete systolic geometry serialized to 15,124,306 UTF-8 bytes.
The API client rejected it locally because it exceeded the documented
10,000,000-byte limit, so no external submission was created. Reordering
parser ports and moving generator, merge, reducer, selector, and shared-value
corridors reduced the exact source to 9,743,784 bytes without changing the
program logic.

## Local validation

The exact compact artifact produced these public-case results under the
15,000,000-tick cap:

| Case | Ticks |
|---|---:|
| tiny warm up | 6,640,497 |
| multiple solutions, lex pin | 7,199,445 |
| no solution | 6,718,443 |
| single-element subset | 7,274,629 |
| last-index-required | 6,468,694 |
| duplicate values | 7,263,957 |
| near-total-sum, 20 values | 7,378,811 |

The average is 6,992,068 ticks. With footprint 13,293,316, the local score is
92,947,769,417,488.

Focused tests also validate the lexicographic Python oracle, both pair-sort
orders, padded-mask clearing, and a seeded merge/reducer/selector integration
case with multiple valid candidates. The simulator's compact pipe-run index
is checked against a cell-by-cell reference model over 10,000 deterministic
random operations.

`uv run pytest -q` passed all 127 repository tests in 53.83 seconds after the
final geometry was generated. The final source reproduces byte-for-byte from
`build_subset_sum()`:

```text
SHA-256  cd1000a2b5b944e6905e991022116f5b6a6daf7729c4a93bd13f72a683c65d77
bytes    9743784
rooms    2121
pipes    2164
men      2119
```

The `.man` artifact is tracked through the path-specific Git LFS rule in
`.gitattributes`.

## Live result

The exact locally validated artifact was submitted once. The terminal API
response reported `done`, 20/20 cases passed, no error, area² 13,293,316,
average 6,903,439.05 ticks, and score 91,769,596,778,389.8. The complete
response is preserved in
`submissions/subset-sum/subset_sum_00-submit.json`.
