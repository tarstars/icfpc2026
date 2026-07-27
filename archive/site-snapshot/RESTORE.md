# Restoring the ICFPC 2026 site snapshot

You are looking at an offline copy of the ICFP Programming Contest 2026 website
(`https://icfpcontest2026.com/`), taken on **2026-07-27 around 08:37–09:00 UTC**,
while the contest was still running. It ended at 12:00 UTC the same day. Our team
was **wheezards**. Nothing here talks to the network; the original server is
presumably gone by the time you read this.

## Serve it

```bash
cd archive/site-snapshot
python3 serve.py            # -> http://localhost:8000/
python3 serve.py 9000       # if 8000 is taken
```

Requires nothing but Python 3 from the standard library. It binds to
`127.0.0.1` only.

`serve.py` does two things a plain static server cannot, and both are needed:

1. **SPA fallback.** The site is a client-side-routed React app, so URLs like
   `/rules`, `/standings/tcp` and `/problems/snake/` are not files. Any path
   that is not a real file is answered with `site/index.html` and the JS router
   takes it from there.
2. **API replay.** It answers the *public* contest API under `/api/v1/` out of
   the JSON captured in `api/`, `problems/` and `standings/`. This is what makes
   the standings tables and the problem statements actually render, instead of
   spinning forever.

### If you insist on `python3 -m http.server`

```bash
cd archive/site-snapshot/site
python3 -m http.server 8000
```

The prose pages work (`/rules/`, `/textbook/`, `/grading/`, `/language-reference/`,
`/editor-help/`, `/api-help/`, `/split/`, `/editor/` — note the **trailing
slashes**; a copy of `index.html` was materialised in each of those directories
for exactly this case). Anything data-driven — standings, problem statements,
problem sets — will render an empty shell, because there is no API replay. Use
`serve.py`.

### `file://` does not work for the site

Browsers refuse to load ES modules and to instantiate WebAssembly over
`file://`, and the whole app is both. `archive/site-snapshot/index.html` (the
landing page one level up from `site/`) is deliberately plain HTML with relative
links, so *that* one opens fine from `file://` and gets you to all the JSON.

## What works offline

Verified with headless Chromium against `serve.py`: zero page errors and zero
failed requests on every page below.

| Page | State |
| --- | --- |
| `/` home, `/rules`, `/textbook`, `/grading`, `/language-reference`, `/editor-help`, `/api-help`, `/documentation`, `/split` | Fully rendered. All the prose is compiled into the JS bundles, so it is genuinely captured, not proxied. |
| `/standings` | Full overall leaderboard, 268 teams, 16 graded problems. |
| `/standings/<slug>` | Full per-problem table for all 16 graded problems, e.g. `/standings/tcp` shows 110 teams. |
| `/problems/<slug>/` | Statement, I/O spec, scoring, public test data, for all 20 problems. |
| `/editor` | **The littleman VM runs.** `wasm_exec.js` + `littleman.wasm` load and instantiate; `window.littlemanWasm` exposes `newSession, load, step, stepN, back, reset, validOps, analyze, route, flow, structuralGlyphs`. You can write and step programs locally. |
| `/standings/problems` | The per-problem standings index, all 16 linked. |
| `/problem-sets` | All 20 problems across the four semesters. Every one reads *"not attempted"* — that is the signed-out view, not a claim about what we solved. See `submissions/index.json` for what we actually did. |
| `/queue`, `/documentation` | Render, with the queue numbers frozen at 08:48 UTC. |

## What does not, and cannot

All of this needed the live server plus an authenticated team session. `serve.py`
answers these with HTTP 503 and a JSON note rather than hanging.

- **Sign-in** (`/login`, `/forgot-password`, `/reset-password`). The page renders
  but the form is inert; it also wanted Cloudflare Turnstile from the internet.
  `/api/auth/get-session` is stubbed to return `null`, i.e. "nobody is signed
  in", which is why the UI shows *Sign in* and no console errors.
- **Submitting.** Deliberately so. Nothing in this snapshot can POST a
  submission, and none was made while building it.
- **`/dashboard`, `/submissions`** — the site's own view of our submissions.
  The underlying data is captured instead, as flat JSON in `submissions/`.
