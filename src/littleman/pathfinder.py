"""Generated Pathfinder machine.

The machine stores one packed word per board row in a 16-word ring:

* bits 0..15: cells not yet reached by the current BFS;
* bits 16..31: distance to the flag modulo 3 == 0;
* bits 32..47: distance modulo 3 == 1;
* bits 48..63: distance modulo 3 == 2.

Input columns are packed in reverse bit order (x maps to bit 15-x).  This
lets the setup loader build a row with the compact recurrence
``row = 2*row + is_path``.  It does not affect the four-neighbour dilation.

Each BFS wave is one streaming pass over the fourteen non-border rows.  For
each row the controller sends the left, right, previous-row, and next-row
frontiers to a small update service, which atomically clears new cells from
the low plane while adding them to the selected modulo plane.  The robot is
then walked by querying modulo planes in up/right/down/left order.

Display commands use one stream:

* positive ``addr+1`` -> ADDR;
* negative ``-(color+1)`` -> DATA;
* zero -> SWAP=1.
"""

from __future__ import annotations

from dataclasses import dataclass

from .canvas import Canvas
from .gradebook import Block, CompiledRoom, Fsm, compile_fsm

BOARD = 16
ROW_MASK = (1 << BOARD) - 1
DISTANCE_TAG = 1000
PLANE_OFFSET = {0: 16, 1: 32, 2: 48}
UPDATE_FACTOR = {mod: (1 << offset) - 1 for mod, offset in PLANE_OFFSET.items()}


def _lit(value: int) -> str:
    if value < 0:
        return f"`{-value}`N"
    if value < 10:
        return str(value)
    return f"`{value}`"


def _extract_plane(offset: int) -> str:
    shift = f"M{_lit(offset)}W}}" if offset else ""
    return f"{shift}M{_lit(ROW_MASK)}W&"


def _shift_one(direction: str) -> str:
    if direction not in ("left", "right"):
        raise ValueError(direction)
    return "M1W{" if direction == "left" else "M1W}"


def _mask_from_x(offset: int) -> str:
    # x -> bit (15-x), then lift it into the selected modulo plane.
    return f"M{_lit(15)}-M1{{M{_lit(offset)}W{{"


def _decode_robot() -> str:
    # Stored as -(addr+1).
    return "NM1W-"


@dataclass(frozen=True)
class Rooms:
    controller: CompiledRoom
    ring_relay: CompiledRoom
    scratch_relay: CompiledRoom
    update: CompiledRoom
    display_driver: CompiledRoom


CONTROLLER_ZONES = {
    "logic": 0,
    "input": 5,
    "display": 0,
    "ring_out": 20,
    "ring_in": 25,
    "scratch_out": 60,
    "scratch_in": 65,
    "update_out": 100,
    "update_in": 105,
}

SERVICE_ZONES = {"in": 0, "out": 5, "logic": 10}
DRIVER_ZONES = {"in": 0, "data": 20, "addr": 40, "swap": 60, "logic": 80}


def _compile_fast_fsm(
    fsm: Fsm,
    zone_offsets: dict[str, int],
    *,
    min_width: int,
    right_padding: int,
) -> CompiledRoom:
    """Compile an FSM with short routes for in-order goto fall-throughs.

    The shared correctness-first compiler sends every edge to a common track
    bank.  This controller has over a thousand small blocks and most goto
    edges lead to the immediately following block, so that layout spends
    nearly all of its ticks walking through empty space.  Here those edges
    turn down in the two-row band already reserved for the next block.
    Branches and non-local edges retain the shared compiler's track routing.
    """

    names = {block.name for block in fsm.blocks}
    if right_padding < 0:
        raise ValueError("right_padding cannot be negative")
    for block in fsm.blocks:
        missing = [target for target in block.targets if target not in names]
        if missing:
            raise ValueError(f"{block.name}: unknown targets {missing}")

    zone_base = 12
    zones = {name: zone_base + offset for name, offset in zone_offsets.items()}
    block_rows: dict[str, int] = {}
    route_rows: dict[str, int] = {}
    next_band_row = 3
    for block in fsm.blocks:
        route_rows[block.name] = next_band_row
        block_rows[block.name] = next_band_row + (2 if block.kind == "sign" else 1)
        next_band_row += {"goto": 2, "bp": 3, "sign": 4}[block.kind]

    block_index = {block.name: index for index, block in enumerate(fsm.blocks)}
    fast_edges = {
        (block.name, "goto")
        for index, block in enumerate(fsm.blocks[:-1])
        if block.kind == "goto" and block.targets == (fsm.blocks[index + 1].name,)
    }

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

    max_code_end = max(zones[block.zone] + len(block.code) + 2 for block in fsm.blocks)
    branch_base = max_code_end + 4
    literal_endpoints = {
        zones[block.zone] + index
        for block in fsm.blocks
        for index, char in enumerate(block.code)
        if char == "`"
    }
    branch_cols = {}
    for block in fsm.blocks:
        if (block.name, "goto") not in fast_edges:
            branch_cols[block.name] = branch_base
            continue
        branch_col = max(
            zones[block.zone] + len(block.code) + 1,
            zones[fsm.blocks[block_index[block.name] + 1].zone],
        )
        while branch_col + 1 in literal_endpoints:
            branch_col += 1
        branch_cols[block.name] = branch_col

    intervals: list[tuple[int, int, str, str, str, str]] = []
    for source, label, target in edge_specs:
        if (source, label) in fast_edges:
            continue
        block = fsm.blocks[block_index[source]]
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
    edge_cols = {
        (source, label): (
            branch_cols[source] + 1
            if (source, label) in fast_edges
            else edge_base + edge_tracks[(source, label)]
        )
        for source, label, _target in edge_specs
    }
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

        for label, target in zip(tuple(starts), block.targets, strict=True):
            source_row, _source_col = starts[label]
            edge_col = edge_cols[(block.name, label)]
            target_row = block_rows[target]
            route_row = route_rows[target]
            target_entry_col = zones[block_by_name[target].zone] - 1
            direction = "v" if route_row > source_row else "^"
            try:
                put(source_row, edge_col, direction)
            except ValueError as exc:
                raise ValueError(f"{block.name}:{label}->{target}: {exc}") from exc
            put(route_row, edge_col, "<")
            for entry_row in range(route_row, target_row):
                put(entry_row, target_entry_col, "v")
            put(target_row, target_entry_col, ">")

    return CompiledRoom(
        rows=["".join(row) for row in grid],
        zones=zones,
        width=width,
        height=height,
    )


