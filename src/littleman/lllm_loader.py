"""Frozen LLLM loader stream and an executable two-pipe test rig.

The generated LOADER has one man, one incoming pipe, and one outgoing pipe.
Its persistent state is a positive 63-bit word in B:

* bits 0..38: the first three records of the current output token;
* bits 39..43: ``W - 1 - x + 16``;
* bits 44..48: ``H - 1 - y + 16``;
* bits 49..52: y;
* bits 53..60: the remembered man address;
* bits 61..62: a temporary fourth-record continuation tag.

Position and glyph decisions copy only the relevant value to BP and decode it
by parity, leaving B untouched.  A fourth-record send consumes a BP snapshot
to rebuild the low 39 bits and metadata separately.  This avoids an internal
scratch pipe while preserving the frozen two-pipe interface.
"""

from __future__ import annotations

from dataclasses import dataclass

from .canvas import Canvas

BASE = 1 << 13
RECORD_MASK = (1 << 39) - 1
D_SHIFT = 39
E_SHIFT = 44
Y_SHIFT = 49
MAN_SHIFT = 53
TAG_SHIFT = 61

SPACE = 0
WALL = 4 | (1 << 4) | (1 << 12)
HEADING = tuple(3 | (2 << 4) | (value << 8) for value in range(4))
DIGIT = tuple(8 | (3 << 4) | (value << 8) for value in range(10))
M_RECORD = 12 | (4 << 4)
ADD_RECORD = 10 | (5 << 4)
SUB_RECORD = 10 | (6 << 4)
X_RECORD = 3 | (7 << 4)
H_RECORD = 3 | (8 << 4)

GLYPH_RECORD = {
    ord(" "): SPACE,
    ord("^"): HEADING[0],
    ord(">"): HEADING[1],
    ord("v"): HEADING[2],
    ord("<"): HEADING[3],
    **{ord(str(value)): DIGIT[value] for value in range(10)},
    ord("M"): M_RECORD,
    ord("+"): ADD_RECORD,
    ord("-"): SUB_RECORD,
    ord("X"): X_RECORD,
    ord("H"): H_RECORD,
}


def reference_stream(tokens: list[int]) -> list[int]:
    """Return the frozen LOADER output stream for one complete input stream."""

    width, height = tokens[:2]
    chars = iter(tokens[2 : 2 + width * height])
    records: list[int] = []
    man_addr = 0
    for y in range(16):
        for x in range(16):
            if x >= width or y >= height:
                record = SPACE
            else:
                char = next(chars)
                if x in (0, width - 1) or y in (0, height - 1):
                    record = WALL
                elif char == ord("@"):
                    record = SPACE
                    man_addr = y * 16 + x
                else:
                    record = GLYPH_RECORD[char]
            records.append(record)

    packed = [
        sum(records[base + offset] << (13 * offset) for offset in range(4))
        for base in range(0, 256, 4)
    ]
    return packed + [man_addr] + tokens[2 + width * height :]


@dataclass(frozen=True)
class _Block:
    name: str
    zone: str
    code: str
    kind: str
    targets: tuple[str, ...]


class _Fsm:
    def __init__(self) -> None:
        self.blocks: list[_Block] = []

    def go(self, name: str, zone: str, code: str, target: str) -> None:
        self.blocks.append(_Block(name, zone, code, "goto", (target,)))

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
        self.blocks.append(_Block(name, zone, code, "sign", (negative, zero, positive)))

    def parity(
        self,
        name: str,
        zone: str,
        code: str,
        *,
        even: str,
        odd: str,
    ) -> None:
        self.blocks.append(_Block(name, zone, code, "parity", (even, odd)))


@dataclass(frozen=True)
class _Room:
    rows: list[str]
    zones: dict[str, int]


ZONES = {"logic": 0, "input": 40, "output": 80}


def _literal(value: int) -> str:
    if value < 0:
        return f"`{-value}`N"
    if value < 10:
        return str(value)
    return f"`{value}`"


def _add_constant(value: int) -> str:
    """Add a compile-time constant to A without relying on the old B."""

    return f"M{_literal(value)}W+"


