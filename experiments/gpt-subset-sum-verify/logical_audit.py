"""Audit logical pipe identity, length, endpoint role and instruction binding."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from littleman.sim import Machine
from littleman.subset_sum import build_subset_sum

OPS = "sSrRUq"


class Probe:
    pass


def logical_map(text: str):
    machine = Machine.parse(text)
    room_index = {id(room): i for i, room in enumerate(machine.rooms)}
    pair_groups = defaultdict(list)
    for pipe in machine.pipes:
        pair = (room_index[id(pipe.source)], room_index[id(pipe.dest)])
        pair_groups[pair].append(pipe)

    # A source/destination pair is the logical identity when unique.  Preserve
    # an ordinal as a guard for machines that contain parallel pipes.
    pipe_key = {}
    for pair, pipes in pair_groups.items():
        for ordinal, pipe in enumerate(
            sorted(pipes, key=lambda p: (p.cells[0], p.cells[-1]))
        ):
            pipe_key[id(pipe)] = (pair[0], pair[1], ordinal)

    operations = []
    for room_i, room in enumerate(machine.rooms):
        op_i = 0
        incoming = sorted(
            machine.in_pipes.get(id(room), []), key=lambda p: p.cells[-1]
        )
        outgoing = sorted(
            machine.out_pipes.get(id(room), []), key=lambda p: p.cells[0]
        )
        for row in range(room.top + 1, room.bottom):
            for col in range(room.left + 1, room.right):
                char = machine.grid[row][col]
                if char not in OPS:
                    continue
                probe = Probe()
                probe.r, probe.c, probe.room = row, col, room
                if char == "s":
                    resolved = (pipe_key[id(machine._nearest_outgoing(probe))],)
                elif char in "rq":
                    resolved = (pipe_key[id(machine._nearest_incoming(probe))],)
                elif char == "S":
                    resolved = tuple(pipe_key[id(pipe)] for pipe in outgoing)
                else:  # R/U: reading-order priority over all incoming pipes
                    resolved = tuple(pipe_key[id(pipe)] for pipe in incoming)
                operations.append((room_i, op_i, char, resolved))
                op_i += 1

    lengths = {pipe_key[id(pipe)]: len(pipe.cells) for pipe in machine.pipes}
    endpoints = {
        pipe_key[id(pipe)]: (
            (
                pipe.cells[0][0] - pipe.source.top,
                pipe.cells[0][1] - pipe.source.left,
            ),
            (
                pipe.cells[-1][0] - pipe.dest.top,
                pipe.cells[-1][1] - pipe.dest.left,
            ),
        )
        for pipe in machine.pipes
    }
    pair_counts = Counter(
        (room_index[id(pipe.source)], room_index[id(pipe.dest)])
        for pipe in machine.pipes
    )
    return machine, operations, lengths, endpoints, pair_counts


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: logical_audit.py CANDIDATE.man")

    original = build_subset_sum()
    candidate = Path(sys.argv[1]).read_text()
    before, ops_before, len_before, end_before, pairs_before = logical_map(original)
    after, ops_after, len_after, end_after, pairs_after = logical_map(candidate)

    binding_diffs = [
        {"before": old, "after": new}
        for old, new in zip(ops_before, ops_after)
        if old != new
    ]
    keys = set(len_before) | set(len_after)
    length_diffs = [
        (key, len_before.get(key), len_after.get(key))
        for key in sorted(keys)
        if len_before.get(key) != len_after.get(key)
    ]
    endpoint_diffs = [
        (key, end_before.get(key), end_after.get(key))
        for key in sorted(keys)
        if end_before.get(key) != end_after.get(key)
    ]

    report = {
        "structure_before": [len(before.rooms), len(before.pipes), len(before.men)],
        "structure_after": [len(after.rooms), len(after.pipes), len(after.men)],
        "duplicate_room_pairs_before": {
            str(key): value for key, value in pairs_before.items() if value > 1
        },
        "duplicate_room_pairs_after": {
            str(key): value for key, value in pairs_after.items() if value > 1
        },
        "pipe_ops_before": len(ops_before),
        "pipe_ops_after": len(ops_after),
        "logical_binding_diffs_count": len(binding_diffs),
        "logical_binding_diffs": binding_diffs,
        "length_diffs_count": len(length_diffs),
        "length_diffs": length_diffs,
        "endpoint_role_diffs_count": len(endpoint_diffs),
        "endpoint_role_diffs": endpoint_diffs,
    }
    print(json.dumps(report, indent=1, default=list))
    Path(__file__).with_name("logical_binding_audit.json").write_text(
        json.dumps(report, indent=1, default=list)
    )
    if binding_diffs:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
