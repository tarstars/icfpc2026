"""History tokenizer scheme experiments (n-gram / escape / context-class variants).

Measurement-only module: builds alternative tokenizations of the history text
(see history_pack.py for the baseline encoder) and reports data_cells,
table_cells, and total_cells for each scheme so they can be compared against
the baseline from history_pack.build() (4,242 data + 525 table = 4,767).

Two independent schemes live here, both built on top of history_pack's
generic, already-tested primitives (expected_text, choose_tokens, tokenise,
untokenise, pack, unpack, word_cells, symbols_per_word, LIMIT):

  * Scheme A - escape the rare tail: 11 characters occur <= 3 times each (25
    occurrences total, not the 31 originally guessed) and gate the alphabet
    at 71, capping token slots at 128 - 71 = 57. Replacing each rare
    occurrence with an ESCAPE symbol + a stand-in index shrinks the alphabet
    to 61 (60 remaining characters + ESCAPE) and raises the slot budget to
    67, at the cost of +25 symbols and a small table recording which 11 of
    the master 71 characters are rare (must be packed against the master
    alphabet, radix 71 - packing the rare list against its *own* induced
    alphabet is a degenerate no-op, since a short sorted list of distinct
    symbols packed over its own alphabet always yields the identity sequence
    0..n-1 and stores no information about which characters they actually
    are).

  * Scheme C - order-1 with grouped contexts: the 71 characters are bucketed
    into K context classes; the class of the *previous* character (already
    decoded, so always known exactly) selects which of K independent
    (local-alphabet + token-dictionary) codebooks interprets the next
    symbol. All K codebooks share one global radix (128, so 9 symbols/word,
    21 cells/word as in the baseline) - contexts with a smaller local
    alphabet simply get more of that shared id space for their own tokens.
    Every context's token dictionary is chosen by a context-restricted
    greedy substring search (`choose_tokens_ctx`), then the *number* of
    tokens kept per context is tuned (coordinate descent over per-context
    caps) because table cost, not data cost, is what makes this scheme
    marginal: a context's own token table must be paid for in cells the
    same way the baseline's single dictionary is.
"""

from __future__ import annotations

import collections

from littleman import history_pack as hp

# ---------------------------------------------------------------------------
# Scheme A: escape the rare tail
# ---------------------------------------------------------------------------

ESCAPE = "\x01"  # sentinel: absent from the history text and from hp.SEP


def rare_characters(text: str, max_count: int = 3) -> list[str]:
    """Characters occurring at most `max_count` times in `text`, sorted."""
    counts = collections.Counter(text)
    return sorted(ch for ch, n in counts.items() if n <= max_count)


def escape_text(text: str, rare: list[str]) -> tuple[str, list[str]]:
    """Replace each rare character with ESCAPE + a stand-in character drawn
    from the reduced (non-rare) alphabet.

    Returns (transformed, standins) where standins[r] means "rare[r]"
    whenever it is the symbol immediately following ESCAPE. The stand-ins
    are just the first len(rare) characters of the reduced alphabet reused
    contextually - they cost no extra alphabet slots because their normal
    (non-escaped) meaning is unchanged everywhere else.
    """
    rare_set = set(rare)
    reduced_alphabet = sorted(set(text) - rare_set)
    standins = reduced_alphabet[:len(rare)]
    rare_to_standin = dict(zip(rare, standins))
    out: list[str] = []
    for ch in text:
        if ch in rare_set:
            out.append(ESCAPE)
            out.append(rare_to_standin[ch])
        else:
            out.append(ch)
    return "".join(out), standins