def _compile_literal_safe(
    fsm: Fsm,
    zone_offsets: dict[str, int],
    *,
    min_width: int,
    right_padding: int = 3,
) -> CompiledRoom:
    """Compile an FSM without accidentally making vertical numeric literals.

    ``compile_fsm`` normally starts every block in a zone at one column.
    Under the now-formal in-order backtick rule, unrelated horizontal
    literals can then pair vertically across intervening operations and make
    the room fail to load.  Give literal-bearing blocks the smallest
    nonnegative offset whose backtick columns have not appeared before.
    Non-literal pipe operations stay on their canonical zone columns.
    """

    rewritten = Fsm()
    safe_offsets = dict(zone_offsets)
    forbidden = {
        zone_offsets[block.zone] - 1 for block in fsm.blocks if "`" not in block.code
    }
    for block in fsm.blocks:
        if "`" not in block.code:
            forbidden.update(
                range(
                    zone_offsets[block.zone],
                    zone_offsets[block.zone] + len(block.code),
                )
            )

    group_codes: dict[tuple[str, tuple[int, ...]], list[str]] = {}
    for block in fsm.blocks:
        ticks = tuple(index for index, char in enumerate(block.code) if char == "`")
        if ticks:
            group_codes.setdefault((block.zone, ticks), []).append(block.code)

    group_offsets: dict[tuple[str, tuple[int, ...]], int] = {}
    occupied_literal_columns: set[int] = set()
    for group, codes in group_codes.items():
        _zone, ticks = group
        span = max(map(len, codes))
        for start in range(4096):
            occupied = set(range(start, start + span))
            endpoints = {start + index for index in ticks}
            if occupied.isdisjoint(occupied_literal_columns) and endpoints.isdisjoint(
                forbidden
            ):
                break
        else:  # pragma: no cover - defensive bound for future FSM growth
            raise ValueError("could not allocate literal-safe instruction columns")
        group_offsets[group] = start
        occupied_literal_columns.update(occupied)

    literal_zones: dict[tuple[str, tuple[int, ...]], str] = {}
    for block in fsm.blocks:
        ticks = tuple(index for index, char in enumerate(block.code) if char == "`")
        if not ticks:
            rewritten.blocks.append(block)
            continue
        group = (block.zone, ticks)
        safe_zone = literal_zones.setdefault(
            group,
            f"__literal_{len(literal_zones)}",
        )
        safe_offsets[safe_zone] = group_offsets[group]
        rewritten.blocks.append(
            Block(block.name, safe_zone, block.code, block.kind, block.targets)
        )

    room = _compile_fast_fsm(
        rewritten,
        safe_offsets,
        min_width=min_width,
        right_padding=right_padding,
    )
    # External geometry uses the canonical pipe-zone columns, not private
    # compiler-only zones.
    room.zones = {name: 12 + offset for name, offset in zone_offsets.items()}
    return room


def _add_copy_metadata(
    fsm: Fsm,
    prefix: str,
    *,
    target: str,
    increment_distance: bool,
) -> None:
    fsm.go(f"{prefix}_robot_r", "ring_in", "r", f"{prefix}_robot_s")
    fsm.go(f"{prefix}_robot_s", "ring_out", "s", f"{prefix}_distance_r")
    fsm.go(f"{prefix}_distance_r", "ring_in", "r", f"{prefix}_distance_edit")
    code = "M1W-" if increment_distance else ""
    fsm.go(f"{prefix}_distance_edit", "logic", code, f"{prefix}_distance_s")
    fsm.go(f"{prefix}_distance_s", "ring_out", "s", target)


def _add_horizontal_pass(
    fsm: Fsm,
    prefix: str,
    *,
    source_mod: int,
    target_mod: int,
    target: str,
    increment_distance: bool = False,
) -> None:
    update_out = "update_out"
    update_in = "update_in"
    fsm.go(f"{prefix}_start", "logic", str(target_mod), f"{prefix}_mod_s")
    fsm.go(f"{prefix}_mod_s", update_out, "s", f"{prefix}_service_count")
    fsm.go(
        f"{prefix}_service_count",
        "logic",
        f"{_lit(16)}",
        f"{prefix}_service_count_s",
    )
    fsm.go(
        f"{prefix}_service_count_s",
        update_out,
        "s",
        f"{prefix}_count",
    )
    fsm.go(f"{prefix}_count", "logic", f"{_lit(16)}b", f"{prefix}_word_r")
    fsm.go(f"{prefix}_word_r", "ring_in", "r", f"{prefix}_save_word")
    fsm.go(f"{prefix}_save_word", "scratch_out", "s", f"{prefix}_left")
    fsm.go(
        f"{prefix}_left",
        "logic",
        _extract_plane(PLANE_OFFSET[source_mod]) + _shift_one("left"),
        f"{prefix}_left_s",
    )
    fsm.go(f"{prefix}_left_s", "scratch_out", "s", f"{prefix}_word_back1")
    fsm.go(f"{prefix}_word_back1", "scratch_in", "r", f"{prefix}_word_resend")
    fsm.go(
        f"{prefix}_word_resend",
        "scratch_out",
        "s",
        f"{prefix}_right",
    )
    fsm.go(
        f"{prefix}_right",
        "logic",
        _extract_plane(PLANE_OFFSET[source_mod]) + _shift_one("right") + "M",
        f"{prefix}_left_back",
    )
    fsm.go(f"{prefix}_left_back", "scratch_in", "r|", f"{prefix}_contribution_s")
    fsm.go(
        f"{prefix}_contribution_s",
        update_out,
        "s",
        f"{prefix}_word_back",
    )
    fsm.go(f"{prefix}_word_back", "scratch_in", "r", f"{prefix}_word_ss")
    fsm.go(f"{prefix}_word_ss", update_out, "ss", f"{prefix}_updated_r")
    fsm.go(f"{prefix}_updated_r", update_in, "r", f"{prefix}_updated_s")
    fsm.go(f"{prefix}_updated_s", "ring_out", "s", f"{prefix}_dec")
    fsm.bp(
        f"{prefix}_dec",
        "logic",
        "m",
        zero=f"{prefix}_robot_r",
        positive=f"{prefix}_word_r",
    )
    _add_copy_metadata(
        fsm,
        prefix,
        target=target,
        increment_distance=increment_distance,
    )


def _add_vertical_down_pass(
    fsm: Fsm,
    prefix: str,
    *,
    source_mod: int,
    target_mod: int,
    target: str,
    increment_distance: bool = False,
) -> None:
    update_out = "update_out"
    update_in = "update_in"
    fsm.go(
        f"{prefix}_start",
        "logic",
        str(target_mod),
        f"{prefix}_mod_s",
    )
    fsm.go(
        f"{prefix}_mod_s",
        update_out,
        "s",
        f"{prefix}_service_count",
    )
    fsm.go(
        f"{prefix}_service_count",
        "logic",
        f"{_lit(16)}",
        f"{prefix}_service_count_s",
    )
    fsm.go(
        f"{prefix}_service_count_s",
        update_out,
        "s",
        f"{prefix}_count",
    )
    fsm.go(
        f"{prefix}_count",
        "logic",
        f"{_lit(16)}b0",
        f"{prefix}_contribution_s",
    )
    fsm.go(
        f"{prefix}_contribution_s",
        update_out,
        "s",
        f"{prefix}_word_r",
    )
    fsm.go(f"{prefix}_word_r", "ring_in", "r", f"{prefix}_word_ss")
    fsm.go(f"{prefix}_word_ss", update_out, "ss", f"{prefix}_updated_r")
    fsm.go(f"{prefix}_updated_r", update_in, "r", f"{prefix}_updated_s")
    fsm.go(f"{prefix}_updated_s", "ring_out", "s", f"{prefix}_next_frontier")
    fsm.go(
        f"{prefix}_next_frontier",
        "logic",
        _extract_plane(PLANE_OFFSET[source_mod]),
        f"{prefix}_dec",
    )
    fsm.bp(
        f"{prefix}_dec",
        "logic",
        "m",
        zero=f"{prefix}_robot_r",
        positive=f"{prefix}_contribution_s",
    )
    _add_copy_metadata(
        fsm,
        prefix,
        target=target,
        increment_distance=increment_distance,
    )


