# LLM state-index binding margin

Status: read-only final geometry audit.

I enumerated all 47 `r`/`s` instruction cells in the generated STATEINDEX
controller and compared Manhattan distance to the intended external/scratch
port against the competing same-direction port.

Ports:

- external output `(55, 4)`;
- scratch output `(65, 91)`;
- external input `(45, 4)`;
- scratch input `(89, 91)`.

Minimum strict margin is **19 cells**, at the late scratch sentinel send.
The next weakest margins are 23 cells. Therefore every binding remains
strict and has substantially more than the project's required margin of 2.

This numerically closes the two geometry faults found during construction;
the physical/reference tests already pass all 14 public and 10 fuzz states.
