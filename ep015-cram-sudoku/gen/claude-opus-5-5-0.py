# Fast bitmask Sudoku solver: constraint propagation (naked + hidden singles)
# combined with minimum-remaining-values backtracking search.

ALL = 0x1FF

_ROWS = [[r * 9 + c for c in range(9)] for r in range(9)]
_COLS = [[r * 9 + c for r in range(9)] for c in range(9)]
_BOXES = [[(br * 3 + r) * 9 + bc * 3 + c for r in range(3) for c in range(3)]
          for br in range(3) for bc in range(3)]
UNITS = _ROWS + _COLS + _BOXES

PEERS = []
for _i in range(81):
    _s = set()
    for _u in UNITS:
        if _i in _u:
            _s.update(_u)
    _s.discard(_i)
    PEERS.append(tuple(_s))

POP = [bin(x).count("1") for x in range(512)]


def _propagate(cand, queue):
    peers = PEERS
    units = UNITS
    while True:
        while queue:
            i, b = queue.pop()
            if not cand[i] & b:
                return False
            cand[i] = b
            nb = ~b
            for p in peers[i]:
                c = cand[p]
                if c & b:
                    c &= nb
                    if not c:
                        return False
                    cand[p] = c
                    if not c & (c - 1):
                        queue.append((p, c))
        # hidden singles
        for u in units:
            once = 0
            twice = 0
            for k in u:
                c = cand[k]
                twice |= once & c
                once |= c
            if once != ALL:
                return False
            h = once & ~twice
            if h:
                for k in u:
                    c = cand[k]
                    m = c & h
                    if m:
                        if m & (m - 1):
                            return False
                        if c != m:
                            queue.append((k, m))
        if not queue:
            return True


def _search(cand):
    best = -1
    bc = 10
    pop = POP
    for i in range(81):
        n = pop[cand[i]]
        if 1 < n < bc:
            bc = n
            best = i
            if n == 2:
                break
    if best < 0:
        return cand
    c = cand[best]
    while c:
        b = c & -c
        c ^= b
        nc = cand[:]
        if _propagate(nc, [(best, b)]):
            r = _search(nc)
            if r is not None:
                return r
    return None


def solve(puzzle: str) -> str:
    cand = [ALL] * 81
    queue = []
    for i, ch in enumerate(puzzle[:81]):
        if ch in "123456789":
            queue.append((i, 1 << (int(ch) - 1)))
    if not _propagate(cand, queue):
        return ""
    res = _search(cand)
    if res is None:
        return ""
    return "".join(str(b.bit_length()) for b in res)