def _literal_safe_fsm(fsm: _Fsm) -> tuple[_Fsm, dict[str, int]]:
    """Give each literal shape a private horizontal span.

    Equal backtick shapes share a span and therefore form valid vertical
    pairs.  Distinct shapes have disjoint spans, so no operation can appear
    between another shape's paired backticks.
    """

    normalized = _Fsm()
    for block in fsm.blocks:
        first_tick = block.code.find("`")
        if first_tick >= 0:
            # Every generated block has at most one literal.  Leading spaces
            # align its opening delimiter, collapsing shapes to digit length.
            code = " " * (3 - first_tick) + block.code
            block = _Block(
                block.name,
                block.zone,
                code,
                block.kind,
                block.targets,
            )
        normalized.blocks.append(block)

    rewritten = _Fsm()
    offsets = dict(ZONES)
    groups: dict[tuple[int, ...], list[str]] = {}
    for block in normalized.blocks:
        ticks = tuple(index for index, char in enumerate(block.code) if char == "`")
        if ticks:
            groups.setdefault(ticks, []).append(block.code)

    group_offset: dict[tuple[int, ...], int] = {}
    cursor = 100
    for ticks, codes in groups.items():
        group_offset[ticks] = cursor
        cursor += max(map(len, codes)) + 2

    names: dict[tuple[int, ...], str] = {}
    for block in normalized.blocks:
        ticks = tuple(index for index, char in enumerate(block.code) if char == "`")
        if not ticks:
            rewritten.blocks.append(block)
            continue
        zone = names.setdefault(ticks, f"literal_{len(names)}")
        offsets[zone] = group_offset[ticks]
        rewritten.blocks.append(
            _Block(block.name, zone, block.code, block.kind, block.targets)
        )
    return rewritten, offsets


def _compile(fsm: _Fsm, *, min_width: int = 0) -> _Room:
    """Embed goto, sign-X, and BP-parity-x blocks in one room."""

    fsm, zone_offsets = _literal_safe_fsm(fsm)
    names = {block.name for block in fsm.blocks}
    if len(names) != len(fsm.blocks):
        raise ValueError("duplicate FSM block")
    for block in fsm.blocks:
        missing = [target for target in block.targets if target not in names]
        if missing:
            raise ValueError(f"{block.name}: unknown targets {missing}")

    zone_base = 12
    zones = {name: zone_base + offset for name, offset in zone_offsets.items()}
    block_rows: dict[str, int] = {}
    route_rows: dict[str, int] = {}
    next_band = 3
    band_height = {"goto": 2, "sign": 4, "parity": 4}
    for block in fsm.blocks:
        route_rows[block.name] = next_band
        block_rows[block.name] = next_band + (
            2 if block.kind in ("sign", "parity") else 1
        )
        next_band += band_height[block.kind]

    edge_specs: list[tuple[str, str, str]] = []
    for block in fsm.blocks:
        labels = {
            "goto": ("goto",),
            "sign": ("negative", "zero", "positive"),
            "parity": ("even", "odd"),
        }[block.kind]
        edge_specs.extend(
            (block.name, label, target)
            for label, target in zip(labels, block.targets, strict=True)
        )

    literal_end = max(
        zones[block.zone] + len(block.code) + 2
        for block in fsm.blocks
        if "`" in block.code
    )
    max_plain_length = max(
        len(block.code) for block in fsm.blocks if "`" not in block.code
    )
    branch_col = literal_end + max_plain_length + 4
    block_starts = {
        block.name: (
            zones[block.zone] if "`" in block.code else branch_col - len(block.code) - 2
        )
        for block in fsm.blocks
    }
    by_name = {block.name: block for block in fsm.blocks}
    intervals: list[tuple[int, int, str, str, str, str]] = []
    for source, label, target in edge_specs:
        block = by_name[source]
        offset = {
            ("sign", "negative"): -1,
            ("sign", "zero"): 0,
            ("sign", "positive"): 1,
            ("parity", "even"): -1,
            ("parity", "odd"): 1,
        }.get((block.kind, label), 0)
        source_row = block_rows[source] + offset
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
    edge_track: dict[tuple[str, str], int] = {}
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
        edge_track[(source, label)] = track

    edge_base = branch_col + 3
    edge_cols = {edge: edge_base + track for edge, track in edge_track.items()}
    width = max(min_width, max(edge_cols.values()) + 4)
    height = next_band + 1
    grid = [[" "] * (width + 2) for _ in range(height + 2)]
    for column in range(width + 2):
        grid[0][column] = grid[height + 1][column] = "-"
    for row in range(height + 2):
        grid[row][0] = grid[row][width + 1] = "|"
    for row, column in (
        (0, 0),
        (0, width + 1),
        (height + 1, 0),
        (height + 1, width + 1),
    ):
        grid[row][column] = "+"

    def put(row: int, column: int, char: str) -> None:
        old = grid[row][column]
        if old not in (" ", char):
            raise ValueError(f"FSM collision at {(row, column)}: {old!r} vs {char!r}")
        grid[row][column] = char

    for block in fsm.blocks:
        row = block_rows[block.name]
        start = block_starts[block.name]
        put(row, start - 1, ">")
        for offset, char in enumerate(block.code):
            put(row, start + offset, char)

        if block.kind == "sign":
            put(row, branch_col, "X")
            put(row - 1, branch_col, ">")
            put(row + 1, branch_col, ">")
            starts = {
                "negative": row - 1,
                "zero": row,
                "positive": row + 1,
            }
        elif block.kind == "parity":
            put(row, branch_col, "x")
            put(row - 1, branch_col, ">")
            put(row + 1, branch_col, ">")
            starts = {"even": row - 1, "odd": row + 1}
        else:
            starts = {"goto": row}

        for label, target in zip(tuple(starts), block.targets, strict=True):
            source_row = starts[label]
            edge_col = edge_cols[(block.name, label)]
            target_row = block_rows[target]
            route_row = route_rows[target]
            target_entry = block_starts[target] - 1
            put(source_row, edge_col, "v" if route_row > source_row else "^")
            put(route_row, edge_col, "<")
            for entry_row in range(route_row, target_row):
                put(entry_row, target_entry, "v")
            put(target_row, target_entry, ">")

    public_zones = {name: zone_base + offset for name, offset in ZONES.items()}
    return _Room(["".join(row) for row in grid], public_zones)


