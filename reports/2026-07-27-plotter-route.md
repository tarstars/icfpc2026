# Plotter paired-room route squeeze

Date: 2026-07-27

## Result

`plotter_07` is a placement-only successor to the counted `plotter_06`.
It translates the stacked ETEST/EUPD pair two columns west into the last safe
column of slack and redraws two external feed-forward pipes.

| metric | `plotter_06` | `plotter_07` | change |
|---|---:|---:|---:|
| occupied dimensions | 155x145 | 152x145 | max -1.94% |
| footprint | 24,025 | 23,104 | -3.834% |
| average public ticks | 47,476.667 | 47,315.667 | -0.339% |
| local score | 1,140,626,916.67 | 1,093,181,162.67 | **-4.160%** |

The exact candidate is
`submissions/plotter/plotter_07.man`, SHA-256
`8e85252c84b2f89771642b823ecf38d9b49eb8a1eb6c2a09a4c687daedbb07e8`,
25,230 bytes.

## Contract

All fourteen room rectangles are byte-identical to `plotter_06`. The
ETEST/EUPD rooms, their two three-cell links, and the hot 193-cell state ring
move rigidly. All 181 `s`/`r` instruction resolutions and every pipe-port
offset are unchanged.

Only two feed-forward pipe lengths change:

- SETUP to ETEST: 111 to 109;
- EUPD to ADDRESS: 295 to 251.

The three display-driver paths remain exactly 3, 19, and 56 cells. The
strict parser still finds 14 rooms, 18 pipes, and 12 men.

## Validation

`scripts/preflight.py` reports `READY TO SUBMIT`, 6/6 public cases, and exact
ticks `[23854, 56010, 1719, 36052, 80755, 85504]`.

The focused Plotter suite passes 15/15, including:

- deterministic generator and exact source/candidate hashes;
- byte-identical rooms, ports, bindings, and resolution maps;
- strict server-layout and pipe-length checks;
- all public cases;
- a 32-round deterministic frame oracle covering degenerate, axial,
  diagonal, reversed, and random segments.

## Freshness

Immediately before the candidate commit, the branch was updated to
`origin/main@38b2573`. The live standings snapshot at
`2026-07-26T22:58:10.402Z` showed `wheezards` rank 59 at score
`1,668,891,820`; rank 58 was `1,621,735,833.6`, requiring a 2.826%
improvement. Scaling the live score by the measured local ratio predicts
approximately `1,599,472,249`, enough for one place if hidden-case behavior
tracks the public ratio.

## Live result

Submission `c4e94257-0709-4eb4-bd4c-894721ec2294` passed 20/20 at 152x145,
average 69,221 ticks, and score `1,599,281,984`. This is a 4.170% reduction
from the counted `1,668,891,820`, closely matching the public-case
projection. The terminal response is preserved in
`submissions/plotter/plotter_07-submit.json`.
