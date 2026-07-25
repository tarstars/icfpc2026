"""Attach released contest problem specifications to the repository.

With explicit slugs, fetch those problems and refresh the complete released
problem index.  With no slugs, fetch only released problems that do not yet
have a local JSON file.  Every API response is fetched before any file is
changed, so a failed request cannot leave a partial release snapshot.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from icfpc_api.client import ContestApiClient

REPO_ROOT = Path(__file__).resolve().parents[1]
PROBLEM_ROOT = REPO_ROOT / "data" / "small" / "problems"
SAFE_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch released problem specs and refresh index.json."
    )
    parser.add_argument(
        "slugs",
        nargs="*",
        help="released problem slugs; omit to attach every locally missing problem",
    )
    return parser.parse_args()


def _compact_json(document: Any) -> str:
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n"
    )


def main() -> int:
    args = _parse_args()
    with ContestApiClient() as client:
        index = client.list_problems()
        released = {
            str(problem["slug"]): problem
            for problem in index
            if isinstance(problem, dict) and isinstance(problem.get("slug"), str)
        }
        requested = list(dict.fromkeys(args.slugs))
        if not requested:
            requested = [
                slug
                for slug in released
                if not (PROBLEM_ROOT / f"{slug}.json").exists()
            ]

        unknown = sorted(set(requested) - released.keys())
        if unknown:
            raise SystemExit(f"not released: {', '.join(unknown)}")
        unsafe = sorted(slug for slug in requested if not SAFE_SLUG.fullmatch(slug))
        if unsafe:
            raise SystemExit(f"unsafe slug: {', '.join(unsafe)}")

        documents = {slug: client.get_problem(slug) for slug in requested}

    for slug, document in documents.items():
        if document.get("slug") != slug:
            raise SystemExit(
                f"API slug mismatch for {slug!r}: {document.get('slug')!r}"
            )

    PROBLEM_ROOT.mkdir(parents=True, exist_ok=True)
    for slug, document in documents.items():
        (PROBLEM_ROOT / f"{slug}.json").write_text(
            _compact_json(document),
            encoding="utf-8",
        )
    (PROBLEM_ROOT / "index.json").write_text(
        _compact_json(index),
        encoding="utf-8",
    )

    print(f"attached {len(documents)} problem(s): {', '.join(documents) or 'none'}")
    print(f"indexed {len(index)} released problem(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
