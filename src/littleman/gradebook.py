"""Generated Grade Book machine with four parallel subject workers.

The parser broadcasts a normalized command stream to four workers.  Worker
``j`` stores a ring of ``(-N, id, grade_j, ...)`` and acknowledges every
command; only the worker whose subject matches the command performs it.

TOP ranks records by ``(grade + 1) * 10000 - id``.  Maximizing that key
implements both highest-grade selection and the smallest-id tie break.

This module includes a deliberately roomy finite-state-room compiler.  Each
basic block is a left-to-right instruction string.  Control-flow edges receive
dedicated tracks, which makes the generated maze easy to validate and change;
later variants can compact the geometry without changing the state machine.
"""

from __future__ import annotations

from dataclasses import dataclass

from .canvas import Canvas


@dataclass(frozen=True)
class Block:
    name: str
    zone: str
    code: str
    kind: str
    targets: tuple[str, ...]


class Fsm:
    def __init__(self) -> None:
        self.blocks: list[Block] = []

    def go(self, name: str, zone: str, code: str, target: str) -> None:
        self.blocks.append(Block(name, zone, code, "goto", (target,)))

    def sign(
        self,
        name: str,
        zone: str,
        code: str,
        *,
        negative: str,
        zero: str,
        positive: str,
    ) -> None:
        self.blocks.append(Block(name, zone, code, "sign", (negative, zero, positive)))

    def bp(
        self,
        name: str,
        zone: str,
        code: str,
        *,
        zero: str,
        positive: str,
    ) -> None:
        self.blocks.append(Block(name, zone, code, "bp", (zero, positive)))


@dataclass
class CompiledRoom:
    rows: list[str]
    zones: dict[str, int]
    width: int
    height: int


