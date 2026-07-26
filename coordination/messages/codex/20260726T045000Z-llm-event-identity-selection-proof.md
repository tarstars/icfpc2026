# LLM event-identity selection proof

Status: final read-only differential validation.

The indexed protocol replaces numeric source/room indices with each room's
stable negative event token. I compared both forms at every executed `s`/`r`
action while advancing exact reference state:

- 200 deterministic pipe-bearing fuzz programs, up to 100 ticks each:
  1,558 states and 1,437 actions;
- all 14 public programs, up to 100 ticks each:
  258 states and 159 actions;
- public selection coverage includes 4 actions with both pipe slots eligible
  and 2 exact Manhattan-distance ties.

For all 1,596 actions, PIPECANDIDATE plus SELECTELIGIBLE chose the same pipe
as the original room-index action protocol. Every action had at least one
eligible pipe, as required by the problem's well-formedness guarantee.

This validates event tokens as source identities, including the nontrivial
two-slot/read-order paths.
