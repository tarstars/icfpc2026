# Matrix Multiply Program Variants

Checked-in `.man` files are immutable candidates. New algorithms or geometry
optimizations get a new `matmul_NN.man` file and a corresponding
`variants.json` entry; older candidates are never overwritten.

`matmul_00.man` is the first correctness baseline. It broadcasts matrix data
to 16 parallel column workers and passes all seven archived public cases, but
its 1,982-cell width makes its footprint expensive.

`matmul_01.man` replaces the worker fleet with one controller and nested FIFO
rings for A, B, the current factor, and K partial sums. It also passes all
seven public cases, including 16×16×16 below the 5,000,000-tick cap. Its local
footprint-tick score is 25.01 times smaller than `matmul_00`.

`matmul_02.man` is a geometry-only successor to `matmul_01`. The controller
and algorithm are unchanged; A becomes an outer rectangular pipe, B folds
inside it, and output uses a side corridor. Its occupied bounds are 183×180
and its local score is 2.41 times smaller than `matmul_01` (60.25 times smaller
than `matmul_00`). It passed all 20 live cases as submission
`c2e95f37-585d-41b2-8f71-a255345fa784`.

`matmul_07.man` starts from the later 115×142 `matmul_06` geometry. It folds
the controller as a separately tested component, removes the resulting empty
rows, and gives the 256-value A ring a strict input-room-safe route. It is
115×98, passes public and deterministic 16×16×16 gates, and improves local
score by 58.26% over `matmul_06`.

`matmul_08.man` preserves `matmul_07` logic, squeezes 16 columns, and reroutes
the A ring at its exact 256-value capacity. It is 99×98, passed the public and
directed release gates, and passed all 20 live cases as submission
`b281b2af-dae3-40da-bfc4-317e3ff3b4b2` at score 5,931,034,965.9.
