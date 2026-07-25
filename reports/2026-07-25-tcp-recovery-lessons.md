# Recovered Packet Reassembly Lineage and Reusable Lessons

Date: 2026-07-25

## Recovery result

The contest dashboard's authenticated download action recovered four
previously untracked Packet Reassembly sources. Together with the two
preserved files, they reveal one optimization lineage:

```text
tcp_01 / tcp_05 (identical) -> tcp_04 -> tcp_03 -> tcp_02
```

All recovered programs use the same five-room, six-pipe, three-man process
network: an input splitter, a window pump, and a tagged-output forwarder,
plus the I/O rooms. The important differences are on the serialized path.

| Variant | SHA-256 prefix | Dimensions | Public average ticks | Local score | Interpretation |
|---|---|---:|---:|---:|---|
| `tcp_00` | `fd8f78f09ce0` | 38×41 | 7,276.67 | 12,232,076.67 | Original paired-value ring |
| `tcp_01` | `e5e45693b594` | 30×62 | 8,943.83 | 34,380,095.33 | First tag-through-ring implementation |
| `tcp_04` | `7868665ea88c` | 43×38 | 2,798.17 | 5,173,810.17 | Compact protocol and pump |
| `tcp_03` | `8962e6f2eaa2` | 43×38 | 2,533.83 | 4,685,057.83 | Faster pump/splitter schedule |
| `tcp_02` | `61613871dc69` | 38×38 | 2,516.33 | 3,633,585.33 | Geometry-only compaction of `tcp_03` |
| `tcp_05` | `e5e45693b594` | 30×62 | 8,943.83 | 34,380,095.33 | Byte-identical duplicate of `tcp_01` |

`tcp_04 -> tcp_03` changes instructions in the splitter and pump while
retaining 43×38 geometry. Its gains concentrate in burst draining and loss
handling, reducing local score 9.45%. `tcp_03 -> tcp_02` leaves every room
instruction unchanged and relocates I/O and pipes to fill the 38-cell binding
height, reducing local score another 22.44%.

The counted live score of 5,981,625.6 identifies `tcp_02` exactly. Its
footprint is 38² = 1,444, so the live average is 4,142.4 ticks and the sum
over 20 cases is the integer 82,848. The 43-square and 62-square candidates
cannot produce that score from 20 integer case tick counts.

## Validation

All variants pass all six public cases. `tcp_02` through `tcp_05` also passed
a deterministic 45-case suite containing an in-order length-48 stream, full
reverse windows, a maximum-delay sawtooth, immediate loss, shortest input, and
40 seeded valid random permutations. All recovered layouts pass
`littleman.server_compat`.

`littleman.alexey_tcp_recovered:build_tcp_recovered_best` now reconstructs
`tcp_02` byte-for-byte from separately represented room programs, placements,
and pipe routes. Stable hashes and the boundary suite are enforced by
`tests/test_tcp_recovered.py`. The submission UUID is still absent from Git;
the dashboard submission row or browser download URL remains the authoritative
place to recover it.

## Reusable design lessons

1. **Remove serialized protocol work before physical compaction.**
   The compact protocol reduced local score by roughly 85% from `tcp_01`;
   final square balancing contributed a further 22%.
2. **Keep durable control in registers.**
   The pump keeps `expected` in B and transient loop counts in BP instead of
   circulating them through long pipes.
3. **Put control tags in the data stream when the value domain leaves space.**
   Negative tags let the pump write only to the ring; a dedicated forwarder
   decodes output and loss tags and refills slots.
4. **Split responsibilities into patient processes.**
   The input splitter and output forwarder prepare work concurrently while
   the pump owns window state.
5. **Track phase debt instead of paying for full realignment laps.**
   A known ring offset can be folded into the next operation's count.
6. **Use arithmetic bounds.**
   Four backpack shifts test `d >= 16`, replacing a long decrement chain.
7. **Treat pipe length as capacity and latency.**
   Preserve the proven minimum capacity, but remove surplus cells on the
   critical feedback path.
8. **Optimize the bounding square, not rectangular area.**
   Moving I/O into slack changed 43×38 into 38×38 without changing room code.
9. **Keep a measured lineage.**
   Architecture, component scheduling, and layout changes need separate
   variants so their individual value remains visible.

## Reuse priorities

The in-band control-token idea is directly applicable to Sort: replace its
`q`-counted parked ring and repeated settling corridor with a circulating
remaining-count token. Memory is the next architectural target because its
record ring dominates both capacity and latency. Grade Book and Matrix can
use tagged collectors where separate acknowledgement and result routes
inflate geometry. Plotter, Brackets, and Reverse primarily benefit from phase
tracking and square balancing. Sudoku and Subset Sum benefit mainly from
packing and balanced placement rather than TCP's ring protocol.
