# Precompute units, peers and helper tables
_UNITS = []
for _r in range(9):
    _UNITS.append([_r * 9 + _c for _c in range(9)])
for _c in range(9):
    _UNITS.append([_r * 9 + _c for _r in range(9)])
for _br in range(3):
    for _bc in range(3):
        _UNITS.append([(_br * 3 + _r) * 9 + _bc * 3 + _c
                       for _r in range(3) for _c in range(3)])

_PEERS = []
for _i in range(81):
    _s = set()
    for _u in _UNITS:
        if _i in _u:
            _s.update(_u)
    _s.discard(_i)
    _PEERS.append(tuple(sorted(_s)))

_UNITS = [tuple(u) for u in _UNITS]
_POPCOUNT = [bin(_x).count('1') for _x in range(512)]
_BIT2DIGIT = {1 << _d: str(_d + 1) for _d in range(9)}
_ALL = 0x1FF


def _place(c, g, stack):
    peers = _PEERS
    while stack:
        i, b = stack.pop()
        gi = g[i]
        if gi:
            if gi != b:
                return False
            continue
        if not (c[i] & b):
            return False
        g[i] = b
        c[i] = b
        for p in peers[i]:
            v = c[p]
            if v & b:
                if g[p]:
                    return False
                v ^= b
                if not v:
                    return False
                c[p] = v
                if not (v & (v - 1)):
                    stack.append((p, v))
    return True


def _propagate(c, g, stack):
    while True:
        if not _place(c, g, stack):
            return False
        for unit in _UNITS:
            once = 0
            twice = 0
            placed = 0
            for i in unit:
                v = c[i]
                twice |= once & v
                once |= v
                placed |= g[i]
            if once != _ALL:
                return False
            singles = once & ~twice & ~placed
            while singles:
                b = singles & -singles
                singles ^= b
                for i in unit:
                    if c[i] & b:
                        stack.append((i, b))
                        break
        if not stack:
            return True


def _search(c, g):
    best = -1
    best_count = 10
    pc = _POPCOUNT
    for i in range(81):
        if not g[i]:
            n = pc[c[i]]
            if n < best_count:
                best_count = n
                best = i
                if n == 2:
                    break
    if best < 0:
        return g
    v = c[best]
    while v:
        b = v & -v
        v ^= b
        c2 = c[:]
        g2 = g[:]
        if _propagate(c2, g2, [(best, b)]):
            r = _search(c2, g2)
            if r is not None:
                return r
    return None


def solve(puzzle: str) -> str:
    puzzle = puzzle.strip()
    c = [_ALL] * 81
    g = [0] * 81
    stack = []
    for i, ch in enumerate(puzzle[:81]):
        if '1' <= ch <= '9':
            stack.append((i, 1 << (ord(ch) - 49)))
    if not _propagate(c, g, stack):
        return ''
    res = _search(c, g)
    if res is None:
        return ''
    return ''.join(_BIT2DIGIT[b] for b in res)
