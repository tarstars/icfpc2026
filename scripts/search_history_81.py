"""Search the joint History dictionary/lookup frontier for an 81-square fit."""

from __future__ import annotations

import argparse
import collections
import json
import math
import random
import time

from littleman.history_82 import TOKENS
from littleman.history_compact import _item_width, _token_word
from littleman.history_pack import expected_text

LIMIT = (1 << 63) - 1
TARGET_SYMBOLS = 1_755
TARGET_LOOKUP = 450
LOW_LOOKUP_TOKENS = (
    ' "',
    " C",
    " J",
    " M",
    " S",
    " and ",
    " for ",
    '" (',
    "); ",
    "); 20",
    ", ",
    ", S",
    ", USA",
    "199",
    ": ",
    "; 20",
    "Haskell",
    "a ",
    "act",
    "al",
    "am",
    "an",
    "ap",
    "ar",
    "at",
    "co",
    "e ",
    "ed ",
    "el",
    "en",
    "er",
    "es",
    "gh",
    "ic",
    "id",
    "im",
    "in",
    "ing ",
    "io",
    "ir",
    "is",
    "it",
    "la",
    "le",
    "on",
    "on Peyt",
    "or",
    "re",
    "s ",
    's" (',
    "st",
    "t ",
    "th",
    "tion",
    "un",
    "ur",
)
FRONTIER_TOKENS = (
    ' "',
    " C",
    " J",
    " M",
    " S",
    " and ",
    " for ",
    '" (',
    "); ",
    "); 20",
    ", ",
    ", S",
    ", USA",
    "199",
    ": ",
    "; 20",
    'Canada "',
    "Haskell",
    "a ",
    "al",
    "am",
    "an",
    "ap",
    "ar",
    "at",
    "co",
    "e ",
    "ed ",
    "el",
    "en",
    "er",
    "es",
    "gh",
    "ic",
    "id",
    "im",
    "in",
    "ing ",
    "io",
    "ir",
    "is",
    "it",
    "la",
    "le",
    "on",
    "on Peyt",
    "or",
    "re",
    "s ",
    's" (',
    "st",
    "t ",
    "th",
    "tion",
    "un",
    "ur",
)


def parser_safe(value: int) -> bool:
    return value <= LIMIT and int(str(value)[::-1]) <= LIMIT


def lookup_cost(alphabet: str, tokens: list[str]) -> int:
    widths = [_item_width(ord(char)) for char in alphabet]
    widths.extend(_item_width(_token_word(token)) for token in tokens)
    widths.extend([2] * (56 - len(tokens)))
    smallest = min(widths)
    widths.remove(smallest)
    widths.sort(reverse=True)
    return smallest + sum(widths[::2])


def build_candidates(text: str, max_len: int) -> tuple[list[str], list[list[int]]]:
    counts: collections.Counter[str] = collections.Counter()
    for length in range(2, max_len + 1):
        counts.update(
            text[start : start + length] for start in range(len(text) - length + 1)
        )
    candidates = [
        token
        for token, count in counts.items()
        if count >= 2 and parser_safe(_token_word(token))
    ]
    candidates.sort(
        key=lambda token: (
            -counts[token] * (len(token) - 1),
            _item_width(_token_word(token)),
            token,
        )
    )
    index = {token: candidate for candidate, token in enumerate(candidates)}
    matches: list[list[int]] = [[] for _ in text]
    for token, candidate in index.items():
        start = text.find(token)
        while start >= 0:
            matches[start].append(candidate)
            start = text.find(token, start + 1)
    return candidates, matches


def token_count(
    text: str,
    candidates: list[str],
    matches: list[list[int]],
    selected: set[int],
) -> int:
    cost = [0] * (len(text) + 1)
    for position in range(len(text) - 1, -1, -1):
        best = 1 + cost[position + 1]
        for candidate in matches[position]:
            if candidate in selected:
                best = min(best, 1 + cost[position + len(candidates[candidate])])
        cost[position] = best
    return cost[0]


def energy(symbols: int, lookup: int, weight: float) -> float:
    return symbols + weight * lookup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=200_000)
    parser.add_argument("--seed", type=int, default=20260727)
    parser.add_argument("--max-len", type=int, default=8)
    parser.add_argument("--weight", type=float, default=2.0)
    parser.add_argument(
        "--start",
        choices=("live", "low-lookup", "frontier"),
        default="live",
    )
    args = parser.parse_args()

    text = expected_text()
    alphabet = "".join(sorted(set(text)))
    candidates, matches = build_candidates(text, args.max_len)
    candidate_index = {token: index for index, token in enumerate(candidates)}
    initial_tokens = {
        "live": TOKENS,
        "low-lookup": LOW_LOOKUP_TOKENS,
        "frontier": FRONTIER_TOKENS,
    }[args.start]
    selected = {candidate_index[token] for token in initial_tokens}
    rng = random.Random(args.seed)

    symbols = token_count(text, candidates, matches, selected)
    lookup = lookup_cost(alphabet, [candidates[index] for index in selected])
    current = energy(symbols, lookup, args.weight)
    best = (symbols, lookup, sorted(candidates[index] for index in selected))
    started = time.monotonic()

    for step in range(args.steps):
        removed = rng.choice(tuple(selected))
        pool_limit = min(len(candidates), 512 + step // 100)
        added = rng.randrange(pool_limit)
        if added in selected:
            continue
        selected.remove(removed)
        selected.add(added)
        proposed_symbols = token_count(text, candidates, matches, selected)
        proposed_lookup = lookup_cost(
            alphabet, [candidates[index] for index in selected]
        )
        proposed = energy(proposed_symbols, proposed_lookup, args.weight)
        temperature = max(0.02, 4.0 * (1.0 - step / args.steps))
        accept = proposed <= current or rng.random() < math.exp(
            (current - proposed) / temperature
        )
        if accept:
            symbols, lookup, current = proposed_symbols, proposed_lookup, proposed
        else:
            selected.remove(added)
            selected.add(removed)

        key = (
            max(symbols - TARGET_SYMBOLS, 0) + max(lookup - TARGET_LOOKUP, 0),
            symbols,
            lookup,
        )
        best_key = (
            max(best[0] - TARGET_SYMBOLS, 0) + max(best[1] - TARGET_LOOKUP, 0),
            best[0],
            best[1],
        )
        if key < best_key:
            best = (symbols, lookup, sorted(candidates[index] for index in selected))
            print(json.dumps({"step": step, "symbols": symbols, "lookup": lookup}))
        if symbols <= TARGET_SYMBOLS and lookup <= TARGET_LOOKUP:
            break

    print(
        json.dumps(
            {
                "symbols": best[0],
                "lookup": best[1],
                "elapsed": time.monotonic() - started,
                "tokens": best[2],
            }
        )
    )


if __name__ == "__main__":
    main()
