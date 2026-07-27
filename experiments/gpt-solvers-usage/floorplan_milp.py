#!/usr/bin/env python3
"""Exact small-instance floorplanning with SciPy/HiGHS MILP.

The model places fixed-orientation rectangular rooms on integer coordinates and
minimizes the Littleman footprint term ``max(width, height)``.  Optional ports
and per-net ``max_cells`` constraints bound the Manhattan distance between pipe
endpoints, a necessary (but not sufficient) condition for routing a pipe without
making it longer than a known-good route.

This is deliberately an experiment, not a package dependency.  It uses the
SciPy HiGHS MILP backend so the model can be evaluated before the project
chooses between CP-SAT, SMT, and custom search.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import csr_matrix, lil_matrix
except ImportError as exc:  # pragma: no cover - exercised only without SciPy
    raise SystemExit(
        "floorplan_milp.py requires SciPy with scipy.optimize.milp; "
        "install experiments/gpt-solvers-usage/requirements.txt"
    ) from exc


@dataclass(frozen=True)
class Rectangle:
    name: str
    width: int
    height: int

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("rectangle name must be non-empty")
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"rectangle {self.name!r} must have positive size")


@dataclass(frozen=True)
class Port:
    rectangle: str
    dx: int
    dy: int


@dataclass(frozen=True)
class Net:
    name: str
    source: Port
    sink: Port
    max_cells: int

    def __post_init__(self) -> None:
        if self.max_cells < 2:
            raise ValueError(f"net {self.name!r} must allow at least two cells")


@dataclass(frozen=True)
class PlacedRectangle:
    name: str
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class FloorplanSolution:
    side: int
    lower_bound: int
    clearance: int
    endpoint_policy: str
    rectangles: tuple[PlacedRectangle, ...]
    solver: str
    status: str
    mip_gap: float | None
    objective: float

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["rectangles"] = [asdict(rect) for rect in self.rectangles]
        return data


class _Rows:
    def __init__(self) -> None:
        self.coefficients: list[dict[int, float]] = []
        self.lower: list[float] = []
        self.upper: list[float] = []

    def add(
        self,
        coefficients: Mapping[int, float],
        *,
        lower: float = -math.inf,
        upper: float = math.inf,
    ) -> None:
        self.coefficients.append(dict(coefficients))
        self.lower.append(lower)
        self.upper.append(upper)

    def constraint(self, variable_count: int) -> LinearConstraint:
        matrix = lil_matrix((len(self.coefficients), variable_count), dtype=float)
        for row, coefficients in enumerate(self.coefficients):
            for column, value in coefficients.items():
                if value:
                    matrix[row, column] = value
        return LinearConstraint(
            csr_matrix(matrix),
            np.asarray(self.lower, dtype=float),
            np.asarray(self.upper, dtype=float),
        )


def _port_extent(ports: Iterable[Port]) -> int:
    return max((max(abs(port.dx), abs(port.dy)) for port in ports), default=0)


def _safe_side_upper_bound(
    rectangles: Sequence[Rectangle], ports: Sequence[Port], clearance: int
) -> int:
    # A horizontal row is always a legal rectangle packing.  Extra border makes
    # room for ports one or more cells outside the room wall.
    border = _port_extent(ports) + 1
    return (
        sum(rect.width for rect in rectangles)
        + clearance * max(0, len(rectangles) - 1)
        + 2 * border
    )


def solve_floorplan(
    rectangles: Sequence[Rectangle],
    nets: Sequence[Net] = (),
    *,
    clearance: int = 0,
    time_limit: float = 60.0,
) -> FloorplanSolution:
    """Solve a fixed-orientation square-envelope floorplan exactly.

    ``clearance`` is the number of empty grid columns/rows required between any
    two room rectangles.  A zero-clearance model permits adjacent room walls,
    matching accepted Littleman layouts.

    Every declared endpoint is kept out of unrelated room cells and away from
    their non-corner side-wall attachment cells.  Corner grazing remains legal,
    matching the preserved accepted TCP layout and ``room_ports.perimeter``.

    A net constraint ``max_cells=L`` enforces endpoint Manhattan distance
    ``<= L-1``.  This is necessary for an orthogonal route of at most ``L``
    cells, but it does not model obstacles, endpoint arrow direction, pipe
    disjointness, nearest-pipe binding, capacity lower bounds, or timing.
    """

    if not rectangles:
        raise ValueError("at least one rectangle is required")
    if clearance < 0:
        raise ValueError("clearance must be non-negative")
    if time_limit <= 0:
        raise ValueError("time_limit must be positive")

    rectangle_names = [rect.name for rect in rectangles]
    if len(set(rectangle_names)) != len(rectangle_names):
        raise ValueError("rectangle names must be unique")
    rectangle_index = {name: index for index, name in enumerate(rectangle_names)}

    ports = list(dict.fromkeys(
        port for net in nets for port in (net.source, net.sink)
    ))
    for port in ports:
        if port.rectangle not in rectangle_index:
            raise ValueError(f"unknown rectangle in port: {port.rectangle!r}")
        rectangle = rectangles[rectangle_index[port.rectangle]]
        on_vertical_wall = (
            port.dx in (-1, rectangle.width)
            and 0 < port.dy < rectangle.height - 1
        )
        on_horizontal_wall = (
            port.dy in (-1, rectangle.height)
            and 0 < port.dx < rectangle.width - 1
        )
        if not (on_vertical_wall or on_horizontal_wall):
            raise ValueError(
                f"port {port!r} must be one cell outside a non-corner wall cell"
            )

    count = len(rectangles)
    pairs = list(combinations(range(count), 2))
    # A pipe cell must not occupy an unrelated room or touch one of its
    # non-corner wall cells.  Represent that forbidden shape as up to five
    # axis-aligned boxes: the room itself plus four one-cell side strips.
    port_obstacle_boxes: list[tuple[Port, int, int, int, int, int]] = []
    for port in ports:
        for other_index, other in enumerate(rectangles):
            if other.name == port.rectangle:
                continue
            boxes = [(0, other.width - 1, 0, other.height - 1)]
            if other.width >= 3:
                boxes.extend(
                    [
                        (1, other.width - 2, -1, -1),
                        (1, other.width - 2, other.height, other.height),
                    ]
                )
            if other.height >= 3:
                boxes.extend(
                    [
                        (-1, -1, 1, other.height - 2),
                        (other.width, other.width, 1, other.height - 2),
                    ]
                )
            for x_low, x_high, y_low, y_high in boxes:
                port_obstacle_boxes.append(
                    (port, other_index, x_low, x_high, y_low, y_high)
                )
    port_pairs = list(combinations(ports, 2))

    x_index = list(range(count))
    y_index = list(range(count, 2 * count))
    side_index = 2 * count
    binary_start = side_index + 1
    disjunction_count = (
        len(pairs) + len(port_obstacle_boxes) + len(port_pairs)
    )
    variable_count = binary_start + 4 * disjunction_count

    objective = np.zeros(variable_count, dtype=float)
    objective[side_index] = 1.0
    integrality = np.ones(variable_count, dtype=np.uint8)

    total_area = sum(rect.width * rect.height for rect in rectangles)
    lower_bound = max(
        max(max(rect.width, rect.height) for rect in rectangles),
        math.isqrt(total_area - 1) + 1,
    )
    upper_bound = _safe_side_upper_bound(rectangles, ports, clearance)

    lower = np.zeros(variable_count, dtype=float)
    upper = np.full(variable_count, np.inf, dtype=float)
    lower[side_index] = lower_bound
    upper[side_index] = upper_bound
    for index, rect in enumerate(rectangles):
        upper[x_index[index]] = upper_bound - rect.width
        upper[y_index[index]] = upper_bound - rect.height
    upper[binary_start:] = 1.0

    rows = _Rows()

    # Room cells must fit within the square [0, side-1]^2.
    for index, rect in enumerate(rectangles):
        rows.add({x_index[index]: 1, side_index: -1}, upper=-rect.width)
        rows.add({y_index[index]: 1, side_index: -1}, upper=-rect.height)

    # Every declared port cell must also stay inside the scored envelope.
    for port in ports:
        index = rectangle_index[port.rectangle]
        rows.add({x_index[index]: 1}, lower=-port.dx)
        rows.add(
            {x_index[index]: 1, side_index: -1},
            upper=-port.dx - 1,
        )
        rows.add({y_index[index]: 1}, lower=-port.dy)
        rows.add(
            {y_index[index]: 1, side_index: -1},
            upper=-port.dy - 1,
        )

    # Pairwise disjunction: exactly one selected relation is enough to prove
    # non-overlap.  Other relations may also happen geometrically.
    big_m = upper_bound + max(
        max(rect.width, rect.height) for rect in rectangles
    ) + clearance
    disjunction = 0

    def binary_group() -> list[int]:
        nonlocal disjunction
        group = [
            binary_start + 4 * disjunction + direction for direction in range(4)
        ]
        disjunction += 1
        rows.add({index: 1 for index in group}, lower=1, upper=1)
        return group

    for left, right in pairs:
        binary = binary_group()
        rows.add(
            {
                x_index[left]: 1,
                x_index[right]: -1,
                binary[0]: big_m,
            },
            upper=big_m - rectangles[left].width - clearance,
        )
        rows.add(
            {
                x_index[right]: 1,
                x_index[left]: -1,
                binary[1]: big_m,
            },
            upper=big_m - rectangles[right].width - clearance,
        )
        rows.add(
            {
                y_index[left]: 1,
                y_index[right]: -1,
                binary[2]: big_m,
            },
            upper=big_m - rectangles[left].height - clearance,
        )
        rows.add(
            {
                y_index[right]: 1,
                y_index[left]: -1,
                binary[3]: big_m,
            },
            upper=big_m - rectangles[right].height - clearance,
        )

    # Exclude each endpoint from every forbidden box of every unrelated room.
    # A four-way disjunction says the point is left, right, above, or below.
    for port, other, x_low, x_high, y_low, y_high in port_obstacle_boxes:
        owner = rectangle_index[port.rectangle]
        binary = binary_group()
        rows.add(
            {x_index[owner]: 1, x_index[other]: -1, binary[0]: big_m},
            upper=big_m + x_low - port.dx - 1,
        )
        rows.add(
            {x_index[other]: 1, x_index[owner]: -1, binary[1]: big_m},
            upper=big_m + port.dx - x_high - 1,
        )
        rows.add(
            {y_index[owner]: 1, y_index[other]: -1, binary[2]: big_m},
            upper=big_m + y_low - port.dy - 1,
        )
        rows.add(
            {y_index[other]: 1, y_index[owner]: -1, binary[3]: big_m},
            upper=big_m + port.dy - y_high - 1,
        )

    # Distinct logical endpoints need distinct cells.  This also enforces the
    # language's minimum two-cell pipe for every source/sink pair.
    for first, second in port_pairs:
        first_owner = rectangle_index[first.rectangle]
        second_owner = rectangle_index[second.rectangle]
        binary = binary_group()
        rows.add(
            {
                x_index[first_owner]: 1,
                x_index[second_owner]: -1,
                binary[0]: big_m,
            },
            upper=big_m - first.dx + second.dx - 1,
        )
        rows.add(
            {
                x_index[second_owner]: 1,
                x_index[first_owner]: -1,
                binary[1]: big_m,
            },
            upper=big_m - second.dx + first.dx - 1,
        )
        rows.add(
            {
                y_index[first_owner]: 1,
                y_index[second_owner]: -1,
                binary[2]: big_m,
            },
            upper=big_m - first.dy + second.dy - 1,
        )
        rows.add(
            {
                y_index[second_owner]: 1,
                y_index[first_owner]: -1,
                binary[3]: big_m,
            },
            upper=big_m - second.dy + first.dy - 1,
        )

    assert disjunction == disjunction_count

    # |dx| + |dy| <= D is equivalent to all four signed inequalities
    # +/-dx +/-dy <= D.  Coordinates include each port's room-relative offset.
    for net in nets:
        source_index = rectangle_index[net.source.rectangle]
        sink_index = rectangle_index[net.sink.rectangle]
        maximum_distance = net.max_cells - 1
        for x_sign, y_sign in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            coefficients: dict[int, float] = {}
            coefficients[x_index[source_index]] = x_sign
            coefficients[x_index[sink_index]] = -x_sign
            coefficients[y_index[source_index]] = (
                coefficients.get(y_index[source_index], 0) + y_sign
            )
            coefficients[y_index[sink_index]] = (
                coefficients.get(y_index[sink_index], 0) - y_sign
            )
            offset = (
                x_sign * (net.source.dx - net.sink.dx)
                + y_sign * (net.source.dy - net.sink.dy)
            )
            rows.add(coefficients, upper=maximum_distance - offset)

    result = milp(
        objective,
        integrality=integrality,
        bounds=Bounds(lower, upper),
        constraints=rows.constraint(variable_count),
        options={
            "time_limit": float(time_limit),
            "mip_rel_gap": 0.0,
            "presolve": True,
        },
    )

    if result.x is None:
        raise RuntimeError(f"MILP produced no feasible placement: {result.message}")
    if not result.success:
        raise RuntimeError(
            "MILP stopped before proving optimality; "
            f"status={result.status}, message={result.message}, "
            f"gap={getattr(result, 'mip_gap', None)}"
        )

    coordinates = [
        (int(round(result.x[x_index[index]])), int(round(result.x[y_index[index]])))
        for index in range(count)
    ]
    side = int(round(result.x[side_index]))
    placed = tuple(
        PlacedRectangle(rect.name, x, y, rect.width, rect.height)
        for rect, (x, y) in zip(rectangles, coordinates)
    )
    solution = FloorplanSolution(
        side=side,
        lower_bound=lower_bound,
        clearance=clearance,
        endpoint_policy="exclude-room-cells-and-noncorner-wall-grazing",
        rectangles=placed,
        solver="scipy.optimize.milp/HiGHS",
        status=str(result.message),
        mip_gap=(
            None
            if getattr(result, "mip_gap", None) is None
            else float(result.mip_gap)
        ),
        objective=float(result.fun),
    )
    validate_solution(rectangles, nets, solution)
    return solution


def validate_solution(
    rectangles: Sequence[Rectangle],
    nets: Sequence[Net],
    solution: FloorplanSolution,
) -> None:
    """Raise ``AssertionError`` if a returned solution violates the model."""

    by_name = {rect.name: rect for rect in solution.rectangles}
    assert set(by_name) == {rect.name for rect in rectangles}
    assert solution.side >= solution.lower_bound

    for rect in solution.rectangles:
        assert rect.x >= 0 and rect.y >= 0
        assert rect.x + rect.width <= solution.side
        assert rect.y + rect.height <= solution.side

    for first, second in combinations(solution.rectangles, 2):
        separated = (
            first.x + first.width + solution.clearance <= second.x
            or second.x + second.width + solution.clearance <= first.x
            or first.y + first.height + solution.clearance <= second.y
            or second.y + second.height + solution.clearance <= first.y
        )
        assert separated, (first, second)

    endpoints: dict[Port, tuple[int, int]] = {}
    for net in nets:
        source_room = by_name[net.source.rectangle]
        sink_room = by_name[net.sink.rectangle]
        source = (source_room.x + net.source.dx, source_room.y + net.source.dy)
        sink = (sink_room.x + net.sink.dx, sink_room.y + net.sink.dy)
        for port, (x, y) in ((net.source, source), (net.sink, sink)):
            assert 0 <= x < solution.side
            assert 0 <= y < solution.side
            endpoints[port] = (x, y)
            for other in solution.rectangles:
                if other.name == port.rectangle:
                    continue
                in_room = (
                    other.x <= x <= other.x + other.width - 1
                    and other.y <= y <= other.y + other.height - 1
                )
                above_or_below_side = (
                    other.x + 1 <= x <= other.x + other.width - 2
                    and y in (other.y - 1, other.y + other.height)
                )
                left_or_right_side = (
                    other.y + 1 <= y <= other.y + other.height - 2
                    and x in (other.x - 1, other.x + other.width)
                )
                assert not (
                    in_room or above_or_below_side or left_or_right_side
                ), (port, other)
        cells = abs(source[0] - sink[0]) + abs(source[1] - sink[1]) + 1
        assert 2 <= cells <= net.max_cells, (net.name, cells, net.max_cells)

    assert len(set(endpoints.values())) == len(endpoints), endpoints


def load_instance(path: Path) -> tuple[list[Rectangle], list[Net], dict[str, Any]]:
    payload = json.loads(path.read_text())
    rectangles = [Rectangle(**item) for item in payload["rectangles"]]

    def port(data: Mapping[str, Any]) -> Port:
        return Port(
            rectangle=str(data["rectangle"]),
            dx=int(data["dx"]),
            dy=int(data["dy"]),
        )

    nets = [
        Net(
            name=str(item["name"]),
            source=port(item["source"]),
            sink=port(item["sink"]),
            max_cells=int(item["max_cells"]),
        )
        for item in payload.get("nets", [])
    ]
    return rectangles, nets, payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--clearance", type=int)
    parser.add_argument("--time-limit", type=float, default=60.0)
    args = parser.parse_args(argv)

    rectangles, nets, payload = load_instance(args.instance)
    clearance = (
        args.clearance
        if args.clearance is not None
        else int(payload.get("clearance", 0))
    )
    solution = solve_floorplan(
        rectangles,
        nets,
        clearance=clearance,
        time_limit=args.time_limit,
    )
    encoded = json.dumps(solution.to_json(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
