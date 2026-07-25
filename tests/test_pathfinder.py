from collections import deque

from littleman.judge import judge_case
from littleman.pathfinder import build_pathfinder
from littleman.server_compat import validate_layout
from littleman.sim import Machine


W = H = 16


def _distances(board, flag):
    distances = [-1] * (W * H)
    fx, fy = flag
    distances[fy * W + fx] = 0
    queue = deque([flag])
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            nx, ny = x + dx, y + dy
            index = ny * W + nx
            if board[index] == 0 and distances[index] < 0:
                distances[index] = distances[y * W + x] + 1
                queue.append((nx, ny))
    return distances


def _frame(board, robot, flag=None):
    rows = []
    for y in range(H):
        row = []
        for x in range(W):
            color = 7 if board[y * W + x] else 0
            if flag == (x, y):
                color = 9
            if robot == (x, y):
                color = 10
            row.append(format(color, "x"))
        rows.append("".join(row))
    return rows


def _rounds(board, robot, flags):
    rounds = [{"in": board + list(robot), "frames": [_frame(board, robot)]}]
    for flag in flags:
        distances = _distances(board, flag)
        frames = []
        x, y = robot
        distance = distances[y * W + x]
        while distance:
            for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                nx, ny = x + dx, y + dy
                if distances[ny * W + nx] == distance - 1:
                    x, y, distance = nx, ny, distance - 1
                    break
            frames.append(_frame(board, (x, y), flag if distance else None))
        robot = (x, y)
        rounds.append({"in": list(flag), "frames": frames})
    return rounds


def test_pathfinder_is_deterministic_and_server_compatible():
    first = build_pathfinder()
    second = build_pathfinder()
    assert first == second
    validate_layout(first)
    machine = Machine.parse(first)
    assert len(machine.rooms) == 7
    assert len(machine.pipes) == 11
    assert len(machine.men) == 5
    assert min(len(pipe.cells) for pipe in machine.pipes) >= 2


def test_pathfinder_ties_and_all_move_directions():
    board = [
        1 if x in (0, W - 1) or y in (0, H - 1) else 0
        for y in range(H)
        for x in range(W)
    ]
    rounds = _rounds(board, (8, 8), [(10, 6), (7, 9)])
    result = judge_case(build_pathfinder(), rounds, max_ticks=15_000_000)
    assert result.passed, result

