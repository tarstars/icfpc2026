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
454×450.

`gradebook_05.man` starts from the later folded `gradebook_04` architecture.
Its subject engines rely on blocking ring receives instead of three fixed
80-cell delays, then apply only the fold prefixes that pass the whole-program
judge. It is 382×307, passes all seven public cases, and improves the measured
local score by 13.44% over `gradebook_04`. Submission
`010701d6-3d29-41e1-a09f-dae700e2f9ec` passed 20/20 at server score
47,115,780,603.6 and is the current submitted best.
