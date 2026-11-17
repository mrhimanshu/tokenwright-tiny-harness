"""Fast exact Sudoku solver using bitmask candidates, constraint propagation
(naked singles and hidden singles), and minimum-remaining-values backtracking.
Standard library only."""

_ALL = 0x1FF  # candidate bit k (0..8) means digit k+1


def _build_structure():
    units = []
    for r in range(9):
        units.append([r * 9 + c for c in range(9)])
    for c in range(9):
        units.append([r * 9 + c for r in range(9)])
    for br in range(0, 9, 3):
        for bc in range(0, 9, 3):
            units.append([(br + dr) * 9 + (bc + dc) for dr in range(3) for dc in range(3)])

    units_of = [[] for _ in range(81)]
    for k, unit in enumerate(units):
        for i in unit:
            units_of[i].append(k)

    peers = []
    for i in range(81):
        s = set()
        for k in units_of[i]:
            s.update(units[k])
        s.discard(i)
        peers.append(tuple(sorted(s)))
    return units, units_of, peers


_UNITS, _UNITS_OF, _PEERS = _build_structure()
_POPCOUNT = [bin(x).count("1") for x in range(512)]


def _propagate(cand, queue):
    """Apply eliminations from queue (list of (cell, bitmask_to_remove)).
    Returns False on contradiction, True otherwise."""
    units = _UNITS
    units_of = _UNITS_OF
    peers = _PEERS
    while queue:
        i, bits = queue.pop()
        c = cand[i]
        hit = c & bits
        if not hit:
            continue
        c ^= hit
        cand[i] = c
        if not c:
            return False
        if c & (c - 1) == 0:
            # Naked single: remove its digit from all peers.
            for p in peers[i]:
                if cand[p] & c:
                    queue.append((p, c))
        # Hidden singles: check every digit that was just removed from cell i.
        h = hit
        while h:
            b = h & -h
            h ^= b
            for u in units_of[i]:
                count = 0
                last = -1
                for j in units[u]:
                    if cand[j] & b:
                        count += 1
                        if count > 1:
                            break
                        last = j
                if count == 0:
                    return False
                if count == 1 and cand[last] != b:
                    queue.append((last, cand[last] & ~b))
    return True


def _search(cand):
    best = -1
    best_n = 10
    for i in range(81):
        c = cand[i]
        if c & (c - 1):
            n = _POPCOUNT[c]
            if n < best_n:
                best_n = n
                best = i
                if n == 2:
                    break
    if best < 0:
        return cand
    c = cand[best]
    while c:
        b = c & -c
        c ^= b
        new = cand[:]
        if _propagate(new, [(best, _ALL ^ b)]):
            res = _search(new)
            if res is not None:
                return res
    return None


def solve(puzzle: str) -> str:
    """Return the 81-character solution for a 9x9 Sudoku given as 81 characters
    (row by row, '.' or '0' for empty cells). Returns "" if no solution exists."""
    s = "".join(ch for ch in puzzle if not ch.isspace())
    if len(s) != 81:
        raise ValueError("puzzle must contain exactly 81 cell characters")

    cand = [_ALL] * 81
    queue = []
    for i, ch in enumerate(s):
        if ch == "." or ch == "0":
            continue
        if ch not in "123456789":
            raise ValueError("invalid character in puzzle: %r" % ch)
        queue.append((i, _ALL ^ (1 << (ord(ch) - ord("1")))))

    if not _propagate(cand, queue):
        return ""
    res = _search(cand)
    if res is None:
        return ""
    return "".join(str(c.bit_length()) for c in res)