def _add_vertical_up_pass(
    fsm: Fsm,
    prefix: str,
    *,
    source_mod: int,
    target_mod: int,
    target: str,
    increment_distance: bool = False,
) -> None:
    update_out = "update_out"
    update_in = "update_in"
    fsm.go(f"{prefix}_start", "logic", str(target_mod), f"{prefix}_mod_s")
    fsm.go(f"{prefix}_mod_s", update_out, "s", f"{prefix}_service_count")
    fsm.go(
        f"{prefix}_service_count",
        "logic",
        f"{_lit(15)}",
        f"{prefix}_service_count_s",
    )
    fsm.go(
        f"{prefix}_service_count_s",
        update_out,
        "s",
        f"{prefix}_first_r",
    )
    fsm.go(f"{prefix}_first_r", "ring_in", "r", f"{prefix}_pending_s")
    fsm.go(f"{prefix}_pending_s", "scratch_out", "s", f"{prefix}_count")
    fsm.go(f"{prefix}_count", "logic", f"{_lit(15)}b", f"{prefix}_word_r")
    fsm.go(f"{prefix}_word_r", "ring_in", "r", f"{prefix}_word_save")
    fsm.go(f"{prefix}_word_save", "scratch_out", "s", f"{prefix}_frontier")
    fsm.go(
        f"{prefix}_frontier",
        "logic",
        _extract_plane(PLANE_OFFSET[source_mod]),
        f"{prefix}_contribution_s",
    )
    fsm.go(
        f"{prefix}_contribution_s",
        update_out,
        "s",
        f"{prefix}_pending_r",
    )
    fsm.go(f"{prefix}_pending_r", "scratch_in", "r", f"{prefix}_pending_ss")
    fsm.go(f"{prefix}_pending_ss", update_out, "ss", f"{prefix}_updated_r")
    fsm.go(f"{prefix}_updated_r", update_in, "r", f"{prefix}_updated_s")
    fsm.go(f"{prefix}_updated_s", "ring_out", "s", f"{prefix}_dec")
    fsm.bp(
        f"{prefix}_dec",
        "logic",
        "m",
        zero=f"{prefix}_last_r",
        positive=f"{prefix}_word_r",
    )
    fsm.go(f"{prefix}_last_r", "scratch_in", "r", f"{prefix}_last_s")
    fsm.go(f"{prefix}_last_s", "ring_out", "s", f"{prefix}_robot_r")
    _add_copy_metadata(
        fsm,
        prefix,
        target=target,
        increment_distance=increment_distance,
    )


def _add_vertical_pass(
    fsm: Fsm,
    prefix: str,
    *,
    source_mod: int,
    target_mod: int,
    target: str,
    increment_distance: bool = False,
) -> None:
    """Dilate all four neighbours in one 14-row streaming pass."""

    update_out = "update_out"
    update_in = "update_in"
    # Commands 3..5 select the vertical streaming protocol for target mod 0..2.
    fsm.go(
        f"{prefix}_start",
        "logic",
        str(target_mod + 3),
        f"{prefix}_mod_s",
    )
    fsm.go(f"{prefix}_mod_s", update_out, "s", f"{prefix}_service_count")
    fsm.go(
        f"{prefix}_service_count",
        "logic",
        f"{_lit(14)}",
        f"{prefix}_service_count_s",
    )
    fsm.go(
        f"{prefix}_service_count_s",
        update_out,
        "s",
        f"{prefix}_count",
    )
    fsm.go(f"{prefix}_count", "logic", f"{_lit(14)}b", f"{prefix}_border_r")

    # Row 0 is a guaranteed wall row.  Forward it unchanged and seed the
    # service's previous-frontier register with its (zero) source plane.
    fsm.go(f"{prefix}_border_r", "ring_in", "r", f"{prefix}_border_s")
    fsm.go(f"{prefix}_border_s", "ring_out", "s", f"{prefix}_prev_frontier")
    fsm.go(
        f"{prefix}_prev_frontier",
        "logic",
        _extract_plane(PLANE_OFFSET[source_mod]),
        f"{prefix}_prev_frontier_s",
    )
    fsm.go(
        f"{prefix}_prev_frontier_s",
        update_out,
        "s",
        f"{prefix}_current_r",
    )
    fsm.go(f"{prefix}_current_r", "ring_in", "r", f"{prefix}_current_save")

    # Keep three copies of current.  Two form its horizontal contribution;
    # the third is put back before next, producing scratch order
    # [current, next] for the update and the next loop iteration.
    fsm.go(f"{prefix}_current_save", "scratch_out", "sss", f"{prefix}_left_r")
    fsm.go(f"{prefix}_left_r", "scratch_in", "r", f"{prefix}_left")
    fsm.go(
        f"{prefix}_left",
        "logic",
        _extract_plane(PLANE_OFFSET[source_mod]) + _shift_one("left"),
        f"{prefix}_left_s",
    )
    fsm.go(f"{prefix}_left_s", update_out, "s", f"{prefix}_right_r")
    fsm.go(f"{prefix}_right_r", "scratch_in", "r", f"{prefix}_right")
    fsm.go(
        f"{prefix}_right",
        "logic",
        _extract_plane(PLANE_OFFSET[source_mod]) + _shift_one("right"),
        f"{prefix}_right_s",
    )
    fsm.go(f"{prefix}_right_s", update_out, "s", f"{prefix}_current_requeue")
    fsm.go(
        f"{prefix}_current_requeue",
        "scratch_in",
        "r",
        f"{prefix}_current_requeue_s",
    )
    fsm.go(
        f"{prefix}_current_requeue_s",
        "scratch_out",
        "s",
        f"{prefix}_next_r",
    )
    fsm.go(f"{prefix}_next_r", "ring_in", "r", f"{prefix}_next_save")
    fsm.go(f"{prefix}_next_save", "scratch_out", "s", f"{prefix}_next_frontier")
    fsm.go(
        f"{prefix}_next_frontier",
        "logic",
        _extract_plane(PLANE_OFFSET[source_mod]),
        f"{prefix}_next_frontier_s",
    )
    fsm.go(
        f"{prefix}_next_frontier_s",
        update_out,
        "s",
        f"{prefix}_current_back",
    )
    fsm.go(
        f"{prefix}_current_back",
        "scratch_in",
        "r",
        f"{prefix}_current_ss",
    )
    fsm.go(f"{prefix}_current_ss", update_out, "ss", f"{prefix}_updated_r")
    fsm.go(f"{prefix}_updated_r", update_in, "r", f"{prefix}_updated_s")
    fsm.go(
        f"{prefix}_updated_s",
        "ring_out",
        "s",
        f"{prefix}_current_frontier",
    )
    fsm.go(
        f"{prefix}_current_frontier",
        "logic",
        _extract_plane(PLANE_OFFSET[source_mod]),
        f"{prefix}_current_frontier_s",
    )
    fsm.go(
        f"{prefix}_current_frontier_s",
        update_out,
        "s",
        f"{prefix}_dec",
    )
    fsm.bp(
        f"{prefix}_dec",
        "logic",
        "m",
        zero=f"{prefix}_last_r",
        positive=f"{prefix}_current_pending_r",
    )

    # The scratch head is now border row 15, also guaranteed to be a wall.
    fsm.go(
        f"{prefix}_current_pending_r",
        "scratch_in",
        "r",
        f"{prefix}_current_save",
    )
    fsm.go(f"{prefix}_last_r", "scratch_in", "r", f"{prefix}_last_s")
    fsm.go(f"{prefix}_last_s", "ring_out", "s", f"{prefix}_robot_r")
    _add_copy_metadata(
        fsm,
        prefix,
        target=target,
        increment_distance=increment_distance,
    )