def compile_fsm(
    fsm: Fsm,
    zone_offsets: dict[str, int],
    min_width: int = 0,
    right_padding: int = 3,
) -> CompiledRoom:
    """Embed a finite-state graph in one rectangular littleman room.

    Each block gets the smallest safe horizontal band: two rows for a goto,
    three for a backpack branch, and four for a sign branch.  Directed edges
    share vertical tracks when their row intervals do not overlap.  Horizontal
    tracks cross those vertical tracks only on blank cells, so the walkers do
    not affect each other.
    """
    names = {block.name for block in fsm.blocks}
    if right_padding < 0:
        raise ValueError("right_padding cannot be negative")
    for block in fsm.blocks:
        if any(target not in names for target in block.targets):
            missing = [target for target in block.targets if target not in names]
            raise ValueError(f"{block.name}: unknown targets {missing}")

    edge_specs: list[tuple[str, str, str]] = []
    for block in fsm.blocks:
        labels = (
            ("goto",)
            if block.kind == "goto"
            else (
                ("negative", "zero", "positive")
                if block.kind == "sign"
                else ("zero", "positive")
            )
        )
        edge_specs.extend(
            (block.name, label, target)
            for label, target in zip(labels, block.targets, strict=True)
        )

    zone_base = 12
    zones = {name: zone_base + offset for name, offset in zone_offsets.items()}
    block_rows: dict[str, int] = {}
    route_rows: dict[str, int] = {}
    next_band_row = 3
    for block in fsm.blocks:
        route_rows[block.name] = next_band_row
        block_rows[block.name] = next_band_row + (2 if block.kind == "sign" else 1)
        next_band_row += {"goto": 2, "bp": 3, "sign": 4}[block.kind]
    max_code_end = max(zones[block.zone] + len(block.code) + 2 for block in fsm.blocks)
    branch_base = max_code_end + 4
    branch_cols = {block.name: branch_base for block in fsm.blocks}

    intervals: list[tuple[int, int, str, str, str, str]] = []
    for source, label, target in edge_specs:
        block = next(block for block in fsm.blocks if block.name == source)
        branch_offset = (
            {"negative": -1, "zero": 0, "positive": 1}.get(label, 0)
            if block.kind != "goto"
            else 0
        )
        source_row = block_rows[source] + branch_offset
        route_row = route_rows[target]
        intervals.append(
            (
                min(source_row, route_row),
                max(source_row, route_row),
                source,
                label,
                target,
                "down" if route_row > source_row else "up",
            )
        )

    # Interval colouring: disjoint edges can always reuse a track.  Overlapping
    # edges can also share when they converge on the same target in the same
    # direction; their intermediate ^/v source arrows point straight along
    # the shared path.
    tracks: list[list[tuple[int, int, str, str]]] = []
    edge_tracks: dict[tuple[str, str], int] = {}
    for start, end, source, label, target, direction in sorted(intervals):
        track = next(
            (
                index
                for index, members in enumerate(tracks)
                if all(
                    member_end < start
                    or end < member_start
                    or (member_target == target and member_direction == direction)
                    for (
                        member_start,
                        member_end,
                        member_target,
                        member_direction,
                    ) in members
                )
            ),
            len(tracks),
        )
        if track == len(tracks):
            tracks.append([])
        tracks[track].append((start, end, target, direction))
        edge_tracks[(source, label)] = track

    edge_base = branch_base + 3
    edge_cols = {edge: edge_base + track for edge, track in edge_tracks.items()}
    width = max(min_width, max(edge_cols.values()) + right_padding)
    height = next_band_row + 1
    grid = [[" "] * (width + 2) for _ in range(height + 2)]
    for col in range(width + 2):
        grid[0][col] = grid[height + 1][col] = "-"
    for row in range(height + 2):
        grid[row][0] = grid[row][width + 1] = "|"
    for row, col in (
        (0, 0),
        (0, width + 1),
        (height + 1, 0),
        (height + 1, width + 1),
    ):
        grid[row][col] = "+"

    def put(row: int, col: int, char: str) -> None:
        old = grid[row][col]
        if old not in (" ", char):
            raise ValueError(
                f"FSM routing collision at {(row, col)}: {old!r} vs {char!r}"
            )
        grid[row][col] = char

    block_by_name = {block.name: block for block in fsm.blocks}
    for block in fsm.blocks:
        row = block_rows[block.name]
        start = zones[block.zone]
        put(row, start - 1, ">")
        for offset, char in enumerate(block.code):
            put(row, start + offset, char)
        branch_col = branch_cols[block.name]
        if block.kind == "sign":
            put(row, branch_col, "X")
            put(row - 1, branch_col, ">")
            put(row + 1, branch_col, ">")
            starts = {
                "negative": (row - 1, branch_col),
                "zero": (row, branch_col),
                "positive": (row + 1, branch_col),
            }
        elif block.kind == "bp":
            put(row, branch_col, "d")
            put(row + 1, branch_col, ">")
            starts = {
                "zero": (row, branch_col),
                "positive": (row + 1, branch_col),
            }
        else:
            starts = {"goto": (row, branch_col)}

        labels = tuple(starts)
        for label, target in zip(labels, block.targets, strict=True):
            source_row, _source_col = starts[label]
            edge_col = edge_cols[(block.name, label)]
            target_row = block_rows[target]
            route_row = route_rows[target]
            target_entry_col = zones[block_by_name[target].zone] - 1
            direction = "v" if route_row > source_row else "^"
            put(source_row, edge_col, direction)
            put(route_row, edge_col, "<")
            for entry_row in range(route_row, target_row):
                put(entry_row, target_entry_col, "v")
            put(target_row, target_entry_col, ">")

    rows = ["".join(row) for row in grid]
    return CompiledRoom(rows=rows, zones=zones, width=width, height=height)


PARSER_ZONES = {
    "logic": 0,
    "input": 5,
    "command": 10,
    "ack": 15,
}


