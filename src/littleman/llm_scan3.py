"""SCAN v3: room-shaped model of the pinned LLM machine_stream contract.

Chain of 1-in/1-out stream rooms (cookbook section 4's most reliable
pattern), each function here the exact algorithm its room will run:

  S1  = build_scan_room_v2() VERBATIM: 256 cell tokens (char + heuristic
        wall bit + padding bit), 3 man addrs (0 = absent), then relay.
  S2  strip+pack: drop v2's heuristic wall bit (bit 8) from every cell,
        pack 4 cells per word in 13-bit fields; men + tail ride along.
  P1  store-all room: ingest the 64 words + 3 men into one big scratch
        ring, then run find_rooms / wall pokes / man->room / pipe-head
        candidates / traces with random reads over the ring (a read =
        one counted rotation), emit the full machine_stream, and relay
        every later token forever.

Every stage keeps state within its room's scratch budget (asserted via
the CAP constants) and touches values only in ways A/B/ring FIFOs can.
find_rooms runs on the space-padded 16x16 canvas, which is equivalent
to running it on the true WxH grid: padding is all spaces, so every
run/corner probe fails at the boundary exactly as the bounds check
would.  The nested-candidate drop is asserted to be a no-op (interiors
cannot contain `|`, so a candidate can never nest inside another in a
valid program) and the room therefore omits it.
"""

from __future__ import annotations

from .lllm_scan import scan_reference_v2

FIELD = 8192          # 2**13, one packed cell field
CHAR = 256            # char lives in bits 0-7 of a field
WALL = 256            # wall bit inside a field
ROWS = 16
WORDS = 64
MEN = 3
DR = (-1, 0, 1, 0)    # 0=N 1=E 2=S 3=W, clockwise (llm_lockstep order)
DC = (0, 1, 0, -1)
ARROW_CODE = {94: 0, 62: 1, 118: 2, 60: 3}     # ^ > v <
PROBE = {0: 0, 2: 1, 3: 2, 1: 3}               # dir -> N,S,W,E probe rank
CAND_CAP = 8          # pipe-head candidate slots in P1
SENT_KEY = 1 << 14    # sorts after every real candidate key


def s2_pack(stream: list[int]) -> list[int]:
    """Strip the heuristic wall bit, pack 4 cells per 13-bit-field word.

    The room's per-cell strip is  t % 256  +  512 * (t >> 9)  — char plus
    the padding bit re-attached — which equals dropping bit 8, but every
    term is a one-literal A/B sequence with the raw token parked once.
    """
    out = []
    for w in range(WORDS):
        word = 0
        for k in range(4):
            t = stream[4 * w + k]
            word += (t % CHAR + 512 * (t >> 9)) * FIELD**k
        out.append(word)
    return out + stream[4 * WORDS:]         # men, then every later token


def p1_rooms(words: list[int]) -> list[tuple[int, int, int, int]]:
    """find_rooms via the P1 read primitive, walk-for-walk.

    Candidate scan order is reading order of the `+` top-left corner;
    the right run stops at the first non-`-`, the down run at the first
    non-`|`, and both must land on `+` at distance >= 2; then the far
    corner, bottom `-` run and right `|` column are validated.
    """
    rooms = []
    for r in range(ROWS):
        for c in range(ROWS):
            if _char(words, r * 16 + c) != 43:
                continue
            c2 = c + 1
            while c2 < ROWS and _char(words, r * 16 + c2) == 45:
                c2 += 1
            if c2 >= ROWS or c2 == c + 1 or _char(words, r * 16 + c2) != 43:
                continue
            r2 = r + 1
            while r2 < ROWS and _char(words, r2 * 16 + c) == 124:
                r2 += 1
            if r2 >= ROWS or r2 == r + 1 or _char(words, r2 * 16 + c) != 43:
                continue
            if _char(words, r2 * 16 + c2) != 43:
                continue
            if any(_char(words, r2 * 16 + x) != 45 for x in range(c + 1, c2)):
                continue
            if any(_char(words, y * 16 + c2) != 124 for y in range(r + 1, r2)):
                continue
            rooms.append((r, c, r2, c2))
    assert len(rooms) <= 3, "more than three rooms"
    for i, a in enumerate(rooms):                # find_rooms' nested drop:
        for j, b in enumerate(rooms):            # must be a no-op, or the
            if i != j:                           # room transcription breaks
                assert not (b[0] <= a[0] and b[1] <= a[1]
                            and b[2] >= a[2] and b[3] >= a[3]), "nested room"
    return rooms