def _add_reconstruction(
    fsm: _Fsm,
    prefix: str,
    *,
    start_bit: int,
    end_bit: int,
    target: str,
    weights: dict[int, int] | None = None,
    finish_with_copy: bool = True,
) -> str:
    """Add BP parity reconstruction, expecting the initial sum in A."""

    entry = f"{prefix}_bit{start_bit}"
    for bit in range(start_bit, end_bit):
        parity = f"{prefix}_bit{bit}"
        add = f"{prefix}_add{bit}"
        shift = f"{prefix}_shift{bit}"
        next_target = (
            f"{prefix}_bit{bit + 1}" if bit + 1 < end_bit else f"{prefix}_done"
        )
        weight = (1 << bit) if weights is None else weights.get(bit, 0)
        fsm.parity(parity, "logic", "", even=shift, odd=add)
        fsm.go(add, "logic", _add_constant(weight) if weight else "", shift)
        fsm.go(shift, "logic", "]", next_target)
    fsm.go(
        f"{prefix}_done",
        "logic",
        "M" if finish_with_copy else "",
        target,
    )
    return entry


def _add_lsb_trie(
    fsm: _Fsm,
    prefix: str,
    *,
    width: int,
    targets: dict[int, str],
    consume: bool = True,
) -> str:
    """Decode ``width`` low BP bits, consuming them before the target."""

    expected = set(range(1 << width))
    if set(targets) != expected:
        raise ValueError(f"{prefix}: incomplete trie")

    def build(
        bit: int,
        values: tuple[int, ...],
        path: str,
        *,
        shift_before: bool,
    ) -> str:
        name = f"{prefix}_{path or 'root'}"
        outcomes = {targets[value] for value in values}
        if len(outcomes) == 1:
            shifts = (int(shift_before) + width - bit) if consume else 0
            fsm.go(name, "logic", "]" * shifts, outcomes.pop())
            return name

        even_values = tuple(value for value in values if not (value >> bit) & 1)
        odd_values = tuple(value for value in values if (value >> bit) & 1)
        children: list[str] = []
        for label, members in (("0", even_values), ("1", odd_values)):
            if bit + 1 == width and not consume:
                child = targets[members[0]]
            elif bit + 1 == width:
                child = f"{name}_{label}_consume"
                fsm.go(child, "logic", "]", targets[members[0]])
            else:
                child = build(
                    bit + 1,
                    members,
                    path + label,
                    shift_before=True,
                )
            children.append(child)
        fsm.parity(
            name,
            "logic",
            "]" if shift_before else "",
            even=children[0],
            odd=children[1],
        )
        return name

    return build(0, tuple(range(1 << width)), "", shift_before=False)


