"""Physical two-slot candidate selection pipeline for the LLM coordinator."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_fetch import build_relay
from .llm_bindscore import build_bindscore_room
from .llm_candidatejoin import (
    build_candidatejoin_room,
    candidatejoin_reference,
)
from .llm_packedcandidate import (
    build_packedcandidate_echo_room,
    packedcandidate_echo_reference,
)
from .llm_selecteligible import (
    build_selecteligible_room,
    selecteligible_reference,
)


def candidateselect_reference(tokens: list[int]) -> list[int]:
    """Select a slot from repeated ``context, pipe0, context, pipe1`` words."""
    echoed = packedcandidate_echo_reference(tokens)
    joined = candidatejoin_reference(echoed)
    return selecteligible_reference(joined)


def _add_ring(
    cv: Canvas,
    *,
    top: int,
    right: int,
) -> None:
    relay_left = right + 5
    far = relay_left + 17
    cv.put(top + 20, relay_left, build_relay().render())
    cv.pipe(
        [
            (top + 2, right + 1),
            (top + 2, far),
            (top + 21, far),
            (top + 21, relay_left + 6),
        ]
    )
    cv.pipe(
        [
            (top + 21, relay_left - 1),
            (top + 21, right + 2),
            (top + 9, right + 2),
            (top + 9, right + 1),
        ]
    )


def build_candidateselect_rig() -> str:
    candidate = build_packedcandidate_echo_room()
    join = build_candidatejoin_room()
    select = build_selecteligible_room()
    score = build_bindscore_room()

    left = 5
    candidate_top = 0
    join_top = len(candidate) + 20
    select_top = join_top + len(join) + 20
    candidate_right = left + len(candidate[0]) - 1
    join_right = left + len(join[0]) - 1
    select_right = left + len(select[0]) - 1
    score_left = select_right + 10
    score_right = score_left + len(score[0]) - 1

    cv = Canvas()
    cv.put(candidate_top, left, candidate)
    cv.put(join_top, left, join)
    cv.put(select_top, left, select)
    cv.put(select_top, score_left, score)
    _add_ring(cv, top=candidate_top, right=candidate_right)
    _add_ring(cv, top=join_top, right=join_right)

    # External input and final output.
    cv.put(1, 0, ["+-+", "|I|", "+-+"])
    cv.put(select_top + 5, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(2, 3), (2, left - 1)])
    cv.pipe([(select_top + 6, left - 1), (select_top + 6, 3)])

    # Candidate reply -> join input, then join reply -> selector input.
    cv.pipe(
        [
            (candidate_top + 6, left - 1),
            (candidate_top + 6, 1),
            (join_top + 2, 1),
            (join_top + 2, left - 1),
        ]
    )
    cv.pipe(
        [
            (join_top + 6, left - 1),
            (join_top + 6, 2),
            (select_top + 2, 2),
            (select_top + 2, left - 1),
        ]
    )

    # Selector RPC to BIND-SCORE and its private scratch ring.
    cv.pipe(
        [
            (select_top + 2, select_right + 1),
            (select_top + 2, score_left - 1),
        ]
    )
    cv.pipe(
        [
            (select_top + 6, score_left - 1),
            (select_top + 6, select_right + 4),
            (select_top + 9, select_right + 4),
            (select_top + 9, select_right + 1),
        ]
    )
    _add_ring(cv, top=select_top, right=score_right)
    return cv.render()
