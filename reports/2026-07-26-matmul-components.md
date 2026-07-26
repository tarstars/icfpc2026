# Matrix Multiply component fold

Date: 2026-07-26

## Baseline

The frozen source is `submissions/matmul/matmul_06.man`, SHA-256
`db5dfb9a81fc8e5cec900d37b50e7c52446e619b5dce6e5f7bfdf23d778d07d8`.
It is 115×142 and passed 20/20 live at score `20,042,330,424`.

The machine contains one 109×124 controller, nine small relay rooms, I, O,
and 19 pipes. The controller has nine incoming and nine outgoing pipes.
Every one attaches to its bottom wall, so deleting controller rows preserves
the row term of every nearest-pipe distance.

## Transformation

`build_matmul_controller_folded()` applies the same component method that
improved Grade Book:

1. freeze the controller's 9-in/9-out contract;
2. fold its compiled staircase while keeping instruction columns fixed;
3. remove only rows that contain no operation or horizontal structure;
4. re-route the A ring away from the input-room wall;
5. trim that ring from 334 cells to its proven maximum capacity of 256.

The full staircase fold frees 48 controller rows. A rows-only squeeze removes
44 global rows. The A-ring repair is required by the strict server-layout
gate: the inherited 334-cell route ran alongside I and was counted as a
second input connection. The new route stays clear and does not change any
public tick count.

## Results

| metric | `matmul_06` | `matmul_07` | change |
|---|---:|---:|---:|
| dimensions | 115×142 | 115×98 | max −19.01% |
| footprint | 20,164 | 13,225 | −34.41% |
| average public ticks | 810,886.000 | 516,025.714 | −36.36% |
| local score | 16,350,705,304.0 | 6,824,440,071.4 | **−58.26%** |
| public cases | 7/7 | 7/7 | unchanged |

The candidate passes six component tests, including exact controller
pipe-role preservation, deterministic reproduction, strict layout checking,
ring capacities 256/268, all public cases, and six deterministic adversarial
matrix shapes including 16×16×16.

Preflight reports 12 rooms, 19 pipes, 10 men, valid layout, and 7/7. The
artifact SHA-256 is
`9deb5b44092e1099e09de12ca4fee7ab71811e6187392e76482ef070c01e51d3`.

The mandatory freshness snapshot at 2026-07-26T15:02:05Z found the current
team result at 20/20, score `20,042,330,424`, rank 48 before `matmul_07`.
