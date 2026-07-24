# Memory Program Variants

Checked-in `.man` files are immutable candidates. New algorithms or geometry
optimizations get a new `memory_NN.man` file and a corresponding
`variants.json` entry; older candidates are never overwritten.

`memory.man` is the original `memory_00` pipeline-ring baseline.
`memory_01.man` preserves every room and protocol from that baseline, but
moves the head-pointer room below the storage ring and routes its two pipes
through disjoint wraparound corridors. It is the current best submitted
variant.
