# Sudoku Auditor Program Variants

Checked-in `.man` files are immutable candidates. New algorithms or geometry
optimizations get a new `sudoku_NN.man` and a corresponding `variants.json`
entry; older candidates are never overwritten.

`sudoku_00.man` is the first complete candidate. A broadcaster feeds parallel
row, column, and box workers, each maintaining nine digit bit masks in a FIFO
ring. It passed all 20 live cases as submission
`09a4a36c-3ff5-4560-a57a-f14879767fe4`.
