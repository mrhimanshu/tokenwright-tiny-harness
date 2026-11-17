import sys

sys.setrecursionlimit(10000)

_ROWS = [[r * 9 + c for c in range(9)] for r in range(9)]
_COLS = [[r * 9 + c for r in range(9)] for c in range(9)]
_BOXES = [[(br * 3 + r) * 9 + bc * 3 + c for r in range(3) for c in range(3)]
          for br in range(3) for bc in range(3)]
_UNITS = _ROWS + _COLS + _BOXES
_UNITS_OF = [[] for _ in range(81)]
for _u in _UNITS:
    for _s in _u:
        _UNITS_OF[_s].append(_u)
_PEERS = []
for _s in range(81):
    _p = set()
    for _u in _UNITS_OF[_s]:
        _p.update(_u)
    _p.discard(_s)
    _PEERS.append(sorted(_p))

_POP = [bin(i).count("1") for i in range(512)]


def _eliminate(c, s, bit):
    v = c[s]
    if not v & bit:
        return True
    v &= ~bit
    c[s] = v
    if v == 0:
        return False
    if v & (v - 1) == 0:
        for p in _PEERS[s]:
            if not _eliminate(c, p, v):
                return False
    for u in _UNITS_OF[s]:
        places = [x for x in u if c[x] & bit]
        if not places:
            return False
        if len(places) == 1:
            x = places[0]
            if c[x] != bit:
                if not _assign(c, x, bit):
                    return False
    return True


def _assign(c, s, bit):
    others = c[s] & ~bit
    while others:
        b = others & -others
        others ^= b
        if not _eliminate(c, s, b):
            return False
    return True


def _search(c):
    best = -1
    bn = 10
    for i in range(81):
        n = _POP[c[i]]
        if n > 1 and n < bn:
            bn = n
            best = i
            if n == 2:
                break
    if best < 0:
        return c
    v = c[best]
    while v:
        b = v & -v
        v ^= b
        c2 = c[:]
        if _assign(c2, best, b):
            r = _search(c2)
            if r is not None:
                return r
    return None


def solve(puzzle: str) -> str:
    puzzle = puzzle.strip()
    if len(puzzle) != 81:
        raise ValueError("Puzzle must have 81 characters")
    c = [511] * 81
    for i, ch in enumerate(puzzle):
        if ch in ".0":
            continue
        if ch not in "123456789":
            raise ValueError("Invalid character")
        if not _assign(c, i, 1 << (int(ch) - 1)):
            raise ValueError("Contradictory puzzle")
    r = _search(c)
    if r is None:
        raise ValueError("No solution")
    return "".join(str(x.bit_length()) for x in r)
