"""Step lab for compacting brackets_04, same method as the reverse lab.

brackets_04 is 35 wide x 30 tall, so fp = 35^2 = 1225 and only the WIDTH is
paid for.  The widest room (R2) spans cols 5-33; everything east of col 33 is
pipe.  So the first move is to fold the 69-cell pipe back inside col 33 and
see what the box does.
"""

from __future__ import annotations

import json
from pathlib import Path

from littleman.alexey_piperoute import Router
from littleman.judge import judge_case
from littleman.server_compat import find_shared_walls, judge_problem
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PROBLEM = json.loads((ROOT / "data/small/problems/brackets.json").read_text())
BASE = (ROOT / "submissions/brackets/brackets_04.man").read_text()


def box(text):
    lines = [l for l in text.split("\n")]
    cells = [(r, c) for r, l in enumerate(lines) for c, ch in enumerate(l) if ch != " "]
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    return (max(cs) - min(cs) + 1, max(rs) - min(rs) + 1)


def _border(room):
    cells = set()
    for c in range(room.left, room.right + 1):
        cells.add((room.top, c))
        cells.add((room.bottom, c))
    for r in range(room.top, room.bottom + 1):
        cells.add((r, room.left))
        cells.add((r, room.right))
    return cells


def gates(text, want_pipes, want_lengths=None):
    out = []
    try:
        m = Machine.parse(text)
    except Exception as exc:  # noqa: BLE001
        return [("parse", False, str(exc))], None
    lens = sorted(len(p.cells) for p in m.pipes)
    out.append((f"pipes=={want_pipes}", len(m.pipes) == want_pipes, len(m.pipes)))
    out.append(("min2cells", all(x >= 2 for x in lens), lens))
    if want_lengths is not None:
        out.append(("lengths kept", lens == sorted(want_lengths), lens))
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


def check(text, name, want_pipes=6, want_lengths=None, verbose=True):
    w, h = box(text)
    rows, _ = gates(text, want_pipes, want_lengths)
    hard = all(ok for _, ok, _ in rows)
    report = judge_problem(text, PROBLEM) if hard else None
    passed = report.cases_passed if report else 0
    score = report.score if report and passed == report.cases_total else float("inf")
    if verbose:
        print(f"[{name}] {w}x{h} fp {max(w, h) ** 2}  cases {passed}/9  score {score}")
        for gname, ok, detail in rows:
            if not ok:
                print(f"    FAIL {gname}: {detail}")
        if report and passed < report.cases_total:
            for cr in report.case_results:
                if not cr.passed:
                    print(f"    case fail: {cr.reason}")
    return max(w, h) ** 2, passed, score


def save(text, name, note=""):
    (HERE / f"{name}.man").write_text(text)
    with (HERE / "STEPS.md").open("a") as fh:
        fh.write(f"\n## {name}\n\n{note}\n\n```\n{text}```\n")


def show(text):
    lines = text.split("\n")
    print("    " + "".join(str(c % 10) for c in range(max(len(l) for l in lines))))
    for i, l in enumerate(lines):
        if l.strip() or i < len(lines) - 1:
            print(f"{i:3d} {l}")