def unescape_text(text: str, rare: list[str], standins: list[str]) -> str:
    """Inverse of escape_text: ESCAPE + stand-in -> the original rare char."""
    standin_to_rare = dict(zip(standins, rare))
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == ESCAPE:
            out.append(standin_to_rare[text[i + 1]])
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def build_scheme_a(text: str | None = None, count: int | None = None) -> dict:
    """The escape-the-rare-tail encoding.

    `count` is the token count for the (61-character-alphabet) dictionary;
    defaults to the maximum slot budget (128 - alphabet size = 67).
    """
    text = hp.expected_text() if text is None else text
    master_alphabet = sorted(set(text))
    rare = rare_characters(text)
    transformed, standins = escape_text(text, rare)
    alphabet = sorted(set(transformed))
    max_tokens = 128 - len(alphabet)
    token_count = max_tokens if count is None else count

    tokens = hp.choose_tokens(transformed, token_count)
    radix = len(alphabet) + len(tokens)
    ids = hp.tokenise(transformed, tokens)
    words = hp.pack(ids, radix)
    data_cells = len(words) * hp.word_cells(radix)

    # Dictionary table: identical convention to history_pack.build().
    table_text = hp.SEP.join(tokens)
    table_alpha = sorted(set(table_text))
    table_radix = len(table_alpha)
    table_index = {ch: i for i, ch in enumerate(table_alpha)}
    table_words = hp.pack([table_index[ch] for ch in table_text], table_radix)
    dict_table_cells = len(table_words) * hp.word_cells(table_radix)

    # Tiny rare-character table: which 11 of the master 71 characters are
    # rare, in the fixed order that defines the stand-in mapping. This MUST
    # be packed against the master alphabet (not against `rare` itself) or
    # it stores no information - see the module docstring.
    master_index = {ch: i for i, ch in enumerate(master_alphabet)}
    rare_radix = len(master_alphabet)
    rare_words = (hp.pack([master_index[ch] for ch in rare], rare_radix)
                  if rare else [])
    rare_table_cells = len(rare_words) * hp.word_cells(rare_radix)

    table_cells = dict_table_cells + rare_table_cells
    return {
        "text": text, "rare": rare, "standins": standins,
        "master_alphabet": master_alphabet,
        "transformed": transformed, "alphabet": alphabet, "tokens": tokens,
        "radix": radix, "ids": ids, "words": words,
        "table_words": table_words, "table_alpha": table_alpha,
        "table_radix": table_radix,
        "rare_words": rare_words, "rare_radix": rare_radix,
        "data_cells": data_cells, "table_cells": table_cells,
        "total_cells": data_cells + table_cells,
    }


def decode_scheme_a(enc: dict) -> str:
    """The in-machine operation for scheme A, in Python."""
    ids = hp.unpack(enc["words"], enc["radix"], len(enc["ids"]))
    transformed = hp.untokenise(ids, enc["alphabet"], enc["tokens"])
    rare = hp.unpack(enc["rare_words"], enc["rare_radix"], len(enc["rare"]))
    rare_chars = [enc["master_alphabet"][i] for i in rare]
    return unescape_text(transformed, rare_chars, enc["standins"])


def sweep_scheme_a(text: str | None = None, counts: range | None = None) -> dict:
    """Try several token counts and return the cheapest by total_cells."""
    text = hp.expected_text() if text is None else text
    rare = rare_characters(text)
    transformed, _ = escape_text(text, rare)
    alphabet_size = len(sorted(set(transformed)))
    max_tokens = 128 - alphabet_size
    if counts is None:
        counts = range(1, max_tokens + 1)
    best = None
    for count in counts:
        enc = build_scheme_a(text, count)
        if best is None or enc["total_cells"] < best["total_cells"]:
            best = enc
    return best


# ---------------------------------------------------------------------------
# Scheme C: order-1 with grouped contexts
# ---------------------------------------------------------------------------

PUNCT_SENTENCE = set(",.;:-")
PUNCT_OTHER = set("\"'()?")


def fine_category(ch: str) -> str:
    """One of 8 base buckets; every one of the 71 alphabet characters maps
    to exactly one, so any coarser K-way grouping is just a merge of these."""
    if ch == " ":
        return "space"
    if ch.isdigit():
        return "digit"
    if ch in PUNCT_SENTENCE:
        return "punct_sentence"
    if ch in PUNCT_OTHER:
        return "punct_other"
    if ch.isalpha():
        if ch.isupper():
            return "upper_vowel" if ch.lower() in "aeiou" else "upper_consonant"
        return "lower_vowel" if ch in "aeiou" else "lower_consonant"
    raise ValueError(f"unclassified character {ch!r}")


