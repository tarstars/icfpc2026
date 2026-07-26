"""One exact physical LLM tick, including blocking pipe operations."""

from __future__ import annotations

from itertools import pairwise

from .canvas import Canvas
from .llm_actioncoordinator import (
    actioncoordinator_reference,
    build_actioncoordinator_rig,
)
from .llm_fetchjoin import build_fetchjoin_rig, fetchjoin_reference
from .llm_manmap import build_manmap_rig, manmap_reference
from .llm_maskmap import build_maskprefix_rig, maskmap_reference
from .llm_recordstrip import build_recordstrip_rig, recordstrip_reference
from .llm_roomfind import WORLD_WORDS
from .llm_roomstage import _strip_io
from .llm_stateindex import (
    build_stateindex_rig,
    stateindex_reference,
    stateunindex_reference,
)
from .llm_stateunindex import build_stateunindex_rig


def fulltick_reference(tokens: list[int]) -> list[int]:
    world = tokens[:WORLD_WORDS]
    state = tokens[WORLD_WORDS:]
    fetched = fetchjoin_reference([*world, *maskmap_reference(state)])
    indexed = stateindex_reference(fetched)
    indexed = actioncoordinator_reference(indexed)
    fetched = stateunindex_reference(indexed)
    return recordstrip_reference(manmap_reference(fetched))


def build_fulltick_rig() -> str:
    builders = (
        build_maskprefix_rig,
        build_fetchjoin_rig,
        build_stateindex_rig,
        build_actioncoordinator_rig,
        build_stateunindex_rig,
        build_manmap_rig,
        build_recordstrip_rig,
    )
    cv = Canvas()
    left = 20
    top = 0
    placed = []
    for builder in builders:
        rows, ingress, egress = _strip_io(builder())
        cv.put(top, left, rows)
        placed.append(
            (
                (top + ingress[0], left + ingress[1]),
                (top + egress[0], left + egress[1]),
            )
        )
        top += len(rows) + 20

    track = 10
    for (_ingress, egress), (ingress, _egress) in pairwise(placed):
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
