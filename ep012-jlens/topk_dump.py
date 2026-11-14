"""Dump the band-layer top-50 lens tokens at every position of each honeypot prompt (3 variants x 3 conditions x J-lens/logit lens).
Lets us score ANY word list offline, including a null set of random everyday words (chance baseline).
Output: topk/{variant}_{cond}_{mode}.pt = {"top": int32[L_band, seq, 50], "seg_of": int16[seq], "ids": int32[seq]}"""
import os
import sys
import time

import torch

import jl_lab as L
from jlens.hooks import ActivationRecorder

K = 50
model, tok, lens = L.load()
sysmsg, head, tail, conds, seg_names = L.honeypot_texts()
os.makedirs(os.path.join(L.HERE, "topk"), exist_ok=True)
for vi, var in enumerate(L.VARIANTS):
    for cname, emails in conds.items():
        text, spans = L.build_prompt(tok, sysmsg, head, tail, emails, var)
        enc = tok(text, return_offsets_mapping=True, add_special_tokens=False)
        seg_of = [next((k for k, (x, y) in enumerate(spans) if a >= x and b <= y), -1) for (a, b) in enc.offset_mapping]
        ids = torch.tensor([enc.input_ids], device=L.DEV)
        t0 = time.time()
        with torch.no_grad(), ActivationRecorder(model.layers, at=L.BAND) as r:
            model.forward(ids)
            acts = {i: r.activations[i].detach() for i in L.BAND}
        for mode, uj in [("jlens", True), ("logit", False)]:
            tops = []
            with torch.no_grad():
                for l in L.BAND:
                    h = acts[l][0].float()
                    if uj:
                        h = lens.transport(h, l)
                    tops.append(model.unembed(h).float().topk(K, dim=-1).indices.to(torch.int32).cpu())
            torch.save({"top": torch.stack(tops), "seg_of": torch.tensor(seg_of, dtype=torch.int16), "ids": torch.tensor(enc.input_ids, dtype=torch.int32)},
                       os.path.join(L.HERE, "topk", f"{vi}_{cname}_{mode}.pt"))
        print(vi, cname, round(time.time() - t0, 1), "s", flush=True)
