# tcp handoff — what to build next and how to verify it

Written for a smaller model taking over. Read this and
`docs/alexey-simple-model-tricks.md`; do NOT re-derive the architecture,
it is proven on the server. Everything here is measured, not guessed.

## Where things stand

- `submissions/tcp/tcp_01.man` — the v2 machine, **20/20 live**, score
  52,747,175 (submission 9f1985a4). WORSE than tcp_00's 20,028,106; the
  team's counted best is still tcp_00. tcp_01 is the working base.
- Why it loses: score = max(w,h)² × avgTicks = 3844 × 13,722. Ticks
  dominate. Each packet runs three full ring laps (rotate + lap-to-marker,
  then a 15-relay realign) serialized against ~30 ticks of ring latency
  (22-cell return pipe + 8-tick forwarder loop).
- Break-even math: to beat 20.0M you need fp × ticks < 20M. Realistic
  combo: fp ≈ 2400 (compaction below) AND ticks ≈ 8.3k (ideas 2–3).
  All three ideas together are estimated to land at ~20M ± 15%, so
  execute all of them and measure after each.

## The machine in one paragraph

I → SPLITTER (discards round-1 `n`, sends `seq` down to the pump top,
`val` to a pipe that parks it at the insert point). PUMP holds `expected`
in B forever and writes ONLY to the ring: per packet it computes
d = seq − expected (`r - b ]]]] d b`, loss when BP>0 after 4 shifts),
rotates exactly d, discards the stale slot, inserts val (`r` from V,
`s` to ring), laps to the resident marker (−3000) consuming it, drains by
sending tags (data v → −v via `N s`; loss → −2000), then realigns: push
the terminating 0 (already in A), relay 15, re-push the marker. The
FORWARDER room rides the ring: 0/+ forwarded, −v → emit v to OUTPUT and
push a 0 refill, −2000 → emit −1, −3000 → forwarded. Reference semantics:
`littleman.alexey_tcp_v2.run_model` (validated 6/6).

The assembly script (single source of truth for the layout) is committed
at `docs/` history — rebuild from `scratchpad`-style: see the cell lists
in `src/littleman/alexey_tcp_v2.py` and the final `submissions/tcp/tcp_01.man`.
Treat tcp_01.man as immutable; new attempts are tcp_02, tcp_03, …

## Ideas to implement, in this order

### 1. Compaction (safe, mechanical) — fp 3844 → ~2400

The pump interior is 40×24 with rows 12–23 almost empty: they exist only
because ring-reads must sit deep enough that RIN beats the S pipe in
nearest-incoming distance. When you shrink the pump, THE ZONE BOUNDARY
MOVES — recompute it, do not eyeball it: for a read cell at (r,c) the
ring wins when |bottom+1−r|+|c−9| < r+|c−3| (S enters top rel col 4).
Shrink pump height to ~30, keep every ring loop below the recomputed
boundary with margin ≥2. Then pull the FWD room and O tighter under it.
Every move must keep: `assert_pipe_map`-style audits for the pump's three
incoming pipes (S top, V bottom rel col 22, RIN bottom rel col 9), the
forwarder's five `s` resolutions, RIN capacity ≥ 17 cells.

### 2. Kill the realign relay (−15 relays/packet, ≈ −2k ticks/case)

After the drain, instead of push-0 + relay-15 + push-marker, do just:
push 0 (A already holds it), push marker (`3000` N s — the literal is
already in the room). Ring is then rotated one slot forward with 0 and M
at the tail — the OLD rotation debt, now on purpose. Compensate in the
next packet's rotation count: rotate d−1, and d = 0 rotates 15. That
needs the three-way `X` branch back: copy it verbatim from
`src/littleman/alexey_sort_ring2.py` PUMP_INTERIOR rows 3–5 (the `X` /
vertical `15` literal / `b` merge) — it is a proven idiom. The drain and
the insert both index from the head, and BOTH are consistent with the
debt as long as the count is d−1/15 — this was verified on paper once
(see worklog 2026-07-24 'fault 4'): the debt broke the OLD design only
because the drain there assumed head = s0. In the new order (marker
consumed by the lap, drain starts at true w0) re-derive the alignment ON
PAPER with the 4-line ring model BEFORE laying cells, and extend
`run_model` first — if the model passes 6/6, the cells will follow.

### 3. Shorten the ring latency (~ −300 ticks/round)

- Forwarder fast path (0/+ values) is currently 8 cells around the loop;
  reshape so the common path is 6. Keep `r` before the first `s` on the
  startup walk.
- Return pipe RIN is 21 cells; it only needs capacity ≥ 17 minus what
  ROUT holds. ROUT is 3. Keep RIN ≥ 15 and total ≥ 18 with margin;
  shorter pipe = lower lap-start stall.

### Do NOT attempt

- Draining during the lap (order makes it impossible — the lap must
  finish before the head is w0).
- Overlapping packets (round gating forbids reading the next seq early).
- 4-slots-per-word packing — real but a full redesign; only if 1–3 land
  above 20M and more is still needed.

## Verification workflow (run after EVERY change)

```
PYTHONPATH=src python3 -c "…judge tcp_02.man on all 6 public cases…"
# then the 45-case boundary stress from this session:
#   n=48 in order, full-window burst, instant loss (first packet seq 16),
#   40 random shuffles judged against run_model
```

Local 6/6 + stress 45/45 came before both server submissions and the
server agreed both times. Submit with
`icfpc-api submit d61a3af1-c74f-44c0-98f7-4f20eeefa3fb <file> --confirm --wait`,
capture the full JSON to `submissions/tcp/alexey-tcp_0N-submit.json`.
Best-submission-counts: a worse score does no harm.

## Traps already paid for (do not rediscover)

1. A pipe's FIRST arrowhead must point away from the source wall with its
   backward cell ON that wall — a west-pointing start cannot leave a
   bottom wall.
2. A route drawn over another room's wall column mints a phantom pipe
   from that wall (parser starts pipes at any arrowhead backing onto a
   border). Symptom: pipe count wrong, or `bad pipe glyph`.
3. Canvas.pipe's terminal arrowhead follows the segment direction; when
   the pipe must END pointing into a room sideways, patch the last cell
   (`cv.cells[(r,c)] = "^"`).
4. The splitter's two `s` cells resolve by distance — after any splitter
   geometry change re-audit which pipe gets seq and which gets val.
5. Walk crossings on EMPTY cells are legal and free; crossings on
   instruction/turn cells are the #1 bug source. The walk checker
   (`walk_report` in `alexey_tcp_ring.py`) reads a stray walk as an
   unexpected phase name — use it before judging.
6. Wall-step after final `s` is server-legal (`alexey_walljudge`), rooms
   sharing a wall are NOT.
