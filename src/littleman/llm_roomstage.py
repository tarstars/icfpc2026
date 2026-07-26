"""Reference composition for one complete physical indexed-room stage."""

from __future__ import annotations

from .canvas import Canvas
from .llm_actioncopy import actioncopy_reference, build_actioncopy_rig
from .llm_decisionprep import decisionprep_reference, build_decisionprep_rig
from .llm_decisionselect import decisionselect_reference, build_decisionselect_rig
from .llm_headerapply import headerapply_reference, build_headerapply_rig
from .llm_indexcopy import indexcopy_reference, build_indexcopy_rig
from .llm_indexdecision import indexdecision_reference, build_indexdecision_rig
from .llm_selectedapply import selectedapply_reference, build_selectedapply_rig
from .llm_selectedreplace import (
    selectedreplace_reference,
    build_selectedreplace_rig,
)


def roomstage_reference(tokens: list[int], room_no: int) -> list[int]:
    stream = indexcopy_reference(tokens)
    stream = indexdecision_reference(stream, room_no)
    stream = decisionprep_reference(stream)
    stream = decisionselect_reference(stream)
    stream = actioncopy_reference(stream)
    stream = selectedapply_reference(stream)
    stream = selectedreplace_reference(stream)
    return headerapply_reference(stream, room_no)


def _strip_io(text: str) -> tuple[list[str], tuple[int, int], tuple[int, int]]:
    rows = [list(row) for row in text.splitlines()]
    width = max(map(len, rows))
    for row in rows:
        row.extend([" "] * (width - len(row)))
    ports = {}
    for label in ("I", "O"):
        matches = [
            (r, c)
            for r, row in enumerate(rows)
            for c, char in enumerate(row)
            if char == label and c and c + 1 < width and row[c - 1 : c + 2] == ["|", label, "|"]
        ]
        if len(matches) != 1:
            raise ValueError(f"expected one {label} box, found {matches}")
        r, center = matches[0]
        left = center - 1
        for rr in range(r - 1, r + 2):
            for cc in range(left, left + 3):
                rows[rr][cc] = " "
        ports[label] = (r, left + 3)
    return ["".join(row) for row in rows], ports["I"], ports["O"]


def build_roomstage_rig(room_no: int) -> str:
    builders = (
        build_indexcopy_rig,
        lambda: build_indexdecision_rig(room_no),
        build_decisionprep_rig,
        build_decisionselect_rig,
        build_actioncopy_rig,
        build_selectedapply_rig,
        build_selectedreplace_rig,
        lambda: build_headerapply_rig(room_no),
    )
    cv = Canvas()
    offset_col = 20
    top = 0
    placed = []
    for builder in builders:
        rows, ingress, egress = _strip_io(builder())
        cv.put(top, offset_col, rows)
        placed.append(
            (
                (top + ingress[0], offset_col + ingress[1]),
                (top + egress[0], offset_col + egress[1]),
            )
        )
        top += len(rows) + 20

    track = 10
    for (_ingress, egress), (ingress, _egress) in zip(placed, placed[1:]):
        cv.pipe(
            [
                egress,
                (egress[0], track),
                (ingress[0], track),
                ingress,
            ]
        )
    ingress = placed[0][0]
    egress = placed[-1][1]
    cv.put(ingress[0] - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(egress[0] - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(ingress[0], 3), ingress])
    cv.pipe([egress, (egress[0], 3)])
    return cv.render()
