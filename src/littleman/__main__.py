"""CLI: judge a .man program against a problem's public tests.

Usage: python -m littleman <program.man> <problem-slug-or-json-path>
"""

import json
import sys
from pathlib import Path

from .judge import judge_problem

REPO = Path(__file__).resolve().parent.parent.parent
PROBLEMS = REPO / "data" / "small" / "problems"


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    program = Path(sys.argv[1]).read_text()
    spec = Path(sys.argv[2])
    if not spec.exists():
        spec = PROBLEMS / f"{sys.argv[2]}.json"
    problem = json.loads(spec.read_text())
    report = judge_problem(program, problem)
    print(f"problem:   {problem['slug']} ({problem['scoring']})")
    print(f"footprint: {report.footprint}")
    print(f"cases:     {report.cases_passed}/{report.cases_total} passed")
    for case, result in zip(problem["publicTestData"], report.case_results):
        mark = "PASS" if result.passed else f"FAIL ({result.reason})"
        print(f"  {case['name']:<40} {mark:<20} ticks={result.ticks}")
    if report.score != float("inf"):
        print(f"score:     {report.score:.1f}")
    sys.exit(0 if report.cases_passed == report.cases_total else 1)


if __name__ == "__main__":
    main()
