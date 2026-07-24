from pathlib import Path

from littleman.canvas import Canvas
from littleman.judge import judge_problem
from littleman.sim import Machine
from littleman.sort import (
    build_sort,
    build_sort_compact_geometry,
    build_sort_loader_room,
    build_sort_stage_room,
)

REPO = Path(__file__).resolve().parent.parent


def _stage_harness() -> str:
    room = build_sort_stage_room()
    canvas = Canvas()
    canvas.put(0, 5, room)
    canvas.put(3, 0, ["+-+", "|I|", "+-+"])
    canvas.pipe([(4, 3), (4, 4)])
    canvas.put(3, 27, ["+-+", "|O|", "+-+"])
    canvas.pipe([(4, 25), (4, 26)])
    return canvas.render()


def test_sort_stage_keeps_max_forwards_min_and_resets():
    machine = Machine.parse(_stage_harness())
    result = machine.run(inputs=[5, 2, 7, -1, 3], max_ticks=2_000)
    assert result.output[:5] == [0, 2, 5, -1, 0]
    assert machine.men[0].B == 3


def _loader_harness(stage_count: int) -> str:
    room = build_sort_loader_room(stage_count)
    canvas = Canvas()
    canvas.put(0, 5, room)
    canvas.put(0, 0, ["+-+", "|I|", "+-+"])
    canvas.pipe([(1, 3), (1, 4)])
    canvas.put(6, 57, ["+-+", "|O|", "+-+"])
    canvas.pipe([(7, 50), (7, 56)])
    return canvas.render()


def test_sort_loader_encodes_flushes_and_resets():
    machine = Machine.parse(_loader_harness(stage_count=16))
    result = machine.run(inputs=[3, 3, -10000, 10000], max_ticks=5_000)
    assert result.output[:3] == [10004, 1, 20001]
    assert result.output[3:19] == [20002] * 16
    assert result.output[19] == -1


def test_complete_sort_pipeline_on_small_rounds():
    problem = {
        "publicTestData": [
            {
                "rounds": [
                    {"in": ["3", "3", "1", "2"], "out": ["1", "2", "3"]},
                    {
                        "in": ["4", "5", "-1", "5", "0"],
                        "out": ["-1", "0", "5", "5"],
                    },
                ]
            }
        ],
        "scoring": "footprint-tick",
    }
    report = judge_problem(build_sort(), problem, max_ticks=100_000)
    assert report.cases_passed == 1, report.case_results[0]

    compact_report = judge_problem(
        build_sort_compact_geometry(),
        problem,
        max_ticks=100_000,
    )
    assert compact_report.cases_passed == 1, compact_report.case_results[0]
    assert compact_report.footprint < report.footprint


def test_checked_in_sort_variants_match_generators():
    submission_dir = REPO / "submissions" / "sort"
    assert (submission_dir / "sort.man").read_text() == build_sort()
    assert (submission_dir / "sort_01.man").read_text() == build_sort_compact_geometry()
