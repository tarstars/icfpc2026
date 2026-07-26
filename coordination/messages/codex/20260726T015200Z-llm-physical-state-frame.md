# LLM physical runtime-frame checkpoint

Status: pushed component checkpoint; no contest mutation.

The later-frame output path is now physical:

- `llm_pipeframe.py` consumes a normalized pipe record and emits exact
  `(address, color)` pairs from its occupancy mask, including cell 0,
  zero/negative FIFO values, empty pipes, and the 20-cell maximum.
- `llm_stateframe.py` consumes the packed raw world plus a normalized runtime
  state and emits a complete frame as `(color, address)` pairs followed by
  `-1`. It composes COLORFETCH, WALLGEN, and PIPEFRAME and overlays in the
  required order: base, walls, men, pipe animation.

Adversarial geometry findings fixed during construction:

1. vertically stacked service routes crossed once a third service was added;
   PIPEFRAME now uses independent bottom/top routes;
2. the main-state read and rendered-pair output initially rebound to those
   new routes; their FSM lanes were separated and every relevant `r`/`s`
   binding was audited against `Machine._nearest_*`;
3. the terminal arrow on the returning service pipe required an explicit
   bend glyph.

Evidence:

- 12 selected public state snapshots (0/1 interpreted ticks; 0/1/2 program
  pipes; 1/2/3 rooms) are physical/reference byte exact:
  `12 passed in 54.80s`.
- All 42 public-reference frame states plus generator gates and directed
  pipe-frame cases: `45 passed, 12 deselected in 0.68s`; PIPEFRAME's separate
  physical cases also pass.
- Determinism, server layout, pipe audit, Ruff, and `git diff --check` pass.
- PIPEFRAME room: `60 x 82`, 452 occupied cells.
- STATEFRAME room: `108 x 94`, 741 occupied cells; complete three-service rig:
  `361 x 374`, 5,901 occupied cells.

Remaining LLM blocker:

- The exact reference action cycle and all arithmetic services now exist,
  and frame output exists. The missing physical component is the streaming
  whole-state controller that filters candidate pipes, calls PIPESELECT,
  routes the selected record through PIPEAPPLY, and patches the man record
  sequentially in room order. Final recirculation/wall-freeze/assembly follow
  that controller.
