"""Property-based stress test for lib/similarity.damerau_levenshtein_distance.

This test file proves that the early-exit optimization added in commit b18c72a
(14.8x speedup via abs(len1-len2) > max_dist pruning) does NOT introduce
false negatives vs the canonical un-pruned implementation.

Design rationale
----------------
The optimized function returns (max_dist + 1) as sentinel when the length
difference exceeds max_dist.  The optimized path must therefore be compared
against the REAL distance — not just the sentinel — to ensure no genuine
matches are skipped.  The reference implementation here is the identical
matrix algorithm without the early-exit guard, giving us a pure oracle.

Coverage targets:
  - 500 random string pairs with length 3-15, character set a-z0-9
  - All max_dist values 1, 2, 3 (the values actually used in find_similar)
  - Pairs where abs(len(s1) - len(s2)) == max_dist (the exact boundary)
  - Pairs where abs(len(s1) - len(s2)) == max_dist + 1 (pruned case)
  - Empty string edge cases
"""

from __future__ import annotations

import random
import string

import pytest

from lib.similarity import damerau_levenshtein_distance


# ==============================================================================
# Reference implementation (no early-exit, canonical DL matrix)
# ==============================================================================

def _reference_dl(s1: str, s2: str) -> int:
    """Canonical Damerau-Levenshtein without any pruning guard.

    This is the same matrix algorithm as the optimized version, but without
    the abs(len1-len2) > max_dist early return.  Used as oracle in property
    tests.
    """
    if s1 == s2:
        return 0
    len1, len2 = len(s1), len(s2)
    if len1 == 0:
        return len2
    if len2 == 0:
        return len1

    d = [[0] * (len2 + 2) for _ in range(len1 + 2)]
    boundary_max = len1 + len2
    d[0][0] = boundary_max
    for i in range(0, len1 + 1):
        d[i + 1][0] = boundary_max
        d[i + 1][1] = i
    for j in range(0, len2 + 1):
        d[0][j + 1] = boundary_max
        d[1][j + 1] = j

    da: dict[str, int] = {}
    for i in range(1, len1 + 1):
        db = 0
        c1 = s1[i - 1]
        for j in range(1, len2 + 1):
            c2 = s2[j - 1]
            k = da.get(c2, 0)
            ll = db
            cost = 0 if c1 == c2 else 1
            if cost == 0:
                db = j
            d[i + 1][j + 1] = min(
                d[i][j + 1] + 1,
                d[i + 1][j] + 1,
                d[i][j] + cost,
                d[k][ll] + (i - k - 1) + 1 + (j - ll - 1),
            )
        da[c1] = i
    return d[len1 + 1][len2 + 1]


# ==============================================================================
# Property: optimized DL with max_dist >= real distance == reference DL
# ==============================================================================

ALPHABET = string.ascii_lowercase + string.digits
NUM_RANDOM_PAIRS = 500
RANDOM_SEED = 42


def _random_string(rng: random.Random, min_len: int = 3, max_len: int = 15) -> str:
    length = rng.randint(min_len, max_len)
    return "".join(rng.choice(ALPHABET) for _ in range(length))


@pytest.fixture(scope="module")
def random_pairs() -> list[tuple[str, str]]:
    """Generate 500 reproducible random string pairs for stress-testing."""
    rng = random.Random(RANDOM_SEED)
    return [(_random_string(rng), _random_string(rng)) for _ in range(NUM_RANDOM_PAIRS)]


