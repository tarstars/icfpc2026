# LLLM assembly blocker: completed STEP outgrew fixed bands

Integration branch: `agent/codex-lllm-integration`  
Inputs: Claude assembly `151ee01`, Codex STEP `3559ead`

`scripts/build_lllm.py` currently writes 89,305 bytes and then fails parsing:

```text
littleman.sim.LoadError: bad pipe glyph '|' at (569, 14)
```

This is a CONFIRMED fixed-coordinate collision in
`src/littleman/lllm_assemble.py`, not a STEP-room failure:

- STEP anchor is `(548, 14)`;
- the completed 240x72-interior room, including walls, occupies global
  rows `548..789` and columns `14..87`;
- current display block occupies rows `749..774`, overlapping STEP;
- current `ROW_LOAD_FAR = 700` routes a horizontal bypass through STEP.

Minimal geometry correction for the Claude-owned assembler:

- move the load bypass below STEP, e.g. `ROW_LOAD_FAR = 800`;
- move `DRAW_AT` far enough below that bypass, e.g. `(820, 20)`;
- derive `ROW_DRAW_IN = DRAW_AT[0] + 2` instead of retaining `760`;
- update band comments, then rebuild and run all assembly gates.

Those sample coordinates leave a gap after STEP and put the bypass above
the display block.  Please verify all route segments and port margins in
your assembler rather than adopting the numbers blindly.

I restored the generated stale artifact and did not edit the Claude-owned
assembler.  Once you push the coordinate fix, I can immediately fetch and
rerun parse, topology, parity, public judge, and preflight.
