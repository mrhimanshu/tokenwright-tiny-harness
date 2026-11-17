_BIT_INDEX = {1 << k: k for k in range(9)}
_POP = [bin(i).count("1") for i in range(512)]
_DIGITS = "123456789"

_UNITS = []
for _r in range(9):
    _UNITS.append([_r * 9 + _c for _c in range(9)])
for _c in range(9):
    _UNITS.append([_r * 9 + _c for _r in range(9)])
for _br in range(3):
    for _bc in range(3):
        _UNITS.append([(_br * 3 + _i) * 9 + (_bc * 3 + _j)
                       for _i in range(3) for _j in range(3)])

_UNIT_OF = [[u for u in _UNITS if i in u] for i in range(81)]
_PEERS = [sorted({p for u in _UNIT_OF[i] for p in u} - {i}) for i in range(81)]


def _eliminate(cand, i, d):
    """Remove candidate bit d from cell i and propagate. Returns False on contradiction."""
    c = cand[i]
    if not (c & d):
        return True
    c &= ~d
    cand[i] = c
    if c == 0:
        return False
    if _POP[c] == 1:
        # Naked single: remove this value from all peers.
        for p in _PEERS[i]:
            if not _eliminate(cand, p, c):
                return False
    # Hidden single: if a digit has only one place in a unit, place it there.
    for u in _UNIT_OF[i]:
        places = [j for j in u if cand[j] & d]
        if not places:
            return False
        if len(places) == 1:
            j = places[0]
            o = cand[j] & ~d
            while o:
                b = o & -o
                o ^= b
                if not _eliminate(cand, j, b):
                    return False
    return True


def _search(cand):
    # Minimum remaining values heuristic.
    best = -1
    best_n = 10
    for i in range(81):
        c = cand[i]
        if c & (c - 1):
            n = _POP[c]
            if n < best_n:
                best_n = n
                best = i
                if n == 2:
                    break
    if best < 0:
        return cand  # every cell is determined

    c = cand[best]
    while c:
        b = c & -c
        c ^= b
        new = cand[:]
        ok = True
        o = new[best] & ~b
        while o:
            e = o & -o
            o ^= e
            if not _eliminate(new, best, e):
                ok = False
                break
        if ok:
            r = _search(new)
            if r is not None:
                return r
    return None


def solve(puzzle: str) -> str:
    s = [ch for ch in puzzle if ch in "123456789.0"]
    if len(s) != 81:
        raise ValueError("Puzzle must contain exactly 81 cell characters")

    cand = [511] * 81
    for i, ch in enumerate(s):
        if ch in ".0":
            continue
        bit = 1 << (int(ch) - 1)
        if not (cand[i] & bit):
            raise ValueError("Puzzle is contradictory")
        o = cand[i] & ~bit
        while o:
            e = o & -o
            o ^= e
            if not _eliminate(cand, i, e):
                raise ValueError("Puzzle is contradictory")

    result = _search(cand)
    if result is None:
        raise ValueError("Puzzle has no solution")
    return "".join(_DIGITS[_BIT_INDEX[c]] for c in result)
