# Manual Memory submission by the user, 2026-07-26 — record and analysis

The user submitted a Memory artifact by hand through the web interface.
This records what changed, what is verified, and the one field needed to
close the record. Written because the artifact is NOT in the repository:
no `.man` under any ref reproduces the live score, so without this note
the team's best Memory machine would be unreproducible.

## What changed, live (measured from standings)

| | before | after |
|---|---|---|
| score | 17,236,875 | **16,033,454.75** |
| cases | 24/24 | 24/24 |
| uberStrictPassed | — | true |
| rank | 18/166 | **17/168** |
| points | 1.90 | 1.904 |

A 7.0% score improvement. Top-5 on this problem is ~9.55M, so we sit
17th of 168 with 0.096 points still available there.

## The artifact is not in the repository

Every `.man` on `origin/main` (22 candidates: memory_01..10, memory.man,
the `room-packing/` lineage, the Y probes) was judged locally and
projected to the server using memory_10's measured local->server tick
ratio of **4.8392** (server avgTicks 19,152.08 / local 3,957.7):

    memory_10   30x30  fp 900  local avg 3957.7  -> projected 17,236,937
    memory_09   31x31  fp 961  local avg 3900.1  -> projected 18,137,484
    memory_08   31x31  fp 961  local avg 4109.9  -> projected 19,112,753
    ... everything else is worse

memory_10's projection reproduces its own live score to 4 significant
figures (17,236,937 vs 17,236,875), so the method is sound — and the
**closest repository artifact is still 7.5% above the new live score**.
The submitted machine is therefore a new artifact that exists only on the
contest server and (presumably) on the user's disk.

## Most likely change: a 29x29 repack

Score = footprint x avgTicks. Two hypotheses fit the number:

1. **Pure geometry, 30x30 -> 29x29** (fp 900 -> 841). Holding memory_10's
   tick count fixed, the implied footprint is 16,033,454.75 / 19,152.08 =
   **837.2**, and the nearest square is **841 = 29^2** — a 0.45% residual,
   which a slightly shorter pipe route would explain exactly.
2. Same 30x30 box with ~7% fewer ticks (server avg 17,815, local ~3,681).

Hypothesis 1 is far more likely: the entire Memory lineage
(memory_04 37x37 -> 06 34x32 -> 10 30x30) moved on geometry alone, with
ticks changing under 5% across the whole chain, and 29x29 continues that
pattern one step. Hypothesis 2 would require a tick win nobody has found
in three generations.

## To close this record (one field settles it)

The public API returns submission METADATA including `width`, `height`
and `avgTicks` — but not the program source:

    curl -H "Authorization: Bearer $KEY" \
      https://icfpcontest2026.com/api/v1/submissions/<submission-id>

So the **submission id** alone (visible in the web dashboard) confirms
the dimensions and settles the hypothesis. The artifact itself must be
copied in by hand — either the `.man` file, or a browser-session export.

Once available: save as `submissions/memory/memory_11.man`, add its
`-submit.json`, judge it locally to record the true local avg, and
extend the lineage table in `docs/littleman_triangle_memory.pdf` (which
currently documents memory_04 -> 06 -> 10 and would gain a fourth row).

## API discovery worth keeping

The web dashboard lists a team's own submissions via
`GET /api/v1/dashboard/submissions?problemId=<uuid>` (found in the SPA
bundle `/assets/index-*.js`, hono RPC client with base `/api/v1`). It is
**session-authenticated** and rejects the API key with
`401 unauthorized: Not signed in`, so it is unusable from scripts. There
is no bearer-authenticated endpoint that lists submissions or returns
program source; `/api/v1/submissions/<id>` is metadata-only.
