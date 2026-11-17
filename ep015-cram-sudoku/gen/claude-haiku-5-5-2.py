ALL = 0x1FF  # bits 0..8 represent digits 1..9


def _build_tables():
    peers = []
    for i in range(81):
        r, c = divmod(i, 9)
        br, bc = 3 * (r // 3), 3 * (c // 3)
        s = set()
        for k in range(9):
            s.add(r * 9 + k)
            s.add(k * 9 + c)
            s.add((br + k // 3) * 9 + bc + k % 3)
        s.discard(i)
        peers.append(tuple(s))

    units = []
    for k in range(9):
        units.append(tuple(k * 9 + c for c in range(9)))  # rows
    for k in range(9):
        units.append(tuple(r * 9 + k for r in range(9)))  # columns
    for br in (0, 3, 6):
        for bc in (0, 3, 6):
            units.append(tuple((br + a) * 9 + bc + b
                               for a in range(3) for b in range(3)))  # boxes
    return tuple(peers), tuple(units)


PEERS, UNITS = _build_tables()
POP = [bin(i).count('1') for i in range(512)]


def _propagate(cand, queue):
    """Naked-single elimination. queue holds cells whose candidate set is a single bit."""
    while queue:
        i = queue.pop()
        bit = cand[i]
        for j in PEERS[i]:
            cj = cand[j]
            if cj & bit:
                cj ^= bit
                if not cj:
                    return False
                cand[j] = cj
                if not (cj & (cj - 1)):
                    queue.append(j)
    return True


def _fix(cand, queue):
    """Propagate naked and hidden singles to a fixpoint. Returns False on contradiction."""
    while True:
        if not _propagate(cand, queue):
            return False
        queue = []
        for unit in UNITS:
            seen = 0
            twice = 0
            for k in unit:
                b = cand[k]
                twice |= seen & b
                seen |= b
            if seen != ALL:
                return False  # some digit has no place in this unit
            single = seen & ~twice & ALL  # digits that fit in exactly one cell
            while single:
                bit = single & -single
                single ^= bit
                for k in unit:
                    if cand[k] & bit:
                        break
                else:
                    return False
                if cand[k] != bit:
                    cand[k] = bit
                    queue.append(k)
        if not queue:
            return True


def _dfs(cand):
    best = -1
    bestc = 10
    for i in range(81):
        b = cand[i]
        if b & (b - 1):
            c = POP[b]
            if c < bestc:
                best = i
                bestc = c
                if c == 2:
                    break
    if best < 0:
        return cand  # every cell is a singleton and consistent: solved
    b = cand[best]
    while b:
        bit = b & -b
        b ^= bit
        nc = cand[:]
        nc[best] = bit
        if _fix(nc, [best]):
            r = _dfs(nc)
            if r is not None:
                return r
    return None


def solve(puzzle: str) -> str:
    chars = [ch for ch in puzzle if ch in '.0123456789']
    if len(chars) != 81:
        raise ValueError("puzzle must contain exactly 81 cells")

    cand = [ALL] * 81
    queue = []
    for i, ch in enumerate(chars):
        if ch in '123456789':
            cand[i] = 1 << (ord(ch) - ord('1'))
            queue.append(i)

    if not _fix(cand, queue):
        raise ValueError("no solution")

    res = _dfs(cand)
    if res is None:
        raise ValueError("no solution")

    return ''.join(str(b.bit_length()) for b in res)
