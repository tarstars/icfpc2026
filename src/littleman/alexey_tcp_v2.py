"""tcp_01 v2: tag-through-ring architecture. Parts validated, assembly pending.

The four-round routing stall had one root cause: the pump needed OUTPUT
writes (drain, loss) *and* RING writes, and the two zones tug every loop.
This design removes OUTPUT from the pump entirely:

* SPLITTER (validated standalone, incl. round gating): discards the
  round-1 `n`, then alternates `seq` -> S pipe (pump top), `val` -> V pipe
  (parks at the pump's insert point; no register, no highway to the top).
* PUMP: writes ONLY to the ring. The drain emits by sending a TAG:
  data v -> -v, loss -> -2000; the resident marker is -3000.
* FORWARDER (validated standalone on all five value kinds): rides the
  ring in place of the plain relay. 0/+ forwarded; -v -> emit v to OUTPUT
  and push a 0 refill; -2000 -> emit -1; -3000 (marker) -> forwarded.
* Ring protocol (model validated 6/6 public, ~505 ops/case): marker rests
  in the ring; per packet rotate exactly d (no X branch, d=0 relays 0),
  discard, insert val, lap to the marker consuming it, drain by tags,
  then realign: push the terminating 0 (already in A), relay 15, re-push
  the marker. Init seeds 15 zeros and reuses the realign tail verbatim.

With no OUTPUT zone, pump phases lay out in EXECUTION ORDER top-to-bottom
(prologue, rotate, discard, insert, lap, drain, realign) and connections
become one downward thread plus one return column. The 40x18 draft in
`docs/alexey-tcp-v2-pump-draft.txt` places every phase with zero cell
collisions; what remains is four exit-route conflicts, all of the same
kind (an exit lane wanting a column another loop already turns on):
marker-exit column vs rotate's `d`, seed-exit vs the ascent column,
realign literal vs the ascent turn, lap-return vs the 0-merge. The clean
fix is +6 pump columns so every vertical lane is exclusive -- footprint
is not the fight yet, correctness is.

Score math: pump ~48x30 with splitter+FWD -> fp ~2300, ~505 ops x ~5
ticks/op -> ~2500 ticks -> ~5.8M vs tcp_00's 20.0M, before compaction.
"""

# --- validated splitter (probe passed: single round and multi-round) ---
SPLITTER = [
    "+--------+",
    "|@r     v|",
    "| >rsrs v|",
    "| ^<<<<<<|",
    "+--------+",
]

# --- validated forwarder interior (probe: [5,0,-7,-3000,12,-2000] -> [7,-1],
#     all five s-resolutions audited) ---
FWD_CELLS = {
    (3,1):'>', (3,2):'r', (3,3):'X', (3,4):'v',
    (4,4):'<', (4,3):'v', (5,3):'s', (6,3):'<', (6,2):'<', (6,1):'^',
    (2,3):'>', (2,4):'M',
    (2,5):'`',(2,6):'2',(2,7):'0',(2,8):'0',(2,9):'0',(2,10):'`',
    (2,11):'+', (2,12):'X',
    (3,12):'W', (4,12):'N', (5,12):'s', (6,12):'<', (6,6):'0', (6,5):'s',
    (2,13):'v', (3,13):'1', (4,13):'N', (5,13):'v', (6,13):'s', (7,13):'H',
    (1,12):'<', (1,11):'W', (1,2):'s', (1,1):'v',
    (8,1):'@', (8,2):'^',
}


def run_model(rounds):
    """Reference semantics; validated 6/6 on the public cases."""
    ring = [0]*16 + [-1]
    exp, out, first = 0, [], True
    for rd in rounds:
        vals = [int(v) for v in rd["in"]]
        if first:
            seq, val = vals[1], vals[2]; first = False
        else:
            seq, val = vals[0], vals[1]
        d = seq - exp
        if d >= 16:
            out.append(-1); return out
        for _ in range(d):
            ring.append(ring.pop(0))
        ring.pop(0); ring.append(val)
        while True:
            x = ring.pop(0)
            if x < 0: break
            ring.append(x)
        while True:
            x = ring.pop(0)
            if x > 0: out.append(x); exp += 1; ring.append(0)
            else: break
        ring.append(0)
        for _ in range(15):
            ring.append(ring.pop(0))
        ring.append(-1)
    return out
