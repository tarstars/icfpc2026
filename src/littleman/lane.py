"""Compact in-room layout for Little Man instruction lanes.

The public surface is deliberately about control flow rather than room
coordinates.  Compilation returns a walled grid plus an instruction-to-cell
map so callers can audit generated geometry.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

Op = str


class LaneError(ValueError):
    """The requested lane cannot be represented safely."""


class _Unreachable:
    pass


unreachable = _Unreachable()


@dataclass(frozen=True)
class _Seq:
    ops: tuple[Op, ...]


@dataclass(frozen=True)
class _BranchBP:
    taken: Lane | _Unreachable
    straight: Lane | _Unreachable
    opcode: str = "d"


@dataclass(frozen=True)
class _BranchSign:
    neg: Lane | _Unreachable
    zero: Lane | _Unreachable
    pos: Lane | _Unreachable


@dataclass(frozen=True)
class _Loop:
    body: Lane
    forever: bool
    bp_expr: tuple[Op, ...] = ()


@dataclass(frozen=True)
class _Label:
    name: str


@dataclass(frozen=True)
class _Goto:
    name: str


@dataclass(frozen=True)
class LayoutSnapshot:
    rows: int
    cols: int
    cells_used: int
    fill_ratio: float
    max_width: int


@dataclass(frozen=True)
class LayoutMetrics:
    rows: int
    cols: int
    cells_used: int
    fill_ratio: float
    ticks_per_lap: int | None
    before: LayoutSnapshot
    after: LayoutSnapshot
    invariants: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompiledRoom:
    grid: list[str]
    cells: tuple[tuple[int, int], ...]
    metrics: LayoutMetrics
    ports: Mapping[str, tuple[int, int]] = field(default_factory=dict)


def _coerce_lane(value: Lane | Iterable[Op] | _Unreachable) -> Lane | _Unreachable:
    if value is unreachable:
        return value
    if isinstance(value, Lane):
        return value
    return Lane().seq(value)


def _normalise_ops(ops: Iterable[Op] | Op) -> tuple[Op, ...]:
    if isinstance(ops, str):
        ops = tuple(ops)
    result = tuple(ops)
    for op in result:
        if not isinstance(op, str) or not op:
            raise LaneError(f"invalid operation token: {op!r}")
        if len(op) != 1 and not (
            len(op) >= 3
            and op.startswith("`")
            and op.endswith("`")
            and all(ch.isdigit() or ch == " " for ch in op[1:-1])
        ):
            raise LaneError(f"operation must be one glyph or one literal: {op!r}")
    return result


class Lane:
    """A fluent control-flow description for one room."""

    def __init__(self, ops: Iterable[Op] | Op = ()):
        self._nodes: list[object] = []
        if ops:
            self.seq(ops)

    def seq(self, ops: Iterable[Op] | Op) -> Lane:
        normal = _normalise_ops(ops)
        if normal:
            self._nodes.append(_Seq(normal))
        return self

    def branch_bp(
        self,
        *,
        taken: Lane | Iterable[Op] | _Unreachable,
        straight: Lane | Iterable[Op] | _Unreachable,
        opcode: str = "d",
    ) -> Lane:
        if opcode not in {"d", "a"}:
            raise LaneError("BP branch opcode must be 'd' or 'a'")
        self._nodes.append(
            _BranchBP(_coerce_lane(taken), _coerce_lane(straight), opcode)
        )
        return self

    def branch_sign(
        self,
        *,
        neg: Lane | Iterable[Op] | _Unreachable,
        zero: Lane | Iterable[Op] | _Unreachable,
        pos: Lane | Iterable[Op] | _Unreachable,
    ) -> Lane:
        self._nodes.append(
            _BranchSign(_coerce_lane(neg), _coerce_lane(zero), _coerce_lane(pos))
        )
        return self

    def loop_counted(
        self, body: Lane | Iterable[Op], bp_expr: Iterable[Op] | Op
    ) -> Lane:
        coerced = _coerce_lane(body)
        assert isinstance(coerced, Lane)
        self._nodes.append(_Loop(coerced, False, _normalise_ops(bp_expr)))
        return self

    def loop_forever(self, body: Lane | Iterable[Op]) -> Lane:
        coerced = _coerce_lane(body)
        assert isinstance(coerced, Lane)
        self._nodes.append(_Loop(coerced, True))
        return self

    def label(self, name: str) -> Lane:
        if not name:
            raise LaneError("label name cannot be empty")
        self._nodes.append(_Label(name))
        return self

    def goto(self, name: str) -> Lane:
        if not name:
            raise LaneError("goto name cannot be empty")
        self._nodes.append(_Goto(name))
        return self

    def compile(
        self,
        *,
        max_width: int,
        ports: Mapping[str, tuple[int, int]] | None = None,
        compact: bool = True,
    ) -> CompiledRoom:
        if max_width < 4:
            raise LaneError("max_width must leave room for turns")
        return _Compiler(self, max_width, ports or {}, compact).compile()

    @property
    def nodes(self) -> tuple[object, ...]:
        return tuple(self._nodes)


def _flat_ops(lane: Lane) -> tuple[Op, ...]:
    result: list[Op] = []
    for node in lane.nodes:
        if isinstance(node, _Seq):
            result.extend(node.ops)
        else:
            raise LaneError("this layout pattern requires straight-line arms")
    return tuple(result)


def _physical(op: Op, east: bool) -> str:
    return op if east or len(op) == 1 else op[::-1]


def _op_width(op: Op) -> int:
    return len(op)


class _Draft:
    def __init__(self, width: int):
        self.width = width
        self.cells: dict[tuple[int, int], str] = {}
        self.op_cells: list[tuple[int, int]] = []
        self.invariants: list[str] = []
        self.ticks_per_lap: int | None = None

    def put(self, row: int, col: int, text: str) -> None:
        if row < 1 or col < 1 or col + len(text) - 1 > self.width:
            raise LaneError(f"placement outside {self.width}-cell room")
        for offset, glyph in enumerate(text):
            pos = (row, col + offset)
            old = self.cells.get(pos)
            if old is not None and old != glyph:
                raise LaneError(f"cell conflict at {pos}: {old!r} vs {glyph!r}")
            self.cells[pos] = glyph

    def op(self, row: int, col: int, token: Op, east: bool) -> None:
        text = _physical(token, east)
        self.put(row, col if east else col - len(text) + 1, text)
        end = col + len(text) - 1 if east else col - len(text) + 1
        self.op_cells.append((row, end))

    @property
    def height(self) -> int:
        return max((row for row, _ in self.cells), default=1)

    def snapshot(self) -> LayoutSnapshot:
        used = len(self.cells)
        area = self.height * self.width
        return LayoutSnapshot(
            self.height + 2,
            self.width + 2,
            used,
            used / area,
            self.width,
        )

    def render(self) -> list[str]:
        top = "+" + "-" * self.width + "+"
        body = [
            "|"
            + "".join(
                self.cells.get((row, col), " ") for col in range(1, self.width + 1)
            )
            + "|"
            for row in range(1, self.height + 1)
        ]
        return [top, *body, top]


def _emit_serpentine(
    draft: _Draft,
    ops: Sequence[Op],
    *,
    row: int = 1,
    col: int = 2,
    east: bool = True,
    literal_padding: Mapping[int, int] | None = None,
    base_index: int = 0,
) -> tuple[int, int, bool]:
    """Emit ops, reserving the outer columns for shared turns."""
    draft.put(row, 1 if east else draft.width, ">" if east else "<")
    literal_padding = literal_padding or {}
    for offset, token in enumerate(ops):
        width = _op_width(token)
        padding = literal_padding.get(base_index + offset, 0)
        if len(token) > 1 and padding:
            col += padding if east else -padding
        fits = col + width - 1 < draft.width if east else col - width + 1 > 1
        if not fits:
            if east:
                draft.put(row, draft.width, "v")
                row += 1
                draft.put(row, draft.width, "<")
                col, east = draft.width - 1, False
            else:
                draft.put(row, 1, "v")
                row += 1
                draft.put(row, 1, ">")
                col, east = 2, True
            fits = col + width - 1 < draft.width if east else col - width + 1 > 1
            if not fits:
                raise LaneError(
                    f"literal width {width} does not fit max_width={draft.width}"
                )
        draft.op(row, col, token, east)
        col += width if east else -width
    return row, col, east


def _close_forever(draft: _Draft, row: int, col: int, east: bool) -> None:
    if row == 1 or east:
        draft.put(row, draft.width, "v")
        row += 1
        draft.put(row, draft.width, "<")
    draft.put(row, 1, "^")
    for return_row in range(1, row):
        old = draft.cells.get((return_row, 1))
        if old not in {None, ">", "^"}:
            raise LaneError("return column crosses a turn; choose a wider room")
        if return_row != 1:
            draft.put(return_row, 1, "^")
    draft.invariants.append("forever loop re-enters after prologue")
    draft.ticks_per_lap = sum(1 for glyph in draft.cells.values() if glyph != " ")


def _backtick_collision(
    draft: _Draft,
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """Return the first unintended pair of vertically aligned delimiters."""
    by_col: dict[int, list[int]] = {}
    for (row, col), glyph in draft.cells.items():
        if glyph == "`":
            by_col.setdefault(col, []).append(row)
    for col, rows in sorted(by_col.items()):
        for upper, lower in zip(sorted(rows), sorted(rows)[1:]):
            between = [
                draft.cells.get((row, col), " ") for row in range(upper + 1, lower)
            ]
            if all(glyph.isdigit() or glyph == " " for glyph in between):
                return (upper, col), (lower, col)
    return None


def _literal_owner(
    ops: Sequence[Op], cells: Sequence[tuple[int, int]], pos: tuple[int, int]
) -> int | None:
    for index, (token, end) in enumerate(zip(ops, cells)):
        if len(token) == 1 or end[0] != pos[0]:
            continue
        delimiters = {
            end[1],
            end[1] - len(token) + 1,
            end[1] + len(token) - 1,
        }
        if pos[1] in delimiters:
            return index
    return None


def _flatten_simple_loop(lane: Lane) -> tuple[tuple[Op, ...], bool] | None:
    if len(lane.nodes) == 1 and isinstance(lane.nodes[0], _Loop):
        loop = lane.nodes[0]
        if loop.forever:
            try:
                return _flat_ops(loop.body), True
            except LaneError:
                return None
    try:
        return _flat_ops(lane), False
    except LaneError:
        pass
    if (
        len(lane.nodes) >= 3
        and isinstance(lane.nodes[0], _Label)
        and isinstance(lane.nodes[-1], _Goto)
        and lane.nodes[0].name == lane.nodes[-1].name
    ):
        middle = Lane()
        middle._nodes.extend(lane.nodes[1:-1])
        try:
            return _flat_ops(middle), True
        except LaneError:
            return None
    return None


def _prologue_loop_shape(
    lane: Lane,
) -> tuple[tuple[Op, ...], tuple[Op, ...]] | None:
    prefix: list[Op] = []
    loop: _Loop | None = None
    for node in lane.nodes:
        if isinstance(node, _Seq) and loop is None:
            prefix.extend(node.ops)
        elif isinstance(node, _Loop) and loop is None and node.forever:
            loop = node
        else:
            return None
    if not prefix or loop is None:
        return None
    try:
        return tuple(prefix), _flat_ops(loop.body)
    except LaneError:
        return None


def _compile_prologue_loop(
    lane: Lane, width: int, padding: Mapping[int, int] | None = None
) -> _Draft:
    shape = _prologue_loop_shape(lane)
    if shape is None:
        raise LaneError("unsupported prologue shape")
    prologue, body = shape
    draft = _Draft(width)
    _, _, _, prologue_cells = _put_run(
        draft,
        prologue,
        row=1,
        col=2,
        east=True,
        left=1,
        right=width,
        literal_padding=padding,
    )
    draft.put(1, 1, ">")
    draft.put(1, width, "v")
    draft.put(2, width, "<")
    draft.put(2, 1, "v")
    draft.put(3, 1, ">")
    end_row, _, east, body_cells = _put_run(
        draft,
        body,
        row=3,
        col=2,
        east=True,
        left=1,
        right=width,
        literal_padding=padding,
        base_index=len(prologue),
    )
    if end_row != 3 or not east:
        raise LaneError("off-lap prologue pattern needs a one-row loop body")
    draft.put(3, width, "v")
    draft.put(4, width, "<")
    draft.put(4, 1, "^")
    draft.op_cells = prologue_cells + body_cells
    draft.invariants.append("prologue path cannot be reached from the lap")
    draft.ticks_per_lap = 2 * width
    return draft


def _counted_shape(
    lane: Lane,
) -> tuple[tuple[Op, ...], _Loop, tuple[Op, ...]] | None:
    prefix: list[Op] = []
    suffix: list[Op] = []
    loop: _Loop | None = None
    for node in lane.nodes:
        if isinstance(node, _Seq):
            (prefix if loop is None else suffix).extend(node.ops)
        elif isinstance(node, _Loop) and loop is None and not node.forever:
            loop = node
        else:
            return None
    return (tuple(prefix), loop, tuple(suffix)) if loop is not None else None


def _compile_counted(
    lane: Lane, width: int, padding: Mapping[int, int] | None = None
) -> _Draft:
    shape = _counted_shape(lane)
    if shape is None:
        raise LaneError("unsupported counted loop shape")
    prefix, loop, suffix = shape
    draft = _Draft(width)
    seed = prefix + loop.bp_expr
    _, _, _, seed_cells = _put_run(
        draft,
        seed,
        row=1,
        col=2,
        east=True,
        left=1,
        right=width,
        literal_padding=padding,
    )
    draft.put(1, 1, ">")
    draft.put(1, width, "v")
    draft.put(2, width, "<")
    draft.put(2, 1, "v")
    draft.put(3, 1, ">")
    body = _flat_ops(loop.body)
    _, _, east, body_cells = _put_run(
        draft,
        body,
        row=3,
        col=2,
        east=True,
        left=1,
        right=width,
        literal_padding=padding,
        base_index=len(seed),
    )
    if not east:
        raise LaneError("counted body must fit one eastbound row")
    draft.put(3, width, "v")
    draft.put(4, width, "d")
    draft.put(4, 2, "m")
    draft.put(4, 1, "^")
    draft.put(5, width, "<")
    _, _, _, suffix_cells = _put_run(
        draft,
        suffix,
        row=5,
        col=width - 1,
        east=False,
        left=1,
        right=width,
        literal_padding=padding,
        base_index=len(seed) + len(body),
    )
    draft.op_cells = seed_cells + body_cells + suffix_cells
    draft.invariants.append("counted-loop seed is outside the return path")
    draft.invariants.append("BP is tested at d before m decrements the next lap")
    return draft


class _Compiler:
    def __init__(
        self,
        lane: Lane,
        max_width: int,
        ports: Mapping[str, tuple[int, int]],
        compact: bool,
    ):
        self.lane = lane
        self.max_width = max_width
        self.ports = dict(ports)
        self.compact = compact

    def _simple_at(self, width: int) -> _Draft:
        flattened = _flatten_simple_loop(self.lane)
        if flattened is None:
            return self._structured_at(width)
        ops, forever = flattened
        padding: dict[int, int] = {}
        attempts = sum(len(op) > 1 for op in ops) * (width + 1) + 1
        for _ in range(attempts):
            draft = _Draft(width)
            row, col, east = _emit_serpentine(draft, ops, literal_padding=padding)
            if forever:
                _close_forever(draft, row, col, east)
            collision = _backtick_collision(draft)
            if collision is None:
                return draft
            owners = [
                _literal_owner(ops, draft.op_cells, delimiter)
                for delimiter in reversed(collision)
            ]
            owner = next(
                (candidate for candidate in owners if candidate is not None), None
            )
            if owner is None:
                raise LaneError(f"cannot disambiguate backticks at {collision}")
            padding[owner] = padding.get(owner, 0) + 1
        raise LaneError("backtick safety did not converge")

    def _structured_at(self, width: int) -> _Draft:
        tokens = _collect_tokens(self.lane)
        padding: dict[int, int] = {}
        attempts = sum(len(op) > 1 for op in tokens) * (width + 1) + 1
        for _ in range(attempts):
            if _forever_bp_shape(self.lane) is not None:
                draft = _compile_bp_loop(self.lane, width, padding)
            elif _forever_sign_shape(self.lane) is not None:
                draft = _compile_sign_loop(self.lane, width, padding)
            elif _prologue_loop_shape(self.lane) is not None:
                draft = _compile_prologue_loop(self.lane, width, padding)
            elif _counted_shape(self.lane) is not None:
                draft = _compile_counted(self.lane, width, padding)
            else:
                raise LaneError("unsupported structured control flow")
            collision = _backtick_collision(draft)
            if collision is None:
                return draft
            owners = [
                _literal_owner(tokens, draft.op_cells, delimiter)
                for delimiter in reversed(collision)
            ]
            owner = next(
                (candidate for candidate in owners if candidate is not None),
                None,
            )
            if owner is None:
                break
            padding[owner] = padding.get(owner, 0) + 1
        raise LaneError("structured backtick safety did not converge")

    def _compile_at(self, width: int) -> _Draft:
        simple = _flatten_simple_loop(self.lane)
        return (
            self._simple_at(width) if simple is not None else self._structured_at(width)
        )

    def _minimum_width(self) -> int:
        minimum = 4
        tokens = _collect_tokens(self.lane)
        if tokens:
            minimum = max(minimum, max(map(len, tokens)) + 2)
        return minimum

    def compile(self) -> CompiledRoom:
        before_draft = self._compile_at(self.max_width)
        candidates = [before_draft]
        if self.compact:
            low, high = self._minimum_width(), self.max_width
            tried = {self.max_width}
            while low <= high:
                width = (low + high) // 2
                tried.add(width)
                try:
                    candidate = self._compile_at(width)
                except LaneError:
                    low = width + 1
                    continue
                candidates.append(candidate)
                if candidate.height + 2 > candidate.width + 2:
                    low = width + 1
                else:
                    high = width - 1
            provisional = min(
                candidates,
                key=lambda item: (
                    max(item.height + 2, item.width + 2),
                    (item.height + 2) * (item.width + 2),
                ),
            )
            for width in range(
                max(self._minimum_width(), provisional.width - 4),
                min(self.max_width, provisional.width + 4) + 1,
            ):
                if width in tried:
                    continue
                try:
                    candidates.append(self._compile_at(width))
                except LaneError:
                    continue
        selected = min(
            candidates,
            key=lambda item: (
                max(item.height + 2, item.width + 2),
                (item.height + 2) * (item.width + 2),
                -item.snapshot().fill_ratio,
                item.width,
            ),
        )
        before = before_draft.snapshot()
        after = selected.snapshot()
        invariants = list(selected.invariants)
        invariants.extend(
            (
                "logical rows trailing-trimmed before rectangular render",
                "same-direction corridors share turn cells",
                "sequential blocks reuse the outer return column",
                "max_width selected by deterministic bisection",
                "backtick columns verified after placement",
            )
        )
        metrics = LayoutMetrics(
            after.rows,
            after.cols,
            after.cells_used,
            after.fill_ratio,
            selected.ticks_per_lap,
            before,
            after,
            tuple(invariants),
        )
        return CompiledRoom(
            selected.render(), tuple(selected.op_cells), metrics, self.ports
        )


def _collect_tokens(lane: Lane) -> tuple[Op, ...]:
    result: list[Op] = []
    for node in lane.nodes:
        if isinstance(node, _Seq):
            result.extend(node.ops)
        elif isinstance(node, _Loop):
            result.extend(node.bp_expr)
            result.extend(_collect_tokens(node.body))
        elif isinstance(node, _BranchBP):
            result.append(node.opcode)
            for arm in (node.taken, node.straight):
                if isinstance(arm, Lane):
                    result.extend(_collect_tokens(arm))
        elif isinstance(node, _BranchSign):
            result.append("X")
            for arm in (node.neg, node.zero, node.pos):
                if isinstance(arm, Lane):
                    result.extend(_collect_tokens(arm))
    return tuple(result)


def _put_run(
    draft: _Draft,
    ops: Sequence[Op],
    *,
    row: int,
    col: int,
    east: bool,
    left: int,
    right: int,
    literal_padding: Mapping[int, int] | None = None,
    base_index: int = 0,
) -> tuple[int, int, bool, list[tuple[int, int]]]:
    """Place a serpentine run inside inclusive turn columns."""
    mapped: list[tuple[int, int]] = []
    literal_padding = literal_padding or {}
    for offset, token in enumerate(ops):
        size = len(token)
        padding = literal_padding.get(base_index + offset, 0)
        if len(token) > 1 and padding:
            col += padding if east else -padding
        fits = col + size - 1 < right if east else col - size + 1 > left
        if not fits:
            if east:
                draft.put(row, right, "v")
                row += 1
                draft.put(row, right, "<")
                col, east = right - 1, False
            else:
                draft.put(row, left, "v")
                row += 1
                draft.put(row, left, ">")
                col, east = left + 1, True
            fits = col + size - 1 < right if east else col - size + 1 > left
            if not fits:
                raise LaneError(f"token {token!r} cannot fit branch corridor")
        previous = len(draft.op_cells)
        draft.op(row, col, token, east)
        mapped.append(draft.op_cells.pop(previous))
        col += size if east else -size
    return row, col, east, mapped


def _forever_bp_shape(lane: Lane) -> tuple[tuple[Op, ...], _BranchBP] | None:
    if len(lane.nodes) != 1 or not isinstance(lane.nodes[0], _Loop):
        return None
    loop = lane.nodes[0]
    if not loop.forever:
        return None
    prefix: list[Op] = []
    branch: _BranchBP | None = None
    for node in loop.body.nodes:
        if isinstance(node, _Seq) and branch is None:
            prefix.extend(node.ops)
        elif isinstance(node, _BranchBP) and branch is None:
            branch = node
        else:
            return None
    if branch is None:
        return None
    return tuple(prefix), branch


def _forever_sign_shape(
    lane: Lane,
) -> tuple[tuple[Op, ...], _BranchSign] | None:
    if len(lane.nodes) != 1 or not isinstance(lane.nodes[0], _Loop):
        return None
    loop = lane.nodes[0]
    if not loop.forever:
        return None
    prefix: list[Op] = []
    branch: _BranchSign | None = None
    for node in loop.body.nodes:
        if isinstance(node, _Seq) and branch is None:
            prefix.extend(node.ops)
        elif isinstance(node, _BranchSign) and branch is None:
            branch = node
        else:
            return None
    return (tuple(prefix), branch) if branch is not None else None


def _compile_sign_loop(
    lane: Lane, width: int, padding: Mapping[int, int] | None = None
) -> _Draft:
    shape = _forever_sign_shape(lane)
    if shape is None:
        raise LaneError("unsupported sign-branch shape")
    prefix, branch = shape
    if branch.zero is unreachable:
        raise LaneError("a zero arm cannot be wall-unrouted in the merge pattern")
    draft = _Draft(width)
    draft.put(2, 1, ">")
    _, col, _, prefix_cells = _put_run(
        draft,
        prefix,
        row=2,
        col=2,
        east=True,
        left=1,
        right=width,
        literal_padding=padding,
    )
    if col >= width:
        raise LaneError("X branch does not fit on its entry row")
    draft.put(2, col, "X")
    arm_rows = ((branch.neg, 1), (branch.zero, 2), (branch.pos, 3))
    arm_cells: list[list[tuple[int, int]]] = []
    arm_base = len(prefix) + 1
    for arm, row in arm_rows:
        if arm is unreachable:
            arm_cells.append([])
            continue
        assert isinstance(arm, Lane)
        arm_ops = _flat_ops(arm)
        if row != 2:
            draft.put(row, col, ">")
        _, _, east, mapped = _put_run(
            draft,
            arm_ops,
            row=row,
            col=col + 1,
            east=True,
            left=col,
            right=width,
            literal_padding=padding,
            base_index=arm_base,
        )
        if not east:
            raise LaneError("X arm must fit its single eastbound corridor")
        draft.put(row, width, "v")
        arm_cells.append(mapped)
        arm_base += len(arm_ops)
    draft.put(4, width, "<")
    draft.put(4, 1, "^")
    draft.put(3, 1, "^")
    draft.op_cells = (
        prefix_cells + [(2, col)] + arm_cells[0] + arm_cells[1] + arm_cells[2]
    )
    draft.invariants.append("X arms merge down the shared right column")
    draft.invariants.append("unreachable turning arms walk into the room wall")
    draft.ticks_per_lap = len(draft.cells)
    return draft


def _compile_bp_loop(
    lane: Lane, width: int, padding: Mapping[int, int] | None = None
) -> _Draft:
    shape = _forever_bp_shape(lane)
    if shape is None:
        raise LaneError("unsupported structured control flow")
    prefix, branch = shape
    if branch.opcode == "a":
        mirrored_body = (
            Lane()
            .seq(prefix)
            .branch_bp(
                taken=branch.taken,
                straight=branch.straight,
                opcode="d",
            )
        )
        lower = _compile_bp_loop(Lane().loop_forever(mirrored_body), width, padding)
        mirrored = _Draft(width)
        height = lower.height
        branch_cell = lower.op_cells[len(prefix)]
        for (row, col), glyph in lower.cells.items():
            target = (height + 1 - row, col)
            if (row, col) == branch_cell:
                glyph = "a"
            else:
                glyph = {"v": "^", "^": "v"}.get(glyph, glyph)
            mirrored.put(*target, glyph)
        mirrored.op_cells = [(height + 1 - row, col) for row, col in lower.op_cells]
        mirrored.invariants = [
            item.replace("d arms", "a arms") for item in lower.invariants
        ]
        mirrored.invariants.append("a uses the vertically mirrored corner pattern")
        mirrored.ticks_per_lap = lower.ticks_per_lap
        return mirrored
    draft = _Draft(width)
    draft.put(1, 1, ">")
    _, col, _, prefix_cells = _put_run(
        draft,
        prefix,
        row=1,
        col=2,
        east=True,
        left=1,
        right=width,
        literal_padding=padding,
    )
    if col >= width:
        raise LaneError("branch does not fit on its entry row")
    draft.put(1, col, "d")
    branch_cell = (1, col)
    taken_cells: list[tuple[int, int]] = []
    straight_cells: list[tuple[int, int]] = []
    taken_end_row = 1
    if isinstance(branch.taken, Lane):
        draft.put(2, col, "v")
        draft.put(3, col, ">")
        taken_ops = _flat_ops(branch.taken)
        taken_end_row, _, taken_east, taken_cells = _put_run(
            draft,
            taken_ops,
            row=3,
            col=col + 1,
            east=True,
            left=1,
            right=width - 1,
            literal_padding=padding,
            base_index=len(prefix) + 1,
        )
        if taken_east:
            draft.put(taken_end_row, width - 1, "v")
            taken_end_row += 1
            draft.put(taken_end_row, width - 1, "<")
        draft.put(taken_end_row, 1, "^")
    if isinstance(branch.straight, Lane):
        straight_ops = _flat_ops(branch.straight)
        end_row, _, end_east, straight_cells = _put_run(
            draft,
            straight_ops,
            row=1,
            col=col + 1,
            east=True,
            left=col,
            right=width,
            literal_padding=padding,
            base_index=len(prefix) + 1 + len(taken_cells),
        )
        if end_row != 1 or not end_east:
            raise LaneError("straight arm must fit before its return column")
        bottom = max(2, taken_end_row + 1)
        draft.put(1, width, "v")
        draft.put(bottom, width, "<")
        draft.put(bottom, 1, "^")
        for row in range(2, bottom):
            if row != taken_end_row:
                draft.put(row, 1, "^")
    draft.op_cells = prefix_cells + [branch_cell] + taken_cells + straight_cells
    draft.invariants.append("d arms merge at the shared left return column")
    draft.invariants.append("branch arms preserve caller-declared register state")
    draft.ticks_per_lap = len(draft.cells)
    return draft