def _at_weights(start_bit: int, end_bit: int) -> dict[int, int]:
    """Preserve state while copying y into the remembered address."""

    weights = {bit: 1 << bit for bit in range(start_bit, end_bit)}
    for bit in range(MAN_SHIFT + 4, MAN_SHIFT + 8):
        weights[bit] = 0
    for bit in range(Y_SHIFT, Y_SHIFT + 4):
        weights[bit] += 1 << (MAN_SHIFT + 4 + bit - Y_SHIFT)
    return weights


def _add_biased_status(
    fsm: _Fsm,
    prefix: str,
    *,
    padding: str,
    wall: str,
    interior: str,
) -> str:
    """Decode biased five-bit ``remaining + 16`` and consume the field."""

    for bit in range(4):
        even = f"{prefix}_low{bit}_even"
        odd = f"{prefix}_low{bit}_odd"
        fsm.parity(
            f"{prefix}_low{bit}",
            "logic",
            "",
            even=even,
            odd=odd,
        )
        next_even = f"{prefix}_low{bit + 1}" if bit < 3 else f"{prefix}_zero"
        fsm.go(even, "logic", "]", next_even)
        fsm.go(odd, "logic", "]" * (4 - bit), f"{prefix}_seen")

    for kind, odd_target in (("zero", wall), ("seen", interior)):
        even = f"{prefix}_{kind}_even"
        odd = f"{prefix}_{kind}_odd"
        fsm.parity(
            f"{prefix}_{kind}",
            "logic",
            "",
            even=even,
            odd=odd,
        )
        fsm.go(even, "logic", "]", padding)
        fsm.go(odd, "logic", "]", odd_target)
    return f"{prefix}_low0"


def _add_equality_test(
    fsm: _Fsm,
    prefix: str,
    *,
    width: int,
    value: int,
    equal: str,
    different: str,
) -> str:
    """Test BP's low bits against one value; later BP contents are dead."""

    for bit in range(width):
        expected_odd = bool((value >> bit) & 1)
        if bit + 1 == width:
            expected_target = equal
        else:
            expected_target = f"{prefix}_shift{bit}"
            fsm.go(
                expected_target,
                "logic",
                "]",
                f"{prefix}_bit{bit + 1}",
            )
        fsm.parity(
            f"{prefix}_bit{bit}",
            "logic",
            "",
            even=different if expected_odd else expected_target,
            odd=expected_target if expected_odd else different,
        )
    return f"{prefix}_bit0"


