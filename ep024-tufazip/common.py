import json
ENWIK9 = "/data/projects/Tokenwright/EP024-tufazip/data/enwik9"
OFFSETS = [10_000_000, 300_000_000, 600_000_000]   # three places in the 1 GB file (n = 3)
def read_slice(off, n):
    with open(ENWIK9, "rb") as f:
        f.seek(off); b = f.read(n + 8)
    # start/end on a UTF-8 character boundary so tokenizers round-trip exactly
    s = 0
    while b[s] & 0xC0 == 0x80: s += 1
    b = b[s:s + n]
    while True:
        try: b.decode("utf-8"); return b
        except UnicodeDecodeError: b = b[:-1]
def log(path, rec):
    with open(path, "a") as f: f.write(json.dumps(rec) + "\n")
