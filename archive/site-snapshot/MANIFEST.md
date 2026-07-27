# ICFPC 2026 site snapshot

Start time (UTC): 2026-07-27T08:37:35Z
End time (UTC):   2026-07-27T09:00Z (approx)
Total size: 7.7 MB, 231 files. Contest ended 2026-07-27T12:00:00Z.

Purpose: an offline, self-contained copy of the ICFP Contest 2026 website plus our
own contest data (team **wheezards**), so it can be restored and browsed locally
after the contest server goes away. `RESTORE.md` says how to serve it.

**Fetch policy actually followed:** one request at a time, never less than 1.1 s
apart, no retries. `robots.txt` was read first — it disallows nothing. 52 requests
to the static site (all HTTP 200, ~955 KB, logged in `fetch-log.csv`) plus 43
requests to the public API. Nothing was submitted. No authenticated endpoint, no
other team's credentials, and no other team's submissions were touched. The API
key and `.env` contents were never printed, echoed, or copied — verified by grep
over the finished snapshot.

## Contents

| Path | What | Files |
| --- | --- | --- |
| `index.html` | Plain-HTML landing page; works from `file://` | 1 |
| `serve.py` | Local server: SPA fallback + replay of the captured public API | 1 |
| `RESTORE.md` | How to serve it, what works, what does not, provenance table | 1 |
| `fetch-log.csv` | Every HTTP request to the static site: time, status, bytes | 1 |
| `site/` | The website: HTML, 37 JS chunks, CSS, 4 fonts, icons, `littleman.wasm` | 73 |
| `engine/` | Vendored engine embed JS (reference/pretty-printed) | 2 |
| `problems/` | All 20 problem statements + public tests, + `index.json` with UUIDs | 21 |
| `standings/` | Frozen standings for all 16 graded problems, + `index.json` | 17 |
| `api/` | Other public API captures + `index.json` describing each | 7 |
| `submissions/` | Our 105 submission response records, + `index.json` | 106 |

## Log

- 08:37:35Z — created `archive/site-snapshot/`, started MANIFEST.
- 08:37:56Z — `GET /api/v1/public/problems` → `api/problems.json`. 20 problems:
  4 practice (ungraded), 16 graded across Semesters 1–4.
- 08:38:17Z — `GET /api/v1/public/contest-clock` → `api/clock.json`.
  start 07-24T12:00Z, lightningEnd 07-25T12:00Z, finalFreeze 07-27T10:00Z,
  end 07-27T12:00Z, `standingsFrozen: false`, `submissionsClosed: false`.
- 08:38:30Z–08:38:58Z — `GET /api/v1/standings/problems/<uuid>` for each of the
  16 graded problems, 1.2 s apart, all 200, 1880 rows total. Saved to
  `standings/<slug>.json`, each stamped with a `_snapshot` block carrying its own
  `fetchedAtUtc`, the problem UUID and a note that the value is a live pre-freeze
  reading. The endpoint takes the **UUID**; a slug returns an empty row list.
- 08:39:22Z — probed `https://icfpcontest2026.com/` and `robots.txt`. Vite SPA,
  Cloudflare-fronted, `Disallow:` empty.
- 08:39:52Z–08:41:51Z — mirrored the static site with a self-written rate-limited
  fetcher (not `wget --mirror`, see below): `index.html`, the 3 entry assets, all
  37 lazily-loaded JS chunks named in the bundle's `__vite__mapDeps` table, the
  CSS, 4 Lato `.woff2` fonts, `favicon.svg`, `favicon.ico`, `apple-touch-icon.png`,
  `og.png`, `ascii.txt`, `robots.txt`. A second pass re-scanned every downloaded
  chunk for further references and found none missing — the asset graph is closed.
- 08:41Z — `site.webmanifest` and `sitemap.xml` returned HTTP 200 but with the
  SPA's `index.html` body; they do not exist. Deleted, recorded here.
- 08:42Z — engine provenance check. `HEAD /littleman.wasm` and `/wasm_exec.js`
  gave ETags that do **not** match the MD5 of our vendored copies, so
  `wasm_exec.js` (17 KB) was downloaded and byte-compared: **identical**. The
  ETags are therefore not content MD5s and prove nothing. Conclusion: the vendored
  copies are current, and the 4 MB `littleman.wasm` was **not** re-downloaded, as
  instructed.
- 08:44Z — copied in from the repo: `claude/official-sim/vendor/littleman.wasm`
  and `wasm_exec.js` → `site/` (the paths the site expects); `embed.js` and
  `embed.pretty.js` → `engine/`. All four were saved 2026-07-25 ~15:49 UTC.
  Note: the live site now serves a *newer* bundled embed as
  `site/assets/embed-DpaTuuw2.js` (215 KB) than the vendored `embed.js` (174 KB);
  the site uses the bundled one, `engine/` is reference only.
