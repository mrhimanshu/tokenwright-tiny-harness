# Classic compressors on the same slices (64 KB and 1 MB at each offset); 3 timed repeats each.
import gzip, bz2, lzma, time, zstandard, brotli, json
from common import OFFSETS, read_slice, log
tools = {"gzip -9": lambda b: gzip.compress(b, 9), "bzip2 -9": lambda b: bz2.compress(b, 9),
         "xz -9e": lambda b: lzma.compress(b, preset=9 | lzma.PRESET_EXTREME),
         "zstd -22": lambda b: zstandard.ZstdCompressor(level=22).compress(b),
         "brotli -q11": lambda b: brotli.compress(b, quality=11, lgwin=24)}
dec = {"gzip -9": gzip.decompress, "bzip2 -9": bz2.decompress, "xz -9e": lzma.decompress,
       "zstd -22": lambda c: zstandard.ZstdDecompressor().decompress(c), "brotli -q11": brotli.decompress}
for n in [65536, 1_000_000]:
    for off in OFFSETS:
        b = read_slice(off, n)
        for name, f in tools.items():
            ts = []
            for _ in range(3):
                t = time.time(); c = f(b); ts.append(time.time() - t)
            assert dec[name](c) == b
            rec = dict(method="classic", tool=name, offset=off, bytes=len(b), bytes_out=len(c), bpb=8 * len(c) / len(b),
                       seconds=min(ts), bytes_per_s=len(b) / min(ts), roundtrip=True)
            log("results.jsonl", rec); print(name, off, len(b), len(c), round(rec["bpb"], 3))
