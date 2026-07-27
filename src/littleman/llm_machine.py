"""Complete raw-input physical LLM machine composition."""

from __future__ import annotations

from collections.abc import Callable

from .canvas import Canvas
from .llm_geometry_assemble import build_geometry_pipeline
from .llm_packraw import build_pack_rig, pack_reference
from .llm_perimeter import perimeter_reference
from .llm_pipestarts import pipestarts_reference
from .llm_pipetrace import pipetrace_dest_reference
from .llm_roomfind import roomfind_reference
from .llm_roomstage import _strip_io
from .llm_roundcontrol import _strip_input, build_runtime_loop_rig
from .llm_scan import build_scan_rig, scan_reference
from .llm_statebuild import build_statebuild_rig, statebuild_reference


def normalize_input_reference(tokens: list[int]) -> list[int]:
    """Convert raw round input into the frozen world/state stream plus tail."""
    stream = scan_reference(tokens)
    stream = pack_reference(stream)
    stream = roomfind_reference(stream)
    stream = perimeter_reference(stream)
    stream = pipestarts_reference(stream)
    stream = pipetrace_dest_reference(stream)
    return statebuild_reference(stream)


def build_llm_machine() -> str:
    """Stack one-shot setup stages above the persistent round runtime."""
    setup_builders: tuple[Callable[[], str], ...] = (
        build_scan_rig,
        build_pack_rig,
        lambda: build_geometry_pipeline(annotate_dest=True),
        build_statebuild_rig,
    )
    cv = Canvas()
    left = 20
    top = 0
    placed: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for builder in setup_builders:
        rows, ingress, egress = _strip_io(builder())
        cv.put(top, left, rows)
        placed.append(
            (
                (top + ingress[0], left + ingress[1]),
                (top + egress[0], left + egress[1]),
            )
        )
        top += len(rows) + 20

    runtime_rows, runtime_ingress = _strip_input(build_runtime_loop_rig())
    cv.put(top, left, runtime_rows)
    runtime_port = (
        top + runtime_ingress[0],
        left + runtime_ingress[1],
    )

    track = 10
    targets = [port[0] for port in placed[1:]] + [runtime_port]
    for (_ingress, source), target in zip(placed, targets, strict=True):
        cv.pipe(
            [
                source,
                (source[0], track),
                (target[0], track),
                target,
            ]
        )

    ingress = placed[0][0]
    cv.put(ingress[0] - 1, 0, ["+-+", "|I|", "+-+"])
    cv.pipe([(ingress[0], 3), ingress])
    return cv.render()
