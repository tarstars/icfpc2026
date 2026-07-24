# Reverse-a-List Program Variants

Checked-in `.man` files are immutable candidates: a new optimization gets a
new `reverse_NN.man` and a new entry in `variants.json`; older programs are
never overwritten.

`reverse_00.man` is the shrinking-ring machine: a pump room and a relay room
form a value ring; each emit cycle skips j-1 values and consumes the j-th,
so the ring shrinks and values come out reversed. Ring size is measured with
`q` after a delay corridor guarantees all in-flight values have parked
(corridor ticks > ring round-trip; see tests). Empty ring falls through to
the input lane, which blocks until the next round.
