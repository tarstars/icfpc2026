# Plotter Program Variants

Checked-in `.man` files are immutable candidates. New algorithms or geometry
optimizations get a new `plotter_NN.man` file and a corresponding
`variants.json` entry; older candidates are never overwritten.

`plotter_00.man` is the first complete correctness baseline. Five setup rooms
derive Bresenham constants, paired test/update rooms circulate the error
state, an address room applies step codes, and three small display rooms plot
and commit each frame. Its deliberately roomy generated layout is suitable
for later geometry-only compaction.

`plotter_01.man` preserves that protocol while tightening only generated-room
padding and vertical pipe clearances. It occupies 388×441 instead of 394×535,
passes the public and deterministic oracle suites locally, and improves the
measured local score by 32.98%. It has not been submitted.
