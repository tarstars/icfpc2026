"""Duplicate indexed state while preserving a selected-action prefix."""

from __future__ import annotations

from .canvas import Canvas
from .llm_indexcopy import add_indexcopy_network, indexcopy_reference
from .llm_indexdecision import _indexed_end

ACTION_PREFIX_WORDS = 5


def actioncopy_reference(tokens: list[int]) -> list[int]:
    out = []
    index = 0
    while index < len(tokens):
        prefix = tokens[index : index + ACTION_PREFIX_WORDS]
        if len(prefix) != ACTION_PREFIX_WORDS:
            raise ValueError("truncated selected-action prefix")
        index += ACTION_PREFIX_WORDS
        end = _indexed_end(tokens, index)
        state = tokens[index:end]
        index = end
        out.extend((*prefix, *indexcopy_reference(state)))
    return out


def build_actioncopy_rig() -> str:
    cv = Canvas()
    ingress, egress = add_indexcopy_network(
        cv,
        top=0,
        left=5,
        prefix_words=ACTION_PREFIX_WORDS,
    )
    cv.put(ingress[0] - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(egress[0] - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(ingress[0], 3), ingress])
    cv.pipe([egress, (egress[0], 3)])
    return cv.render()
