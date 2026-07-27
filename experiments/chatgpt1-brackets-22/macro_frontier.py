#!/usr/bin/env python3
"""Enumerate the narrow 22-square Brackets macro-placement frontier.

This is a necessary-conditions model, not a `.man` synthesizer.  It keeps the
five outer room rectangles from the accepted `gpt_brackets_17` component family,
places the 22-cell-wide CLOSE room on the top or bottom edge, stacks OPEN and
CLASSIFY in the remaining 15 rows with one routing row between them, and places
the two 3x3 I/O rooms in the remaining pockets.

A placement survives when every room has enough endpoint cells that:

* are one cell outside a non-corner wall cell;
* lie inside the 22x22 canvas;
* do not occupy another room;
* are adjacent to exactly one room wall, preventing an immediate phantom attach.

For each logical connection the script then records the independent Manhattan
lower bound between safe endpoint cells.  It does not yet enforce exact
nearest-pipe bindings, endpoint uniqueness across all nets, vertex-disjoint
routes, parser topology, or runtime behaviour.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Iterable

SIDE = 22

SIZES: dict[str, tuple[int, int]] = {
    # width, height, walls included
    "close": (22, 7),
    "classify": (16, 6),
    "open": (18, 8),
    "input": (3, 3),
    "output": (3, 3),
}

EDGES: tuple[tuple[str, str], ...] = (
    ("classify", "close"),
    ("close", "classify"),
    ("close", "output"),
    ("open", "close"),
    ("open", "classify"),
    ("input", "open"),
)


@dataclass(frozen=True, order=True)
class Placement:
    row: int
    column: int


def overlaps(
    first: Placement,
    first_size: tuple[int, int],
    second: Placement,
    second_size: tuple[int, int],
) -> bool:
    first_width, first_height = first_size
    second_width, second_height = second_size
    return not (
        first.column + first_width <= second.column
        or second.column + second_width <= first.column
        or first.row + first_height <= second.row
        or second.row + second_height <= first.row
    )


def rectangle_cells(
    placement: Placement, size: tuple[int, int]
) -> set[tuple[int, int]]:
    width, height = size
    return {
        (row, column)
        for row in range(placement.row, placement.row + height)
        for column in range(placement.column, placement.column + width)
    }


def border_cells(
    placement: Placement, size: tuple[int, int]
) -> set[tuple[int, int]]:
    width, height = size
    top = placement.row
    left = placement.column
    bottom = top + height - 1
    right = left + width - 1
    cells = {(top, column) for column in range(left, right + 1)}
    cells.update((bottom, column) for column in range(left, right + 1))
    cells.update((row, left) for row in range(top, bottom + 1))
    cells.update((row, right) for row in range(top, bottom + 1))
    return cells


def raw_endpoint_cells(
    placement: Placement, size: tuple[int, int]
) -> Iterable[tuple[int, int]]:
    width, height = size
    top = placement.row
    left = placement.column
    bottom = top + height - 1
    right = left + width - 1

    if top > 0:
        yield from ((top - 1, column) for column in range(left + 1, right))
    if bottom + 1 < SIDE:
        yield from ((bottom + 1, column) for column in range(left + 1, right))
    if left > 0:
        yield from ((row, left - 1) for row in range(top + 1, bottom))
    if right + 1 < SIDE:
        yield from ((row, right + 1) for row in range(top + 1, bottom))


def free_io_spots(
    placements: dict[str, Placement],
) -> list[Placement]:
    result: list[Placement] = []
    io_size = SIZES["input"]
    for row in range(SIDE - io_size[1] + 1):
        for column in range(SIDE - io_size[0] + 1):
            candidate = Placement(row, column)
            if all(
                not overlaps(candidate, io_size, other, SIZES[name])
                for name, other in placements.items()
            ):
                result.append(candidate)
    return result


def stack_packings() -> Iterable[dict[str, Placement]]:
    """Yield the exact stack family described in the checkpoint report."""

    for close_row in (0, SIDE - SIZES["close"][1]):
        close = Placement(close_row, 0)
        band_start = SIZES["close"][1] if close_row == 0 else 0

        for first_name, second_name in (
            ("classify", "open"),
            ("open", "classify"),
        ):
            first_height = SIZES[first_name][1]
            second_height = SIZES[second_name][1]
            first_row = band_start
            second_row = first_row + first_height + 1
            if second_row + second_height != (
                SIDE if close_row == 0 else close_row
            ):
                continue

            for first_column in range(SIDE - SIZES[first_name][0] + 1):
                for second_column in range(SIDE - SIZES[second_name][0] + 1):
                    macro = {
                        "close": close,
                        first_name: Placement(first_row, first_column),
                        second_name: Placement(second_row, second_column),
                    }
                    spots = free_io_spots(macro)
                    for input_spot, output_spot in combinations(spots, 2):
                        if overlaps(
                            input_spot,
                            SIZES["input"],
                            output_spot,
                            SIZES["output"],
                        ):
                            continue
                        yield {
                            **macro,
                            "input": input_spot,
                            "output": output_spot,
                        }


def safe_ports(
    placements: dict[str, Placement],
) -> dict[str, list[tuple[int, int]]]:
    occupied = {
        name: rectangle_cells(placement, SIZES[name])
        for name, placement in placements.items()
    }
    borders = {
        name: border_cells(placement, SIZES[name])
        for name, placement in placements.items()
    }
    all_occupied = set().union(*occupied.values())

    result: dict[str, list[tuple[int, int]]] = {}
    for name, placement in placements.items():
        candidates: list[tuple[int, int]] = []
        for row, column in raw_endpoint_cells(placement, SIZES[name]):
            cell = (row, column)
            if cell in all_occupied:
                continue
            neighbours = {
                (row - 1, column),
                (row + 1, column),
                (row, column - 1),
                (row, column + 1),
            }
            owners = {
                owner for owner, border in borders.items() if neighbours & border
            }
            if owners == {name}:
                candidates.append(cell)
        result[name] = sorted(set(candidates))
    return result


def inclusive_manhattan(
    first: tuple[int, int], second: tuple[int, int]
) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1]) + 1


def placement_json(
    placements: dict[str, Placement],
) -> dict[str, list[int]]:
    return {
        name: [placement.row, placement.column]
        for name, placement in sorted(placements.items())
    }


def enumerate_frontier() -> dict:
    examined = 0
    survivors: list[dict] = []
    degrees: defaultdict[str, int] = defaultdict(int)
    for source, destination in EDGES:
        degrees[source] += 1
        degrees[destination] += 1

    for placements in stack_packings():
        examined += 1
        ports = safe_ports(placements)
        if any(len(ports[name]) < degree for name, degree in degrees.items()):
            continue

        lower_bounds = [
            min(
                inclusive_manhattan(source, destination)
                for source in ports[source_name]
                for destination in ports[destination_name]
            )
            for source_name, destination_name in EDGES
        ]
        survivors.append(
            {
                "sumLowerBound": sum(lower_bounds),
                "maxLowerBound": max(lower_bounds),
                "perNetLowerBounds": lower_bounds,
                "placements": placement_json(placements),
                "safePortCounts": {
                    name: len(values) for name, values in sorted(ports.items())
                },
            }
        )

    survivors.sort(
        key=lambda item: (
            item["sumLowerBound"],
            item["maxLowerBound"],
            item["perNetLowerBounds"],
            tuple(
                (name, tuple(position))
                for name, position in sorted(item["placements"].items())
            ),
        )
    )
    best = survivors[0] if survivors else None
    return {
        "schemaVersion": 1,
        "canvas": [SIDE, SIDE],
        "roomArea": sum(width * height for width, height in SIZES.values()),
        "freeCellsAfterRooms": SIDE * SIDE
        - sum(width * height for width, height in SIZES.values()),
        "edges": [list(edge) for edge in EDGES],
        "stackPackingsExamined": examined,
        "safePortPackings": len(survivors),
        "bestIndependentLowerBound": best,
        "limitations": [
            "independent endpoint minima may reuse the same endpoint cell",
            "exact nearest-pipe instruction bindings are not enforced",
            "directed vertex-disjoint pipe routes are not constructed",
            "the Littleman parser is not run, so phantom pipes remain possible",
            "no behavioural or organizer-WASM claim is made",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = enumerate_frontier()
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
