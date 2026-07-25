"""LLLM FETCH station acceptance (work order claude_11a).

Model first: :func:`littleman.lllm_fetch.fetch_reference` is the oracle, and
the rig must equal it token for token.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from littleman import llm_fuzz, lllm_step, server_compat
from littleman.ir_export import machine_ir
from littleman.lllm_fetch import (
    CELLS,
    WORLD_TOKENS,
    build_fetch_rig,
    fetch_reference,
    pack_world,
    rig_stream,
    unpack_world,
)
from littleman.sim import Machine

TINY = [
    "+--------+",
    "|@ 12 M  |",
    "| >v< H  |",
    "| +- X   |",
    "+--------+",
]


def tiny_world():
    tokens, _man = pack_world(TINY)
    return tokens


class Script:
    """Feed the rig its tokens; stop the run on the last expected response."""

    def __init__(self, tokens, expected):
        self.tokens = list(tokens)
        self.expected = list(expected)
        self.got: list[int] = []
        self.last_tick = 0

    def pop_input(self):
        return self.tokens.pop(0) if self.tokens else None

    def on_output(self, value, tick):
        self.got.append(value)
        self.last_tick = tick
        return "passed" if len(self.got) >= len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_fetch_rig()


def run_rig(text, world, requests, max_ticks=3_000_000):
    """Run the rig on one request script and return (responses, last tick)."""
    expected = fetch_reference(world, requests)
    script = Script(rig_stream(world, requests), expected)
    res = Machine.parse(text).run(max_ticks=max_ticks, controller=script)
    assert res.error is None, res.error
    assert res.status == "passed", (res.status, len(script.got), len(expected))
    return script.got, script.last_tick


def check(text, world, requests):
    got, ticks = run_rig(text, world, requests)
    assert got == fetch_reference(world, requests)
    return ticks


# ------------------------------------------------------------ layout gates
CMD_READERS = {(2, 26), (6, 7)}            # setup relay, MAIN request read
RESP_SENDERS = {(9, 8), (13, 8), (21, 15)}  # colour tail, op tail, peel body


def test_generator_is_deterministic(text):
    assert build_fetch_rig() == text


def test_layout_passes_server_compatibility(text):
    server_compat.validate_layout(text)
    for pipe in Machine.parse(text).pipes:
        assert len(pipe.cells) >= 2      # the server rejects 1-cell pipes


def test_rooms_and_pipes(text):
    machine = Machine.parse(text)
    assert len(machine.rooms) == 4       # I, FETCH, RELAY, O
    assert len(machine.men) == 2         # FETCH and RELAY
    ring = [p for p in machine.pipes if p.source.kind == p.dest.kind == "room"]
    assert len(ring) == 2
    # 64 world tokens + the marker must all fit with the relay man's hand.
    assert sum(len(p.cells) for p in ring) >= WORLD_TOKENS + 1


def test_pipe_binding_audit(text):
    """Every pipe op in FETCH binds the pipe the design intends (2 in/2 out).

    FETCH is the only room with two incoming and two outgoing pipes, so this
    is the one place nearest-pipe resolution can silently go wrong.
    """
    ir = machine_ir(text)
    kinds = [
        (ir["rooms"][p["source"]]["kind"], ir["rooms"][p["dest"]]["kind"])
        for p in ir["pipes"]
    ]
    cmd = kinds.index(("input", "room"))
    resp = kinds.index(("room", "output"))
    fetch = min(
        (i for i, r in enumerate(ir["rooms"]) if r["kind"] == "room"),
        key=lambda i: ir["rooms"][i]["left"],
    )
    ring_out = next(
        i for i, p in enumerate(ir["pipes"]) if p["source"] == fetch and i != resp
    )
    ring_in = next(
        i for i, p in enumerate(ir["pipes"]) if p["dest"] == fetch and i != cmd
    )
    seen = {"cmd": set(), "resp": set()}
    for key, entry in ir["resolution"].items():
        r, c = (int(v) for v in key.split(","))
        if not (ir["rooms"][fetch]["left"] < c < ir["rooms"][fetch]["right"]):
            continue                      # the relay's own ops
        if entry["op"] == "r":
            want = cmd if (r, c) in CMD_READERS else ring_in
            if want == cmd:
                seen["cmd"].add((r, c))
        else:
            want = resp if (r, c) in RESP_SENDERS else ring_out
            if want == resp:
                seen["resp"].add((r, c))
        assert entry["pipe"] == want, (key, entry)
    assert seen["cmd"] == CMD_READERS and seen["resp"] == RESP_SENDERS


def test_packer_agrees_with_lllm_step():
    """The two stations must share one claude_09 record layout."""
    assert pack_world(TINY) == lllm_step.pack_world(TINY)


# ------------------------------------------------------- corpora (acc 1)
PROBLEM = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "data/small/problems/little-little-little-man.json"
    ).read_text()
)
CASES = PROBLEM["publicTestData"]
FUZZ = llm_fuzz.corpus(20260727, 30)

# every addr op-fetched, every addr colour-fetched, then a full stream
FULL_COVER = list(range(CELLS)) + [CELLS + a for a in range(CELLS)] + [-1]


def world_of(case):
    return pack_world(lllm_step.case_rounds(case)[0])[0]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_public_case_world_full_coverage(text, case):
    check(text, world_of(case), FULL_COVER)


@pytest.mark.parametrize("seed", range(len(FUZZ)))
def test_fuzz_world_mixed_script(text, seed):
    rng = random.Random(9000 + seed)
    script = [rng.randrange(-1, 2 * CELLS) for _ in range(70)]
    script = [t if t >= 0 else -1 for t in script]
    script += [0, CELLS + 255, -1, 255, CELLS]
    check(text, world_of(FUZZ[seed]), script)


# --------------------------------------------------------- directed (acc 2)
@pytest.mark.parametrize(
    "requests",
    [
        [0],
        [255],
        [CELLS + 0],
        [CELLS + 255],
        [0, 255, 0],                      # full backward jump, twice round
        [4, 5, 6, 7],                     # every field of one word
        [CELLS + 4, CELLS + 5, CELLS + 6, CELLS + 7],
        [3, 4, 7, 8, 251, 252],           # word-boundary straddles
        [-1, -1],                         # ring order must survive a stream
        [-1, 9, CELLS + 9, -1, 9],        # streams interleaved with fetches
        [17, CELLS + 17, 18, CELLS + 18],
    ],
    ids=str,
)
def test_directed_requests(text, requests):
    check(text, tiny_world(), requests)


def test_ring_order_survives_streams_and_fetches(text):
    """The world is read-only: every path re-emits and the counts restore."""
    world = tiny_world()
    script = [-1, -1] + list(range(0, CELLS, 7)) + [-1] + [CELLS, CELLS + 255]
    check(text, world, script)


def test_reported_ticks(record_property):
    """Ticks per op fetch and per full stream, measured not guessed."""
    text = build_fetch_rig()
    world = tiny_world()
    _, setup_and_one = run_rig(text, world, [0])
    _, sweep = run_rig(text, world, list(range(CELLS)))
    _, stream = run_rig(text, world, [-1])
    per_op = (sweep - setup_and_one) / (CELLS - 1)
    record_property("setup_ticks", setup_and_one)
    record_property("ticks_per_op_fetch", per_op)
    record_property("ticks_full_stream", stream - setup_and_one)
    assert setup_and_one < 1500
    assert per_op < 1200
    assert stream < 20000


def test_reference_matches_packed_records():
    world = tiny_world()
    records = unpack_world(world)
    assert len(records) == CELLS
    assert len(world) == WORLD_TOKENS

    addrs = [0, 1, 17, 18, 255]
    ops = fetch_reference(world, addrs)
    cols = fetch_reference(world, [CELLS + a for a in addrs])
    for i, addr in enumerate(addrs):
        rec = records[addr]
        assert ops[i] == (((rec >> 4) & 15) << 4) | ((rec >> 8) & 15)
        assert cols[i] == rec & 15

    stream = fetch_reference(world, [-1])
    assert stream == [rec & 15 for rec in records]
