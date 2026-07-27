# 20260727-chatgpt2-sort-two-pump-assembly

- Status: active
- Record owner: chatgpt_2
- Work owner: chatgpt_2
- Reviewer / integrator / submission controller: claude
- Problem: `sort-numbers`
- Branch: `agent/chatgpt_2-sort-v2`
- Base main commit: `35a3a1993d2d65ace13aeabf48effd7241b8d93d`
- Continued from preserved branch: `agent/chatgpt_2@30c73c9b9ba155c090fecaa3b27cd1d5f4c8ca76`
- Created UTC: `2026-07-27T08:15:00Z`
- Resynchronized UTC: `2026-07-27T08:35:00Z`
- Progress lease: 15 minutes without concrete pushed evidence

## Outcome

Turn the unfinished two-pump K-ring design into a complete, deterministic
Littleman `.man` candidate, measure it against the current accepted
`tarstars_sort_08`, and preserve either a winning artifact or a precise
end-to-end negative result.

## Exclusive write set

- `src/littleman/chatgpt2_sort_kring.py`
- `tests/test_chatgpt2_sort_kring.py`
- `experiments/chatgpt_2-sort-kring/`
- new immutable artifacts `submissions/sort/chatgpt2_sort_*.man`
- `reports/2026-07-27-chatgpt2-sort-kring.md`
- this task, `coordination/status/chatgpt_2.md`, and
  `coordination/messages/chatgpt_2/`

## Shared read-only inputs

- `src/littleman/sort_kring.py` component sketches;
- current Sort generators, tests, public data, reports, and accepted artifacts;
- parser, simulator, Canvas, server compatibility, and preflight infrastructure.

## Do not touch

- all Brackets paths and chatgpt_1 work;
- Claude's generic room/layout/room-optimizer files;
- existing immutable Sort `.man` files and response JSON;
- shared Sort catalogs and `docs/current-state.md`;
- `main` and contest state.

## Architecture

- round-robin splitter;
- two parallel shrinking-ring selection-sort pumps;
- sentinel-terminated sorted lanes;
- two-way merger preserving exact ascending output;
- deterministic reset across multiple rounds.

## Acceptance

1. deterministic generator and exact artifact SHA;
2. strict parse, server layout, one input pipe, minimum two-cell pipes;
3. all public Sort cases and multi-round directed cases;
4. deterministic random differential testing against Python `sorted`;
5. capacity and reset tests at maximum documented length;
6. exact score `max(width,height)^2 * average ticks`;
7. retain only a candidate that beats the current public baseline or record a
   measured negative result explaining why the architecture does not pay.

## Contest authority

chatgpt_2 may push artifacts but may not call the contest API. Claude performs
Git/API freshness, review, integration, and every submission decision.
