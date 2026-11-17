import sys

sys.setrecursionlimit(10000)

def _build():
    units = []
    for r in range(9):
        units.append([r * 9 + c for c in range(9)])
    for c in range(9):
        units.append([r * 9 + c for r in range(9)])
    for br in range(0, 9, 3):
        for bc in range(0, 9, 3):
            units.append([(br + dr) * 9 + bc + dc for dr in range(3) for dc in range(3)])
    units_of = [[] for _ in range(81)]
    for u in units:
        for i in u:
            units_of[i].append(u)
    peers = []
    for i in range(81):
        s = set()
        for u in units_of[i]:
            s.update(u)
        s.discard(i)
        peers.append(tuple(sorted(s)))
    return units_of, peers

_UNITS_OF, _PEERS = _build()
_POP = [bin(i).count("1") for i in range(512)]


def _eliminate(cand, i, bit):
    if not cand[i] & bit:
        return True
    c = cand[i] & ~bit
    cand[i] = c
    if c == 0:
        return False
    if c & (c - 1) == 0:
        for p in _PEERS[i]:
            if cand[p] & c:
                if not _eliminate(cand, p, c):
                    return False
    for u in _UNITS_OF[i]:
        cnt = 0
        last = -1
        for j in u:
            if cand[j] & bit:
                cnt += 1
                last = j
                if cnt > 1:
                    break
        if cnt == 0:
            return False
        if cnt == 1 and cand[last] & (cand[last] - 1):
            if not _assign(cand, last, bit):
                return False
    return True


def _assign(cand, i, bit):
    if not cand[i] & bit:
        return False
    other = cand[i] & ~bit
    while other:
        b = other & -other
        other ^= b
        if not _eliminate(cand, i, b):
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
    c = cand[best]
    while c:
        b = c & -c
        c ^= b
        new = cand[:]
        if _assign(new, best, b):
            r = _search(new)
            if r is not None:
                return r
    return None


def solve(puzzle: str) -> str:
    p = puzzle.strip()
    if len(p) != 81:
        raise ValueError("puzzle must have 81 characters")
    cand = [511] * 81
    for i, ch in enumerate(p):
        if ch in "123456789":
            if not _assign(cand, i, 1 << (int(ch) - 1)):
                return ""
    res = _search(cand)
    if res is None:
        return ""
    return "".join(str(c.bit_length()) for c in res)
