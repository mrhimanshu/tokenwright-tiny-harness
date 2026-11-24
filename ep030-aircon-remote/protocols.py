"""Ground-truth air-con remote protocols (my code, never a model).

panasonic : the real PANASONIC_AC 216-bit protocol, layout from IRremoteESP8266 ir_Panasonic.{h,cpp}
            (two sections, 8 + 19 bytes, LSB first, checksum = 0xF4 + sum(bytes[0..25]) & 0xFF,
             quirk: in fan-only mode the temperature byte is forced to 27 C).
brandx    : an invented protocol of similar size that exists nowhere online (one 14-byte frame, MSB first,
            redundancy byte = bitwise NOT of the temp/power byte, XOR+0x37 checksum,
            quirk: in dry mode the fan field is forced to auto).
Settings: power on/off, mode auto|cool|heat|dry|fan, temp 16-30, fan auto|min|low|med|high|max, vane auto|1..5
"""
import random

MODES = ["auto", "cool", "heat", "dry", "fan"]
FANS = ["auto", "min", "low", "med", "high", "max"]
VANES = ["auto", "1", "2", "3", "4", "5"]


def random_settings(rng):
    return dict(power=rng.choice(["on", "on", "on", "off"]), mode=rng.choice(MODES), temp=rng.randint(16, 30),
                fan=rng.choice(FANS), vane=rng.choice(VANES))


# ---------------- Panasonic (real) ----------------
PANA_BASE = [0x02, 0x20, 0xE0, 0x04, 0x00, 0x00, 0x00, 0x06, 0x02,
             0x20, 0xE0, 0x04, 0x00, 0x00, 0x00, 0x80, 0x00, 0x00,
             0x00, 0x0E, 0xE0, 0x00, 0x00, 0x81, 0x00, 0x00, 0x00]
PANA_MODE = dict(auto=0, dry=2, cool=3, heat=4, fan=6)
PANA_FAN = dict(min=0, low=1, med=2, high=3, max=4, auto=7)  # stored as value + 3 in the high nibble
PANA_VANE = {"auto": 0xF, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}


def pana_bytes(s):
    b = list(PANA_BASE)
    b[13] = (PANA_MODE[s["mode"]] << 4) | (1 if s["power"] == "on" else 0) | 0x08  # bit3 always set by DKE-style remotes
    t = 27 if s["mode"] == "fan" else s["temp"]
    b[14] = (t & 0x1F) << 1
    b[16] = ((PANA_FAN[s["fan"]] + 3) << 4) | PANA_VANE[s["vane"]]
    b[26] = (0xF4 + sum(b[:26])) & 0xFF
    return b


# ---------------- Brand X (invented) ----------------
BX_MODE = dict(auto=5, cool=1, heat=6, dry=2, fan=3)
BX_FAN = dict(auto=0, min=1, low=2, med=3, high=4, max=5)
BX_VANE = {"auto": 0x8, "1": 0x1, "2": 0x2, "3": 0x3, "4": 0x4, "5": 0x5}


def bx_bytes(s):
    b = [0x5A, 0xC3, 0x1D, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00, 0x21, 0x00, 0x00, 0x00]
    b[4] = (0x80 if s["power"] == "on" else 0) | ((s["temp"] - 16) << 3) | 0x02
    fan = "auto" if s["mode"] == "dry" else s["fan"]
    b[7] = (BX_FAN[fan] << 4) | BX_MODE[s["mode"]]
    b[8] = 0x30 | BX_VANE[s["vane"]]
    b[9] = (~b[4]) & 0xFF
    x = 0
    for v in b[:13]:
        x ^= v
    b[13] = (x + 0x37) & 0xFF
    return b


# ---------------- timing (what an IR receiver dumps) ----------------
SPEC = {
    "panasonic": dict(hdr=(3456, 1728), mark=432, one=1296, zero=432, lsb=True, sections=[8, 19], gap=10000),
    "brandx": dict(hdr=(6000, 2400), mark=500, one=1500, zero=500, lsb=False, sections=[14], gap=None),
}


def frame_bytes(proto, s):
    return pana_bytes(s) if proto == "panasonic" else bx_bytes(s)


def bits_of(proto, byts):
    sp = SPEC[proto]; out = []
    for v in byts:
        rng = range(8) if sp["lsb"] else range(7, -1, -1)
        out += [(v >> i) & 1 for i in rng]
    return out


def section_bits(proto, s):
    sp = SPEC[proto]; byts = frame_bytes(proto, s); res = []; i = 0
    for n in sp["sections"]:
        res.append(bits_of(proto, byts[i:i + n])); i += n
    return res


def timings(proto, s, rng=None, jitter=0.07):
    """Raw mark/space microseconds, alternating, starting with a mark; ~7% receiver jitter, rounded to 2 us."""
    sp = SPEC[proto]; seq = []
    for k, bits in enumerate(section_bits(proto, s)):
        seq += list(sp["hdr"])
        for bit in bits:
            seq += [sp["mark"], sp["one"] if bit else sp["zero"]]
        seq.append(sp["mark"])
        if k < len(sp["sections"]) - 1:
            seq.append(sp["gap"])
    if rng:
        seq = [int(round(v * (1 + rng.uniform(-jitter, jitter)) / 2) * 2) for v in seq]
    return seq


def decode_generic(seq):
    """Decode ANY pulse-distance timing list into sections of bits (no protocol knowledge used except
    'a space > 4x the bit mark ends a section' and 'long space = 1'). Returns list of (hdr, bits)."""
    seq = [int(abs(v)) for v in seq]
    if len(seq) < 4:
        return []
    sections = []; i = 0
    while i + 1 < len(seq):
        hdr = (seq[i], seq[i + 1]); i += 2
        marks, spaces = [], []
        while i < len(seq):
            m = seq[i]; i += 1
            if i >= len(seq):
                marks.append(m); break
            sp = seq[i]; i += 1
            if sp > 6 * max(m, 1) and sp > 3000:   # section gap
                marks.append(m); break
            marks.append(m); spaces.append(sp)
        if not spaces:
            continue
        mk = sorted(marks)[len(marks) // 2]
        bits = [1 if sp > 2 * mk else 0 for sp in spaces]
        sections.append((hdr, bits))
    return sections


def matches(proto, s, seq):
    """True if a candidate timing list carries exactly the right bits with plausible header timing."""
    want = section_bits(proto, s); hdr = SPEC[proto]["hdr"]
    got = decode_generic(seq)
    if len(got) != len(want):
        return False
    for (h, bits), wb in zip(got, want):
        if bits != wb:
            return False
        if not (0.75 * hdr[0] <= h[0] <= 1.25 * hdr[0] and 0.75 * hdr[1] <= h[1] <= 1.25 * hdr[1]):
            return False
    return True


if __name__ == "__main__":
    r = random.Random(1)
    for p in SPEC:
        for _ in range(200):
            s = random_settings(r)
            assert matches(p, s, timings(p, s, r)), (p, s)
        s = dict(power="on", mode="cool", temp=24, fan="auto", vane="auto")
        print(p, " ".join(f"{v:02X}" for v in frame_bytes(p, s)), len(timings(p, s)), "pulses")
    print("self-test ok")
