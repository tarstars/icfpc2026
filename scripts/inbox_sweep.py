"""Sweep EVERY peer message namespace across all remote refs; flag unacked mail.

The two-agent protocol defines message ownership, immutability and which
kinds require acknowledgement -- but no reading cadence. On 2026-07-26 an
ack-required message (LLM 14/28, with a review request) sat unread for three
hours while both agents worked the same problem. This tool makes the sweep
one command so a cadence can actually be kept:

    uv run python scripts/inbox_sweep.py          # report
    uv run python scripts/inbox_sweep.py --mark   # advance the watermark

A message may exist only on a codex branch (the protocol says to inspect the
peer's remote ref after fetch), so the union over origin/main and every
origin/agent/codex-* ref is scanned, not the working tree.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
WATERMARK = REPO / "claude" / "inbox-watermark.txt"
ME = "claude"
NAMESPACE = "coordination/messages/"   # every peer under here, not just codex


def _git(*args: str) -> str:
    out = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    return out.stdout


def peer_refs() -> list[str]:
    """Every remote ref, not just Codex's.

    Hardcoding the peer to "codex" hid a THIRD agent (alexey) working
    directly on main for a full day, including a message addressed to me
    requiring acknowledgement. Sweep everything; discover peers from the
    tree rather than from an assumption.
    """
    refs = ["origin/main"]
    for line in _git("branch", "-r").splitlines():
        ref = line.strip()
        if ref and "->" not in ref and ref != "origin/main":
            refs.append(ref)
    return refs


def sweep() -> list[dict]:
    seen: dict[str, dict] = {}
    for ref in peer_refs():
        for path in _git("ls-tree", "-r", "--name-only", ref, NAMESPACE).splitlines():
            name = path.rsplit("/", 1)[-1]
            sender = path.split("/")[2] if path.count("/") > 2 else "?"
            if sender == ME:                      # my own outbox
                continue
            if not name.endswith(".md") or name == "README.md" or name in seen:
                continue
            body = _git("show", f"{ref}:{path}")
            ack = "requires acknowledgement: yes" in body.lower()
            seen[name] = {"name": name, "ref": ref, "ack_required": ack, "from": sender}
    # was each ack-required message answered from our side (any ref)?
    ours = ""
    for ref in ["origin/agent/claude", "HEAD"]:
        for path in _git("ls-tree", "-r", "--name-only", ref,
                         "coordination/messages/claude/").splitlines():
            ours += _git("show", f"{ref}:{path}")
    for msg in seen.values():
        # Match by the UTC timestamp stem, not the full filename: it is unique
        # per message, and acks legitimately abbreviate long names (an ack that
        # wrote "20260725T141300Z-...-review.md" must still count).
        stem = msg["name"].split("-", 1)[0]
        msg["acked"] = (not msg["ack_required"]) or (stem in ours)
    return sorted(seen.values(), key=lambda m: m["name"])


def main() -> int:
    _git("fetch", "-q", "origin")
    messages = sweep()
    mark = WATERMARK.read_text().strip() if WATERMARK.exists() else ""
    fresh = [m for m in messages if m["name"] > mark]
    unacked = [m for m in messages if not m["acked"]]
    print(f"peer messages: {len(messages)} total, {len(fresh)} new since watermark")
    for m in fresh:
        tag = " [ACK REQUIRED]" if m["ack_required"] else ""
        print(f"  NEW [{m['from']}] {m['name']}  ({m['ref']}){tag}")
    for m in unacked:
        print(f"  !! UNACKED [{m['from']}]: {m['name']}  ({m['ref']})")
    if "--mark" in sys.argv and messages:
        WATERMARK.write_text(messages[-1]["name"] + "\n")
        print(f"watermark -> {messages[-1]['name']}")
    return 1 if unacked else 0


if __name__ == "__main__":
    sys.exit(main())
