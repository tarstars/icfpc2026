# Sort Program Variants

Checked-in `.man` files are immutable candidates. A new optimization gets a
new `sort_NN.man` file and a new entry in `variants.json`; an older program is
not overwritten.

`sort.man` is the original `sort_00` baseline whose exact bytes were submitted
successfully. `sort_01.man` is a geometry-only optimization: it uses the same
rooms, 16-stage pipeline, and token protocol, but packs and routes them more
tightly. `sort_02.man` replaces that pipeline with a much smaller shrinking-ring
selection sort and is the current best submitted variant.

`variants.json` is the comparison catalogue. It records generator identity,
hash, dimensions, footprint, public-case ticks, local and server scores,
live-submission identity, and a timestamped standings snapshot.
