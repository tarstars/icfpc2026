#!/usr/bin/env python3
"""Focused regression tests for the experimental MILP floorplanner."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from floorplan_milp import (
    FloorplanSolution,
    Net,
    PlacedRectangle,
    Port,
    Rectangle,
    load_instance,
    solve_floorplan,
    validate_solution,
)


HERE = Path(__file__).resolve().parent


class FloorplanMilpTest(unittest.TestCase):
    def test_two_rectangles_stack_into_four_square(self) -> None:
        solution = solve_floorplan(
            [Rectangle("a", 3, 2), Rectangle("b", 3, 2)],
            time_limit=5,
        )
        self.assertEqual(solution.side, 4)
        self.assertEqual(solution.mip_gap, 0.0)

    def test_net_distance_is_inclusive_pipe_cell_count(self) -> None:
        rectangles = [Rectangle("a", 3, 3), Rectangle("b", 3, 3)]
        net = Net(
            "ab",
            Port("a", 3, 1),
            Port("b", -1, 1),
            max_cells=2,
        )
        solution = solve_floorplan(rectangles, [net], time_limit=5)
        by_name = {rect.name: rect for rect in solution.rectangles}
        a_port = (by_name["a"].x + 3, by_name["a"].y + 1)
        b_port = (by_name["b"].x - 1, by_name["b"].y + 1)
        cells = abs(a_port[0] - b_port[0]) + abs(a_port[1] - b_port[1]) + 1
        self.assertLessEqual(cells, 2)


    def test_known_tcp_38_square_layout_satisfies_the_model(self) -> None:
        rectangles, nets, payload = load_instance(HERE / "tcp_room_instance.json")
        known = FloorplanSolution(
            side=38,
            lower_bound=28,
            clearance=0,
            endpoint_policy="exclude-room-cells-and-noncorner-wall-grazing",
            rectangles=(
                PlacedRectangle("pump", 0, 0, 24, 23),
                PlacedRectangle("output", 17, 23, 3, 3),
                PlacedRectangle("input", 33, 24, 3, 3),
                PlacedRectangle("forwarder", 6, 28, 18, 7),
                PlacedRectangle("splitter", 25, 29, 13, 6),
            ),
            solver="preserved tcp_02 geometry",
            status="known good",
            mip_gap=None,
            objective=38.0,
        )
        self.assertEqual(payload["metadata"]["known_full_program_side"], 38)
        validate_solution(rectangles, nets, known)

    def test_tcp_room_endpoint_obstacle_model_has_exact_35_square_optimum(self) -> None:
        rectangles, nets, payload = load_instance(HERE / "tcp_room_instance.json")
        solution = solve_floorplan(
            rectangles,
            nets,
            clearance=int(payload["clearance"]),
            time_limit=30,
        )
        self.assertEqual(solution.side, 35)
        self.assertEqual(solution.mip_gap, 0.0)

    def test_cli_solution_fixture_matches_model(self) -> None:
        fixture = json.loads((HERE / "tcp_room_solution.json").read_text())
        self.assertEqual(fixture["side"], 35)
        self.assertEqual(fixture["mip_gap"], 0.0)
        self.assertEqual(
            fixture["endpoint_policy"],
            "exclude-room-cells-and-noncorner-wall-grazing",
        )
        self.assertEqual(len(fixture["rectangles"]), 5)


if __name__ == "__main__":
    unittest.main()
