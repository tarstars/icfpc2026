# Overnight autonomous goal — execute the queue

## Activation

Pursue this goal autonomously from activation until the queue in
`docs/architecture/claude_19_overnight_handoff.md` is empty, or until
**2026-07-26T06:00Z (09:00 Europe/Moscow)** — when the user wakes and
rejoins — whichever comes first. That is roughly TEN HOURS from
activation, not two days: scope accordingly. Work only in
`/home/tarstars/prj/icfpc2026-claude` on branch `agent/claude`.

The user is asleep. Do not wait for input. Do not ask questions you can
answer from the repository.

## Mission

**Execute the pre-selected queue. Do no new design.**

Every item is already specified in `docs/architecture/claude_09` through
`claude_19`. The "which hypothesis is most promising" decision has
already been made and written down, in priority order, by the previous
session — that ordering encodes measured evidence you will not have time
to re-derive. Follow it top-down.

Startup, in this order:

1. `git fetch origin`, rebase/merge `agent/claude` onto `origin/main`.
2. Read `docs/architecture/claude_19_overnight_handoff.md` fully. It is
   the queue, the operating rules, and the trap list.
3. Read `coordination/status/codex.md` and any new files in
   `coordination/messages/codex/`.
4. Check for subagents still running from the previous session (SCAN and
   CLASSIFY were in flight) before starting anything that touches their
   files.

## The loop

For each queue item, top of the queue first:

1. Read its definition of done in `claude_19`.
2. Execute it (directly, or by dispatching a subagent per
   `docs/architecture/claude_14_subagent_policy.md`).
3. Run **every mandatory gate** for that item.
4. Append the outcome under `## RESULTS` in `claude_19` — with the exact
   command and the exact number. A claim without a command is not a
   result.
5. Commit and push.
6. Take the next item.

If an item fails its gates **twice**, record why and move to the next
item. Do not spend a third attempt.

## Submission authority

The user granted standing authorization: submit any candidate that passes
its gates. Gates are not optional:

- `uv run python scripts/preflight.py <artifact> <slug>` must print
  **READY TO SUBMIT**;
- the problem's oracle/fuzz check must pass with zero failures;
- submit only via
  `uv run icfpc-api --env-file /home/tarstars/prj/icfpc2026/.env submit
  <problemId> <artifact> --confirm --wait > <artifact>-submit.json`;
- preserve the response file and message Codex afterwards.

Submissions can never lower a score, so a **gated** submission is always
safe. An ungated one wastes the artifact and misleads the team.

## Codex is working in parallel

Codex is the integrator and is running its own session. Assume it is
active overnight.

- Codex owns `main`, `docs/` (except `docs/architecture/claude_*`),
  `src/littleman/sim.py`, the variant catalogs
  (`submissions/*/variants.json`), and its own `codex/` and
  `coordination/messages/codex/` areas. **Do not edit those.**
- Fetch before each committing session and merge `origin/main` regularly;
  Codex pushes geometry work frequently and conflicts are cheap to
  resolve early and expensive to resolve late.
- Codex has open items that may land overnight: the `lane.py` room
  assembler (`docs/architecture/claude_12`), Pathfinder, and a decision
  on adding `Y` to `sim.py`. If any lands, it changes the queue:
  a working `lane.py` makes queue item 1 much cheaper; a Y-capable
  `sim.py` unblocks queue item 6.
- Coordinate only through immutable messages in
  `coordination/messages/claude/`. Never edit Codex's status or messages.
- If Codex claims a queue item first, skip it and record that.

### Use the review loop — it is the highest-yield mechanism available

Today it caught real defects in BOTH directions, each within an hour:

- Codex reviewing Claude found two missing semantics in `llm.py`
  (signed-64 wrapping; man-to-man collision) that no public fixture
  covered.
- Claude reviewing Codex found a frontier-ordering bug in the Pathfinder
  bitboard walk (fixed by distance-mod-3 bit-planes), and rejected a
  correct-but-723x8134 LOADER room that would have been unshippable.
- Codex's `brackets_00` monkey-patch experiment upgraded the B-register
  correction from spec-reading to server-proven.

So, actively:

1. **Ask for review** whenever a component is about to be trusted by
   something else — post a message naming the artifact, the exact claim,
   and the command that proves it. Do not block on the answer; continue
   and fold the reply in when it arrives.
2. **Review what Codex pushes.** Fetch regularly; when it lands a
   candidate, run the gates yourself before believing the numbers, and
   check the thing a builder cannot see — footprint against our best
   artifacts, binding margins (`littleman.room_ports.audit`), and whether
   the claim was measured or assumed.
3. **Leave notes for the morning** in `coordination/messages/claude/`:
   what was accepted, what was rejected and why, and any correction that
   belongs in the cookbook or the tool registry.
4. Accept useful findings without ego, and say plainly when a review is
   wrong — today both sides did both, and that is why it worked.

## Hard rules

- **Do no new design.** If an item seems to need a design decision, take
  the conservative option already recorded in the specs, and note it.
- Never modify a shipped artifact or its generator; a new attempt is a
  new `<slug>_NN.man`.
- Push a checkpoint at least every 15 minutes.
- Subagent supervision per `claude_14`: check at 3 minutes then every 5,
  classify with `scripts/agent_watch.py`, and after two failures change
  the task rather than the prompt.
- Never claim a test passed without running it.

## End condition

Stop when the queue is empty, at **2026-07-26T06:00Z (09:00 Moscow)**, or
if every remaining item has failed twice. Start no NEW queue item after
05:00Z; an item already in flight may finish. Before stopping:

1. finish or safely terminate running commands and subagents;
2. push everything;
3. update `coordination/status/claude.md`;
4. write a short summary under `## RESULTS` in `claude_19`: what was
   submitted with which scores, what failed and why, and the smallest
   next action for the morning.

The user rejoins at 06:00Z and will take over; leave the tree clean, the
branch pushed, and the morning's smallest next action written down. The
contest itself runs until 2026-07-27T12:00Z (freeze 10:00Z), so there is
a full day left after the handback — do not gamble the night on item 6.