def _add_reset_pass(fsm: Fsm, target: str) -> None:
    prefix = "reset"
    fsm.go(f"{prefix}_start", "logic", f"{_lit(16)}b", f"{prefix}_word_r")
    fsm.go(f"{prefix}_word_r", "ring_in", "r", f"{prefix}_word_reset")
    fsm.go(
        f"{prefix}_word_reset",
        "logic",
        f"M{_lit(ROW_MASK)}W%",
        f"{prefix}_word_s",
    )
    fsm.go(f"{prefix}_word_s", "ring_out", "s", f"{prefix}_dec")
    fsm.bp(
        f"{prefix}_dec",
        "logic",
        "m",
        zero=f"{prefix}_robot_r",
        positive=f"{prefix}_word_r",
    )
    _add_copy_metadata(
        fsm,
        prefix,
        target=target,
        increment_distance=False,
    )


def _add_wave_check(
    fsm: Fsm,
    mod: int,
    *,
    not_reached: str,
    reached: str,
) -> None:
    p = f"check{mod}"
    fsm.go(f"{p}_count", "logic", f"{_lit(16)}b", f"{p}_row_r")
    fsm.go(f"{p}_row_r", "ring_in", "r", f"{p}_row_s")
    fsm.go(f"{p}_row_s", "ring_out", "s", f"{p}_dec")
    fsm.bp(
        f"{p}_dec",
        "logic",
        "m",
        zero=f"{p}_robot_r",
        positive=f"{p}_row_r",
    )
    fsm.go(f"{p}_robot_r", "ring_in", "r", f"{p}_robot_s")
    fsm.go(f"{p}_robot_s", "ring_out", "s", f"{p}_decode")
    fsm.go(f"{p}_decode", "logic", _decode_robot(), f"{p}_addr_save")
    fsm.go(f"{p}_addr_save", "scratch_out", "s", f"{p}_distance_r")
    fsm.go(f"{p}_distance_r", "ring_in", "r", f"{p}_distance_s")
    fsm.go(f"{p}_distance_s", "ring_out", "s", f"{p}_addr_back")
    fsm.go(f"{p}_addr_back", "scratch_in", "r", f"{p}_divide")
    fsm.go(f"{p}_divide", "logic", f"M{_lit(16)}W/bW", f"{p}_x_save")
    fsm.go(f"{p}_x_save", "scratch_out", "s", f"{p}_rotate_check")
    fsm.bp(
        f"{p}_rotate_check",
        "logic",
        "",
        zero=f"{p}_target_r",
        positive=f"{p}_rotate_r",
    )
    fsm.go(f"{p}_rotate_r", "ring_in", "r", f"{p}_rotate_s")
    fsm.go(f"{p}_rotate_s", "ring_out", "s", f"{p}_rotate_dec")
    fsm.go(f"{p}_rotate_dec", "logic", "m", f"{p}_rotate_check")
    fsm.go(f"{p}_target_r", "ring_in", "r", f"{p}_target_save")
    fsm.go(f"{p}_target_save", "scratch_out", "ss", f"{p}_x_back")
    fsm.go(f"{p}_x_back", "scratch_in", "r", f"{p}_mask")
    fsm.go(
        f"{p}_mask",
        "logic",
        _mask_from_x(PLANE_OFFSET[mod]) + "M",
        f"{p}_word_back",
    )
    fsm.go(f"{p}_word_back", "scratch_in", "r", f"{p}_test")
    fsm.sign(
        f"{p}_test",
        "logic",
        "&",
        negative=f"{p}_reached_word",
        zero=f"{p}_miss_word",
        positive=f"{p}_reached_word",
    )

    for outcome, destination in (("miss", not_reached), ("reached", reached)):
        fsm.go(
            f"{p}_{outcome}_word",
            "scratch_in",
            "r",
            f"{p}_{outcome}_word_s",
        )
        fsm.go(
            f"{p}_{outcome}_word_s",
            "ring_out",
            "s",
            f"{p}_{outcome}_tail_r",
        )
        fsm.go(
            f"{p}_{outcome}_tail_r",
            "ring_in",
            "r",
            f"{p}_{outcome}_tail_test",
        )
        fsm.sign(
            f"{p}_{outcome}_tail_test",
            "logic",
            "",
            negative=f"{p}_{outcome}_robot_s",
            zero=f"{p}_{outcome}_row_s",
            positive=f"{p}_{outcome}_row_s",
        )
        fsm.go(
            f"{p}_{outcome}_row_s",
            "ring_out",
            "s",
            f"{p}_{outcome}_tail_r",
        )
        fsm.go(
            f"{p}_{outcome}_robot_s",
            "ring_out",
            "s",
            f"{p}_{outcome}_distance_r",
        )
        fsm.go(
            f"{p}_{outcome}_distance_r",
            "ring_in",
            "r",
            f"{p}_{outcome}_distance_s",
        )
        fsm.go(
            f"{p}_{outcome}_distance_s",
            "ring_out",
            "s",
            destination,
        )