# Merges of the 8 fine buckets into K context classes, K in {2, 3, 4, 6, 8}.
# K=6 is the doc's suggested starting point (space, lowercase-vowel,
# lowercase-consonant, uppercase, digit, punctuation).
GROUPING: dict[int, dict[str, str]] = {
    2: {"space": "A", "punct_sentence": "A", "punct_other": "A", "digit": "A",
        "lower_vowel": "B", "lower_consonant": "B",
        "upper_vowel": "B", "upper_consonant": "B"},
    3: {"space": "A",
        "punct_sentence": "B", "punct_other": "B", "digit": "B",
        "lower_vowel": "C", "lower_consonant": "C",
        "upper_vowel": "C", "upper_consonant": "C"},
    4: {"space": "A",
        "punct_sentence": "B", "punct_other": "B", "digit": "B",
        "lower_vowel": "C", "lower_consonant": "C",
        "upper_vowel": "D", "upper_consonant": "D"},
    6: {"space": "A",
        "lower_vowel": "B", "lower_consonant": "C",
        "upper_vowel": "D", "upper_consonant": "D",
        "digit": "E",
        "punct_sentence": "F", "punct_other": "F"},
    8: {"space": "A", "lower_vowel": "B", "lower_consonant": "C",
        "upper_vowel": "D", "upper_consonant": "E", "digit": "F",
        "punct_sentence": "G", "punct_other": "H"},
}

# Per-context token-count caps, found by coordinate descent on total_cells
# (fine grid 0..15 then refined 0..30 per context, holding others fixed,
# to convergence). This is where the real, table-cost-aware optimum lives -
# letting every context fill its full slot budget is much worse (see the
# module docstring / architecture doc for why: table cost dominates).
BEST_CAPS_BY_K: dict[int, dict[str, int]] = {
    2: {"A": 1, "B": 14},
    3: {"A": 7, "B": 5, "C": 3},
    4: {"A": 2, "B": 6, "C": 14, "D": 9},
    6: {"A": 2, "B": 0, "C": 11, "D": 9, "E": 6, "F": 6},
    8: {"A": 1, "B": 0, "C": 12, "D": 3, "E": 0, "F": 4, "G": 4, "H": 4},
}


def make_class_of(k: int):
    grouping = GROUPING[k]
    cache: dict[str, str] = {}

    def class_of(ch: str) -> str:
        if ch not in cache:
            cache[ch] = grouping[fine_category(ch)]
        return cache[ch]

    return class_of


def choose_tokens_ctx(text: str, anchor_positions, count: int,
                       max_len: int = 13) -> list[str]:
    """Greedily pick tokens whose occurrences are anchored at `anchor_positions`
    (the positions in `text` whose context is the one being built for).

    Mirrors history_pack.choose_tokens's savings heuristic
    (occurrences * (length - 1)) but restricted to this context's anchors,
    tracked as a shrinking set of original indices (not a mutated string,
    since indices must stay valid across rounds).
    """
    tokens: list[str] = []
    remaining = set(anchor_positions)
    n = len(text)
    for _ in range(count):
        best = None
        for length in range(2, max_len + 1):
            counts: collections.Counter = collections.Counter()
            for i in remaining:
                if i + length <= n:
                    counts[text[i:i + length]] += 1
            for candidate, hits in counts.items():
                if hits < 2:
                    continue
                if any(candidate in t or t in candidate for t in tokens):
                    continue
                gain = hits * (length - 1)
                if best is None or gain > best[0]:
                    best = (gain, candidate, length)
        if best is None:
            break
        _, candidate, length = best
        tokens.append(candidate)
        remaining = {i for i in remaining
                     if not (i + length <= n and text[i:i + length] == candidate)}
    return tokens


