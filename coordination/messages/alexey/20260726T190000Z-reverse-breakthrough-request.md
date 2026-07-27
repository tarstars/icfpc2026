# question: reverse-a-list needs a breakthrough -- winner is at 15.3k, we are at 84.9k

- From: alexey
- To: both (claude, codex, gpt)
- Created UTC: 2026-07-26T19:00:00Z
- Requires acknowledgement: no, ideas requested

## What 15.3k implies (arithmetic, not guesses)

Our reverse_07: fp 169 (13x13), avg 502.5 ticks, ring cost ~1.5n^2+9n.
15,300 = 169 x 90avg, or 121 x 126, or 144 x 106. Either way the winner's
avg ticks are ~5x ours -- that is LINEAR time, not a faster quadratic.
Reversal in linear time needs LIFO storage. What I have measured/proven:

- **Registers cannot do it cheaply**: BP is write-only (nothing reads it
  back), and every literal writes A, which is where a Horner accumulator
  must live. Measured floor ~34 ticks/value to pack 3-per-word (harness in
  docs/alexey-packing-paused.md), and 3 values/word is the 64-bit max.
  Ring on 6 packed words + pack/unpack loses to the current machine.
- **Pipes are FIFO** everywhere (input, output, rings). No LIFO there.
- **Multi-room stacks** (one man per cell, push/pop ripple) are linear-time
  but need ~16 rooms: fp explodes past any tick win at n<=16.
- Lap floor: a relay loop needs 6 cells (only U and d/a turn while
  working; s and m do not), so 6 ticks/relayed value stands.

So: either the winner found a LIFO trick none of my bounds cover (e.g.
something with U-turn routing or literal-free constant synthesis), or a
linear pipeline with fp <= 169. **Open call: if you see the trick, take it
or tell me.** reverse is mine but a 5x gap outranks ownership.

## The concrete step I can build now: triple extraction

Extract THREE values per pass (hold v_{k-2} in a 1-value stash room off
the ring): relays drop n^2/4 -> n^2/6, passes n/2 -> n/3. Estimated
84.9k -> ~57-65k depending on whether the stash forces 14x14. Design
notes in docs/alexey-worklog.md (2026-07-26 reverse_06 entry). I will
start it; if anyone wants it instead, claim it within the hour.
