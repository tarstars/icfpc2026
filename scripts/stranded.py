"""Find finished-but-unsubmitted artifacts across every branch.

Codex ran out of tokens holding 20+ working branches. Anything they built
and did not submit is points sitting on the floor, and nobody was going to
find it by hand with hours left. This walks every ref, collects every `.man`
under `submissions/`, and reports the ones whose geometry beats what is
live.

It deliberately does NOT judge or submit. Footprint is cheap to compute from
the file; ticks are not, and a smaller box can still be slower overall. So
this narrows dozens of branches to a handful worth a real judge run, and the
gate decides after that.

Score is `max(width, height)^2 * avgTicks`, so the box term is the SQUARE of
the larger side -- which is why a candidate one row narrower is worth
checking even when its area is bigger.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import subprocess
import sys


def refs() -> list[str]:
    out = subprocess.run(["git", "for-each-ref", "--format=%(refname:short)",
                          "refs/remotes", "refs/heads"],
                         capture_output=True, text=True, timeout=120)
    return [r for r in out.stdout.split() if not r.endswith("/HEAD")]


def files_in(ref: str) -> list[str]:
    out = subprocess.run(["git", "ls-tree", "-r", "--name-only", ref],
                         capture_output=True, text=True, timeout=120)
    return [f for f in out.stdout.splitlines()
            if f.startswith("submissions/") and f.endswith(".man")]


def read(ref: str, path: str) -> str | None:
    out = subprocess.run(["git", "show", f"{ref}:{path}"],
                         capture_output=True, text=True, timeout=120)
    return out.stdout if out.returncode == 0 else None


def geometry(text: str) -> tuple[int, int]:
    """Width and height as the server sees them: trailing blank lines are
    not part of the machine."""
    lines = text.split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    return max((len(line) for line in lines), default=0), len(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem", help="restrict to one submissions/ subdir")
    parser.add_argument("--top", type=int, default=3,
                        help="best N candidates per problem")
    args = parser.parse_args()

    # problem -> box -> list of (ref, path, submitted?)
    found: dict[str, dict] = collections.defaultdict(dict)
    all_refs = refs()
    print(f"scanning {len(all_refs)} refs ...", file=sys.stderr)

    for ref in all_refs:
        for path in files_in(ref):
            parts = path.split("/")
            if len(parts) < 3:
                continue
            problem = parts[1]
            if args.problem and problem != args.problem:
                continue
            text = read(ref, path)
            if not text:
                continue
            width, height = geometry(text)
            box = max(width, height)
            key = (path, box)
            if key not in found[problem]:
                found[problem][key] = {
                    "refs": [], "width": width, "height": height, "box": box}
            found[problem][key]["refs"].append(ref)

    # a sibling `-submit.json` anywhere means somebody already sent it
    submitted = set()
    for ref in all_refs:
        out = subprocess.run(["git", "ls-tree", "-r", "--name-only", ref],
                             capture_output=True, text=True, timeout=120)
        for line in out.stdout.splitlines():
            if line.endswith("-submit.json"):
                submitted.add(line.replace("-submit.json", ".man"))

    for problem in sorted(found):
        entries = sorted(found[problem].items(), key=lambda kv: kv[1]["box"])
        print(f"\n{problem}")
        for (path, _box), info in entries[:args.top]:
            mark = "sent" if path in submitted else "** NO SUBMIT RECORD **"
            where = info["refs"][0]
            more = f" (+{len(info['refs']) - 1} refs)" if len(info["refs"]) > 1 else ""
            print(f"   {info['width']:>4}x{info['height']:<4} box={info['box']:<5} "
                  f"{path.split('/')[-1]:34} {mark:24} {where}{more}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
