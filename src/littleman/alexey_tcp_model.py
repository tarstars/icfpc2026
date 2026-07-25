"""Reference model for the rebuilt Packet Reassembly machine (tcp_01).

Validated against all six public cases before any ASCII was drawn. It is the
spec the machine must implement, and the source of the tick estimate: 258
ring operations per case on average, against ~7277 ticks for tcp_00.

Why it is so much cheaper than tcp_00: the delay rule caps the buffer at 15
slots, so the window can be addressed by offset instead of searched. tcp_00
scans the whole buffer per packet and requeues what does not match, which is
quadratic in the window; this is linear with a fixed 16-slot lap.

Window is a 16-slot ring, aligned so the head is the slot for `expected`.
0 marks an empty slot (values are 1..999, so 0 is free). A negative marker
rides the ring so a lap can end on a sign test instead of a counter.

Ring order as the pump reads it: [s0, s1, ..., s15, MARKER].
"""
MARK = -1

def run(rounds):
    ring = [0]*16 + [MARK]      # s0..s15 then the marker
    expected = 0
    out = []
    ops = 0                      # ring reads+writes, the tick driver
    first = True
    for rd in rounds:
        vals = [int(v) for v in rd["in"]]
        if first:
            n, seq, val = vals[0], vals[1], vals[2]; first = False
        else:
            seq, val = vals[0], vals[1]
        d = seq - expected
        if d >= 16:
            out.append(-1)
            return out, ops
        # rotate d, drop the empty slot, insert val, rotate to the marker
        for _ in range(d):
            ring.append(ring.pop(0)); ops += 1
        ring.pop(0); ring.append(val); ops += 1
        while ring[0] != MARK:
            ring.append(ring.pop(0)); ops += 1
        ring.append(ring.pop(0)); ops += 1          # marker back to the tail
        # drain: head is s0 again
        while ring[0] > 0:
            out.append(ring.pop(0)); ring.insert(len(ring)-1, 0)
            expected += 1; ops += 1
    return out, ops

if __name__ == "__main__":
    import json
    prob = json.load(open('/home/claudebox/projects/icfpc2026/data/small/problems/tcp.json'))
    total_ops = 0
    for c in prob["publicTestData"]:
        want = [int(v) for rd in c["rounds"] for v in rd.get("out", [])]
        got, ops = run(c["rounds"])
        total_ops += ops
        status = "OK " if got == want else "FAIL"
        print(f'{status} {c["name"]:28s} rounds={len(c["rounds"]):>3} ring-ops={ops:>4}'
              f'{"" if got==want else f"  got {got[:8]} want {want[:8]}"}')
    print(f'total ring-ops {total_ops}, avg per case {total_ops/len(prob["publicTestData"]):.0f}')
