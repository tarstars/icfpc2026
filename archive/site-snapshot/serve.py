#!/usr/bin/env python3
"""Serve the offline ICFPC 2026 site snapshot.

    python3 serve.py            # http://localhost:8000/
    python3 serve.py 9000       # pick another port

Serves ./site as the document root and does two things a plain
`python3 -m http.server` cannot:

  1. SPA fallback -- the site is a client-side-routed single-page app, so any
     path that is not a real file (/rules, /standings/tcp, /problems/tcp/editor,
     ...) is answered with site/index.html and the JS router takes over.

  2. A read-only replay of the *public* contest API under /api/v1/, answered
     from the JSON captured in ../api and ../standings and ../problems. This is
     what makes the standings and problem pages actually render offline.

Everything else under /api/v1/ (login, submissions, dashboard, admin) returns
503 with a JSON note, because it needed the live server and a team API key.
Nothing here ever talks to the network.
"""

from __future__ import annotations

import json
import os
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")


def _load(*parts):
    path = os.path.join(ROOT, *parts)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


PROBLEMS = _load("api", "problems.json") or []
BY_SLUG = {p["slug"]: p for p in PROBLEMS}
BY_ID = {p["id"]: p for p in PROBLEMS}


def _standings_for(problem_id):
    p = BY_ID.get(problem_id) or BY_SLUG.get(problem_id)
    if p is None:
        return None
    doc = _load("standings", p["slug"] + ".json")
    if doc is None:
        return None
    doc = dict(doc)
    doc.pop("_snapshot", None)  # replay the payload as the server sent it
    return doc


def _problem(slug):
    doc = _load("problems", slug + ".json")
    if doc is None and slug in BY_ID:
        doc = _load("problems", BY_ID[slug]["slug"] + ".json")
    return doc


UNAVAILABLE = {
    "error": {
        "code": "offline_archive",
        "message": (
            "This endpoint is not part of the offline snapshot. It required the "
            "live contest server and an authenticated team session: sign-in, "
            "submissions, the dashboard, private test data, judging and admin. "
            "Only public read-only endpoints were archived."
        ),
    }
}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=SITE, **kw)

    # ---- helpers --------------------------------------------------------
    def _json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Offline-Archive", "icfpc2026 snapshot 2026-07-27")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _api(self, path):
        """Replay a captured public API response, or explain the gap."""
        # better-auth session probe: answer "nobody is signed in", which is the
        # truth offline and keeps the console clean.
        if path.rstrip("/") == "/api/auth/get-session":
            return self._json(None)
        m = re.fullmatch(r"/api/v1/(.*)", path)
        if not m:
            return self._json(UNAVAILABLE, 503)
        route = m.group(1).rstrip("/")

        if route == "public/problems":
            return self._json(PROBLEMS)
        if route == "public/contest-clock":
            return self._json(_load("api", "clock.json"))
        if route == "public/queue":
            return self._json(_load("api", "public-queue.json"))
        if route == "split/docs":
            return self._json(_load("api", "split-docs.json"))
        if route == "standings":
            return self._json(_load("api", "standings-overall.json"))

        m2 = re.fullmatch(r"public/problems/([^/]+)", route)
        if m2:
            doc = _problem(m2.group(1))
            return self._json(doc) if doc else self._json(
                {"error": {"code": "not_found", "message": "No such problem"}}, 404)

        m2 = re.fullmatch(r"standings/problems/([^/]+)", route)
        if m2:
            doc = _standings_for(m2.group(1))
            return self._json(doc) if doc else self._json(
                {"error": {"code": "not_found",
                           "message": "No archived standings for this problem "
                                      "(only the 16 graded problems were captured)"}}, 404)

        m2 = re.fullmatch(r"standings/teams/([^/]+)", route)
        if m2:
            doc = _load("api", "standings-our-team.json")
            if doc and doc.get("teamId") == m2.group(1):
                return self._json(doc)
            return self._json(
                {"error": {"code": "offline_archive",
                           "message": "Only our own team's standings row was archived. "
                                      "Other teams' detail pages were deliberately not fetched."}}, 503)

        return self._json(UNAVAILABLE, 503)

    # ---- request handling ----------------------------------------------
    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0].split("#")[0]
        if self.command == "POST":  # drain the body so the socket stays sane
            try:
                self.rfile.read(int(self.headers.get("Content-Length") or 0))
            except (ValueError, OSError):
                pass
        if path.startswith("/api/"):
            self._api(path)
            return
        if self.command == "POST":
            self._json(UNAVAILABLE, 503)
            return
        local = self.translate_path(path)
        if os.path.isdir(local):
            # Serve the shell in place; do NOT 301 to a trailing slash, because
            # the live site answered /rules and /rules/ alike and the client
            # router should see the URL the user actually asked for.
            if os.path.exists(os.path.join(local, "index.html")):
                self.path = path.rstrip("/") + "/index.html"
                return super().do_GET()
        elif os.path.exists(local):
            return super().do_GET()
        # Real 404 for assets, SPA fallback for everything else.
        if re.search(r"\.(js|css|wasm|woff2?|png|svg|ico|jpg|map|txt|json)$", path):
            self.send_error(404, "Not found in offline snapshot")
            return
        self.path = "/index.html"
        return super().do_GET()

    do_HEAD = do_GET
    do_POST = do_GET  # submissions etc. -> the 503 explanation above

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    if not os.path.isdir(SITE):
        sys.exit(f"missing {SITE} -- run this from the snapshot directory")
    print(f"ICFPC 2026 offline snapshot -> http://localhost:{port}/")
    print(f"  document root : {SITE}")
    print(f"  API replay    : {len(PROBLEMS)} problems, "
          f"{len([p for p in PROBLEMS if p['status'] == 'graded'])} graded standings")
    print("  Ctrl-C to stop.")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