def _contains(rm, r, c):
    return rm[0] <= r <= rm[2] and rm[1] <= c <= rm[3]


def _on_border(rm, r, c):
    return _contains(rm, r, c) and (r in (rm[0], rm[2]) or c in (rm[1], rm[3]))


def _char(words, addr):
    return (words[addr >> 2] >> (13 * (addr & 3))) % CHAR


def _poke_wall(words, addr):
    """Idempotent: field := char + WALL (frame cells are never padding)."""
    k = 13 * (addr & 3)
    f = (words[addr >> 2] >> k) % FIELD
    words[addr >> 2] += (f % CHAR + WALL - f) << k


def p1_stream(stream: list[int]) -> list[int]:
    """Rooms, walls, man rooms, pipe discovery, emission, relay."""
    words = list(stream[:WORDS])
    men = stream[WORDS : WORDS + MEN]
    rooms = p1_rooms(words)
    for t, l, b, r in rooms:                     # wall pokes, 4 runs a room
        for c in range(l, r + 1):
            _poke_wall(words, t * 16 + c)
            _poke_wall(words, b * 16 + c)
        for y in range(t + 1, b):
            _poke_wall(words, y * 16 + l)
            _poke_wall(words, y * 16 + r)
    man_rooms = [
        next(i for i, rm in enumerate(rooms)
             if rm[0] < a >> 4 < rm[2] and rm[1] < (a & 15) < rm[3])
        for a in reversed(men) if a
    ]
    cands = []
    for addr in range(256):                      # one lap: pipe-head hunt
        d = ARROW_CODE.get(_char(words, addr))
        if d is None:
            continue
        gr, gc = addr >> 4, addr & 15
        br, bc = gr - DR[d], gc - DC[d]
        if not (0 <= br < 16 and 0 <= bc < 16):
            continue
        for si, rm in enumerate(rooms):
            if _on_border(rm, br, bc) and not _contains(rm, gr, gc):
                cands.append((si << 10 | (br * 16 + bc) << 2 | PROBE[d], addr, d))
    assert len(cands) <= CAND_CAP, "candidate slot budget exceeded"
    cands.sort()                                 # (room, border scan, NSWE)
    pipes, used = [], set()
    for key, gaddr, d in cands:
        if gaddr in used:
            continue
        si = key >> 10
        r, c = gaddr >> 4, gaddr & 15
        cells = [gaddr]
        while True:
            nd = ARROW_CODE.get(_char(words, r * 16 + c))
            if nd is not None:
                d = nd
                fr, fc = r + DR[d], c + DC[d]
                ti = next((i for i, rm in enumerate(rooms)
                           if _on_border(rm, fr, fc)), -1)
                if ti >= 0 and ti != si:
                    break
            r, c = r + DR[d], c + DC[d]
            cells.append(r * 16 + c)
            assert len(cells) <= 20, "pipe trace overran the cell budget"
        used.update(cells)
        pipes.append((cells, si, ti))
    out = words + list(men) + [len(pipes)]
    for cells, si, ti in pipes:
        om = sum(1 << i for i, mr in enumerate(man_rooms) if mr == si)
        im = sum(1 << i for i, mr in enumerate(man_rooms) if mr == ti)
        out.append(len(cells) | cells[0] << 5 | cells[-1] << 13
                   | om << 21 | im << 24)
        for base in range(0, 21, 3):
            out.append(sum(cells[base + k] << (21 * k) for k in range(3)
                           if base + k < len(cells)))
    return out + stream[WORDS + MEN :]


def scan3_reference(tokens: list[int]) -> list[int]:
    """The whole chain: v2 ingest -> strip+pack -> rooms/walls/pipes."""
    return p1_stream(s2_pack(scan_reference_v2(tokens)))
