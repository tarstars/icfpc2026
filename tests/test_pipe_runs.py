import random

from littleman.sim import Pipe, Room


def _reference_shift(values):
    shifted = list(values)
    for index in range(len(values) - 2, -1, -1):
        if shifted[index] is not None and shifted[index + 1] is None:
            shifted[index + 1] = shifted[index]
            shifted[index] = None
    return shifted


def test_pipe_run_index_matches_cell_model():
    rng = random.Random(20260724)
    source = Room(0, 0, 2, 2)
    destination = Room(0, 4, 2, 6)
    pipe = Pipe(
        cells=[(1, column) for column in range(3, 23)],
        source=source,
        dest=destination,
    )
    reference = [None] * len(pipe.cells)

    for _ in range(10_000):
        operation = rng.choice(("put", "take", "shift"))
        index = rng.randrange(len(reference))
        if operation == "put":
            value = rng.randrange(-1000, 1001)
            pipe.put(index, value)
            reference[index] = value
        elif operation == "take":
            assert pipe.take(index) == reference[index]
            reference[index] = None
        else:
            pipe.shift()
            reference = _reference_shift(reference)

        assert pipe.values == reference
        assert pipe.count == sum(value is not None for value in reference)
