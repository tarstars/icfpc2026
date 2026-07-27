# chatgpt_2: complete two-pump Sort experiment

Date: 2026-07-27

## Result

The repository's unfinished two-pump K-ring design now has a complete,
deterministic end-to-end Littleman machine:

```text
input -> round-robin splitter -> pump A / pump B
pump A -> count prefixer --+
pump B -------------------+-> two-way merger -> output
```

The exact artifact is:

```text
experiments/chatgpt_2-sort-kring/chatgpt2_sort_00.man
SHA-256 8bc7495136458e5caf9bf8f46ded00df22c2d6de84558e879ba8967cbd83fdbe
```

It parses as 9 rooms, 12 pipes and 7 men. It passes all seven public cases and
300 deterministic random multi-round differential cases against Python
`sorted`.

```text
public ticks  [2195, 2132, 1895, 1391, 1980, 2828, 5639]
average       2580.0
box           154x153
score         max(154,153)^2 * 2580 = 61,187,280
```

This is a correctness milestone, not a submission candidate. The accepted
`tarstars_sort_08` public score is only 510,762.857.

## Why the current component family cannot pay

The negative result is stronger than “the first layout is large”. The exact
pump and relay were measured in a minimal four-room rig. Completion times for a
lane of `m=1..8` values are:

```text
m       1   2   3   4   5   6    7    8
ticks  84 134 196 270 356 454  564  686
```

Using `m=ceil(n/2)` for the slower lane gives a pump-only lower bound over the
seven public cases:

```text
[464, 414, 404, 280, 466, 854, 1960]
average = 691.7142857
```

Now remove the prefixer completely and assume free routing, free merger work,
and free splitter work. The remaining concrete room rectangles still occupy:

```text
splitter       27x20 = 540
2 pumps      2*12x15 = 360
2 relays       2*6x4 =  48
merger          18x8 = 144
input/output   2*3x3 =  18
                       ----
                       1110 cells
```

Therefore this component family needs at least a 34-square before a single pipe
cell is placed. Even multiplying that impossible zero-overhead layout only by
the pump lower bound gives:

```text
34^2 * 691.7142857 = 799,621.714
```

That is already 56.55% worse than the accepted public score, before accounting
for the splitter, merger, FIFO transport, reset, or pipe cells.

## Conclusion

Room placement and pipe routing cannot rescue this version. A competitive
parallel Sort requires a **new component idea**, not another floorplan:

- replace the compiled splitter with a genuinely tiny hand/synthesized room;
- integrate the relays into pump geometry or replace the ring protocol;
- shrink/rewrite the merger;
- or change the architecture again.

The complete artifact remains valuable as an oracle and as a regression target
for future component synthesis. It proves the two-pump protocol, sentinel
cleanup and multi-round lifecycle are correct.

No contest submission was made.