- 08:44Z — copied `data/small/problems/*.json` in, then spot-checked two against
  the live API: `pathfinder` identical, `tcp` differed by an added `uberStrict`
  field. Since the divergence was real, all 20 statements were **re-fetched**
  (08:49–08:50Z, one per 1.2 s) so the archive is current. This is a deliberate
  deviation from "copy them in rather than re-download": the local copies were
  two days stale on a scoring-relevant flag. Delta was `uberStrict` on 16 of 20;
  nothing else changed.
- 08:46Z — copied 105 `submissions/**/*-submit.json` records; `.man` sources
  skipped as instructed (they are in git). Three files are not clean JSON and were
  kept verbatim: `brackets/alexey-brackets_08-submit.json` has poll chatter before
  the JSON body; `hello-world/hello_00-submit.json` and
  `llm/llm_codex_00-submit.json` are empty. Recorded in `submissions/index.json`.
- 08:46Z — read the JS bundle to recover the SPA's route table (25 routes) and its
  public API surface, so the offline server could replay it. Public endpoints in
  use: `public/problems`, `public/problems/:slug`, `public/contest-clock`,
  `public/queue`, `standings`, `standings/problems/:problemId`,
  `standings/teams/:teamId`, `split/docs`.
- 08:48Z — fetched the four public endpoints we had not yet captured:
  `/api/v1/standings` (overall leaderboard, 268 teams), `/api/v1/public/queue`,
  `/api/v1/split/docs`, and `/api/v1/standings/teams/<our own teamId>`. Only our
  own team page was fetched; no other team's was.
- 08:52Z–09:00Z — wrote `serve.py`, materialised route shells, verified with
  headless Chromium (see below), wrote `index.html`, `RESTORE.md`, this manifest.

## Verification

Rendered 20 routes under `serve.py` with headless Chromium: **zero page errors,
zero failed requests** on every one.

- `/standings` renders the full 268-team leaderboard; `/standings/tcp` renders
  110 ranked teams. Real data, from the frozen JSON.
- `/problems/<slug>/` renders statements for all 20 problems.
- `/editor` **boots the WebAssembly engine**: `wasm_exec.js` and `littleman.wasm`
  both load and instantiate, and `window.littlemanWasm` exposes `newSession`,
  `closeSession`, `load`, `step`, `stepN`, `back`, `reset`, `validOps`, `analyze`,
  `route`, `flow`, `structuralGlyphs`. The simulator works offline.
- Prose pages (`/rules`, `/textbook`, `/grading`, `/language-reference`,
  `/editor-help`, `/api-help`, `/split`) render in full — their content is
  compiled into the JS bundles, so it is genuinely captured.

## Not captured, and why

Everything below required the live server plus an authenticated team session.
`serve.py` answers each with HTTP 503 and a JSON explanation rather than hanging.

- **Sign-in / session** (`/login`, `/forgot-password`, `/reset-password`). The
  page renders but is inert; it also loads Cloudflare Turnstile from the internet,
  which no offline copy can satisfy. `/api/auth/get-session` is stubbed to `null`
  ("not signed in"), which is both true and what keeps the console clean.
- **Submitting.** Deliberately impossible here; none was made during this work.
- **`/dashboard`, `/submissions`** — the site's own view of our submissions. The
  data itself is captured as flat JSON in `submissions/` instead.
- **`/admin`, `/admin-queue`** — never accessible to us.
- **Private test data** and the judge. Public tests only.
- **Other teams' pages** (`/standings/team/<id>`) — not fetched, on principle.
- **The submitted `.man` programs** — skipped as instructed; already in git under
  the repo's `submissions/`.
- **`site.webmanifest`, `sitemap.xml`** — do not exist on the server.
- Nothing was omitted for size. 7.7 MB against a ~200 MB budget.

## Standings caveat

Captured at 08:38 UTC, i.e. **before** the 10:00 UTC final freeze and 3½ hours
before the contest ended, with `frozen: false`. These are live pre-freeze numbers
and are **not** the final results. At that moment: **wheezards, rank 39 overall,
24.67 points, 16/16 problems fully passed**, best placement rank 1 on `triangle`.
Top of the board was `DIgital Experts` at 31.76.

## Tooling note

`wget --mirror` was available but not used: the site is a Vite SPA, so every URL
returns the same `index.html` (verified against 21 different paths — all byte-identical
to `/`), and `wget` cannot see the asset graph, which lives inside the JS bundle's
`__vite__mapDeps` table. A small purpose-built fetcher was used instead: strictly
serial, ≥1.1 s between requests, one attempt per URL, full CSV log. Links were
**not** rewritten — the site's absolute `/assets/...` paths are already correct
when served from a document root, and rewriting them for `file://` would be
pointless because browsers block ES modules and WebAssembly over `file://`
regardless. The `file://`-browsable entry point is the plain `index.html` at the
snapshot root.