@pytest.mark.parametrize("max_dist", [1, 2, 3])
def test_optimized_dl_matches_reference_on_random_pairs(random_pairs, max_dist):
    """For all 500 random pairs, when max_dist >= the real DL distance, the
    optimized function must return the EXACT same value as the reference.

    A max_dist < real_dist intentionally causes the sentinel (max_dist+1) to
    be returned — that is not a bug, it is the expected pruning behaviour.
    Only pairs where the real distance <= max_dist are tested for exact match.
    """
    mismatches: list[tuple[str, str, int, int, int]] = []

    for s1, s2 in random_pairs:
        real_dist = _reference_dl(s1, s2)
        if real_dist > max_dist:
            # Pruning is allowed here — distance genuinely exceeds threshold
            continue
        optimized = damerau_levenshtein_distance(s1, s2, max_dist=max_dist)
        if optimized != real_dist:
            mismatches.append((s1, s2, max_dist, real_dist, optimized))

    assert not mismatches, (
        f"Optimized DL differs from reference for {len(mismatches)} pair(s) "
        f"(max_dist={max_dist}):\n" +
        "\n".join(
            f"  s1={r[0]!r}, s2={r[1]!r}, max_dist={r[2]}, "
            f"reference={r[3]}, optimized={r[4]}"
            for r in mismatches[:10]
        )
    )


def test_boundary_case_abs_length_diff_equals_max_dist(random_pairs):
    """Pairs where abs(len(s1)-len(s2)) == max_dist are NOT pruned away by the
    early exit (only > max_dist is pruned).  This verifies the boundary is
    correct and no off-by-one exists.
    """
    max_dist = 2
    boundary_pairs = [
        (s1, s2) for s1, s2 in random_pairs
        if abs(len(s1) - len(s2)) == max_dist
    ]
    assert boundary_pairs, "No boundary pairs generated — increase NUM_RANDOM_PAIRS or adjust seed"

    mismatches = []
    for s1, s2 in boundary_pairs:
        real_dist = _reference_dl(s1, s2)
        optimized = damerau_levenshtein_distance(s1, s2, max_dist=max_dist)
        # When real_dist <= max_dist, the results must match exactly.
        # When real_dist > max_dist both are free to return sentinel.
        if real_dist <= max_dist and optimized != real_dist:
            mismatches.append((s1, s2, real_dist, optimized))

    assert not mismatches, (
        f"Boundary mismatch for {len(mismatches)} pair(s): {mismatches[:5]}"
    )


def test_pruned_case_abs_length_diff_exceeds_max_dist():
    """When abs(len(s1)-len(s2)) > max_dist the function MUST return
    a value > max_dist (the sentinel), never the actual real distance.

    This is the correct contract for the pruning optimisation — callers treat
    any return value > max_dist as 'distance exceeds threshold'.
    """
    max_dist = 2
    # s1 length 3, s2 length 6: abs diff = 3 > max_dist=2 → sentinel expected
    s1 = "abc"
    s2 = "abcdef"
    result = damerau_levenshtein_distance(s1, s2, max_dist=max_dist)
    assert result > max_dist, (
        f"Expected sentinel (> {max_dist}) for pruned pair, got {result}"
    )


# ==============================================================================
# Edge cases that must work correctly with any max_dist
# ==============================================================================

@pytest.mark.parametrize("s1, s2, max_dist, expected", [
    # Identical strings
    ("abc", "abc", 1, 0),
    ("", "", 1, 0),
    # One empty
    ("", "abc", 3, 3),
    ("abc", "", 3, 3),
    # Single transposition
    ("ab", "ba", 1, 1),
    ("ab", "ba", 0, 1),   # max_dist=0: sentinel must be > 0
    # Known values
    ("tokopedia", "tokopdia", 2, 1),
    ("mandiri", "mandiri", 2, 0),
])
def test_dl_edge_cases(s1, s2, max_dist, expected):
    result = damerau_levenshtein_distance(s1, s2, max_dist=max_dist)
    if expected <= max_dist:
        assert result == expected, f"dl({s1!r}, {s2!r}, max_dist={max_dist}): got {result}, want {expected}"
    else:
        # Result must be > max_dist (sentinel)
        assert result > max_dist, f"dl({s1!r}, {s2!r}, max_dist={max_dist}): expected sentinel > {max_dist}, got {result}"
