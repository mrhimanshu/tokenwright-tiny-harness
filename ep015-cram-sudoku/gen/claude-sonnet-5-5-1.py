import sys

def _build():
    peers = [set() for _ in range(81)]
    units = []
    for r in range(9):
        units.append([r * 9 + c for c in range(9)])
    for c in range(9):
        units.append([r * 9 + c for r in range(9)])
    for br in range(0, 9, 3):
        for bc in range(0, 9, 3):
            units.append([(br + i) * 9 + bc + j for i in range(3) for j in range(3)])
    units_of = [[] for _ in range(81)]
    for u in units:
        for c in u:
            units_of[c].append(u)
            for d in u:
                if d != c:
                    peers[c].add(d)
    return [tuple(sorted(p)) for p in peers], units_of

_PEERS, _UNITS_OF = _build()
_POP = [bin(i).count("1") for i in range(512)]
_BITS = [1 << i for i in range(9)]


def _eliminate(cand, c, bit):
    old = cand[c]
    if not old & bit:
        return True
    new = old & ~bit
    if not new:
        return False
    cand[c] = new
    if new & (new - 1) == 0:
        for p in _PEERS[c]:
            if not _eliminate(cand, p, new):
                return False
    for u in _UNITS_OF[c]:
        places = [s for s in u if cand[s] & bit]
        if not places:
            return False
        if len(places) == 1:
            s = places[0]
            v = cand[s]
            if v & (v - 1):
                if not _assign(cand, s, bit):
                    return False
    return True


def _assign(cand, c, bit):
    if not cand[c] & bit:
        return False
    for b in _BITS:
        if b != bit and cand[c] & b:
            if not _eliminate(cand, c, b):
                return False
    return True


def _search(cand):
    best = -1
    bn = 10
    for i in range(81):
        n = _POP[cand[i]]
        if n > 1 and n < bn:
            bn = n
            best = i
            if n == 2:
                break
    if best < 0:
        return cand
    v = cand[best]
    for b in _BITS:
        if v & b:
            nc = cand[:]
            if _assign(nc, best, b):
                r = _search(nc)
                if r is not None:
                    return r
    return None


def solve(puzzle: str) -> str:
    sys.setrecursionlimit(10000)
    cand = [511] * 81
    for i, ch in enumerate(puzzle[:81]):
        if ch in "123456789":
            if not _assign(cand, i, 1 << (int(ch) - 1)):
                return ""
    res = _search(cand)
    if res is None:
        return ""
    return "".join(str(v.bit_length()) for v in res)
