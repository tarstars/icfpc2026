"""Command-line tools for the ICFPC 2026 contest API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from .client import DEFAULT_BASE_URL, ContestApiClient

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = REPO_ROOT / ".env"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="icfpc-api",
        description=(
            "List and fetch contest problems, submit programs, and poll results. "
            "Successful results are JSON on stdout."
        ),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help=f"dotenv file (default: {DEFAULT_ENV_FILE})",
    )
    parser.add_argument(
        "--base-url",
        help=(
            "API base URL; defaults to ICFPC2026_API_BASE_URL or the official "
            "contest API"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="per-request timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="emit compact JSON instead of indented JSON",
    )

    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser(
        "problems",
        help="list released problems; no API key required",
    )

    problem = commands.add_parser(
        "problem",
        help="fetch one problem and its public tests; no API key required",
    )
    problem.add_argument("slug", help="problem slug, not problem ID")

    commands.add_parser(
        "clock",
        help="fetch live contest and scoreboard-freeze timing",
    )

    standings = commands.add_parser(
        "standings",
        help="fetch public standings for one graded problem",
    )
    standings.add_argument("problem_id", help="problem ID from `problems`")

    submission = commands.add_parser(
        "submission",
        help="fetch one submission owned by this team",
    )
    submission.add_argument("submission_id")

    wait = commands.add_parser(
        "wait",
        help="poll one submission until it reaches done or failed",
    )
    wait.add_argument("submission_id")
    wait.add_argument(
        "--poll-interval",
        type=float,
        default=2.5,
        help="seconds between polls (default: 2.5)",
    )
    wait.add_argument(
        "--wait-timeout",
        type=float,
        default=600.0,
        help="total polling timeout in seconds (default: 600)",
    )

    submit = commands.add_parser(
        "submit",
        help="create exactly one contest submission (external mutation)",
        description=(
            "Submit the exact UTF-8 contents of PROGRAM_FILE. This creates one "
            "contest submission and therefore requires --confirm."
        ),
    )
    submit.add_argument("problem_id", help="problem ID from `problems`, not slug")
    submit.add_argument("program_file", type=Path)
    submit.add_argument(
        "--confirm",
        action="store_true",
        help="required acknowledgment that this creates a contest submission",
    )
    submit.add_argument(
        "--wait",
        action="store_true",
        help="poll and print the terminal result after submitting",
    )
    submit.add_argument(
        "--poll-interval",
        type=float,
        default=2.5,
        help="seconds between polls with --wait (default: 2.5)",
    )
    submit.add_argument(
        "--wait-timeout",
        type=float,
        default=600.0,
        help="total polling timeout with --wait (default: 600)",
    )
    return parser


def _emit(document: Any, *, compact: bool) -> None:
    if compact:
        print(json.dumps(document, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True))


def _status_update(document: dict[str, Any]) -> None:
    status = document.get("status", "unknown")
    print(f"submission status: {status}", file=sys.stderr, flush=True)


def _run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> Any:
    load_dotenv(args.env_file, override=False)
    api_key = os.environ.get("ICFPC2026_API_KEY")
    base_url = (
        args.base_url or os.environ.get("ICFPC2026_API_BASE_URL") or DEFAULT_BASE_URL
    )

    with ContestApiClient(
        api_key=api_key,
        base_url=base_url,
        timeout=args.timeout,
    ) as client:
        if args.command == "problems":
            return client.list_problems()
        if args.command == "problem":
            return client.get_problem(args.slug)
        if args.command == "clock":
            return client.get_contest_clock()
        if args.command == "standings":
            return client.get_problem_standings(args.problem_id)
        if args.command == "submission":
            return client.get_submission(args.submission_id)
        if args.command == "wait":
            return client.wait_for_submission(
                args.submission_id,
                poll_interval=args.poll_interval,
                timeout=args.wait_timeout,
                on_update=_status_update,
            )
        if args.command == "submit":
            if not args.confirm:
                parser.error(
                    "submit creates an external contest action; pass --confirm"
                )
            try:
                program = args.program_file.read_bytes().decode("utf-8")
            except (OSError, UnicodeError) as error:
                parser.error(f"cannot read program file: {error}")
            result = client.submit(problem_id=args.problem_id, program=program)
            if not args.wait:
                return result
            submission_id = result.get("id")
            if not isinstance(submission_id, str) or not submission_id:
                raise RuntimeError("submission response did not contain an ID")
            _status_update(result)
            return client.wait_for_submission(
                submission_id,
                poll_interval=args.poll_interval,
                timeout=args.wait_timeout,
                on_update=_status_update,
            )
    raise AssertionError(f"unhandled command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        result = _run(args, parser)
    except (RuntimeError, TimeoutError, ValueError, httpx.HTTPError) as error:
        print(f"icfpc-api: {error}", file=sys.stderr)
        return 1
    _emit(result, compact=args.compact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
