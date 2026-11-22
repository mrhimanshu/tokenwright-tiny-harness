"""Write a copy of the official SenseNova Loop-9B GGUF with a different loop count k (same weights, byte-for-byte).
The file stores the unrolled plan: blocks 0-27 physical, the tail (physical 28-31) at blk.(28+(k-1)*24 .. ), MTP after it.
We rename only the tail/MTP block indices and set block_count, loop.count and attention.recurrent_layers.
Usage: replan_gguf.py <in.gguf> <out.gguf> <k>"""
import re, sys
sys.path.insert(0, "/tmp/ep025/snllama/gguf-py")
import gguf
from gguf.scripts.gguf_new_metadata import MetadataDetails

src, dst, k = sys.argv[1], sys.argv[2], int(sys.argv[3])
A = "sensenova_loop"
STORED, LS, LE, W = 32, 4, 28, 24
r = gguf.GGUFReader(src)
old_k = int(r.fields[f"{A}.loop.count"].contents())
old_extra, new_extra = (old_k - 1) * W, (k - 1) * W
n_new = STORED + new_extra  # executed trunk layers
recur = [(i % 4) != 3 for i in range(n_new)] + [False]  # + MTP (full attention)

w = gguf.GGUFWriter(dst, arch=A, endianess=r.endianess)
newmeta = {
    f"{A}.block_count": MetadataDetails(gguf.GGUFValueType.UINT32, n_new + 1),
    f"{A}.loop.count": MetadataDetails(gguf.GGUFValueType.UINT32, k),
}
for field in r.fields.values():
    if field.name == gguf.Keys.General.ARCHITECTURE or field.name.startswith("GGUF."):
        continue
    vt = field.types[0]
    st = field.types[-1] if vt == gguf.GGUFValueType.ARRAY else None
    if field.name in newmeta:
        w.add_key_value(field.name, newmeta[field.name].value, newmeta[field.name].type)
    elif field.name == f"{A}.attention.recurrent_layers":
        w.add_key_value(field.name, recur, vt, sub_type=st)
    else:
        w.add_key_value(field.name, field.contents(), vt, sub_type=st)


def rename(name):
    m = re.match(r"blk\.(\d+)\.(.*)", name)
    if not m:
        return name
    i = int(m.group(1))
    if i >= LE:  # tail or MTP: shift by the change in unrolled width
        i = i - old_extra + new_extra
    return f"blk.{i}.{m.group(2)}"


for t in r.tensors:
    w.add_tensor_info(rename(t.name), t.data.shape, t.data.dtype, t.data.nbytes, t.tensor_type)
w.write_header_to_file()
w.write_kv_data_to_file()
w.write_ti_data_to_file()
for t in r.tensors:
    w.write_tensor_data(t.data, tensor_endianess=r.endianess)
w.close()
print("wrote", dst, "loops", k, "block_count", n_new + 1)
