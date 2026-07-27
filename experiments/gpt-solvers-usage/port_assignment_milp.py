#!/usr/bin/env python3
"""Exact same-wall port assignment for fixed Littleman room placements.

The MILP selects one exterior cell per endpoint, preserves exact nearest-pipe
bindings (distance,row,column), and minimizes annotated transport-pipe length.
It proves endpoint lower bounds, not detailed route feasibility or behavior.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import csr_matrix, lil_matrix
except ImportError as exc:  # pragma: no cover
    raise SystemExit("requires numpy and scipy.optimize.milp") from exc

Cell = tuple[int, int]


@dataclass(frozen=True)
class Port:
    name: str
    room: str
    direction: str
    candidates: tuple[Cell, ...]
    incumbent: Cell


@dataclass(frozen=True)
class Binding:
    op: Cell
    port: str
    competitors: tuple[str, ...]


@dataclass(frozen=True)
class Net:
    name: str
    source: str
    sink: str
    min_cells: int = 2
    max_cells: int | None = None
    weight: int = 1


@dataclass(frozen=True)
class Problem:
    name: str
    ports: tuple[Port, ...]
    bindings: tuple[Binding, ...]
    nets: tuple[Net, ...]


class Rows:
    def __init__(self) -> None:
        self.items: list[tuple[dict[int, float], float, float]] = []

    def add(self, coeffs: Mapping[int, float], lo=-math.inf, hi=math.inf) -> None:
        self.items.append((dict(coeffs), lo, hi))

    def build(self, n: int) -> LinearConstraint:
        a = lil_matrix((len(self.items), n), dtype=float)
        for row, (coeffs, _lo, _hi) in enumerate(self.items):
            for column, value in coeffs.items():
                if value:
                    a[row, column] = value
        return LinearConstraint(
            csr_matrix(a),
            np.asarray([item[1] for item in self.items]),
            np.asarray([item[2] for item in self.items]),
        )


def expand_candidates(data: Any) -> tuple[Cell, ...]:
    if isinstance(data, list):
        cells = [tuple(map(int, cell)) for cell in data]
    elif "positions" in data:
        cells = [tuple(map(int, cell)) for cell in data["positions"]]
    elif "row" in data:
        lo, hi = map(int, data["columns"])
        cells = [(int(data["row"]), c) for c in range(lo, hi + 1)]
    elif "column" in data:
        lo, hi = map(int, data["rows"])
        cells = [(r, int(data["column"])) for r in range(lo, hi + 1)]
    else:
        raise ValueError(f"unsupported candidates: {data!r}")
    cells = tuple(dict.fromkeys(cells))
    if not cells:
        raise ValueError("empty candidate set")
    return cells


def load_problem(path: Path) -> Problem:
    data = json.loads(path.read_text())
    ports = []
    for item in data["ports"]:
        candidates = expand_candidates(item["candidates"])
        incumbent = tuple(map(int, item.get("incumbent", candidates[0])))
        if incumbent not in candidates:
            raise ValueError(f"incumbent outside candidates: {item['name']}")
        direction = str(item["direction"])
        if direction not in {"in", "out"}:
            raise ValueError(f"bad direction: {direction}")
        ports.append(
            Port(str(item["name"]), str(item["room"]), direction, candidates, incumbent)
        )
    known = {port.name for port in ports}
    if len(known) != len(ports):
        raise ValueError("duplicate port name")
    bindings = []
    for item in data.get("bindings", []):
        competitors = tuple(map(str, item["competitors"]))
        target = str(item["port"])
        if target not in competitors or any(name not in known for name in competitors):
            raise ValueError(f"bad binding: {item!r}")
        bindings.append(Binding(tuple(map(int, item["op"])), target, competitors))
    nets = []
    for item in data["nets"]:
        source, sink = str(item["source"]), str(item["sink"])
        if source not in known or sink not in known:
            raise ValueError(f"bad net endpoints: {item!r}")
        maximum = item.get("max_cells")
        nets.append(
            Net(
                str(item["name"]),
                source,
                sink,
                int(item.get("min_cells", 2)),
                None if maximum is None else int(maximum),
                int(item.get("weight", 1)),
            )
        )
    return Problem(str(data.get("name", path.stem)), tuple(ports), tuple(bindings), tuple(nets))


def nearest_key(op: Cell, endpoint: Cell) -> tuple[int, int, int]:
    return (abs(op[0] - endpoint[0]) + abs(op[1] - endpoint[1]), *endpoint)


def pipe_cells(source: Cell, sink: Cell) -> int:
    return abs(source[0] - sink[0]) + abs(source[1] - sink[1]) + 1


def same_wall(room: Mapping[str, Any], endpoint: Cell) -> tuple[Cell, ...]:
    top, left = int(room["top"]), int(room["left"])
    bottom, right = int(room["bottom"]), int(room["right"])
    row, column = endpoint
    if row == top - 1 and left < column < right:
        return tuple((row, c) for c in range(left + 1, right))
    if row == bottom + 1 and left < column < right:
        return tuple((row, c) for c in range(left + 1, right))
    if column == left - 1 and top < row < bottom:
        return tuple((r, column) for r in range(top + 1, bottom))
    if column == right + 1 and top < row < bottom:
        return tuple((r, column) for r in range(top + 1, bottom))
    return (endpoint,)  # keep corner attachments fixed


def problem_from_machine_ir(
    data: Mapping[str, Any], movable_pipes: set[int], transport_pipes: set[int]
) -> Problem:
    """Adapt ``littleman.ir_export.machine_ir`` without duplicating parsing."""
    rooms, pipes = list(data["rooms"]), list(data["pipes"])
    ports = []
    by_room_direction: dict[tuple[int, str], list[str]] = {}
    for index, pipe in enumerate(pipes):
        if pipe.get("source") is None or pipe.get("dest") is None:
            raise ValueError(f"pipe {index} lacks a room endpoint")
        cells = [tuple(map(int, cell)) for cell in pipe["cells"]]
        if len(cells) < 2:
            raise ValueError(f"pipe {index} is shorter than two cells")
        specs = (
            ("source", int(pipe["source"]), "out", cells[0]),
            ("sink", int(pipe["dest"]), "in", cells[-1]),
        )
        for suffix, room_index, direction, incumbent in specs:
            name = f"p{index}.{suffix}"
            candidates = same_wall(rooms[room_index], incumbent) if index in movable_pipes else (incumbent,)
            ports.append(Port(name, f"room{room_index}", direction, candidates, incumbent))
            by_room_direction.setdefault((room_index, direction), []).append(name)

    def room_of(cell: Cell) -> int:
        row, column = cell
        matches = [
            i
            for i, room in enumerate(rooms)
            if int(room["top"]) < row < int(room["bottom"])
            and int(room["left"]) < column < int(room["right"])
        ]
        if len(matches) != 1:
            raise ValueError(f"resolution cell {cell} belongs to {matches}")
        return matches[0]

    bindings = []
    for encoded, entry in sorted(data.get("resolution", {}).items()):
        op = str(entry["op"])
        if op not in "srq":
            continue
        cell = tuple(map(int, encoded.split(",")))
        index = entry.get("pipe")
        if index is None:
            raise ValueError(f"nearest op {encoded} has no pipe")
        direction = "out" if op == "s" else "in"
        suffix = "source" if direction == "out" else "sink"
        room_index = room_of(cell)
        bindings.append(
            Binding(
                cell,
                f"p{int(index)}.{suffix}",
                tuple(by_room_direction[(room_index, direction)]),
            )
        )
    nets = tuple(
        Net(
            f"p{i}",
            f"p{i}.source",
            f"p{i}.sink",
            2,
            len(pipe["cells"]),
            int(i in transport_pipes),
        )
        for i, pipe in enumerate(pipes)
    )
    return Problem(f"machine-ir-{data.get('sha256', 'unhashed')}", tuple(ports), tuple(bindings), nets)


def solve(problem: Problem, time_limit: float = 30.0) -> dict[str, Any]:
    if time_limit <= 0:
        raise ValueError("time_limit must be positive")
    by_name = {port.name: port for port in problem.ports}
    x: dict[tuple[str, int], int] = {}
    nvars = 0
    for port in problem.ports:
        for i in range(len(port.candidates)):
            x[(port.name, i)] = nvars
            nvars += 1

    pairs: dict[str, list[tuple[int, int, int, int]]] = {}
    for net in problem.nets:
        allowed = []
        for i, source in enumerate(by_name[net.source].candidates):
            for j, sink in enumerate(by_name[net.sink].candidates):
                cells = pipe_cells(source, sink)
                if cells < net.min_cells or (net.max_cells is not None and cells > net.max_cells):
                    continue
                allowed.append((i, j, cells, nvars))
                nvars += 1
        if not allowed:
            raise ValueError(f"net {net.name} has no compatible pair")
        pairs[net.name] = allowed

    rows = Rows()
    for port in problem.ports:
        rows.add({x[(port.name, i)]: 1 for i in range(len(port.candidates))}, 1, 1)
    for ai, a in enumerate(problem.ports):
        for b in problem.ports[ai + 1 :]:
            bpos = {cell: i for i, cell in enumerate(b.candidates)}
            for i, cell in enumerate(a.candidates):
                if cell in bpos:
                    rows.add({x[(a.name, i)]: 1, x[(b.name, bpos[cell])]: 1}, hi=1)

    for binding in problem.bindings:
        target = by_name[binding.port]
        for other_name in binding.competitors:
            if other_name == binding.port:
                continue
            other = by_name[other_name]
            if (other.room, other.direction) != (target.room, target.direction):
                raise ValueError(f"mixed binding group: {binding!r}")
            for i, target_cell in enumerate(target.candidates):
                for j, other_cell in enumerate(other.candidates):
                    if nearest_key(binding.op, other_cell) < nearest_key(binding.op, target_cell):
                        rows.add({x[(target.name, i)]: 1, x[(other.name, j)]: 1}, hi=1)

    primary = np.zeros(nvars)
    for net in problem.nets:
        allowed = pairs[net.name]
        rows.add({variable: 1 for _i, _j, _cells, variable in allowed}, 1, 1)
        for i in range(len(by_name[net.source].candidates)):
            coeffs = {x[(net.source, i)]: -1}
            coeffs.update({v: 1 for si, _sj, _c, v in allowed if si == i})
            rows.add(coeffs, 0, 0)
        for j in range(len(by_name[net.sink].candidates)):
            coeffs = {x[(net.sink, j)]: -1}
            coeffs.update({v: 1 for _si, sj, _c, v in allowed if sj == j})
            rows.add(coeffs, 0, 0)
        for _i, _j, cells, variable in allowed:
            primary[variable] = net.weight * cells

    integrality = np.ones(nvars, dtype=np.uint8)
    bounds = Bounds(np.zeros(nvars), np.ones(nvars))
    options = {"time_limit": float(time_limit), "mip_rel_gap": 0.0, "presolve": True}
    first = milp(primary, integrality=integrality, bounds=bounds, constraints=rows.build(nvars), options=options)
    if first.x is None or not first.success:
        raise RuntimeError(f"primary MILP failed: {first.message}")
    optimum = int(round(first.fun))

    rows.add({i: value for i, value in enumerate(primary) if value}, optimum, optimum)
    secondary = np.zeros(nvars)
    for port in problem.ports:
        for i, cell in enumerate(port.candidates):
            move = abs(cell[0] - port.incumbent[0]) + abs(cell[1] - port.incumbent[1])
            secondary[x[(port.name, i)]] = int(cell != port.incumbent) * 1_000_000 + move * 1_000 + i
    second = milp(secondary, integrality=integrality, bounds=bounds, constraints=rows.build(nvars), options=options)
    if second.x is None or not second.success:
        raise RuntimeError(f"secondary MILP failed: {second.message}")

    selected = {}
    for port in problem.ports:
        chosen = [i for i in range(len(port.candidates)) if second.x[x[(port.name, i)]] > 0.5]
        if len(chosen) != 1:
            raise AssertionError((port.name, chosen))
        selected[port.name] = port.candidates[chosen[0]]
    validate(problem, selected)
    nets = [
        {
            "name": net.name,
            "source": list(selected[net.source]),
            "sink": list(selected[net.sink]),
            "cells": pipe_cells(selected[net.source], selected[net.sink]),
            "weight": net.weight,
        }
        for net in problem.nets
    ]
    return {
        "problem": problem.name,
        "objective_weighted_cells": optimum,
        "ports": {name: list(cell) for name, cell in sorted(selected.items())},
        "nets": nets,
        "solver": "scipy.optimize.milp/HiGHS",
        "status": str(second.message),
        "mip_gap": None if getattr(second, "mip_gap", None) is None else float(second.mip_gap),
        "limitations": [
            "fixed room positions",
            "endpoint and Manhattan-length model only",
            "detailed disjoint routing and parser/judge gates still required",
        ],
    }


def validate(problem: Problem, selected: Mapping[str, Cell]) -> None:
    if len(set(selected.values())) != len(selected):
        raise AssertionError("duplicate endpoint cell")
    by_name = {port.name: port for port in problem.ports}
    for binding in problem.bindings:
        chosen = min(binding.competitors, key=lambda name: nearest_key(binding.op, selected[name]))
        if chosen != binding.port:
            raise AssertionError((binding, chosen))
    for net in problem.nets:
        cells = pipe_cells(selected[net.source], selected[net.sink])
        if cells < net.min_cells or (net.max_cells is not None and cells > net.max_cells):
            raise AssertionError((net.name, cells))
        if by_name[net.source].direction != "out" or by_name[net.sink].direction != "in":
            raise AssertionError((net.name, "bad direction"))


def parse_indices(value: str) -> set[int]:
    return {int(part) for part in value.split(",") if part.strip()}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument("--machine-ir", action="store_true")
    parser.add_argument("--movable-pipes", default="")
    parser.add_argument("--transport-pipes", default="")
    args = parser.parse_args(argv)
    if args.machine_ir:
        problem = problem_from_machine_ir(
            json.loads(args.instance.read_text()),
            parse_indices(args.movable_pipes),
            parse_indices(args.transport_pipes),
        )
    else:
        problem = load_problem(args.instance)
    encoded = json.dumps(solve(problem, args.time_limit), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
