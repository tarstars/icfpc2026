import random

from littleman.canvas import Canvas
from littleman.gradebook import compile_fsm
from littleman.judge import judge_case
from littleman.sim import Machine
from littleman.subset_sum import (
    COUNTER_ZONES,
    MERGE_ZONES,
    SELECTOR_ZONES,
    STAGE_ZONES,
    _place_group_pipeline,
    _place_systolic_sorter,
    build_bit_stage_fsm,
    build_counter_fsm,
    build_subset_sum,
    reference_subset,
)


def _sorter_probe(*, descending: bool, count: int = 16) -> str:
    canvas = Canvas()
    sorter = _place_systolic_sorter(
        canvas,
        top=10,
        left=0,
        descending=descending,
        count=count,
    )
    canvas.put(0, sorter.input_x - 1, ["+-+", "|I|", "+-+"])
    canvas.pipe([(3, sorter.input_x), (9, sorter.input_x)])
    output_top = sorter.next_top + 5
    canvas.put(output_top, sorter.output_x - 1, ["+-+", "|O|", "+-+"])
    canvas.pipe(
        [
            (sorter.output_bottom + 1, sorter.output_x),
            (output_top - 1, sorter.output_x),
        ]
    )
    return canvas.render()


def test_reference_subset_prefers_earliest_indices():
    assert reference_subset([500, 500, 500, 300], 1000) == [500, 500]
    assert reference_subset([2, 4, 8], 7) == []


def test_systolic_pair_sorters():
    rng = random.Random(7)
    pairs = [(0, 1023), (0, 1023)] + [
        (rng.randrange(1000), rng.randrange(1024)) for _ in range(14)
    ]
    inputs = [value for pair in pairs for value in pair] + [-1]
    for descending in (True, False):
        if descending:
            ordered = sorted(pairs, key=lambda pair: (pair[0], pair[1]), reverse=True)
        else:
            ordered = sorted(pairs, key=lambda pair: (pair[0], -pair[1]))
        outputs = [value for pair in ordered for value in pair] + [-1]
        result = judge_case(
            _sorter_probe(descending=descending),
            [{"in": inputs, "out": outputs}],
            max_ticks=100_000,
        )
        assert result.passed, result.reason


def test_padded_half_clears_invalid_mask_bits():
    canvas = Canvas()
    counter = compile_fsm(build_counter_fsm(), COUNTER_ZONES)
    stages = [
        compile_fsm(
            build_bit_stage_fsm(index, first=index == 0, last=index == 9),
            STAGE_ZONES,
        )
        for index in range(10)
    ]
    group = _place_group_pipeline(
        canvas,
        top=20,
        left=0,
        counter_left=500,
        counter=counter,
        stages=stages,
    )
    input_x = group.first_stage.room.zones["init"]
    canvas.put(0, input_x - 1, ["+-+", "|I|", "+-+"])
    canvas.pipe([(3, input_x), (group.first_stage.top - 1, input_x)])
    output_x = group.last_stage.room.zones["stream_out"]
    output_top = group.next_top + 10
    canvas.put(output_top, output_x - 1, ["+-+", "|O|", "+-+"])
    canvas.pipe(
        [
            (
                group.last_stage.top + group.last_stage.room.height + 2,
                output_x,
            ),
            (output_top - 1, output_x),
        ]
    )
    result = judge_case(
        canvas.render(),
        [{"in": [0] * 10, "out": [0] * 20}],
        max_ticks=500_000,
    )
    assert result.passed, result.reason


def _seed_pipe(machine: Machine, pipe, values: list[int]) -> None:
    for offset, value in enumerate(values):
        machine._pipe_put(pipe, -1 - offset, value)


def test_merge_reducer_and_selector_choose_greatest_mask():
    machine = Machine.parse(build_subset_sum())
    merge = next(
        room
        for room in machine.rooms
        if room.left == 2800 and 160 <= room.right - room.left + 1 <= 180
    )
    reducer = next(
        room
        for room in machine.rooms
        if room.left == 3000 and room.right - room.left + 1 == 49
    )
    selector = next(
        room
        for room in machine.rooms
        if room.left == 1000 and room.right - room.left + 1 > 1600
    )
    core_room_ids = {id(merge), id(reducer), id(selector)}
    for man in machine.men:
        is_relay = man.room.right - man.room.left + 1 == 5
        if id(man.room) not in core_room_ids and not is_relay:
            man.halted = True
    machine._runnable_men = {
        index for index, man in enumerate(machine.men) if not man.halted
    }

    def incoming(room, relative_column):
        absolute_column = room.left + relative_column
        return next(
            pipe
            for pipe in machine.in_pipes[id(room)]
            if pipe.cells[-1][1] == absolute_column
        )

    a_pairs = [(5, 1), (4, 7), (2, 9), (0, 0)]
    b_pairs = [(0, 2), (1, 3), (3, 4)]
    _seed_pipe(
        machine,
        incoming(merge, 12 + MERGE_ZONES["target_input"]),
        [5],
    )
    _seed_pipe(
        machine,
        incoming(merge, 12 + MERGE_ZONES["a_input"]),
        [value for pair in a_pairs for value in pair] + [-1],
    )
    _seed_pipe(
        machine,
        incoming(merge, 12 + MERGE_ZONES["b_input"]),
        [value for pair in b_pairs for value in pair] + [-1],
    )
    _seed_pipe(
        machine,
        incoming(selector, 12 + SELECTOR_ZONES["values_input"]),
        list(range(100, 120)),
    )

    result = machine.run(max_ticks=1_000_000)
    assert result.error is None
    assert result.output == [3, 106, 109, 117]