def build_parser_fsm() -> Fsm:
    fsm = Fsm()
    fsm.go("start", "input", "@rM", "send_n")
    fsm.go("send_n", "command", "S", "read_k")
    fsm.go("read_k", "input", "rb", "k1")
    fsm.bp("k1", "logic", "m", zero="load1_id", positive="k2")
    fsm.bp("k2", "logic", "m", zero="load2_id", positive="k3")
    fsm.bp("k3", "logic", "m", zero="load3_id", positive="load4_id")

    for subjects in range(1, 5):
        prefix = f"load{subjects}"
        fsm.go(f"{prefix}_id", "input", "r", f"{prefix}_id_send")
        fsm.go(f"{prefix}_id_send", "command", "S", f"{prefix}_g1")
        for grade in range(1, 5):
            name = f"{prefix}_g{grade}"
            send = f"{name}_send"
            if grade <= subjects:
                fsm.go(name, "input", "r", send)
            else:
                fsm.go(name, "logic", "0", send)
            next_name = f"{prefix}_g{grade + 1}" if grade < 4 else f"{prefix}_dec"
            fsm.go(send, "command", "S", next_name)
        fsm.sign(
            f"{prefix}_dec",
            "logic",
            "1W-M",
            negative="roster_ack",
            zero="roster_ack",
            positive=f"{prefix}_id",
        )

    fsm.go("roster_ack", "ack", "r", "batch_count")

    fsm.go("batch_count", "input", "rM", "op_read")
    fsm.go("op_read", "input", "rb", "op_send")
    fsm.go("op_send", "command", "S", "op_dispatch1")
    fsm.bp("op_dispatch1", "logic", "m", zero="get_id", positive="op_dispatch2")
    fsm.bp("op_dispatch2", "logic", "m", zero="set_id", positive="op_dispatch3")
    fsm.bp("op_dispatch3", "logic", "m", zero="avg_id_pad", positive="top_id_pad")

    fsm.go("get_id", "input", "r", "get_id_send")
    fsm.go("get_id_send", "command", "S", "get_subject")
    fsm.go("get_subject", "input", "r", "get_subject_send")
    fsm.go("get_subject_send", "command", "S", "get_value_pad")
    fsm.go("get_value_pad", "logic", "0", "get_value_send")
    fsm.go("get_value_send", "command", "S", "op_ack")

    fsm.go("set_id", "input", "r", "set_id_send")
    fsm.go("set_id_send", "command", "S", "set_subject")
    fsm.go("set_subject", "input", "r", "set_subject_send")
    fsm.go("set_subject_send", "command", "S", "set_value")
    fsm.go("set_value", "input", "r", "set_value_send")
    fsm.go("set_value_send", "command", "S", "op_ack")

    for operation in ("avg", "top"):
        fsm.go(f"{operation}_id_pad", "logic", "0", f"{operation}_id_send")
        fsm.go(
            f"{operation}_id_send",
            "command",
            "S",
            f"{operation}_subject",
        )
        fsm.go(
            f"{operation}_subject",
            "input",
            "r",
            f"{operation}_subject_send",
        )
        fsm.go(
            f"{operation}_subject_send",
            "command",
            "S",
            f"{operation}_value_pad",
        )
        fsm.go(
            f"{operation}_value_pad",
            "logic",
            "0",
            f"{operation}_value_send",
        )
        fsm.go(
            f"{operation}_value_send",
            "command",
            "S",
            "op_ack",
        )

    fsm.go("op_ack", "ack", "r", "op_dec")
    fsm.sign(
        "op_dec",
        "logic",
        "1W-M",
        negative="batch_count",
        zero="batch_count",
        positive="op_read",
    )
    return fsm


WORKER_ZONES = {
    "logic": 0,
    "command": 5,
    "data_in": 10,
    "data_out": 15,
    "state_in": 20,
    "state_out": 25,
    "ack_in": 38,
    "result": 50,
    "ack_out": 60,
}


