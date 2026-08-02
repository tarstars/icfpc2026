"""Production implementation of the organizer's ``Y`` split semantics.

The original simulator predates the mid-contest ``Y`` release.  This module
installs a compatibility subclass as ``littleman.sim.Machine`` while keeping
all parser, pipe, literal, display, and arithmetic code in ``sim.py`` as the
single source of truth.

Why an installed subclass instead of a second simulator:

* every existing caller that imports ``littleman.sim.Machine`` gets the new
  semantics;
* the change is isolated to the dynamic-population and collision phases;
* ``littleman.fastsim.Machine`` still uses its flattened executor for programs
  without ``Y`` and is wrapped at class creation to fall back to this reference
  loop for programs whose population can change.

The contract is the organizer-confirmed text archived in
``docs/language-reference-updates-2026-07-27.md``.  In particular, dead men
remain as tombstones in the stable creation-order list but are removed from
scheduling, waits, and occupancy, so they are not obstacles.
"""

from __future__ import annotations

import functools
import heapq
from types import ModuleType

MEN_CAP = 65_536


def install(sim: ModuleType):
    """Install and return the production ``Machine`` with ``Y`` support.

    The operation is idempotent.  ``sim`` is passed in by ``littleman``'s
    package initializer to avoid an import cycle while the module is loading.
    """

    current = sim.Machine
    if getattr(current, "_y_semantics_installed", False):
        return current

    base_machine = current
    Man = sim.Man
    clockwise = sim.CLOCKWISE
    countercw = sim.COUNTERCW

    class Machine(base_machine):
        _y_semantics_installed = True

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._uses_split = any("Y" in row for row in self.grid)
            self.max_live_men = MEN_CAP
            self._live_men = len(self.men)
            self.graveyard = []
            for man in self.men:
                man.alive = True

        def __init_subclass__(cls, **kwargs):
            """Make the flattened fast executor decline dynamic populations.

            ``fastsim.Machine`` is defined after this class is installed.  Its
            static parallel arrays cannot grow when a man splits, so its
            existing ``run`` method is wrapped at class creation: a ``Y`` grid
            uses the reference run loop, while every ordinary program keeps the
            optimized Python/C path unchanged.
            """

            super().__init_subclass__(**kwargs)
            if cls.__module__ != "littleman.fastsim":
                return
            fast_run = cls.__dict__.get("run")
            if fast_run is None or getattr(fast_run, "_y_reference_fallback", False):
                return

            @functools.wraps(fast_run)
            def run_with_y_fallback(self, inputs=None, max_ticks=5_000_000, controller=None):
                if getattr(self, "_uses_split", False):
                    return base_machine.run(self, inputs, max_ticks, controller)
                return fast_run(self, inputs, max_ticks, controller)

            run_with_y_fallback._y_reference_fallback = True
            cls.run = run_with_y_fallback

        @staticmethod
        def _is_alive(man) -> bool:
            return getattr(man, "alive", True)

        def _kill_index(self, index: int) -> None:
            """Remove one man from the live machine without changing slots."""

            if not 0 <= index < len(self.men):
                return
            man = self.men[index]
            if not self._is_alive(man):
                return
            self._clear_wait(index)
            self._runnable_men.discard(index)
            if self._occupied.get((man.r, man.c)) is man:
                self._occupied.pop((man.r, man.c), None)
            man.alive = False
            man.halted = True
            man.blocked = False
            man.wait_kind = None
            man.wait_pipes = ()
            self._live_men -= 1
            self.graveyard.append(man)

        def _split(self, man):
            """Execute ``Y`` in the current creation-order slot."""

            index = self._tick_current_index
            if not 0 <= index < len(self.men) or self.men[index] is not man:
                raise RuntimeError("splitter is not in the current creation-order slot")

            right_direction = clockwise[man.direction]
            left_direction = countercw[man.direction]
            births = (
                (man.r + right_direction[0], man.c + right_direction[1]),
                (man.r + left_direction[0], man.c + left_direction[1]),
            )

            # Birth onto a wall is an immediate fatal in the same execution
            # phase: there is no normal one-tick wall grace and no sibling move.
            if any(not man.room.contains_interior(r, c) for r, c in births):
                return "wall"

            # Replacing one parent with two children increases the live count
            # by one.  The organizer checks the cap before birth collisions.
            if self._live_men + 1 > self.max_live_men:
                return "split-limit"

            self._clear_wait(index)
            self._runnable_men.discard(index)
            if self._occupied.get((man.r, man.c)) is man:
                self._occupied.pop((man.r, man.c), None)

            right = Man(
                births[0][0],
                births[0][1],
                man.room,
                direction=right_direction,
                A=man.A,
                B=man.B,
                BP=man.BP,
            )
            left = Man(
                births[1][0],
                births[1][1],
                man.room,
                direction=left_direction,
                A=man.A,
                B=man.B,
                BP=man.BP,
            )
            right.alive = True
            left.alive = True

            # The right copy inherits the parent's action slot; the left copy
            # is newest.  The old object becomes a non-live tombstone.
            self._man_indices.pop(id(man), None)
            man.alive = False
            man.halted = True
            man.blocked = False
            man.wait_kind = None
            man.wait_pipes = ()
            self.graveyard.append(man)

            self.men[index] = right
            left_index = len(self.men)
            self.men.append(left)
            self._man_indices[id(right)] = index
            self._man_indices[id(left)] = left_index
            self._live_men += 1

            # Newborns act on the following tick.  Add them only to the next
            # runnable set; never to the current heap.
            self._runnable_men.add(index)
            self._runnable_men.add(left_index)

            # Splits execute in creation order.  Register each child in that
            # order; a later split that targets the same cell sees and kills
            # the earlier newborn, matching simultaneous-spawn annihilation.
            for baby_index in (index, left_index):
                baby = self.men[baby_index]
                if not self._is_alive(baby):
                    continue
                occupant = self._occupied.get((baby.r, baby.c))
                if occupant is not None and self._is_alive(occupant):
                    occupant_index = self._man_indices[id(occupant)]
                    self._kill_index(baby_index)
                    self._kill_index(occupant_index)
                else:
                    self._occupied[(baby.r, baby.c)] = baby
            return None

        def _execute(self, man):
            if self.grid[man.r][man.c] == "Y":
                return self._split(man)
            return super()._execute(man)

        def _movement_phase(self, movers) -> None:
            """Move simultaneously and apply the post-split death rules."""

            active = [
                index
                for index in movers
                if 0 <= index < len(self.men)
                and self._is_alive(self.men[index])
                and not self.men[index].halted
            ]
            origins = {
                index: (self.men[index].r, self.men[index].c) for index in active
            }
            targets = {}

            # Normal movement into a room wall keeps the already implemented
            # one-grace-tick fatal.  The man really enters the wall coordinate,
            # but is no longer an interior obstacle.
            for index in active:
                man = self.men[index]
                nr = man.r + man.direction[0]
                nc = man.c + man.direction[1]
                if not man.room.contains_interior(nr, nc):
                    man.r, man.c = nr, nc
                    man.crashed = True
                    man.halted = True
                    self._runnable_men.discard(index)
                    if self._occupied.get(origins[index]) is man:
                        self._occupied.pop(origins[index], None)
                    continue
                targets[index] = (nr, nc)

            moving = set(targets)
            standing = {}
            for index, man in enumerate(self.men):
                if (
                    index not in moving
                    and self._is_alive(man)
                    and not man.crashed
                    and man.room.contains_interior(man.r, man.c)
                ):
                    standing[(id(man.room), man.r, man.c)] = index

            doomed = set()

            # Adjacent men swapping cells die, even though neither endpoint is
            # occupied after simultaneous movement.
            origin_owner = {
                (id(self.men[index].room), origins[index][0], origins[index][1]): index
                for index in moving
            }
            for index, target in targets.items():
                key = (id(self.men[index].room), target[0], target[1])
                other = origin_owner.get(key)
                if (
                    other is not None
                    and other != index
                    and targets.get(other) == origins[index]
                ):
                    doomed.add(index)
                    doomed.add(other)

            # All men arriving at the same cell on the same tick die.
            by_target = {}
            for index, target in targets.items():
                key = (id(self.men[index].room), target[0], target[1])
                by_target.setdefault(key, []).append(index)
            for group in by_target.values():
                if len(group) > 1:
                    doomed.update(group)

            # Walking onto a blocked, halted, or newborn man kills both.
            for index, target in targets.items():
                key = (id(self.men[index].room), target[0], target[1])
                occupant = standing.get(key)
                if occupant is not None:
                    doomed.add(index)
                    doomed.add(occupant)

            for index in sorted(doomed):
                self._kill_index(index)

            for index, (nr, nc) in targets.items():
                if index in doomed:
                    continue
                man = self.men[index]
                if not self._is_alive(man) or man.halted:
                    continue
                man.r, man.c = nr, nc

            # Rebuild from live interior occupants.  Tombstones and men pending
            # a wall fatal cannot block any later movement or split birth.
            self._occupied = {
                (man.r, man.c): man
                for man in self.men
                if self._is_alive(man)
                and not man.crashed
                and man.room.contains_interior(man.r, man.c)
            }

        def _tick(self, res):
            # 1. pipes shift
            for pipe in tuple(self._active_pipes.values()):
                source_was_full = pipe.values[0] is not None
                destination_was_empty = pipe.values[-1] is None
                pipe.shift()
                pipe_id = id(pipe)
                if self._pipe_can_shift(pipe):
                    self._active_pipes[pipe_id] = pipe
                else:
                    self._active_pipes.pop(pipe_id, None)
                if source_was_full and pipe.values[0] is None:
                    self._wake_pipe_senders(pipe)
                if destination_was_empty and pipe.values[-1] is not None:
                    self._wake_pipe_receivers(pipe)

            # 2. I/O: emit output, then inject input
            self._verdict = None
            if self.output_pipe and self.output_pipe.values[-1] is not None:
                value = self._pipe_take(self.output_pipe, -1)
                res.output.append(value)
                res.output_ticks.append(res.ticks)
                if self._controller:
                    verdict = self._controller.on_output(value, res.ticks)
                    if verdict:
                        self._verdict = verdict
                        return None
            if self.input_pipe and self.input_pipe.values[0] is None:
                if self._controller:
                    value = self._controller.pop_input()
                    if value is not None:
                        self._pipe_put(self.input_pipe, 0, value)
                elif self._input_queue:
                    self._pipe_put(self.input_pipe, 0, self._input_queue.pop(0))

            # 3. execute.  A normal wall crash from the preceding movement
            # phase ends the program after this tick's pipe shift/output emit.
            if any(self._is_alive(man) and man.crashed for man in self.men):
                self._tick_heap = None
                return "wall"

            self._tick_heap = list(self._runnable_men)
            heapq.heapify(self._tick_heap)
            self._runnable_men = set()
            self._tick_processed = set()
            movers = []
            while self._tick_heap:
                index = heapq.heappop(self._tick_heap)
                if index in self._tick_processed:
                    continue
                self._tick_processed.add(index)
                self._tick_current_index = index
                if not 0 <= index < len(self.men):
                    continue
                man = self.men[index]
                if not self._is_alive(man) or man.halted:
                    continue
                man.blocked = False
                err = self._execute(man)
                if err:
                    self._tick_heap = None
                    return err
                if not self._is_alive(man):
                    continue
                if man.blocked:
                    instruction = self.grid[man.r][man.c]
                    if instruction == "r":
                        pipes = [self._nearest_incoming(man)]
                        kind = "r"
                    elif instruction in "RU":
                        pipes = self._incoming(man)
                        kind = "RU"
                    elif instruction == "s":
                        pipes = [self._nearest_outgoing(man)]
                        kind = "s"
                    else:
                        pipes = self._outgoing(man)
                        kind = "S"
                    self._register_wait(index, kind, pipes)
                elif not man.halted:
                    movers.append(index)
                    self._runnable_men.add(index)

            for disp in self.displays:
                err = self._display_tick(disp, res)
                if err:
                    self._tick_heap = None
                    return err

            # 4. simultaneous movement/collision resolution
            self._movement_phase(movers)
            self._tick_heap = None
            self._tick_current_index = -1
            return None

    # Present the installed class as the production simulator class rather
    # than leaking its implementation module through diagnostics.
    Machine.__name__ = "Machine"
    Machine.__qualname__ = "Machine"
    Machine.__module__ = sim.__name__
    sim.Machine = Machine
    return Machine
