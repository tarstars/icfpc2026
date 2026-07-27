"""Working score frontier for chatgpt_2's final Sort hot-loop search.

This is deliberately a calculator, not release evidence.  The baseline ticks
are the accepted tarstars_sort_08 public ticks.  The scan-branch counts are a
working trace captured before the final-main resynchronization and must be
reproduced by a checked-in tracer before any candidate is submitted.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

BASELINE_BOX = 18
BASELINE_TICKS = [755, 617, 772, 544, 928, 2137, 5282]
RANK_FACTOR_TARGET = 1.026

# Working trace counts over the seven public workloads.
SCAN_BRANCH_COUNTS = {
    "positive_requeue": 250,
    "negative_new_minimum": 234,
    "zero_equal": 62,
}


@dataclass(frozen=True)
class Frontier:
    baseline_average_ticks: float
    baseline_score: float
    one_rank_target_score: float
    one_rank_max_average_ticks_at_box18: float
    projected_saved_ticks_total: int
    projected_average_ticks: float
    projected_score: float
    projected_factor: float
    projected_reduction_percent: float


def score(box: int, average_ticks: float) -> float:
    return box * box * average_ticks


def calculate(saved_ticks_per_negative_branch: int = 2) -> Frontier:
    average = sum(BASELINE_TICKS) / len(BASELINE_TICKS)
    baseline = score(BASELINE_BOX, average)
    target = baseline / RANK_FACTOR_TARGET
    saved_total = (
        SCAN_BRANCH_COUNTS["negative_new_minimum"]
        * saved_ticks_per_negative_branch
    )
    projected_average = average - saved_total / len(BASELINE_TICKS)
    projected = score(BASELINE_BOX, projected_average)
    return Frontier(
        baseline_average_ticks=average,
        baseline_score=baseline,
        one_rank_target_score=target,
        one_rank_max_average_ticks_at_box18=target / (BASELINE_BOX**2),
        projected_saved_ticks_total=saved_total,
        projected_average_ticks=projected_average,
        projected_score=projected,
        projected_factor=baseline / projected,
        projected_reduction_percent=(baseline - projected) / baseline * 100,
    )


if __name__ == "__main__":
    result = calculate()
    assert abs(result.baseline_score - 510_762.8571428571) < 1e-6
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