def build_worker_fsm(subject: int, delay_cells: int = 80) -> Fsm:
    if delay_cells < 0:
        raise ValueError("delay_cells cannot be negative")
    fsm = Fsm()
    roster_ack_target = "roster_ack" if subject == 1 else "roster_ack_in"
    operation_ack_target = "operation_ack" if subject == 1 else "operation_ack_in"
    fsm.go("start", "command", "@rM", "marker_negate")
    fsm.go("marker_negate", "logic", "N", "marker_send")
    fsm.go("marker_send", "data_out", "s", "load_id")
    fsm.go("load_id", "command", "r", "load_id_send")
    fsm.go("load_id_send", "data_out", "s", "load_g1")
    for grade in range(1, 5):
        name = f"load_g{grade}"
        fsm.go(name, "command", "r", f"{name}_route")
        target = (
            f"{name}_send"
            if grade == subject
            else (f"load_g{grade + 1}" if grade < 4 else "load_dec")
        )
        fsm.go(f"{name}_route", "logic", "", target)
        if grade == subject:
            next_name = f"load_g{grade + 1}" if grade < 4 else "load_dec"
            fsm.go(f"{name}_send", "data_out", "s", next_name)
    fsm.sign(
        "load_dec",
        "logic",
        "1W-M",
        negative="roster_delay",
        zero="roster_delay",
        positive="load_id",
    )
    fsm.go("roster_delay", "logic", "." * delay_cells, "roster_marker_r")
    fsm.go("roster_marker_r", "data_in", "r", "roster_marker_s")
    fsm.go("roster_marker_s", "data_out", "s", "roster_orient_delay")
    fsm.go(
        "roster_orient_delay",
        "logic",
        "." * delay_cells,
        roster_ack_target,
    )
    if subject > 1:
        fsm.go("roster_ack_in", "ack_in", "r", "roster_ack")
    fsm.go("roster_ack", "ack_out", "0s", "op_read")

    fsm.go("op_read", "command", "rb", "id_read")
    fsm.go("id_read", "command", "r", "id_park")
    fsm.go("id_park", "state_out", "s", "subject_read")
    fsm.go("subject_read", "command", f"rM{subject}-", "subject_cmp")
    fsm.sign(
        "subject_cmp",
        "logic",
        "",
        negative="skip_value",
        zero="match_value",
        positive="skip_value",
    )
    fsm.go("skip_value", "command", "r", "skip_id")
    fsm.go("skip_id", "state_in", "r", "fast_ack")
    fsm.go("fast_ack", "logic", "", operation_ack_target)

    fsm.go("match_value", "command", "r", "dispatch1")
    fsm.bp("dispatch1", "logic", "m", zero="get_id", positive="dispatch2")
    fsm.bp("dispatch2", "logic", "m", zero="set_value_park", positive="dispatch3")
    fsm.bp("dispatch3", "logic", "m", zero="avg_id_drop", positive="top_id_drop")

    fsm.go("get_id", "state_in", "rM", "get_header_r")
    fsm.go("set_value_park", "state_out", "s", "set_id")
    fsm.go("set_id", "state_in", "rM", "set_header_r")
    fsm.go("avg_id_drop", "state_in", "r", "avg_zero")
    fsm.go("avg_zero", "logic", "0M", "avg_header_r")
    fsm.go("top_id_drop", "state_in", "r", "top_init")
    fsm.go("top_init", "logic", "1NM", "top_header_r")

    # GET
    fsm.go("get_header_r", "data_in", "r", "get_header_s")
    fsm.go("get_header_s", "data_out", "s", "get_header_sign")
    fsm.sign(
        "get_header_sign",
        "logic",
        "",
        negative="operation_delay",
        zero="operation_delay",
        positive="get_compare",
    )
    fsm.sign(
        "get_compare",
        "logic",
        "-",
        negative="get_skip_grade_r",
        zero="get_grade_r",
        positive="get_skip_grade_r",
    )
    fsm.go("get_skip_grade_r", "data_in", "r", "get_skip_grade_s")
    fsm.go("get_skip_grade_s", "data_out", "s", "get_header_r")
    fsm.go("get_grade_r", "data_in", "r", "get_grade_s")
    fsm.go("get_grade_s", "data_out", "s", "get_result")
    fsm.go("get_result", "result", "s", "get_header_r")

    # SET
    fsm.go("set_header_r", "data_in", "r", "set_header_s")
    fsm.go("set_header_s", "data_out", "s", "set_header_sign")
    fsm.sign(
        "set_header_sign",
        "logic",
        "",
        negative="operation_delay",
        zero="operation_delay",
        positive="set_compare",
    )
    fsm.sign(
        "set_compare",
        "logic",
        "-",
        negative="set_skip_grade_r",
        zero="set_old_grade_r",
        positive="set_skip_grade_r",
    )
    fsm.go("set_skip_grade_r", "data_in", "r", "set_skip_grade_s")
    fsm.go("set_skip_grade_s", "data_out", "s", "set_header_r")
    fsm.go("set_old_grade_r", "data_in", "r", "set_new_grade_r")
    fsm.go("set_new_grade_r", "state_in", "r", "set_new_grade_s")
    fsm.go("set_new_grade_s", "data_out", "s", "set_header_r")

    # AVG
    fsm.go("avg_header_r", "data_in", "r", "avg_header_s")
    fsm.go("avg_header_s", "data_out", "s", "avg_header_sign")
    fsm.sign(
        "avg_header_sign",
        "logic",
        "",
        negative="avg_finish",
        zero="avg_finish",
        positive="avg_grade_r",
    )
    fsm.go("avg_grade_r", "data_in", "r", "avg_grade_s")
    fsm.go("avg_grade_s", "data_out", "s", "avg_add")
    fsm.go("avg_add", "logic", "+M", "avg_header_r")
    fsm.go("avg_finish", "logic", "NW/", "avg_result")
    fsm.go("avg_result", "result", "s", "operation_delay")

    # TOP
    fsm.go("top_header_r", "data_in", "r", "top_header_s")
    fsm.go("top_header_s", "data_out", "s", "top_header_sign")
    fsm.sign(
        "top_header_sign",
        "logic",
        "",
        negative="top_finish_swap",
        zero="top_finish_swap",
        positive="top_best_park",
    )
    fsm.go("top_best_park", "state_out", "Ws", "top_id_park")
    fsm.go("top_id_park", "state_out", "Ws", "top_grade_r")
    fsm.go("top_grade_r", "data_in", "r", "top_grade_s")
    fsm.go("top_grade_s", "data_out", "s", "top_product")
    # The state queue is [old_best, id].  Compute
    # (grade + 1) * 10000, then rotate the queue through
    # [id, product, old_best] so the final two-register value is
    # A = (grade + 1) * 10000 - id, B = old_best.
    fsm.go("top_product", "logic", "M1+M`10000`*", "top_product_park")
    fsm.go("top_product_park", "state_out", "s", "top_old_best_r")
    fsm.go("top_old_best_r", "state_in", "r", "top_old_best_park")
    fsm.go("top_old_best_park", "state_out", "s", "top_id_r")
    fsm.go("top_id_r", "state_in", "rNM", "top_product_r")
    fsm.go("top_product_r", "state_in", "r+", "top_best_r")
    fsm.go("top_best_r", "state_in", "Mr", "top_compare")
    fsm.sign(
        "top_compare",
        "logic",
        "W-",
        negative="top_header_r",
        zero="top_header_r",
        positive="top_update",
    )
    fsm.go("top_update", "logic", "+M", "top_header_r")
    fsm.go("top_finish_swap", "logic", "WM", "top_finish_mod")
    fsm.go("top_finish_mod", "logic", "`10000`W%M`10000`-", "top_result")
    fsm.go("top_result", "result", "s", "operation_delay")

    fsm.go(
        "operation_delay",
        "logic",
        "." * delay_cells,
        operation_ack_target,
    )
    if subject > 1:
        fsm.go("operation_ack_in", "ack_in", "r", "operation_ack")
    fsm.go("operation_ack", "ack_out", "0s", "op_read")
    return fsm


