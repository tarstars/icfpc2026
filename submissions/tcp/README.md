# Packet Reassembly Variants

Checked-in `.man` files are immutable candidates. A new optimization gets a
new `tcp_NN.man` file and a new entry in `variants.json`; submitted source is
never overwritten.

`tcp_00.man` is the first submitted paired-value ring implementation. Its
exact bytes passed all 20 live cases. `variants.json` records its generator,
hash, dimensions, local measurements, and live result.