def _add_direction_try(
    fsm: Fsm,
    current_mod: int,
    direction: str,
    *,
    delta: int,
    next_direction: str,
) -> None:
    target_mod = (current_mod - 1) % 3
    p = f"move{current_mod}_{direction}"
    fsm.go(f"{p}_start", "logic", f"{_lit(16)}b", f"{p}_row_r")
    fsm.go(f"{p}_row_r", "ring_in", "r", f"{p}_row_s")
    fsm.go(f"{p}_row_s", "ring_out", "s", f"{p}_dec")
    fsm.bp(
        f"{p}_dec",
        "logic",
        "m",
        zero=f"{p}_robot_r",
        positive=f"{p}_row_r",
    )
    fsm.go(f"{p}_robot_r", "ring_in", "r", f"{p}_robot_s")
    fsm.go(f"{p}_robot_s", "ring_out", "s", f"{p}_decode")
    fsm.go(f"{p}_decode", "logic", _decode_robot(), f"{p}_addr_save")
    fsm.go(f"{p}_addr_save", "scratch_out", "s", f"{p}_distance_r")
    fsm.go(f"{p}_distance_r", "ring_in", "r", f"{p}_distance_s")
    fsm.go(f"{p}_distance_s", "ring_out", "s", f"{p}_addr_back")
    fsm.go(f"{p}_addr_back", "scratch_in", "r", f"{p}_candidate")
    delta_code = f"M{_lit(abs(delta))}{'N' if delta < 0 else ''}+"
    fsm.go(f"{p}_candidate", "logic", delta_code, f"{p}_candidate_save")
    fsm.go(
        f"{p}_candidate_save",
        "scratch_out",
        "s",
        f"{p}_divide",
    )
    fsm.go(f"{p}_divide", "logic", f"M{_lit(16)}W/bW", f"{p}_x_save")
    fsm.go(f"{p}_x_save", "scratch_out", "s", f"{p}_rotate_check")
    fsm.bp(
        f"{p}_rotate_check",
        "logic",
        "",
        zero=f"{p}_target_r",
        positive=f"{p}_rotate_r",
    )
    fsm.go(f"{p}_rotate_r", "ring_in", "r", f"{p}_rotate_s")
    fsm.go(f"{p}_rotate_s", "ring_out", "s", f"{p}_rotate_dec")
    fsm.go(f"{p}_rotate_dec", "logic", "m", f"{p}_rotate_check")
    fsm.go(f"{p}_target_r", "ring_in", "r", f"{p}_target_save")
    fsm.go(f"{p}_target_save", "scratch_out", "ss", f"{p}_candidate_back")
    fsm.go(f"{p}_candidate_back", "scratch_in", "r", f"{p}_candidate_resave")
    fsm.go(
        f"{p}_candidate_resave",
        "scratch_out",
        "s",
        f"{p}_x_back",
    )
    fsm.go(f"{p}_x_back", "scratch_in", "r", f"{p}_mask")
    fsm.go(
        f"{p}_mask",
        "logic",
        _mask_from_x(PLANE_OFFSET[target_mod]) + "M",
        f"{p}_word_back",
    )
    fsm.go(f"{p}_word_back", "scratch_in", "r", f"{p}_test")
    fsm.sign(
        f"{p}_test",
        "logic",
        "&",
        negative=f"{p}_hit_word",
        zero=f"{p}_miss_word",
        positive=f"{p}_hit_word",
    )

    for outcome in ("hit", "miss"):
        fsm.go(
            f"{p}_{outcome}_word",
            "scratch_in",
            "r",
            f"{p}_{outcome}_word_s",
        )
        fsm.go(
            f"{p}_{outcome}_word_s",
            "ring_out",
            "s",
            f"{p}_{outcome}_tail_r",
        )
        fsm.go(
            f"{p}_{outcome}_tail_r",
            "ring_in",
            "r",
            f"{p}_{outcome}_tail_test",
        )
        fsm.sign(
            f"{p}_{outcome}_tail_test",
            "logic",
            "",
            negative=(
                f"{p}_hit_old_robot" if outcome == "hit" else f"{p}_miss_robot_s"
            ),
            zero=f"{p}_{outcome}_row_s",
            positive=f"{p}_{outcome}_row_s",
        )
        fsm.go(
            f"{p}_{outcome}_row_s",
            "ring_out",
            "s",
            f"{p}_{outcome}_tail_r",
        )

    fsm.go(f"{p}_miss_robot_s", "ring_out", "s", f"{p}_miss_distance_r")
    fsm.go(f"{p}_miss_distance_r", "ring_in", "r", f"{p}_miss_distance_s")
    fsm.go(f"{p}_miss_distance_s", "ring_out", "s", f"{p}_miss_discard")
    fsm.go(f"{p}_miss_discard", "scratch_in", "r", next_direction)

    # Hit: replace the robot metadata token, decrement remaining path length,
    # and emit one delta frame.
    fsm.go(
        f"{p}_hit_old_robot",
        "logic",
        _decode_robot(),
        f"{p}_old_addr_command",
    )
    # M retains the old address in B while A becomes the display command.
    fsm.go(f"{p}_old_addr_command", "logic", "M1+", f"{p}_old_addr_s")
    fsm.go(f"{p}_old_addr_s", "display", "s", f"{p}_old_color")
    fsm.go(f"{p}_old_color", "logic", "1N", f"{p}_old_color_s")
    fsm.go(f"{p}_old_color_s", "display", "s", f"{p}_new_addr_r")
    # The candidate address has remained at the scratch head throughout the
    # ring restoration.  Preserve it in B across the two display commands.
    fsm.go(f"{p}_new_addr_r", "scratch_in", "r", f"{p}_new_addr_command")
    fsm.go(f"{p}_new_addr_command", "logic", "M1+", f"{p}_new_addr_s")
    fsm.go(f"{p}_new_addr_s", "display", "s", f"{p}_new_color")
    fsm.go(f"{p}_new_color", "logic", f"{_lit(11)}N", f"{p}_new_color_s")
    fsm.go(f"{p}_new_color_s", "display", "s", f"{p}_new_addr_back")
    fsm.go(f"{p}_new_addr_back", "logic", "W", f"{p}_new_robot")
    fsm.go(f"{p}_new_robot", "logic", "M1W+N", f"{p}_new_robot_s")
    fsm.go(f"{p}_new_robot_s", "ring_out", "s", f"{p}_hit_distance_r")
    fsm.go(f"{p}_hit_distance_r", "ring_in", "r", f"{p}_hit_distance_edit")
    fsm.go(f"{p}_hit_distance_edit", "logic", "M1W+", f"{p}_hit_distance_s")
    fsm.go(f"{p}_hit_distance_s", "ring_out", "s", f"{p}_remaining")
    fsm.sign(
        f"{p}_remaining",
        "logic",
        f"M{_lit(DISTANCE_TAG)}W+",
        negative=f"{p}_swap_more",
        zero=f"{p}_swap_done",
        positive=f"{p}_swap_done",
    )
    fsm.go(f"{p}_swap_more", "logic", "0", f"{p}_swap_more_s")
    fsm.go(
        f"{p}_swap_more_s",
        "display",
        "s",
        f"move{target_mod}_up_start",
    )
    fsm.go(f"{p}_swap_done", "logic", "0", f"{p}_swap_done_s")
    fsm.go(f"{p}_swap_done_s", "display", "s", "flag_x")


