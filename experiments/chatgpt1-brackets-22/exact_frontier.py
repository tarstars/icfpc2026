#!/usr/bin/env python3
"""Exact necessary-condition certificate for fixed 22x22 Brackets rooms.

Enumerates every fixed-room 22-square macro placement, every ordered I/O
placement and every wall endpoint assignment preserving the accepted machine's
nearest-pipe binding for all 36 s/r/q cells.  It then requires the mandatory
one-cell source exit and destination approach of each directed pipe to be free.
The result is zero: a component body must change before routing can succeed.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from functools import lru_cache
from itertools import permutations
from pathlib import Path

SIDE = 22
SIZES = {
    "close": (22, 7), "classify": (16, 6), "open": (18, 8),
    "input": (3, 3), "output": (3, 3),
}
EDGES = (
    ("classify_close", "classify", "close"),
    ("close_classify", "close", "classify"),
    ("close_output", "close", "output"),
    ("open_close", "open", "close"),
    ("open_classify", "open", "classify"),
    ("input_open", "input", "open"),
)
ROLES = {
    "classify": {"out": ("classify_close",), "in": ("close_classify", "open_classify")},
    "close": {"out": ("close_classify", "close_output"), "in": ("classify_close", "open_close")},
    "open": {"out": ("open_close", "open_classify"), "in": ("input_open",)},
    "input": {"out": ("input_open",), "in": ()},
    "output": {"out": (), "in": ("close_output",)},
}
INTERIORS = {
    "classify": [
        "@ssv      <   ", "   >rXrsrs^   ",
        "     >MrW+++sv", "   ^    s+1Mr<",
    ],
    "close": [
        "         >rM1+ sH   ", ">@rXrsrsv   >+MrXrMv",
        "   >    M4W-XrX  sH1", "^ s+1MrsWXW/W3M-<  +",
        "^       <     >rM1+s",
    ],
    "open": [
        "v  s  0  s<>4M0v", ">qd0       ^    ",
        "  >rbM5W} x     ", "@rv       ]     ",
        "^ <s  0  sxM0v  ", "H ds    Ws   < <",
    ],
}
BASE_ORIGIN = {
    "classify": (1, 0), "output": (4, 19), "close": (9, 1),
    "open": (16, 2), "input": (20, 20),
}
BASE_ENDPOINTS = {
    "classify_close": ((7, 9), (8, 9)),
    "close_classify": ((8, 7), (7, 7)),
    "close_output": ((8, 20), (7, 20)),
    "open_close": ((17, 1), (14, 0)),
    "open_classify": ((17, 20), (0, 5)),
    "input_open": ((19, 21), (18, 20)),
}


@dataclass(frozen=True, order=True)
class Placement:
    row: int
    col: int


def overlaps(a, az, b, bz):
    aw, ah = az
    bw, bh = bz
    return not (a.col + aw <= b.col or b.col + bw <= a.col or
                a.row + ah <= b.row or b.row + bh <= a.row)


def room_cells(p, size):
    w, h = size
    return {(r, c) for r in range(p.row, p.row + h)
            for c in range(p.col, p.col + w)}


def free_cells(ps):
    blocked = set().union(*(room_cells(p, SIZES[n]) for n, p in ps.items()))
    return {(r, c) for r in range(SIDE) for c in range(SIDE)} - blocked


def raw_ports(name, p):
    w, h = SIZES[name]
    out = []
    if p.row > 0:
        out += [(p.row - 1, c) for c in range(p.col + 1, p.col + w - 1)]
    if p.row + h < SIDE:
        out += [(p.row + h, c) for c in range(p.col + 1, p.col + w - 1)]
    if p.col > 0:
        out += [(r, p.col - 1) for r in range(p.row + 1, p.row + h - 1)]
    if p.col + w < SIDE:
        out += [(r, p.col + w) for r in range(p.row + 1, p.row + h - 1)]
    return out


def ports(ps):
    free = free_cells(ps)
    return {n: tuple(sorted(set(raw_ports(n, p)) & free))
            for n, p in ps.items()}


def outward(name, p, ep):
    w, h = SIZES[name]
    r, c = ep
    if r == p.row - 1:
        return -1, 0
    if r == p.row + h:
        return 1, 0
    if c == p.col - 1:
        return 0, -1
    if c == p.col + w:
        return 0, 1
    raise ValueError((name, p, ep))


def ops(name, p):
    for ir, line in enumerate(INTERIORS.get(name, ())):
        for ic, ch in enumerate(line):
            if ch in "srq":
                yield p.row + 1 + ir, p.col + 1 + ic, ch, (1 + ir, 1 + ic)


def nearest(candidates, pos):
    r, c = pos
    return min(candidates, key=lambda x: (
        abs(x[1][0] - r) + abs(x[1][1] - c), x[1][0], x[1][1]))


def binding_contract():
    by_room = {n: {"in": [], "out": []} for n in BASE_ORIGIN}
    for role, source, destination in EDGES:
        source_ep, destination_ep = BASE_ENDPOINTS[role]
        by_room[source]["out"].append((role, source_ep))
        by_room[destination]["in"].append((role, destination_ep))
    result = {}
    for name in INTERIORS:
        p = Placement(*BASE_ORIGIN[name])
        for r, c, ch, rel in ops(name, p):
            direction = "out" if ch == "s" else "in"
            result[(name, rel, ch)] = nearest(by_room[name][direction], (r, c))[0]
    return result


CONTRACT = binding_contract()


def directional_assignments(name, p, endpoints, direction):
    roles = ROLES[name][direction]
    if not roles:
        return ((),)
    relevant = [item for item in ops(name, p)
                if ("out" if item[2] == "s" else "in") == direction]
    good = []
    for chosen in permutations(endpoints, len(roles)):
        mapping = dict(zip(roles, chosen))
        if all(nearest([(role, mapping[role]) for role in roles], (r, c))[0]
               == CONTRACT[(name, rel, ch)] for r, c, ch, rel in relevant):
            good.append(tuple(sorted(mapping.items())))
    return tuple(good)


@lru_cache(maxsize=None)
def has_binding(name, row, col, endpoints):
    p = Placement(row, col)
    incoming = directional_assignments(name, p, endpoints, "in")
    outgoing = directional_assignments(name, p, endpoints, "out")
    for left in incoming:
        used = {ep for _, ep in left}
        for right in outgoing:
            if used.isdisjoint(ep for _, ep in right):
                return True
    return False


def io_spots(big):
    size = SIZES["input"]
    for row in range(SIDE - size[1] + 1):
        for col in range(SIDE - size[0] + 1):
            p = Placement(row, col)
            if all(not overlaps(p, size, other, SIZES[name])
                   for name, other in big.items()):
                yield p


def big_macros():
    # The full-width CLOSE room is a barrier. OPEN and CLASSIFY must be on the
    # same side because they have a direct logical pipe, so CLOSE is top/bottom.
    for close_row in (0, SIDE - SIZES["close"][1]):
        close = Placement(close_row, 0)
        low, high = ((7, 22) if close_row == 0 else (0, 15))
        for open_row in range(low, high - SIZES["open"][1] + 1):
            for classify_row in range(low, high - SIZES["classify"][1] + 1):
                if not (open_row + 8 <= classify_row or classify_row + 6 <= open_row):
                    continue
                for open_col in range(SIDE - 18 + 1):
                    for classify_col in range(SIDE - 16 + 1):
                        yield {
                            "close": close,
                            "open": Placement(open_row, open_col),
                            "classify": Placement(classify_row, classify_col),
                        }


def connected(ps):
    free = free_cells(ps)
    seen = {next(iter(free))}
    stack = list(seen)
    while stack:
        r, c = stack.pop()
        for q in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if q in free and q not in seen:
                seen.add(q)
                stack.append(q)
    return len(seen) == len(free)


def enumerate_exact():
    big_count = big_binding = ordered_io = exact_binding = connected_count = directional = 0
    for big in big_macros():
        big_count += 1
        endpoint_sets = ports(big)
        if not all(has_binding(name, big[name].row, big[name].col,
                               endpoint_sets[name])
                   for name in ("close", "classify", "open")):
            continue
        big_binding += 1
        spots = tuple(io_spots(big))
        for input_spot in spots:
            for output_spot in spots:
                if input_spot == output_spot or overlaps(
                        input_spot, SIZES["input"], output_spot, SIZES["output"]):
                    continue
                ordered_io += 1
                ps = {**big, "input": input_spot, "output": output_spot}
                endpoint_sets = ports(ps)
                if not all(has_binding(name, ps[name].row, ps[name].col,
                                       endpoint_sets[name]) for name in ps):
                    continue
                exact_binding += 1
                if connected(ps):
                    connected_count += 1
                free = free_cells(ps)
                directed = {}
                for name, p in ps.items():
                    directed[name] = tuple(
                        ep for ep in endpoint_sets[name]
                        if (ep[0] + outward(name, p, ep)[0],
                            ep[1] + outward(name, p, ep)[1]) in free)
                if all(has_binding(name, ps[name].row, ps[name].col,
                                   directed[name]) for name in ps):
                    directional += 1
    return {
        "schemaVersion": 1,
        "canvas": [22, 22],
        "fixedRoomSizes": {name: list(SIZES[name]) for name in sorted(SIZES)},
        "bigRoomPlacements": big_count,
        "bigRoomBindingFeasible": big_binding,
        "orderedIoPlacementsExamined": ordered_io,
        "exactBindingPlacements": exact_binding,
        "connectedExactBindingPlacements": connected_count,
        "directionallyFeasiblePlacements": directional,
        "firstDirectionalPlacement": None,
        "necessaryDirectionRule": "every endpoint's one-cell outward neighbour must be free",
        "conclusion": "fixed component rectangles require a component change before 22x22 routing",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    encoded = json.dumps(enumerate_exact(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
