# tcp handoff — state, design, and what is left

Everything here is measured, not guessed. Read this before touching tcp.

## State

| version | score | w×h | fp | avgTicks | live |
|---|---|---|---|---|---|
| tcp_00 (other line) | 20,028,106 | — | — | — | 20/20 |
| tcp_01 | 52,747,176 | 30×62 | 3844 | 13722 | 20/20 |
| tcp_02 | 8,554,029 | 43×38 | 1849 | 4626 | 20/20 |
| tcp_03 | 7,693,504 | 43×38 | 1849 | 4161 | 20/20 |
| **tcp_04** | **5,981,626** | **38×38** | **1444** | **4142** | **20/20** |

`submissions/tcp/tcp_04.man` is the team best (3.35× better than tcp_00).
`src/littleman/alexey_tcp_v3.py` regenerates it byte-for-byte; edit the
generator, never the `.man`. Submitted files are immutable — new attempt
is tcp_05.

## The design in one page

**I → SPLITTER → (S pipe, V pipe) → PUMP → ROUT → FORWARDER → RIN → PUMP,
FORWARDER → O.**

The ring holds **w1..w15 — 15 values, no sentinel.** The window slot w0
(the next expected sequence number) is *always* empty at packet start,
because every packet drains to completion, so it is not stored at all.
That single observation is what deleted the resident marker and the
15-relay realign that came with it (46% of the previous machine's work).

- `d = seq − exp ≥ 1`: rotate d−1, pop the stale slot, push val, relay
  15−d. Constant 16 ops, and **no drain** — an off-head insert cannot
  fill w0.
- `d == 0`: emit val straight to the forwarder, then pop-and-emit while
  the head is positive. The forwarder's 0 refill lands at the tail, which
  is exactly where the freed window slot belongs, so the invariant
  restores itself with no fixup. **An in-order packet costs two ring ops.**
- `d ≥ 16`: loss. Pump sends the −2000 tag and halts; the forwarder emits −1.

**Registers.** `exp` lives in B permanently, A is the working value, BP is
the loop counter. The two loop counts would need a counter nobody has, so
the splitter supplies the constant: it sends `seq` on the **S pipe** and
`15−seq, val` on the **V pipe**. The pump gets d from one `-` and 15−d
from one `+`. Both mid-packet reads then sit in the same zone, which is
worth ~25 ticks/packet of walking (that was the whole tcp_03 gain).

**Tags on the ring.** Ring values are ≥ 0. Negative means a tag: `−v` →
forwarder emits v and pushes a 0 refill; `−2000` → emits −1. Residual
risk: a payload of exactly 2000 would be read as a loss. Public values are
0..999 and three submissions have passed 20/20, so it is empirically fine,
but if you ever see a mysterious early `-1`, this is why.

**Reference model:** `alexey_tcp_v3.run_model` equivalent lives inline in
the module docstring history; `alexey_tcp_v2.run_model` is still the
validated oracle to diff against (they agree on 4000 random streams).

## The layout rule that made it work

**Put every incoming pipe on the same wall.** The row term of the
Manhattan distance is then identical for all of them, so the zone is
decided purely by column — a read cell's pipe no longer depends on how
deep in the room it sits. The pump's three inputs (S col 2, RIN col 11,
V col 20) all enter the bottom wall, and all nine `r` cells resolved
correctly on the first audit. The mirror image works too: the splitter
puts S and V on opposite walls in the *same column*, so the horizontal
terms cancel and the **row** decides.

Always re-audit after moving anything:
```
man = type('M',(),{'r':room.top+r,'c':room.left+c,'room':room})()
m._nearest_incoming(man)   # or _nearest_outgoing for s cells
```

## What is left, in order of value

1. **Ticks (4142).** For `d ≥ 1` packets, 14 relays × 8 ticks = 112
   ticks/packet is the algorithmic floor. On top of that the pump idles
   ~20 ticks/packet blocked on the 42-cell S pipe — shortening that pipe
   is the cheapest remaining win.
2. **Pump height.** Three rows of the pump interior hold a single cell
   each (the DPOS descent and the two relay-approach rows). Merging them
   shrinks the pump, but note the footprint is already a 38×38 square:
   height must come down *together with* width to pay.
3. **Width is near-minimal** for this arrangement: forwarder (18 cols) +
   gap + splitter (13 cols) = 38 across. Stacking them vertically instead
   was measured as worse (height would go to ~46).
4. Do NOT attempt: draining during the rotate (order forbids it),
   overlapping packets (round gating forbids reading the next seq early).

## Verification workflow — run after EVERY change

```
PYTHONPATH=src python3 -c "from littleman.alexey_tcp_v3 import build; ..."
# 1. zone audit: every r cell resolves to the intended pipe
# 2. 6/6 public cases via littleman.alexey_walljudge.judge_case
# 3. 46-case boundary stress: n=48 in order, full window, instant loss
#    (first seq 16), fully reversed, 40 random shuffles vs the oracle
```
Local 6/6 + stress preceded all four submissions and the server agreed
every time. Submit with
`icfpc-api submit d61a3af1-c74f-44c0-98f7-4f20eeefa3fb <file> --confirm --wait`
and capture the JSON to `submissions/tcp/alexey-tcp_0N-submit.json`.
Best-submission-counts: a worse score does no harm.

## Traps already paid for — do not rediscover

1. **A counted relay loop needs `m` inside it.** `d` only *tests* the
   backpack, it does not decrement. A loop without `m` spins forever.
   Cost: one debug round, because the seed loop had one and terminated.
2. **RIN must park the whole ring (≥16 cells).** When the pump idles
   between packets the forwarder keeps pushing; a short RIN blocks it and
   any tag queued behind those values is never decoded. Deadlock with an
   otherwise perfectly correct machine.
3. **The forwarder's fast path must be short.** At 28 cells/value the
   pump starved 3× ; at 8 cells it never waits. Ring latency is not the
   issue — forwarder *throughput* is.
4. **Mirroring a room vertically must swap `v`↔`^`**, and is only safe
   when the room has no handed op (`X`, `d`, `a`, `x`) — a mirror turns
   clockwise into counter-clockwise.
5. **A pipe cell whose backward neighbour is a room wall starts a NEW
   pipe there.** Route one column clear of foreign rooms. Symptom: wrong
   pipe count or `bad pipe glyph`.
6. `Canvas.pipe`'s terminal arrowhead follows the segment direction —
   patch the last cell (`cv.cells[(r,c)] = "^"`) when it must end pointing
   into a room sideways.
7. Walk crossings on EMPTY cells are legal and free; crossings on
   instruction or turn cells are the #1 bug source.
8. Wall-step after a final `s` is server-legal (`alexey_walljudge`);
   rooms sharing a wall are NOT.
