# Grade Book Program Variants

Checked-in `.man` files are immutable candidates. A new algorithm or geometry
optimization gets a new `gradebook_NN.man` and a new `variants.json` entry;
older candidates are not overwritten.

`gradebook_00.man` is the first complete four-subject-worker candidate. It
passes all archived public cases and passed all 20 live cases as submission
`97526857-55b8-4e83-9ad5-2864afb3a02e`.

`gradebook_01.man` retains the same FSMs, four subject rings, acknowledgement
chain, and collector. Its parameterized layout uses one-cell command
corridors, minimum safe external clearances, a two-row parser/worker gap, and
wall-adjacent rightmost FSM tracks to shrink the machine from 494×462 to
454×450. It is the current best submitted variant.
