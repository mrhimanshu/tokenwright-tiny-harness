import json, time, torch, sys
sys.argv = ["x"]
import jl_lab as L
t0 = time.time()
model, tok, lens = L.load()
print(lens, model, "load", round(time.time() - t0, 1), "s")
# 1. the README/walkthrough example
prompt = "Fact: The capital of Japan is Tokyo.\nFact: The currency used in the country shaped like a boot is"
layers = lens.source_layers
ids = model.encode(prompt)
res = {}
for mode, uj in [("jlens", True), ("logit", False)]:
    _, tops = L.readout(model, lens, ids, layers, [], use_jacobian=uj, topk_layers=tuple(layers), topk=5)
    res[mode] = {l: [tok.decode([t]) for t in tops[l][-2].tolist()] for l in layers}  # the " boot"/" is" position
for l in layers:
    print(l, "J:", res["jlens"][l], "| logit:", res["logit"][l])
json.dump(dict(prompt=prompt, position=-2, readout=res), open("smoke_boot.json", "w"), indent=1)
# 2. honeypot reconstruction check
sysmsg, head, tail, conds, segs = L.honeypot_texts()
bm = json.load(open("vendor_jlens/jlens/data/blackmail.json"))
print("reconstructs original:", head + "\n\n".join(conds["full"]) + tail == bm["user"])
for c, e in conds.items():
    text, spans = L.build_prompt(tok, sysmsg, head, tail, e, L.VARIANTS[1])
    print(c, len(tok(text).input_ids), "tokens")
print({w: [tok.decode([i]) for i in L.single_ids(tok, w)] for w in L.WATCH})
