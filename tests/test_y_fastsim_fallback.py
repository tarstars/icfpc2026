"""Fast-executor routing for final split/collision population semantics."""

from littleman import fastsim
from littleman.sim import LEFT


def room(rows: list[str]) -> str:
    width = max(map(len, rows))
    return "\n".join(
        ["+" + "-" * width + "+"]
        + ["|" + row.ljust(width) + "|" for row in rows]
        + ["+" + "-" * width + "+"]
    )


def live(machine) -> list:
    return [man for man in machine.men if getattr(man, "alive", True)]


def test_same_room_multi_man_machine_uses_reference_collision_phase() -> None:
    machine = fastsim.Machine.parse(room(["@ @"]))
    machine.men[1].direction = LEFT

    assert machine._requires_population_reference
    assert getattr(type(machine).run, "_y_reference_fallback", False)

    result = machine.run(max_ticks=2)

    assert result.status == "halted"
    assert result.error is None
    assert live(machine) == []
    assert machine._occupied == {}


def test_independent_single_man_room_keeps_fast_path_eligible() -> None:
    machine = fastsim.Machine.parse(room(["@H"]))

    assert not machine._uses_split
    assert not machine._requires_population_reference
