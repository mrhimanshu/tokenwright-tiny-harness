import sys

sys.setrecursionlimit(10000)

_ROW = [i // 9 for i in range(81)]
_COL = [i % 9 for i in range(81)]
_BOX = [(i // 27) * 3 + (i % 9) // 3 for i in range(81)]

_UNITS = []
for _r in range(9):
    _UNITS.append([_r * 9 + _c for _c in range(9)])
for _c in range(9):
    _UNITS.append([_r * 9 + _c for _r in range(9)])
for _b in range(9):
    _br, _bc = (_b // 3) * 3, (_b % 3) * 3
    _UNITS.append([(_br + dr) * 9 + _bc + dc for dr in range(3) for dc in range(3)])

_POP = [bin(m).count("1") for m in range(512)]
_BITDIG = {1 << d: d + 1 for d in range(9)}
_FULL = 0x1FF


def _search(g, R, C, B):
    ROW, COL, BOX, POP, BITDIG = _ROW, _COL, _BOX, _POP, _BITDIG
    while True:
        changed = False
        minc = 10
        best = -1
        bestm = 0
        for i in range(81):
            if g[i]:
                continue
            r = ROW[i]; c = COL[i]; b = BOX[i]
            m = ~(R[r] | C[c] | B[b]) & _FULL
            if not m:
                return None
            if not (m & (m - 1)):
                g[i] = BITDIG[m]
                R[r] |= m; C[c] |= m; B[b] |= m
                changed = True
            elif not changed:
                cnt = POP[m]
                if cnt < minc:
                    minc = cnt
                    best = i
                    bestm = m
        if changed:
            continue
        if best == -1:
            return g
        # hidden singles
        for unit in _UNITS:
            once = 0
            twice = 0
            placed = 0
            for i in unit:
                v = g[i]
                if v:
                    placed |= 1 << (v - 1)
                else:
                    m = ~(R[ROW[i]] | C[COL[i]] | B[BOX[i]]) & _FULL
                    twice |= once & m
                    once |= m
            if (once | placed) != _FULL:
                return None
            h = once & ~twice
            if h:
                for i in unit:
                    if g[i]:
                        continue
                    r = ROW[i]; c = COL[i]; b = BOX[i]
                    m = ~(R[r] | C[c] | B[b]) & _FULL
                    bit = m & h
                    if bit:
                        if bit & (bit - 1):
                            return None
                        g[i] = BITDIG[bit]
                        R[r] |= bit; C[c] |= bit; B[b] |= bit
                        changed = True
        if changed:
            continue
        # branch
        r = ROW[best]; c = COL[best]; b = BOX[best]
        m = bestm
        while m:
            bit = m & -m
            m ^= bit
            g2 = g[:]
            R2 = R[:]
            C2 = C[:]
            B2 = B[:]
            g2[best] = BITDIG[bit]
            R2[r] |= bit; C2[c] |= bit; B2[b] |= bit
            res = _search(g2, R2, C2, B2)
            if res is not None:
                return res
        return None


def solve(puzzle: str) -> str:
    s = "".join(ch for ch in puzzle if not ch.isspace())
    g = [0] * 81
    R = [0] * 9
    C = [0] * 9
    B = [0] * 9
    for i in range(min(81, len(s))):
        ch = s[i]
        if "1" <= ch <= "9":
            d = ord(ch) - 48
            bit = 1 << (d - 1)
            r = _ROW[i]; c = _COL[i]; b = _BOX[i]
            if (R[r] | C[c] | B[b]) & bit:
                return ""
            g[i] = d
            R[r] |= bit; C[c] |= bit; B[b] |= bit
    res = _search(g, R, C, B)
    if res is None:
        return ""
    return "".join(map(str, res))