def build_contexts(text: str, k: int, caps: dict[str, int] | None = None):
    """Build the K per-context codebooks.

    Context of position i = class of text[i-1] (a virtual space precedes
    position 0), which is always exactly known to a decoder that has
    already reconstructed the correct prefix - so this is a legitimate
    order-1 model, not a lookahead.
    """
    if caps is None:
        caps = BEST_CAPS_BY_K[k]
    class_of = make_class_of(k)
    classes = sorted(set(GROUPING[k].values()))
    prev_class = [class_of(text[i - 1] if i > 0 else " ")
                  for i in range(len(text))]

    contexts = {}
    total_table_cells = 0
    for c in classes:
        positions = [i for i in range(len(text)) if prev_class[i] == c]
        local_alphabet = sorted(set(text[i] for i in positions))
        cap = caps.get(c, 0)
        budget = max(min(cap, 128 - len(local_alphabet)), 0)
        tokens = choose_tokens_ctx(text, positions, budget) if budget > 0 else []
        ranked = sorted(tokens, key=len, reverse=True)
        alpha_index = {ch: i for i, ch in enumerate(local_alphabet)}
        token_id = {t: len(local_alphabet) + j for j, t in enumerate(tokens)}
        if tokens:
            table_text = hp.SEP.join(tokens)
            table_alpha = sorted(set(table_text))
            table_radix = len(table_alpha)
            t_index = {ch: i for i, ch in enumerate(table_alpha)}
            table_words = hp.pack([t_index[ch] for ch in table_text], table_radix)
            table_cells = len(table_words) * hp.word_cells(table_radix)
        else:
            table_words, table_radix, table_cells = [], 0, 0
        total_table_cells += table_cells
        contexts[c] = {
            "local_alphabet": local_alphabet, "tokens": tokens, "ranked": ranked,
            "alpha_index": alpha_index, "token_id": token_id,
            "table_words": table_words, "table_radix": table_radix,
            "table_cells": table_cells, "n_positions": len(positions),
        }
    return class_of, contexts, total_table_cells


def encode_ctx(text: str, class_of, contexts: dict) -> list[int]:
    ids: list[int] = []
    context = class_of(" ")
    i = 0
    n = len(text)
    while i < n:
        cinfo = contexts[context]
        matched = False
        for token in cinfo["ranked"]:
            if text.startswith(token, i):
                ids.append(cinfo["token_id"][token])
                i += len(token)
                context = class_of(text[i - 1])
                matched = True
                break
        if not matched:
            ch = text[i]
            ids.append(cinfo["alpha_index"][ch])
            i += 1
            context = class_of(ch)
    return ids


def decode_ctx(ids: list[int], class_of, contexts: dict) -> str:
    """The in-machine operation for scheme C, in Python: the context is
    always derived from the *last emitted character*, so encoder and
    decoder stay in lock-step without transmitting anything extra."""
    out: list[str] = []
    context = class_of(" ")
    for value in ids:
        cinfo = contexts[context]
        n_alpha = len(cinfo["local_alphabet"])
        if value < n_alpha:
            piece = cinfo["local_alphabet"][value]
        else:
            piece = cinfo["tokens"][value - n_alpha]
        out.append(piece)
        context = class_of(piece[-1])
    return "".join(out)


def build_scheme_c(text: str | None = None, k: int = 4,
                    caps: dict[str, int] | None = None) -> dict:
    """The grouped-context-class encoding for a given class count `k`."""
    text = hp.expected_text() if text is None else text
    class_of, contexts, table_cells = build_contexts(text, k, caps)
    ids = encode_ctx(text, class_of, contexts)
    radix = max(2, max(len(ci["local_alphabet"]) + len(ci["tokens"])
                       for ci in contexts.values()))
    words = hp.pack(ids, radix)
    data_cells = len(words) * hp.word_cells(radix)
    return {
        "text": text, "k": k, "contexts": contexts, "radix": radix,
        "ids": ids, "words": words,
        "data_cells": data_cells, "table_cells": table_cells,
        "total_cells": data_cells + table_cells,
    }


def decode_scheme_c(enc: dict) -> str:
    class_of = make_class_of(enc["k"])
    ids = hp.unpack(enc["words"], enc["radix"], len(enc["ids"]))
    return decode_ctx(ids, class_of, enc["contexts"])
