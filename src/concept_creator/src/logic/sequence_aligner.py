from typing import List, Tuple


def align_monotone_one_to_one(
    similarity: List[List[float]],
    types_a: List[List[str]],
    types_b: List[List[str]],
) -> List[Tuple[int, int]]:
    """Monotone, 1:1, type-safe alignment of two node sub-paths.

    Returns (a_idx, b_idx) pairs, strictly increasing in both indices, that
    saturate the shorter axis (len(pairs) == min(len(A), len(B)) when a
    same-type monotone full match exists) and maximize total similarity.
    Cross-type pairs (label lists with no shared element) are never produced;
    when type/parity constraints make full saturation impossible the maximal
    feasible set is returned. Never raises.
    """
    m = len(similarity)
    n = len(types_b)
    if m == 0 or n == 0:
        return []

    def compatible(i: int, j: int) -> bool:
        return bool(set(types_a[i]) & set(types_b[j]))

    # dp[i][j] = best (match_count, total_similarity) using A[:i] and B[:j].
    # Lexicographic max: cardinality first (saturates the shorter axis),
    # total similarity as the tie-break.
    dp = [[(0, 0.0)] * (n + 1) for _ in range(m + 1)]
    choice = [[""] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            best = dp[i - 1][j]
            move = "up"
            if dp[i][j - 1] > best:
                best = dp[i][j - 1]
                move = "left"
            if compatible(i - 1, j - 1):
                prev = dp[i - 1][j - 1]
                cand = (prev[0] + 1, prev[1] + similarity[i - 1][j - 1])
                if cand > best:
                    best = cand
                    move = "diag"
            dp[i][j] = best
            choice[i][j] = move

    pairs: List[Tuple[int, int]] = []
    i, j = m, n
    while i > 0 and j > 0:
        move = choice[i][j]
        if move == "diag":
            pairs.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif move == "up":
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    return pairs
