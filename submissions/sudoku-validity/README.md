# Sudoku Auditor Program Variants

Checked-in `.man` files are immutable candidates. New algorithms or geometry
optimizations get a new `sudoku_NN.man` and a corresponding `variants.json`
entry; older candidates are never overwritten.

`sudoku_00.man` is the first complete candidate. A broadcaster feeds parallel
row, column, and box workers, each maintaining nine digit bit masks in a FIFO
ring. It passed all 20 live cases as submission
`09a4a36c-3ff5-4560-a57a-f14879767fe4`.

`sudoku_01.man` keeps those room programs and protocols but packs the row and
column workers above the centered box worker. It occupies 286×285, passes all
focused local gates, and improves measured local score by 59.15%. It has not
been submitted. See `reports/2026-07-25-sudoku-two-row.md`.

`sudoku_05.man` replaces the three worker rings with one canonical 27-mask
ring, then folds and squeezes the complete machine to 75×131. It passed the
public cases and 17 directed order/duplicate workloads locally, then passed
all 20 live cases as submission `fb745779-f719-440e-828a-281583afe964` at
score 9,290,407,667.5.
