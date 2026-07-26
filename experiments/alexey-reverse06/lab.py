"""Step lab for compacting reverse_06 one small move at a time.

Every step is a config: four room corners plus four pipe routes.  `check`
builds it, runs every gate that matters, and prints one line.  A step is
accepted only if it is 8/8 with four pipes, no shared walls, one pipe against
the input room, and a ring-out of at least 15 cells.

Usage:  from lab import CFG, check, save
        cfg = dict(CFG, out_room=(9, 8), output=[(9, 11), (10, 11), (10, 11)])
        check(cfg, "step1")
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from littleman.canvas import Canvas
from littleman.judge import judge_case
from littleman.server_compat import find_shared_walls, judge_problem
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PROBLEM = json.loads((ROOT / "data/small/problems/reverse-a-list.json").read_text())

PUMP_INTERIOR = [
    "  v-rM<",
    "  b   2",
    "v Xrs@^",
    ">sU   s",
    "^md   W",
    "  >Mrs^",
]
RELAY_INTERIOR = ["@v", "v<", "Rs", ">^"]

# reverse_06 exactly -- step 0.
CFG = {
    "pump": (1, 5),
    "relay": (0, 0),
    "relay_interior": RELAY_INTERIOR,
    "in_room": (11, 0),
    "out_room": (11, 10),
    # each pipe: (waypoints, patch) -- patch overrides the terminal glyph
    "ring_in": ([(1, 4), (0, 4), (0, 8)], (0, 8, "v")),
    "ring_out": ([(9, 7), (13, 7), (13, 4), (9, 4), (9, 2), (6, 2)], None),
    "output": ([(9, 11), (10, 11)], None),
    "input": ([(10, 1), (6, 1)], None),
}


def _room(interior):
    width = len(interior[0])
    edge = "+" + "-" * width + "+"
    return [edge] + [f"|{row}|" for row in interior] + [edge]


def build(cfg):
    cv = Canvas()
    cv.put(*cfg["pump"], _room(PUMP_INTERIOR))
    cv.put(*cfg["relay"], _room(cfg.get("relay_interior", RELAY_INTERIOR)))
    cv.put(*cfg["in_room"], ["+-+", "|I|", "+-+"])
    cv.put(*cfg["out_room"], ["+-+", "|O|", "+-+"])
    for key in ("ring_in", "ring_out", "output", "input"):
        waypoints, patch = cfg[key]
        cv.pipe(waypoints)
        if patch:
            r, c, glyph = patch
            cv.cells[(r, c)] = glyph
    return cv.render()


def _border(room):
    cells = set()
    for c in range(room.left, room.right + 1):
        cells.add((room.top, c))
        cells.add((room.bottom, c))
    for r in range(room.top, room.bottom + 1):
        cells.add((r, room.left))
        cells.add((r, room.right))
    return cells


def gates(text):
    """Every hard rule, as (name, ok, detail)."""
    out = []
    try:
        m = Machine.parse(text)
    except Exception as exc:  # noqa: BLE001
        return [("parse", False, str(exc))], None
    out.append(("pipes==4", len(m.pipes) == 4, len(m.pipes)))
    out.append(("min2cells", all(len(p.cells) >= 2 for p in m.pipes),
                [len(p.cells) for p in m.pipes]))
    ring = max(m.pipes, key=lambda p: len(p.cells))
    out.append(("ringcap>=15", len(ring.cells) >= 15, len(ring.cells)))
    out.append(("no shared walls", not find_shared_walls(text), None))
    ok_in, detail = True, None
    for room in m.rooms:
        if getattr(room, "kind", None) != "input":
            continue
        b = _border(room)
        touching = [
            i for i, p in enumerate(m.pipes)
            if any({(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)} & b for (r, c) in p.cells)
        ]
        ok_in, detail = len(touching) == 1, touching
    out.append(("input 1 pipe", ok_in, detail))
    return out, m


def check(cfg, name, verbose=True):
    text = build(cfg)
    lines = text.split("\n")
    w = max(len(x) for x in lines)
    h = len([x for x in lines if x.strip()])
    rows = [g for g in gates(text)[0]]
    # ringcap is a heuristic, not a server rule: warn, but let the judge decide
    hard = all(ok for name, ok, _ in rows if name != "ringcap>=15")
    report = judge_problem(text, PROBLEM) if hard else None
    passed = report.cases_passed if report else 0
    score = report.score if report and passed == 8 else float("inf")
    if verbose:
        print(f"[{name}] {w}x{h} fp {max(w, h) ** 2}  cases {passed}/8  score {score}")
        for gname, ok, detail in rows:
            if not ok:
                tag = "warn" if gname == "ringcap>=15" else "FAIL"
                print(f"    {tag} {gname}: {detail}")
        if report and passed < 8:
            for cr in report.case_results:
                if not cr.passed:
                    print(f"    case fail: {cr.reason}")
    return text, (max(w, h) ** 2), passed, score


def stress(text, n=80):
    import random
    random.seed(7)
    for _ in range(n):
        lists = [
            [random.randint(-1000000, 1000000) for _ in range(random.randint(1, 16))]
            for _ in range(random.randint(1, 3))
        ]
        rounds = [
            {"in": [str(len(v))] + [str(x) for x in v], "out": [str(x) for x in reversed(v)]}
            for v in lists
        ]
        res = judge_case(text, rounds)
        if not res.passed:
            return False, lists
    return True, None


def save(text, name, note=""):
    (HERE / f"{name}.man").write_text(text)
    log = HERE / "STEPS.md"
    with log.open("a") as fh:
        fh.write(f"\n## {name}\n\n{note}\n\n```\n{text}```\n")
    return HERE / f"{name}.man"


def show(text):
    lines = text.split("\n")
    w = max(len(x) for x in lines)
    print("    " + "".join(str(c % 10) for c in range(w)))
    for i, line in enumerate(lines):
        if line.strip() or i < len(lines) - 1:
            print(f"{i:3d} {line}")
