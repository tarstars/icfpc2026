#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

from port_assignment_milp import (
    Binding,
    Net,
    Port,
    Problem,
    load_problem,
    problem_from_machine_ir,
    solve,
    validate,
)

HERE = Path(__file__).resolve().parent


class PortAssignmentMilpTest(unittest.TestCase):
    def test_reading_order_tie_break_is_exact(self) -> None:
        problem = Problem(
            name="tie-break",
            ports=(
                Port("n0.source", "source0", "out", ((4, 1),), (4, 1)),
                Port("n0.sink", "worker", "in", ((0, 1), (0, 3)), (0, 3)),
                Port("n1.source", "source1", "out", ((4, 3),), (4, 3)),
                Port("n1.sink", "worker", "in", ((0, 1), (0, 3)), (0, 1)),
            ),
            bindings=(Binding((1, 2), "n0.sink", ("n0.sink", "n1.sink")),),
            nets=(
                Net("n0", "n0.source", "n0.sink", max_cells=7, weight=0),
                Net("n1", "n1.source", "n1.sink", max_cells=7, weight=0),
            ),
        )
        result = solve(problem, time_limit=5)
        self.assertEqual(result["ports"]["n0.sink"], [0, 1])
        self.assertEqual(result["ports"]["n1.sink"], [0, 3])

    def test_brackets10_replays_six_cell_gap_reduction(self) -> None:
        problem = load_problem(HERE / "brackets_10_port_instance.json")
        result = solve(problem, time_limit=10)
        self.assertEqual(result["objective_weighted_cells"], 4)
        self.assertEqual([net["cells"] for net in result["nets"][:2]], [2, 2])
        self.assertEqual(result["mip_gap"], 0.0)

    def test_brackets11_is_at_endpoint_only_lower_bound(self) -> None:
        problem = load_problem(HERE / "brackets_11_port_instance.json")
        result = solve(problem, time_limit=10)
        self.assertEqual(result["objective_weighted_cells"], 4)
        self.assertEqual(result["ports"]["p0.source"], [7, 6])
        self.assertEqual(result["ports"]["p0.sink"], [8, 6])
        self.assertEqual(result["ports"]["p1.source"], [8, 8])
        self.assertEqual(result["ports"]["p1.sink"], [7, 8])

    def test_machine_ir_adapter_uses_same_wall_and_resolution_map(self) -> None:
        payload = {
            "version": 1,
            "sha256": "synthetic",
            "rooms": [
                {"top": 1, "left": 1, "bottom": 5, "right": 7, "kind": "room"},
                {"top": 8, "left": 1, "bottom": 10, "right": 3, "kind": "output"},
                {"top": 8, "left": 5, "bottom": 10, "right": 7, "kind": "output"},
            ],
            "pipes": [
                {"cells": [[6, 2], [7, 2]], "source": 0, "dest": 1},
                {"cells": [[6, 6], [7, 6]], "source": 0, "dest": 2},
            ],
            "resolution": {
                "3,2": {"op": "s", "pipe": 0},
                "3,6": {"op": "s", "pipe": 1},
                "3,4": {"op": "S", "pipes": [0, 1]},
            },
        }
        problem = problem_from_machine_ir(
            payload, movable_pipes={0, 1}, transport_pipes={0, 1}
        )
        ports = {port.name: port for port in problem.ports}
        self.assertEqual(ports["p0.source"].candidates[0], (6, 2))
        self.assertEqual(ports["p0.source"].candidates[-1], (6, 6))
        self.assertEqual(len(problem.bindings), 2)
        self.assertEqual(problem.nets[0].weight, 1)

    def test_validate_rejects_wrong_binding(self) -> None:
        problem = load_problem(HERE / "brackets_11_port_instance.json")
        selected = {port.name: port.incumbent for port in problem.ports}
        selected["p1.sink"] = (7, 14)
        with self.assertRaises(AssertionError):
            validate(problem, selected)


if __name__ == "__main__":
    unittest.main()