RELAY = [
    "+---+",
    "| @v|",
    "|>sv|",
    "|^r<|",
    "+---+",
]


RESULT_RELAY = [
    "+-----+",
    "| @Rsv|",
    "| ^  v|",
    "| ^  <|",
    "+-----+",
]


@dataclass(frozen=True)
class GradebookLayout:
    """Horizontal placement parameters for the four-worker machine."""

    worker_gap: int = 6
    margin: int = 8
    command_left_clearance: int = 4
    ack_right_clearance: int = 3
    fsm_right_padding: int = 3
    worker_vertical_gap: int = 14

    def validate(self) -> None:
        if self.command_left_clearance < 1:
            raise ValueError("command_left_clearance must be positive")
        if self.worker_gap < self.command_left_clearance:
            raise ValueError("worker_gap must leave command routes outside workers")
        if self.margin <= self.command_left_clearance:
            raise ValueError("margin must leave the first command route off the wall")
        if self.ack_right_clearance < 2:
            raise ValueError("ack route must stay outside the parser wall")
        if self.fsm_right_padding < 0:
            raise ValueError("fsm_right_padding cannot be negative")
        if self.worker_vertical_gap < 2:
            raise ValueError("worker_vertical_gap must separate parser and workers")


BASELINE_LAYOUT = GradebookLayout()
COMPACT_LAYOUT = GradebookLayout(
    worker_gap=1,
    margin=2,
    command_left_clearance=1,
    ack_right_clearance=2,
    fsm_right_padding=0,
    worker_vertical_gap=2,
)