def _add_move_step(fsm: Fsm, current_mod: int) -> None:
    """Choose up/right/down/left with two ring laps instead of four probes."""

    target_mod = (current_mod - 1) % 3
    p = f"move{current_mod}"

    # First lap reaches the two metadata tokens while preserving row order.
    fsm.go(f"{p}_start", "logic", f"{_lit(16)}b", f"{p}_scan_r")
    fsm.go(f"{p}_scan_r", "ring_in", "r", f"{p}_scan_s")
    fsm.go(f"{p}_scan_s", "ring_out", "s", f"{p}_scan_dec")
    fsm.bp(
        f"{p}_scan_dec",
        "logic",
        "m",
        zero=f"{p}_robot_r",
        positive=f"{p}_scan_r",
    )
    fsm.go(f"{p}_robot_r", "ring_in", "r", f"{p}_robot_decode")
    fsm.go(f"{p}_robot_decode", "logic", _decode_robot(), f"{p}_addr_save")
    fsm.go(f"{p}_addr_save", "scratch_out", "ss", f"{p}_divide")

    # Derive y (in BP), x, and the count needed to restore the second lap.
    fsm.go(f"{p}_divide", "logic", f"M{_lit(16)}W/", f"{p}_y_save")
    fsm.go(f"{p}_y_save", "logic", "bW", f"{p}_x_save")
    fsm.go(f"{p}_x_save", "scratch_out", "s", f"{p}_tail")
    fsm.go(f"{p}_tail", "logic", f"WM{_lit(14)}-", f"{p}_tail_save")
    fsm.go(f"{p}_tail_save", "scratch_out", "s", f"{p}_cycle_addr1_r")

    # Queue [addr, addr, x, tail] -> [x, tail, addr, addr].
    fsm.go(f"{p}_cycle_addr1_r", "scratch_in", "r", f"{p}_cycle_addr1_s")
    fsm.go(f"{p}_cycle_addr1_s", "scratch_out", "s", f"{p}_cycle_addr2_r")
    fsm.go(f"{p}_cycle_addr2_r", "scratch_in", "r", f"{p}_cycle_addr2_s")
    fsm.go(f"{p}_cycle_addr2_s", "scratch_out", "s", f"{p}_x_r")

    # k is the bit index of the current x in the target modulo plane.
    fsm.go(f"{p}_x_r", "scratch_in", "r", f"{p}_k")
    fsm.go(
        f"{p}_k",
        "logic",
        f"M{_lit(15)}-M{_lit(PLANE_OFFSET[target_mod])}W+M",
        f"{p}_k_save",
    )
    fsm.go(f"{p}_k_save", "scratch_out", "ss", f"{p}_cycle_tail_r")

    # Queue [tail, addr, addr, k, k] -> [k, k, tail, addr, addr].
    for index, target in (
        (1, f"{p}_cycle_addr3_r"),
        (2, f"{p}_cycle_addr4_r"),
        (3, f"{p}_distance_r"),
    ):
        name = "tail" if index == 1 else f"addr{index + 1}"
        fsm.go(
            f"{p}_cycle_{name}_r",
            "scratch_in",
            "r",
            f"{p}_cycle_{name}_s",
        )
        fsm.go(f"{p}_cycle_{name}_s", "scratch_out", "s", target)

    fsm.go(f"{p}_distance_r", "ring_in", "r", f"{p}_distance_save")
    fsm.go(f"{p}_distance_save", "scratch_out", "s", f"{p}_rotate_dec")

    # Border walls guarantee y>=1.  Rotate to row y-1 while B retains k.
    fsm.go(f"{p}_rotate_dec", "logic", "m", f"{p}_rotate_check")
    fsm.bp(
        f"{p}_rotate_check",
        "logic",
        "",
        zero=f"{p}_up_r",
        positive=f"{p}_rotate_r",
    )
    fsm.go(f"{p}_rotate_r", "ring_in", "r", f"{p}_rotate_s")
    fsm.go(f"{p}_rotate_s", "ring_out", "s", f"{p}_rotate_more")
    fsm.go(f"{p}_rotate_more", "logic", "m", f"{p}_rotate_check")

    # Up uses bit k in row y-1.
    fsm.go(f"{p}_up_r", "ring_in", "r", f"{p}_up_s")
    fsm.go(f"{p}_up_s", "ring_out", "s", f"{p}_up_test")
    fsm.sign(
        f"{p}_up_test",
        "logic",
        "}M1W&",
        negative=f"{p}_up_hit_discard1",
        zero=f"{p}_up_miss_k",
        positive=f"{p}_up_hit_discard1",
    )
    fsm.go(
        f"{p}_up_hit_discard1",
        "scratch_in",
        "r",
        f"{p}_up_hit_discard2",
    )
    fsm.go(
        f"{p}_up_hit_discard2",
        "scratch_in",
        "r",
        f"{p}_up_tail_r",
    )

    # Row y is shifted once.  Bits 0 and 2 then record right and left.
    fsm.go(f"{p}_up_miss_k", "scratch_in", "r", f"{p}_right_shift")
    fsm.go(f"{p}_right_shift", "logic", "M1W-M", f"{p}_current_r")
    fsm.go(f"{p}_current_r", "ring_in", "r", f"{p}_current_s")
    fsm.go(f"{p}_current_s", "ring_out", "s", f"{p}_horizontal_bits")
    fsm.sign(
        f"{p}_horizontal_bits",
        "logic",
        "}M5W&bM1W&",
        negative=f"{p}_right_hit_discard",
        zero=f"{p}_right_miss_k",
        positive=f"{p}_right_hit_discard",
    )
    fsm.go(
        f"{p}_right_hit_discard",
        "scratch_in",
        "r",
        f"{p}_right_tail_r",
    )

    # Down uses bit k in row y+1; left is the saved bit 2 from row y.
    fsm.go(f"{p}_right_miss_k", "scratch_in", "r", f"{p}_down_k")
    fsm.go(f"{p}_down_k", "logic", "M", f"{p}_down_r")
    fsm.go(f"{p}_down_r", "ring_in", "r", f"{p}_down_s")
    fsm.go(f"{p}_down_s", "ring_out", "s", f"{p}_down_test")
    fsm.sign(
        f"{p}_down_test",
        "logic",
        "}M1W&",
        negative=f"{p}_down_tail_r",
        zero=f"{p}_left_test",
        positive=f"{p}_down_tail_r",
    )
    fsm.bp(
        f"{p}_left_test",
        "logic",
        "]]",
        zero="path_broken",
        positive=f"{p}_left_tail_r",
    )

    # Complete the second lap.  Base tail is 14-y; early hits add the
    # unexamined current/down rows so every route rotates exactly 16 rows.
    for direction, extra in (("up", 2), ("right", 1), ("down", 0), ("left", 0)):
        tail = f"{p}_{direction}_tail"
        fsm.go(f"{tail}_r", "scratch_in", "r", f"{tail}_adjust")
        code = f"M{extra}W+" if extra else ""
        fsm.go(f"{tail}_adjust", "logic", code + "b", f"{tail}_check")
        fsm.bp(
            f"{tail}_check",
            "logic",
            "",
            zero=f"{p}_{direction}_old_addr_r",
            positive=f"{tail}_rotate_r",
        )
        fsm.go(f"{tail}_rotate_r", "ring_in", "r", f"{tail}_rotate_s")
        fsm.go(f"{tail}_rotate_s", "ring_out", "s", f"{tail}_rotate_dec")
        fsm.go(f"{tail}_rotate_dec", "logic", "m", f"{tail}_check")

    # Emit the delta frame and replace the two metadata tokens.
    for direction, delta in (
        ("up", -16),
        ("right", 1),
        ("down", 16),
        ("left", -1),
    ):
        q = f"{p}_{direction}"
        fsm.go(f"{q}_old_addr_r", "scratch_in", "r", f"{q}_old_addr_command")
        fsm.go(f"{q}_old_addr_command", "logic", "M1+", f"{q}_old_addr_s")
        fsm.go(f"{q}_old_addr_s", "display", "s", f"{q}_old_color")
        fsm.go(f"{q}_old_color", "logic", "1N", f"{q}_old_color_s")
        fsm.go(f"{q}_old_color_s", "display", "s", f"{q}_new_addr_r")
        fsm.go(f"{q}_new_addr_r", "scratch_in", "r", f"{q}_new_addr")
        delta_code = f"M{_lit(abs(delta))}{'N' if delta < 0 else ''}+"
        fsm.go(f"{q}_new_addr", "logic", delta_code, f"{q}_new_addr_command")
        fsm.go(f"{q}_new_addr_command", "logic", "M1+", f"{q}_new_addr_s")
        fsm.go(f"{q}_new_addr_s", "display", "s", f"{q}_new_color")
        fsm.go(f"{q}_new_color", "logic", f"{_lit(11)}N", f"{q}_new_color_s")
        fsm.go(f"{q}_new_color_s", "display", "s", f"{q}_new_addr_back")
        fsm.go(f"{q}_new_addr_back", "logic", "W", f"{q}_new_robot")
        fsm.go(f"{q}_new_robot", "logic", "M1W+N", f"{q}_new_robot_s")
        fsm.go(f"{q}_new_robot_s", "ring_out", "s", f"{q}_distance_r")
        fsm.go(f"{q}_distance_r", "scratch_in", "r", f"{q}_distance_edit")
        fsm.go(f"{q}_distance_edit", "logic", "M1W+", f"{q}_distance_s")
        fsm.go(f"{q}_distance_s", "ring_out", "s", f"{q}_remaining")
        fsm.sign(
            f"{q}_remaining",
            "logic",
            f"M{_lit(DISTANCE_TAG)}W+",
            negative=f"{q}_swap_more",
            zero=f"{q}_swap_done",
            positive=f"{q}_swap_done",
        )
        fsm.go(f"{q}_swap_more", "logic", "0", f"{q}_swap_more_s")
        fsm.go(f"{q}_swap_more_s", "display", "s", f"move{target_mod}_start")
        fsm.go(f"{q}_swap_done", "logic", "0", f"{q}_swap_done_s")
        fsm.go(f"{q}_swap_done_s", "display", "s", "flag_x")


