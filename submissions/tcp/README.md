# Packet Reassembly Variants

Checked-in `.man` files are immutable candidates. A new optimization gets a
new `tcp_NN.man` file and a new entry in `variants.json`; submitted source is
never overwritten.

`tcp_00.man` is the first submitted paired-value ring implementation. Its
exact bytes passed all 20 live cases. `variants.json` records its generator,
hash, dimensions, local measurements, and live result.

`tcp_01.man` starts the tag-through-ring research line. `tcp_02.man` through
`tcp_05.man` were recovered from the contest platform on 2026-07-25 and are
catalogued in `alexey-variants.json`. The recovered lineage is:

```
tcp_01 / tcp_05 (identical) -> tcp_04 -> tcp_03 -> tcp_02
```

`tcp_02.man` is the identified 38×38 live winner. Its structural generator is
`littleman.alexey_tcp_recovered:build_tcp_recovered_best`; regression tests
require byte-for-byte reproduction, stable hashes for every recovered source,
all public cases, and 45 deterministic boundary cases.