def build_result_collector(width: int) -> list[str]:
    """Build one wide room so four result pipes can enter without crossing."""
    if width < 9:
        raise ValueError("collector width is too small")
    grid = [[" "] * width for _ in range(5)]
    for col in range(width):
        grid[0][col] = grid[4][col] = "-"
    for row in range(5):
        grid[row][0] = grid[row][-1] = "|"
    for row, col in ((0, 0), (0, width - 1), (4, 0), (4, width - 1)):
        grid[row][col] = "+"
    center = width // 2
    for row, col, char in (
        (1, center - 3, ">"),
        (1, center - 2, "@"),
        (1, center - 1, "R"),
        (1, center, "s"),
        (1, center + 1, "v"),
        (2, center - 3, "^"),
        (2, center + 1, "v"),
        (3, center - 3, "^"),
        (3, center + 1, "<"),
    ):
        grid[row][col] = char
    return ["".join(row) for row in grid]


def _build_gradebook(
    layout: GradebookLayout,
    *,
    worker_delay_cells: int = 80,
) -> str:
    layout.validate()
    workers = [
        compile_fsm(
            build_worker_fsm(subject, delay_cells=worker_delay_cells),
            WORKER_ZONES,
            right_padding=layout.fsm_right_padding,
        )
        for subject in range(1, 5)
    ]
    worker_width = max(worker.width for worker in workers) + 2
    gap = layout.worker_gap
    margin = layout.margin
    worker_offsets = [margin + i * (worker_width + gap) for i in range(4)]
    total_width = worker_offsets[-1] + worker_width + margin

    parser = compile_fsm(
        build_parser_fsm(),
        PARSER_ZONES,
        min_width=total_width,
        right_padding=layout.fsm_right_padding,
    )

    canvas = Canvas()
    parser_top = 5
    canvas.put(parser_top, 0, parser.rows)
    parser_bottom = parser_top + parser.height + 1
    workers_top = parser_bottom + layout.worker_vertical_gap
    for offset, worker in zip(worker_offsets, workers, strict=True):
        canvas.put(workers_top, offset, worker.rows)

    # External input -> parser input attachment.
    parser_input_x = parser.zones["input"]
    input_top = 0
    canvas.put(input_top, parser_input_x - 1, ["+-+", "|I|", "+-+"])
    canvas.pipe(
        [
            (input_top + 3, parser_input_x),
            (parser_top - 1, parser_input_x),
        ]
    )

    # Parser broadcasts commands to every worker; acknowledgements return on
    # a chain through the workers.
    for offset, worker in zip(worker_offsets, workers, strict=True):
        worker_cmd_x = offset + worker.zones["command"]
        worker_bottom = workers_top + worker.height + 1
        command_route_x = offset - layout.command_left_clearance
        canvas.pipe(
            [
                (parser_bottom + 1, command_route_x),
                (worker_bottom + 2, command_route_x),
                (worker_bottom + 2, worker_cmd_x),
                (worker_bottom + 1, worker_cmd_x),
            ]
        )

    # Per-worker state and data rings.  Their paths stay inside each worker's
    # horizontal allocation.
    rings_bottom = workers_top
    result_sources: list[tuple[int, int]] = []
    for index, (offset, worker) in enumerate(zip(worker_offsets, workers, strict=True)):
        bottom = workers_top + worker.height + 1
        state_out = offset + worker.zones["state_out"]
        state_in = offset + worker.zones["state_in"]
        data_out = offset + worker.zones["data_out"]
        data_in = offset + worker.zones["data_in"]
        result_x = offset + worker.zones["result"]

        state_relay_top = bottom + 8
        canvas.put(state_relay_top, state_out + 4, RELAY)
        canvas.pipe(
            [
                (bottom + 1, state_out),
                (state_relay_top + 3, state_out),
                (state_relay_top + 3, state_out + 3),
            ]
        )
        canvas.pipe(
            [
                (state_relay_top + 2, state_out + 9),
                (state_relay_top + 2, state_out + 12),
                (state_relay_top + 6, state_out + 12),
                (state_relay_top + 6, state_in),
                (bottom + 1, state_in),
            ]
        )

        data_relay_top = bottom + 20
        canvas.put(data_relay_top, data_out + 4, RELAY)
        canvas.pipe(
            [
                (bottom + 1, data_out),
                (data_relay_top + 3, data_out),
                (data_relay_top + 3, data_out + 3),
            ]
        )
        # Incoming parking pipe has >33 cells and does not self-cross.
        canvas.pipe(
            [
                (data_relay_top + 2, data_out + 9),
                (data_relay_top + 2, data_out + 14),
                (data_relay_top + 10, data_out + 14),
                (data_relay_top + 10, data_in - 18),
                (bottom + 4, data_in - 18),
                (bottom + 4, data_in),
                (bottom + 1, data_in),
            ]
        )

        result_sources.append((bottom + 1, result_x))
        rings_bottom = max(rings_bottom, data_relay_top + 11)

    # Acknowledgements flow 1 -> 2 -> 3 -> 4 -> parser.  The final pipe
    # approaches the parser from above, alongside (but distinct from) input,
    # so nearest-pipe receives cannot consume future contest input.
    ack_route_row = rings_bottom + 3
    for index in range(3):
        source_worker = workers[index]
        target_worker = workers[index + 1]
        source_x = worker_offsets[index] + source_worker.zones["ack_out"]
        target_x = worker_offsets[index + 1] + target_worker.zones["ack_in"]
        source_bottom = workers_top + source_worker.height + 1
        target_bottom = workers_top + target_worker.height + 1
        canvas.pipe(
            [
                (source_bottom + 1, source_x),
                (ack_route_row, source_x),
                (ack_route_row, target_x),
                (target_bottom + 1, target_x),
            ]
        )

    final_worker = workers[-1]
    final_ack_x = worker_offsets[-1] + final_worker.zones["ack_out"]
    final_worker_bottom = workers_top + final_worker.height + 1
    parser_ack_x = parser.zones["ack"]
    far_right = total_width + layout.ack_right_clearance
    canvas.pipe(
        [
            (final_worker_bottom + 1, final_ack_x),
            (ack_route_row, final_ack_x),
            (ack_route_row, far_right),
            (parser_top - 2, far_right),
            (parser_top - 2, parser_ack_x),
            (parser_top - 1, parser_ack_x),
        ]
    )

    # One wide result collector is the sole source feeding O.  Its top
    # attachments align with worker result columns, so the four pipes are
    # straight and cannot cross.
    collector_top = rings_bottom + 10
    canvas.put(collector_top, 0, build_result_collector(total_width))
    for source in result_sources:
        canvas.pipe([source, (collector_top - 1, source[1])])

    output_top = collector_top + 10
    collector_center = total_width // 2
    output_left = collector_center - 1
    canvas.put(output_top, output_left, ["+-+", "|O|", "+-+"])
    canvas.pipe(
        [
            (collector_top + 5, collector_center),
            (output_top - 1, collector_center),
        ]
    )
    return canvas.render()


def build_gradebook() -> str:
    """Reproduce the accepted baseline artifact exactly."""
    return _build_gradebook(BASELINE_LAYOUT)


def build_gradebook_compact() -> str:
    """Build the tighter geometry-only successor to ``gradebook_00``."""
    return _build_gradebook(COMPACT_LAYOUT)


def build_gradebook_no_delay() -> str:
    """Build workers that rely on blocking ring reads instead of fixed waits."""
    return _build_gradebook(COMPACT_LAYOUT, worker_delay_cells=0)