def _build_loader_fsm() -> _Fsm:
    fsm = _Fsm()
    records = sorted(set(GLYPH_RECORD.values()) | {WALL})

    # W stays in BP while H is classified.  Each H arm seeds E and the
    # constant part of D; five BP bits add W into D.
    fsm.go("boot", "input", "@rb", "height_read")
    fsm.go("height_read", "input", "r", "height_cmp_4")
    for height in range(4, 17):
        next_target = f"height_cmp_{height + 1}" if height < 16 else "path_error"
        fsm.sign(
            f"height_cmp_{height}",
            "logic",
            "M4W-" if height == 4 else "M1W-",
            negative="path_error",
            zero=f"height_seed_{height}",
            positive=next_target,
        )
        seed = (15 << D_SHIFT) + ((height + 15) << E_SHIFT)
        fsm.go(
            f"height_seed_{height}",
            "logic",
            _literal(seed),
            "width_restore_bit0",
        )
    width_weights = {bit: 1 << (D_SHIFT + bit) for bit in range(5)}
    _add_reconstruction(
        fsm,
        "width_restore",
        start_bit=0,
        end_bit=5,
        target="pos_0",
        weights=width_weights,
    )

    # Position dispatch.  D and E are biased by 16: <16 is padding, 16
    # is the right/bottom border, and >16 is interior.  x itself is carried
    # by the control path.
    for x in range(16):
        prefix = f"position_{x}"
        entry = f"pos_{x}"
        padding_target = f"pack_{x}_{SPACE}"
        wall_target = f"wall_read_{x}"
        glyph_target = f"glyph_read_{x}"

        if x == 0:
            e_entry = _add_biased_status(
                fsm,
                f"{prefix}_e",
                padding=padding_target,
                wall=wall_target,
                interior=wall_target,
            )
            fsm.go(entry, "logic", "0+b" + "]" * E_SHIFT, e_entry)
            continue

        if x == 15:
            final_e = _add_biased_status(
                fsm,
                f"{prefix}_final_e",
                padding="pack_final_padding",
                wall="final_wall_read",
                interior="final_wall_read",
            )
            final_d = _add_biased_status(
                fsm,
                f"{prefix}_final_d",
                padding="pack_final_padding",
                wall=final_e,
                interior=final_e,
            )
            normal_e = _add_biased_status(
                fsm,
                f"{prefix}_normal_e",
                padding=padding_target,
                wall=wall_target,
                interior=wall_target,
            )
            normal_d = _add_biased_status(
                fsm,
                f"{prefix}_normal_d",
                padding=padding_target,
                wall=normal_e,
                interior=normal_e,
            )
            fsm.go(
                f"{prefix}_final_copy",
                "logic",
                "0+b" + "]" * D_SHIFT,
                final_d,
            )
            fsm.go(
                f"{prefix}_normal_copy",
                "logic",
                "0+b" + "]" * D_SHIFT,
                normal_d,
            )
            y_entry = _add_equality_test(
                fsm,
                f"{prefix}_y15",
                width=4,
                value=15,
                equal=f"{prefix}_final_copy",
                different=f"{prefix}_normal_copy",
            )
            fsm.go(entry, "logic", "0+b" + "]" * Y_SHIFT, y_entry)
            continue

        y_entry = _add_equality_test(
            fsm,
            f"{prefix}_y",
            width=4,
            value=0,
            equal=wall_target,
            different=glyph_target,
        )
        e_wall = _add_biased_status(
            fsm,
            f"{prefix}_e_wall",
            padding=padding_target,
            wall=wall_target,
            interior=wall_target,
        )
        e_interior = _add_biased_status(
            fsm,
            f"{prefix}_e_interior",
            padding=padding_target,
            wall=wall_target,
            interior=y_entry,
        )
        d_entry = _add_biased_status(
            fsm,
            f"{prefix}_d",
            padding=padding_target,
            wall=e_wall,
            interior=e_interior,
        )
        fsm.go(entry, "logic", "0+b" + "]" * D_SHIFT, d_entry)

    # Reads and four shared sparse ASCII tries.  The high tag records x//4;
    # x%4 selects the trie.  BP is scratch here and B retains the full state.
    for x in range(16):
        fsm.go(f"wall_read_{x}", "input", "r", f"pack_{x}_{WALL}")
        group = x // 4
        tag_code = _literal(group << TAG_SHIFT) + "+M" if group else ""
        fsm.go(
            f"glyph_read_{x}",
            "input",
            tag_code + "rb",
            f"glyph_{x % 4}_root",
        )

    for phase in range(4):
        targets = {char: "path_error" for char in range(256)}
        targets.update(
            {
                char: (
                    f"glyph_at_{phase}"
                    if char == ord("@")
                    else f"glyph_pack_{phase}_{GLYPH_RECORD[char]}"
                )
                for char in (*GLYPH_RECORD, ord("@"))
            }
        )
        _add_lsb_trie(
            fsm,
            f"glyph_{phase}",
            width=8,
            targets=targets,
            consume=False,
        )

    # Direct packs for records 0..2 of each token.  The control path provides
    # x, so D is decremented by one without keeping x in a register.
    for x in range(16):
        phase = x % 4
        if phase == 3:
            continue
        for record in records:
            delta = -(1 << D_SHIFT) + (record << (13 * phase))
            fsm.go(
                f"pack_{x}_{record}",
                "logic",
                _literal(delta) + "+M",
                f"pos_{x + 1}",
            )

    # Interior glyph packs share one handler per phase.  Their saved tag
    # dispatches to the correct next x and disappears before the next cell.
    for phase in range(3):
        tag_targets: dict[int, str] = {}
        for group in range(4):
            x = 4 * group + phase
            target = f"glyph_continue_{phase}_{group}"
            tag_targets[group] = target
            clear = -(group << TAG_SHIFT)
            fsm.go(
                target,
                "logic",
                (_literal(clear) + "+M" if clear else ""),
                f"pos_{x + 1}",
            )
        _add_lsb_trie(
            fsm,
            f"glyph_dispatch_{phase}",
            width=2,
            targets=tag_targets,
        )
        fsm.go(
            f"glyph_dispatch_copy_{phase}",
            "logic",
            "0+b" + "]" * TAG_SHIFT,
            f"glyph_dispatch_{phase}_root",
        )
        for record in records:
            delta = -(1 << D_SHIFT) + (record << (13 * phase))
            fsm.go(
                f"glyph_pack_{phase}_{record}",
                "logic",
                _literal(delta) + "+M",
                f"glyph_dispatch_copy_{phase}",
            )

    # @ in phases 0..2 stores x directly, then one shared reconstruction
    # preserves the state while copying y into the high address nibble.
    at_full_weights = _at_weights(0, MAN_SHIFT + 8)
    at_full_entry = _add_reconstruction(
        fsm,
        "at_full",
        start_bit=0,
        end_bit=MAN_SHIFT + 8,
        target="at_dispatch_copy",
        weights=at_full_weights,
    )
    fsm.go(
        "at_full_init",
        "logic",
        _literal(-(1 << D_SHIFT)),
        at_full_entry,
    )
    fsm.go(
        "at_dispatch_copy",
        "logic",
        "M0+b" + "]" * MAN_SHIFT,
        "at_dispatch_root",
    )
    _add_lsb_trie(
        fsm,
        "at_dispatch",
        width=4,
        targets={
            value: f"pos_{value + 1}" if 1 <= value <= 14 else "path_error"
            for value in range(16)
        },
    )
    for x in range(1, 15):
        if x % 4 == 3:
            continue
        fsm.go(
            f"at_{x}",
            "logic",
            _literal(x << MAN_SHIFT) + "+M0+b",
            "at_full_init",
        )
    for phase in range(3):
        _add_lsb_trie(
            fsm,
            f"glyph_at_dispatch_{phase}",
            width=2,
            targets={
                group: (
                    f"at_{4 * group + phase}"
                    if 1 <= 4 * group + phase <= 14
                    else "path_error"
                )
                for group in range(4)
            },
        )
        fsm.go(
            f"glyph_at_{phase}",
            "logic",
            "0+b" + "]" * TAG_SHIFT,
            f"glyph_at_dispatch_{phase}_root",
        )

    # Fourth records: save a two-bit continuation tag, rebuild and send only
    # the low token, then rebuild metadata from the still-shifted BP.
    tag_targets = {0: "pos_4", 1: "pos_8", 2: "pos_12", 3: "path_error"}
    _add_lsb_trie(fsm, "phase3_dispatch", width=2, targets=tag_targets)

    normal_meta_entry = _add_reconstruction(
        fsm,
        "phase3_meta",
        start_bit=D_SHIFT,
        end_bit=TAG_SHIFT,
        target="phase3_dispatch_root",
    )
    fsm.go(
        "phase3_meta_init",
        "logic",
        _literal(-(1 << D_SHIFT)),
        normal_meta_entry,
    )
    at_meta_entry = _add_reconstruction(
        fsm,
        "phase3_at_meta",
        start_bit=D_SHIFT,
        end_bit=TAG_SHIFT,
        target="phase3_dispatch_root",
        weights=_at_weights(D_SHIFT, TAG_SHIFT),
    )
    fsm.go(
        "phase3_at_meta_init",
        "logic",
        _literal(-(1 << D_SHIFT)),
        at_meta_entry,
    )

    normal_low_entry = _add_reconstruction(
        fsm,
        "phase3_low",
        start_bit=0,
        end_bit=D_SHIFT,
        target="phase3_send",
        finish_with_copy=False,
    )
    fsm.go("phase3_send", "output", "s", "phase3_meta_init")
    at_low_entry = _add_reconstruction(
        fsm,
        "phase3_at_low",
        start_bit=0,
        end_bit=D_SHIFT,
        target="phase3_at_send",
        finish_with_copy=False,
    )
    fsm.go("phase3_at_send", "output", "s", "phase3_at_meta_init")

    for x, tag in ((3, 0), (7, 1), (11, 2)):
        tag_delta = tag << TAG_SHIFT
        for record in records:
            init = f"phase3_init_{record}"
            if not any(block.name == init for block in fsm.blocks):
                fsm.go(init, "logic", _literal(record << D_SHIFT), normal_low_entry)
            code = (_literal(tag_delta) + "+M" if tag_delta else "") + "0+b"
            fsm.go(f"pack_{x}_{record}", "logic", code, init)
    for record in records:
        fsm.go(
            f"glyph_pack_3_{record}",
            "logic",
            "0+b",
            f"phase3_init_{record}",
        )
    _add_lsb_trie(
        fsm,
        "glyph_at_dispatch_3",
        width=2,
        targets={0: "at_3", 1: "at_7", 2: "at_11", 3: "path_error"},
    )
    fsm.go(
        "glyph_at_3",
        "logic",
        "0+b" + "]" * TAG_SHIFT,
        "glyph_at_dispatch_3_root",
    )
    for x in (3, 7, 11):
        fsm.go(
            f"at_{x}",
            "logic",
            _literal(x << MAN_SHIFT) + "+M0+b",
            "phase3_at_init",
        )
    fsm.go("phase3_at_init", "logic", "0", at_low_entry)

    # x=15 closes a non-final row.  D resets, E decrements, and y advances.
    row_delta = (15 << D_SHIFT) - (1 << E_SHIFT) + (1 << Y_SHIFT)
    row_meta_entry = _add_reconstruction(
        fsm,
        "row_meta",
        start_bit=D_SHIFT,
        end_bit=TAG_SHIFT,
        target="pos_0",
    )
    fsm.go("row_meta_init", "logic", _literal(row_delta), row_meta_entry)
    row_low_entry = _add_reconstruction(
        fsm,
        "row_low",
        start_bit=0,
        end_bit=D_SHIFT,
        target="row_send",
        finish_with_copy=False,
    )
    fsm.go("row_send", "output", "s", "row_meta_init")
    for record in records:
        fsm.go(
            f"pack_15_{record}",
            "logic",
            "0+b" + _literal(record << D_SHIFT),
            row_low_entry,
        )

    # Final cell: send its token, extract the remembered address from the
    # remaining BP metadata, then relay all later round inputs forever.
    final_low_entry = _add_reconstruction(
        fsm,
        "final_low",
        start_bit=0,
        end_bit=D_SHIFT,
        target="final_token_send",
        finish_with_copy=False,
    )
    for record, name in ((SPACE, "padding"), (WALL, "wall")):
        fsm.go(
            f"pack_final_{name}",
            "logic",
            "0+b" + _literal(record << D_SHIFT),
            final_low_entry,
        )
    fsm.go("final_wall_read", "input", "r", "pack_final_wall")
    fsm.go(
        "final_token_send",
        "output",
        "s",
        "final_man_skip",
    )
    fsm.go(
        "final_man_skip",
        "logic",
        "]" * (MAN_SHIFT - D_SHIFT) + "0",
        "final_man_bit0",
    )
    _add_reconstruction(
        fsm,
        "final_man",
        start_bit=0,
        end_bit=8,
        target="final_man_send",
        weights={bit: 1 << bit for bit in range(8)},
        finish_with_copy=False,
    )
    fsm.go("final_man_send", "output", "s", "relay_read")
    fsm.go("relay_read", "input", "r", "relay_send")
    fsm.go("relay_send", "output", "s", "relay_read")
    fsm.go("path_error", "logic", "H", "path_error")
    return fsm


def _build_loader_room() -> _Room:
    return _compile(_build_loader_fsm(), min_width=120)


def build_loader_rig() -> str:
    """Build ``3x3 I -> LOADER -> 3x3 O`` around the exact loader room."""

    loader = _build_loader_room()
    canvas = Canvas()
    loader_top = 0
    loader_left = 6
    canvas.put(loader_top, loader_left, loader.rows)

    io_top = 2
    canvas.put(io_top, 0, ["+-+", "|I|", "+-+"])
    input_row = io_top + 1
    canvas.pipe([(input_row, 3), (input_row, loader_left - 1)])

    loader_right = loader_left + len(loader.rows[0]) - 1
    output_left = loader_right + 4
    canvas.put(io_top, output_left, ["+-+", "|O|", "+-+"])
    canvas.pipe(
        [
            (input_row, loader_right + 1),
            (input_row, output_left - 1),
        ]
    )
    return canvas.render()