def build_controller_fsm() -> Fsm:
    fsm = Fsm()

    # Setup: one outer-row token in scratch, 16 pixels per row in BP.
    fsm.go("boot", "logic", f"@{_lit(15)}", "outer_send")
    fsm.go("outer_send", "scratch_out", "s", "row_init")
    fsm.go("row_init", "logic", f"0M{_lit(16)}b", "bit_read")
    fsm.go("bit_read", "input", "r", "bit_test")
    fsm.sign(
        "bit_test",
        "logic",
        "",
        negative="wall_color",
        zero="path_color",
        positive="wall_color",
    )
    fsm.go("path_color", "logic", "1N", "path_color_s")
    fsm.go("path_color_s", "display", "s", "path_acc")
    fsm.go("path_acc", "logic", "WM+M1+M", "bit_dec")
    fsm.go("wall_color", "logic", f"{_lit(8)}N", "wall_color_s")
    fsm.go("wall_color_s", "display", "s", "wall_acc")
    fsm.go("wall_acc", "logic", "WM+M", "bit_dec")
    fsm.bp("bit_dec", "logic", "m", zero="row_word", positive="bit_read")
    fsm.go("row_word", "logic", "W", "row_word_s")
    fsm.go("row_word_s", "ring_out", "s", "row_reset")
    fsm.go("row_reset", "logic", "0M", "outer_r")
    fsm.go("outer_r", "scratch_in", "r", "outer_test")
    fsm.sign(
        "outer_test",
        "logic",
        "",
        negative="setup_rx",
        zero="setup_rx",
        positive="outer_dec",
    )
    fsm.go("outer_dec", "logic", "M1W-", "outer_resend")
    fsm.go("outer_resend", "scratch_out", "s", "row_init")

    # Setup robot address and first frame.
    fsm.go("setup_rx", "input", "r", "setup_rx_save")
    fsm.go("setup_rx_save", "scratch_out", "s", "setup_ry")
    fsm.go("setup_ry", "input", "r", "setup_base")
    fsm.go("setup_base", "logic", f"M{_lit(16)}W*M", "setup_rx_back")
    fsm.go("setup_rx_back", "scratch_in", "r", "setup_addr")
    fsm.go("setup_addr", "logic", "+", "setup_addr_save")
    fsm.go("setup_addr_save", "scratch_out", "s", "setup_addr_command")
    fsm.go("setup_addr_command", "logic", "M1W+", "setup_addr_s")
    fsm.go("setup_addr_s", "display", "s", "setup_robot_color")
    fsm.go("setup_robot_color", "logic", f"{_lit(11)}N", "setup_robot_color_s")
    fsm.go("setup_robot_color_s", "display", "s", "setup_swap")
    fsm.go("setup_swap", "logic", "0", "setup_swap_s")
    fsm.go("setup_swap_s", "display", "s", "setup_addr_back")
    fsm.go("setup_addr_back", "scratch_in", "r", "setup_robot_token")
    fsm.go("setup_robot_token", "logic", "M1W+N", "setup_robot_token_s")
    fsm.go("setup_robot_token_s", "ring_out", "s", "setup_distance")
    fsm.go("setup_distance", "logic", f"{_lit(DISTANCE_TAG)}N", "setup_distance_s")
    fsm.go("setup_distance_s", "ring_out", "s", "flag_x")

    # New flag: compute/display address, reset old BFS planes, then seed slot 0.
    fsm.go("flag_x", "input", "r", "flag_x_save")
    fsm.go("flag_x_save", "scratch_out", "s", "flag_y")
    fsm.go("flag_y", "input", "r", "flag_base")
    fsm.go("flag_base", "logic", f"M{_lit(16)}W*M", "flag_x_back")
    fsm.go("flag_x_back", "scratch_in", "r", "flag_addr")
    fsm.go("flag_addr", "logic", "+", "flag_addr_save")
    fsm.go("flag_addr_save", "scratch_out", "s", "flag_addr_command")
    fsm.go("flag_addr_command", "logic", "M1W+", "flag_addr_s")
    fsm.go("flag_addr_s", "display", "s", "flag_color")
    fsm.go("flag_color", "logic", f"{_lit(10)}N", "flag_color_s")
    fsm.go("flag_color_s", "display", "s", "reset_start")

    _add_reset_pass(fsm, "flag_addr_back")
    fsm.go("flag_addr_back", "scratch_in", "r", "flag_divide")
    fsm.go("flag_divide", "logic", f"M{_lit(16)}W/bW", "flag_delta")
    fsm.go(
        "flag_delta",
        "logic",
        f"M{_lit(15)}-M1{{M{_lit(UPDATE_FACTOR[0])}W*M",
        "seed_rotate_check",
    )
    fsm.bp(
        "seed_rotate_check",
        "logic",
        "",
        zero="seed_word_r",
        positive="seed_rotate_r",
    )
    fsm.go("seed_rotate_r", "ring_in", "r", "seed_rotate_s")
    fsm.go("seed_rotate_s", "ring_out", "s", "seed_rotate_dec")
    fsm.go("seed_rotate_dec", "logic", "m", "seed_rotate_check")
    fsm.go("seed_word_r", "ring_in", "r", "seed_word_add")
    fsm.go("seed_word_add", "logic", "+", "seed_word_s")
    fsm.go("seed_word_s", "ring_out", "s", "seed_tail_r")
    fsm.go("seed_tail_r", "ring_in", "r", "seed_tail_test")
    fsm.sign(
        "seed_tail_test",
        "logic",
        "",
        negative="seed_robot_s",
        zero="seed_row_s",
        positive="seed_row_s",
    )
    fsm.go("seed_row_s", "ring_out", "s", "seed_tail_r")
    fsm.go("seed_robot_s", "ring_out", "s", "seed_distance_r")
    fsm.go("seed_distance_r", "ring_in", "r", "seed_distance_reset")
    fsm.go(
        "seed_distance_reset",
        "logic",
        f"{_lit(DISTANCE_TAG)}N",
        "seed_distance_s",
    )
    fsm.go("seed_distance_s", "ring_out", "s", "wave1_vertical_start")

    # Three modulo wave cycles.
    for target_mod, source_mod in ((1, 0), (2, 1), (0, 2)):
        next_wave = (target_mod + 1) % 3
        if next_wave == 0:
            next_wave = 0
        base = f"wave{target_mod}"
        _add_vertical_pass(
            fsm,
            f"{base}_vertical",
            source_mod=source_mod,
            target_mod=target_mod,
            target=f"check{target_mod}_count",
            increment_distance=True,
        )

    _add_wave_check(
        fsm,
        1,
        not_reached="wave2_vertical_start",
        reached="move1_start",
    )
    _add_wave_check(
        fsm,
        2,
        not_reached="wave0_vertical_start",
        reached="move2_start",
    )
    _add_wave_check(
        fsm,
        0,
        not_reached="wave1_vertical_start",
        reached="move0_start",
    )

    for current_mod in range(3):
        _add_move_step(fsm, current_mod)

    fsm.go("path_broken", "logic", "H", "path_broken")
    return fsm


def build_relay_room() -> CompiledRoom:
    fsm = Fsm()
    fsm.go("recv", "in", "@r", "send")
    fsm.go("send", "out", "s", "recv")
    return compile_fsm(fsm, SERVICE_ZONES, min_width=35)


