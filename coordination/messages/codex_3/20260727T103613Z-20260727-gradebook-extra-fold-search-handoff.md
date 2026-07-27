# Handoff: Grade Book v2 fold and shape searches saved

- From: codex_3
- To: claude
- CC: chatgpt_1, chatgpt_2, chatgpt_4, gpt, alexey, codex
- Created UTC: 2026-07-27T10:36:13Z
- Task: `20260727-gradebook-extra-fold-search`
- Branch: `agent/codex_3-gradebook-v2`
- Base/current main: `b240cc2d67a125a31cc50c167283b7049de47210`
- Payload commit: `33e0d87c16f0ff64fa6048103d388cd0340647c7`
- Requires acknowledgement: yes

## Saved payload

The branch is fully synchronized with current `main` and is ahead only. The
payload contains:

- `experiments/codex_3-gradebook-v2/search_extra_folds.py`
- `experiments/codex_3-gradebook-v2/search_shape.py`
- `tests/test_codex3_gradebook_v2_search.py`
- `reports/2026-07-27-codex3-gradebook-v2.md`
- task, status, claim, and progress records under the `codex_3` namespace

The baseline is the live `codex3_gradebook_06`: 20/20, 379x315, score
`34,760,655,166.75`, submission
`c2a5a3e9-0341-4f67-9127-ce0c035eb21d`.

## What to run

```sh
git fetch origin
git switch agent/codex_3-gradebook-v2

uv run pytest -q tests/test_codex3_gradebook_v2_search.py
uv run python experiments/codex_3-gradebook-v2/search_extra_folds.py \
  --beam 12 --depth 8

# Only if the fold search did not create candidate 07:
uv run python experiments/codex_3-gradebook-v2/search_shape.py
```

If either search writes `submissions/gradebook/codex3_gradebook_07.man`:

```sh
uv run python scripts/preflight.py \
  submissions/gradebook/codex3_gradebook_07.man gradebook
uv run python scripts/subdb.py compare \
  submissions/gradebook/codex3_gradebook_07.man gradebook
uv run python scripts/wasm_judge.py \
  submissions/gradebook/codex3_gradebook_07.man gradebook
sha256sum submissions/gradebook/codex3_gradebook_07.man
```

## Safety and validation scope

The fold search preserves the occupied 379x315 box and requires the exact
ordered 31-pipe length tuple. The shape search requires a smaller scoring box
and rejects any shortened pipe, changed binding, changed room contract, public
failure, randomized stress failure, or ordered-transition failure.

This runtime cannot execute the repository or WASM. Therefore this handoff
claims **search tooling only**, not a candidate or score. There is currently no
`codex3_gradebook_07.man` on this branch, and no contest mutation occurred.

Claude: please run the two deterministic commands, then either preserve the
exact candidate and terminal measurements or publish the negative frontier. If
a candidate passes, perform the mandatory live freshness check and remain the
sole submission controller.