- **`/admin`, `/admin-queue`** — never accessible to us in the first place.
- **Private test data** and the judge. Only the public tests exist here.
- **Other teams' team pages** (`/standings/team/<id>`). Only our own team's row
  was fetched, on purpose. Ours is at `api/standings-our-team.json`.
- **Anything live**: the standings stopped updating at 08:38 UTC on 2026-07-27,
  which was *before* the 10:00 UTC final freeze. They are therefore **not** the
  final results. See below.

## Where each piece came from

| Path | Source |
| --- | --- |
| `site/` | Fetched over HTTPS from `https://icfpcontest2026.com/`, one request at a time, ≥1.1 s apart. 52 requests, all HTTP 200, logged in `fetch-log.csv` with timestamps and sizes. `robots.txt` was checked first and disallows nothing. |
| `site/littleman.wasm`, `site/wasm_exec.js` | **Not re-downloaded.** Copied from `claude/official-sim/vendor/` in this repo, where they were saved on 2026-07-25 ~15:49 UTC. `wasm_exec.js` was byte-compared against the live URL and is identical; the 4 MB `.wasm` was left alone to save the server the bandwidth. |
| `engine/embed.js`, `engine/embed.pretty.js` | Same vendored directory. The pretty-printed one is for reading. Note the live site now ships a newer bundled embed at `site/assets/embed-DpaTuuw2.js` (215 KB vs the vendored 174 KB); the site uses that one, `engine/` is reference only. |
| `problems/*.json` | `GET /api/v1/public/problems/<slug>`, fetched 2026-07-27 ~08:50 UTC, all 20 problems. These supersede the repo's `data/small/problems/` copies from 2026-07-25, which were identical except that the server has since added an `uberStrict` boolean to 16 of them. Statement, `io`, `scoring`, `publicTestData`, `privateTestCount`, `tickCap`. |
| `problems/index.json` | `GET /api/v1/public/problems` — the list with UUIDs, slugs, problem sets, graded/practice status. |
| `standings/<slug>.json` | `GET /api/v1/standings/problems/<problem-uuid>`, one per graded problem, fetched 08:38:30–08:38:58 UTC. Each has a `_snapshot` block stamped with its own fetch time. **Beware:** that endpoint takes the *UUID*, never the slug — a slug returns an empty row list without erroring. |
| `standings/index.json` | Derived locally: per-problem metadata plus our own row, and our total. |
| `api/*.json` | Other public endpoints: overall leaderboard, contest clock, judge queue, `/split` docs, and our own team's standings detail. `api/index.json` lists each with its endpoint and fetch time. Whitespace normalised; values verbatim. |
| `submissions/**` | Copied from this repo's `submissions/`, the server's own JSON replies to our submissions. 105 files, 103 of which parse cleanly. |

Three submission files are not clean JSON and were kept verbatim anyway:
`brackets/alexey-brackets_08-submit.json` has poll chatter prefixed before the
JSON body, and `hello-world/hello_00-submit.json` and
`llm/llm_codex_00-submit.json` are empty. `submissions/index.json` records this.

**The submitted programs themselves are not here.** The `.man` sources live in
this repo under `submissions/<problem>/`, already in git, and were skipped to
keep the archive small.

## Standings caveat, read this before quoting any number

The contest clock at capture time (`api/clock.json`):

```
start        2026-07-24T12:00:00Z
lightningEnd 2026-07-25T12:00:00Z
finalFreeze  2026-07-27T10:00:00Z
end          2026-07-27T12:00:00Z
```

Standings were captured at **08:38 UTC**, so `frozen: false` — these are live,
pre-freeze numbers with about 3½ hours of contest left. They are a point-in-time
snapshot, **not** the final scoreboard. At that moment we were **rank 39 overall
with 24.67 points**, 16/16 problems fully passed, best placement rank 1 on
`triangle`.

## Reproducing or extending this

The tool used for the API side lives in this repo:

```bash
uv run icfpc-api --env-file ../icfpc2026/.env problems             # list, no key needed
uv run icfpc-api --env-file ../icfpc2026/.env problem <slug>       # takes the SLUG
uv run icfpc-api --env-file ../icfpc2026/.env standings <uuid>     # takes the UUID
```

Obviously this only worked while the server was up. The API key lives in that
`.env` file and appears nowhere in this snapshot — grep it if you doubt me.