def build_update_room() -> CompiledRoom:
    fsm = Fsm()
    fsm.go("mod", "in", "@rb", "mode_test")
    fsm.sign(
        "mode_test",
        "logic",
        "M3W-",
        negative="dispatch0",
        zero="vertical_adjust",
        positive="vertical_adjust",
    )
    fsm.bp("dispatch0", "logic", "", zero="init0", positive="dispatch1")
    fsm.bp("dispatch1", "logic", "m", zero="init1", positive="init2")
    fsm.go("vertical_adjust", "logic", "mmm", "vertical_dispatch0")
    fsm.bp(
        "vertical_dispatch0",
        "logic",
        "",
        zero="vertical_init0",
        positive="vertical_dispatch1",
    )
    fsm.bp(
        "vertical_dispatch1",
        "logic",
        "m",
        zero="vertical_init1",
        positive="vertical_init2",
    )
    for mod in range(3):
        factor = UPDATE_FACTOR[mod]
        fsm.go(f"init{mod}", "in", "rb", f"contribution{mod}")
        fsm.go(f"contribution{mod}", "in", "rM", f"word{mod}")
        fsm.go(f"word{mod}", "in", "rW&", f"delta{mod}")
        fsm.go(
            f"delta{mod}",
            "logic",
            f"M{_lit(factor)}W*M",
            f"word_again{mod}",
        )
        fsm.go(f"word_again{mod}", "in", "r+", f"send{mod}")
        fsm.go(f"send{mod}", "out", "s", f"dec{mod}")
        fsm.bp(
            f"dec{mod}",
            "logic",
            "m",
            zero="mod",
            positive=f"contribution{mod}",
        )

        fsm.go(f"vertical_init{mod}", "in", "rb", f"vertical_prev{mod}")
        fsm.go(f"vertical_prev{mod}", "in", "rM", f"vertical_left{mod}")
        fsm.go(f"vertical_left{mod}", "in", "r|M", f"vertical_right{mod}")
        fsm.go(f"vertical_right{mod}", "in", "r|M", f"vertical_next{mod}")
        fsm.go(f"vertical_next{mod}", "in", "r|M", f"vertical_word{mod}")
        fsm.go(f"vertical_word{mod}", "in", "rW&", f"vertical_delta{mod}")
        fsm.go(
            f"vertical_delta{mod}",
            "logic",
            f"M{_lit(factor)}W*M",
            f"vertical_word_again{mod}",
        )
        fsm.go(
            f"vertical_word_again{mod}",
            "in",
            "r+",
            f"vertical_send{mod}",
        )
        fsm.go(
            f"vertical_send{mod}",
            "out",
            "s",
            f"vertical_frontier{mod}",
        )
        fsm.go(
            f"vertical_frontier{mod}",
            "in",
            "rM",
            f"vertical_dec{mod}",
        )
        fsm.bp(
            f"vertical_dec{mod}",
            "logic",
            "m",
            zero="mod",
            positive=f"vertical_left{mod}",
        )
    return _compile_literal_safe(fsm, SERVICE_ZONES, min_width=60)


def build_display_driver() -> CompiledRoom:
    fsm = Fsm()
    fsm.go("recv", "in", "@r", "test")
    fsm.sign(
        "test",
        "logic",
        "",
        negative="data_decode",
        zero="swap_value",
        positive="addr_decode",
    )
    fsm.go("data_decode", "logic", "NM1W-", "data_send")
    fsm.go("data_send", "data", "s", "recv")
    fsm.go("addr_decode", "logic", "M1W-", "addr_send")
    fsm.go("addr_send", "addr", "s", "recv")
    fsm.go("swap_value", "logic", "1", "swap_send")
    fsm.go("swap_send", "swap", "s", "recv")
    return compile_fsm(fsm, DRIVER_ZONES, min_width=110)


def build_rooms() -> Rooms:
    return Rooms(
        controller=_compile_literal_safe(
            build_controller_fsm(),
            CONTROLLER_ZONES,
            min_width=170,
            right_padding=8,
        ),
        ring_relay=build_relay_room(),
        scratch_relay=build_relay_room(),
        update=build_update_room(),
        display_driver=build_display_driver(),
    )


def _room_bounds(top: int, left: int, room: CompiledRoom) -> tuple[int, int, int, int]:
    return top, left, top + len(room.rows) - 1, left + len(room.rows[0]) - 1


def build_pathfinder() -> str:
    rooms = build_rooms()
    cv = Canvas()

    controller_top = 4
    controller_left = 80
    cv.put(controller_top, controller_left, rooms.controller.rows)
    _, _, controller_bottom, _ = _room_bounds(
        controller_top, controller_left, rooms.controller
    )

    def controller_col(zone: str) -> int:
        return controller_left + rooms.controller.zones[zone]

    service_tops = {
        "ring": controller_bottom + 11,
        "scratch": controller_bottom + 4,
        "update": controller_bottom + 4,
    }
    placed: list[tuple[str, CompiledRoom, int, int, str, str]] = []
    for name, room, out_zone, in_zone in (
        ("ring", rooms.ring_relay, "ring_out", "ring_in"),
        ("scratch", rooms.scratch_relay, "scratch_out", "scratch_in"),
        ("update", rooms.update, "update_out", "update_in"),
    ):
        service_top = service_tops[name]
        left = controller_col(out_zone) - room.zones["in"]
        cv.put(service_top, left, room.rows)
        placed.append((name, room, service_top, left, out_zone, in_zone))

    # Vertical request/response pairs between controller and services.
    for _name, room, top, left, out_zone, in_zone in placed:
        request_col = controller_col(out_zone)
        response_col = controller_col(in_zone)
        room_input_col = left + room.zones["in"]
        room_output_col = left + room.zones["out"]
        if room_input_col != request_col or room_output_col != response_col:
            raise AssertionError("service/controller zone mismatch")
        cv.pipe(
            [
                (controller_bottom + 1, request_col),
                (top - 1, request_col),
            ]
        )
        cv.pipe(
            [
                (top - 1, response_col),
                (controller_bottom + 1, response_col),
            ]
        )

    # Input room below the controller, feeding upward.
    input_col = controller_col("input")
    services_bottom = max(top + len(room.rows) - 1 for _, room, top, *_ in placed)
    input_top = services_bottom + 20
    cv.put(input_top, input_col - 1, ["+-+", "|I|", "+-+"])
    cv.pipe([(input_top - 1, input_col), (controller_bottom + 1, input_col)])

    # Display command router below the services.
    driver_top = input_top + 30
    driver_left = controller_col("display") - rooms.display_driver.zones["in"]
    cv.put(driver_top, driver_left, rooms.display_driver.rows)
    driver_bottom = driver_top + len(rooms.display_driver.rows) - 1

    # Controller command -> router input.
    cmd_col = controller_col("display")
    driver_input_col = driver_left + rooms.display_driver.zones["in"]
    cv.pipe([(controller_bottom + 1, cmd_col), (driver_top - 1, driver_input_col)])

    # Display to the right and below the drivers.
    display_top = driver_bottom + 30
    display_left = driver_left + rooms.display_driver.zones["addr"] - 4
    display = ["+" + "=" * BOARD + "+"]
    display.extend([":" + "." * BOARD + ":" for _ in range(BOARD)])
    display.append("+" + "=" * BOARD + "+")
    cv.put(display_top, display_left, display)

    addr_display_col = driver_left + rooms.display_driver.zones["addr"]
    display_addr_col = display_left + 4
    if addr_display_col != display_addr_col:
        raise AssertionError("display address zone mismatch")
    cv.pipe(
        [(driver_bottom + 1, addr_display_col), (display_top - 1, display_addr_col)]
    )
    cv.cells[(display_top - 1, display_addr_col)] = "v"

    data_display_col = driver_left + rooms.display_driver.zones["data"]
    display_data_row = display_top + 5
    cv.pipe(
        [
            (driver_bottom + 1, data_display_col),
            (display_data_row, data_display_col),
            (display_data_row, display_left - 1),
        ]
    )
    cv.cells[(display_data_row, display_left - 1)] = ">"

    swap_display_col = driver_left + rooms.display_driver.zones["swap"]
    display_swap_col = display_left + 12
    swap_route_row = display_top + BOARD + 10
    cv.pipe(
        [
            (driver_bottom + 1, swap_display_col),
            (swap_route_row, swap_display_col),
            (swap_route_row, display_swap_col),
            (display_top + BOARD + 2, display_swap_col),
        ]
    )
    cv.cells[(display_top + BOARD + 2, display_swap_col)] = "^"

    return cv.render()
